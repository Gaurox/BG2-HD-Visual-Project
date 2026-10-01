"""Derive a scoped P3 catalog, preserving parent records outside replacements."""
from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import struct
import zlib

import palette_registry as v6
import run_creature_sprite_x2 as registry


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def record_sha(record):
    with Path(record["path"]).open("rb") as stream:
        stream.seek(record["offset"])
        raw = stream.read(record["bytes"])
    if len(raw) != record["bytes"]:
        raise ValueError("Truncated parent record")
    return hashlib.sha256(raw).hexdigest().upper()


def source_contract(record):
    """Geometry/source/lookup only; physical codecs and pixels may differ."""
    with Path(record["path"]).open("rb") as stream:
        stream.seek(record["offset"])
        raw = stream.read(record["bytes"])
    frames, cycles = struct.unpack_from("<II", raw, 40)
    cursor, geometries = 48, []
    fractional = record["storage_version"] == 6
    for _ in range(frames):
        geometries.append(struct.unpack_from("<HHhhB", raw, cursor))
        stored_i = struct.unpack_from("<I", raw, cursor + 12)[0]
        stored_f = struct.unpack_from("<I", raw, cursor + 560)[0] if fractional else 0
        cursor += (568 if fractional else 528) + stored_i + stored_f
    return raw[:48], geometries, raw[cursor:]


def write_v5_subset(path, records, scale):
    """Copy already authenticated V5 records byte for byte; no recompression."""
    if path.exists() or not records or any(r["storage_version"] != 5 for r in records):
        raise ValueError("V5 subset requires new output and V5 source records")
    with path.open("xb") as stream:
        stream.write(struct.pack("<8s4I", registry.XN_REGISTRY_MAGIC, 5, scale,
                                 len(records), registry.CATALOG_SHARD_ANIMATION_SENTINEL))
        for record in records:
            registry._copy_registry_record(stream, record)
    info = registry.inspect_registry(path, include_resource_records=True)
    if [record_sha(r) for r in records] != [record_sha(r) for r in info["resource_records"]]:
        raise ValueError("V5 subset changed parent record bytes")
    return info


def derive(parent_catalog, parent_manifest, replacement_leaf, destination, *, animation="0x6110", canonical_sources=None):
    """Reuse all parent components; split only the targeted animation memberships."""
    if destination.exists():
        raise ValueError("Use a new catalog output directory")
    parent = registry.read_sealed_catalog_index(parent_catalog, parent_manifest["registry_catalog_sha256"])
    if parent["scale"] != 2 or parent_manifest["storage"]["shard_registry_version"] != 5:
        raise ValueError("P3 parent must be the complete V5 x2 catalog")
    leaves = ([Path(replacement_leaf)] if isinstance(replacement_leaf, (str, Path))
              else [Path(p) for p in replacement_leaf])
    parts = [(leaf, v6.inspect(leaf, include_resource_records=True)) for leaf in leaves]
    if not parts or any(info["scale"] != 2 for _, info in parts):
        raise ValueError("P3 replacement must be x2")
    replacement_records = {r["resref"]: r for _, info in parts for r in info["resource_records"]}
    if len(replacement_records) != sum(len(info["resources"]) for _, info in parts):
        raise ValueError("Duplicate replacement resource across V6 leaves")
    targets = set(replacement_records)
    old_animation = next(a for a in parent["animations"] if a["animation_id"] == animation)
    if old_animation["owner"] != 1:
        raise ValueError("P3 replacement requires Character ownership")
    old_rows = [r for r in parent["directory"] if r["animation_id"] == animation]
    if not targets.issubset({r["resref"] for r in old_rows}):
        raise ValueError("Replacement adds an unknown parent resource")
    affected = sorted({r["component_index"] for r in old_rows if r["resref"] in targets})
    # This experiment deliberately leaves shared parent components untouched.
    if any(not any(a["animation_id"] != animation and c in a["component_indices"]
                   for a in parent["animations"]) for c in affected):
        raise ValueError("Unshared affected component requires explicit pruning")
    destination.mkdir(parents=True)
    components, shards = copy.deepcopy(parent["components"]), copy.deepcopy(parent["shards"])
    logical = list(parent_manifest["registry_catalog_logical_component_digests"])
    if len(logical) != len(components):
        raise ValueError("Parent logical component inventory differs")
    for shard in shards:
        source = parent_catalog.parent / Path(shard["registry"]).name
        if source.stat().st_size != shard["registry_bytes"] or sha(source) != shard["sha256"]:
            raise ValueError(f"Parent shard changed: {source}")
        os.link(source, destination / source.name)

    def append_component(info, leaf, digest):
        index, shard_index = len(components), len(shards)
        entry = {key: info[key] for key in ("sha256", "crc32", "resource_count", "frame_count", "index_bytes", "registry_bytes")}
        entry.update(index=shard_index, registry="iee-assets/creature-sprites/" + leaf.name)
        shards.append(entry)
        components.append(dict(index=index, digest=registry.catalog_component_digest(2, [registry.catalog_shard_entry_bytes(info, leaf)]),
            shard_start=shard_index, shard_count=1, **{key: info[key] for key in ("resource_count", "frame_count", "index_bytes", "registry_bytes")}))
        logical.append(digest)
        return index, [dict(animation_id=animation, resref=ref, component_index=index,
                            shard_index=shard_index, resource_ordinal=n) for n, ref in enumerate(info["resources"])]

    new_memberships, new_rows, residual_proofs, source_aliases = [], [], [], []
    extra_storage = dict(stored_index_bytes=0, compressed_frame_count=0, raw_frame_count=0)
    for c in affected:
        component = components[c]
        records = []
        for s in shards[component["shard_start"]:component["shard_start"] + component["shard_count"]]:
            info = registry.inspect_registry(destination / Path(s["registry"]).name, include_resource_records=True)
            records.extend(info["resource_records"])
        records.sort(key=lambda r: r["resref"])
        for record in records:
            if record["resref"] not in targets:
                continue
            old, new = source_contract(record), source_contract(replacement_records[record["resref"]])
            if old[1:] != new[1:] or old[0][:8] + old[0][40:] != new[0][:8] + new[0][40:]:
                raise ValueError(f"Replacement source/geometry/cycles differ: {record['resref']}")
            if old[0][8:40] != new[0][8:40]:
                # Legacy provenance hashes the compressed source BAMC; P1/P2
                # hashes its canonical BAM. Accept only an exact decoding proof.
                canonical = Path((canonical_sources or {}).get(record["resref"], ""))
                packed = canonical.with_suffix(".bamc")
                if not canonical.is_file() or not packed.is_file():
                    raise ValueError("Source identities differ without a BAMC/BAM equivalence proof")
                raw, plain = packed.read_bytes(), canonical.read_bytes()
                if (sha(packed) != old[0][8:40].hex().upper() or sha(canonical) != new[0][8:40].hex().upper()
                        or raw[:8] != b"BAMCV1  " or len(plain) != struct.unpack_from("<I", raw, 8)[0]
                        or zlib.decompress(raw[12:]) != plain):
                    raise ValueError("BAMC/BAM source content differs")
                source_aliases.append(dict(resref=record["resref"], legacy_bamc_sha256=sha(packed),
                    canonical_bam_sha256=sha(canonical), decoded_content_identical=True))
        residual = [r for r in records if r["resref"] not in targets]
        if residual:
            temporary = destination / f"residual-{c}.part"
            info = write_v5_subset(temporary, residual, 2)
            leaf = destination / registry.catalog_shard_filename(info["sha256"])
            temporary.rename(leaf)
            info = registry.inspect_registry(leaf, include_resource_records=True)
            index, rows = append_component(info, leaf, registry.catalog_source_component_sha256(2, info["resource_records"]))
            new_memberships.append(index); new_rows.extend(rows)
            residual_proofs.extend(dict(resref=r["resref"], sha256=record_sha(r)) for r in residual)
            for key in extra_storage:
                extra_storage[key] += info[key]
    for source_leaf, replacement in parts:
        leaf = destination / registry.catalog_shard_filename(replacement["sha256"])
        os.link(source_leaf, leaf)
        index, rows = append_component(replacement, leaf, registry.catalog_source_component_sha256(2, replacement["resource_records"]))
        new_memberships.append(index); new_rows.extend(rows)
    animations = copy.deepcopy(parent["animations"])
    selected = next(a for a in animations if a["animation_id"] == animation)
    selected["component_indices"] = sorted([c for c in old_animation["component_indices"] if c not in affected] + new_memberships)
    directory = [copy.deepcopy(r) for r in parent["directory"]
                 if r["animation_id"] != animation or r["component_index"] not in affected] + new_rows
    storage = dict(shard_registry_version=0, shard_registry_versions=[5, 6],
        frame_storage="mixed-v5-v6-components-v1",
        **{key: parent_manifest["storage"][key] + extra_storage[key] +
           sum(info[key] for _, info in parts) for key in extra_storage})
    result = registry.write_registry_catalog_index(destination / registry.XN_REGISTRY_CATALOG_FILENAME,
        2, animations, components, shards, directory, logical, storage)
    sealed = registry.read_sealed_catalog_index(destination / registry.XN_REGISTRY_CATALOG_FILENAME, result["sha256"])
    old_keys = {(r["animation_id"], r["resref"]) for r in parent["directory"]}
    if old_keys != {(r["animation_id"], r["resref"]) for r in sealed["directory"]}:
        raise ValueError("Derived catalog changed animation/resource coverage")
    old_routes = {(r["animation_id"], r["resref"]): r for r in parent["directory"]}
    for row in sealed["directory"]:
        if row["animation_id"] != animation and row != old_routes[(row["animation_id"], row["resref"])]:
            raise ValueError("Derived catalog changed another actor route")
    for a in sealed["animations"]:
        old = next(v for v in parent["animations"] if v["animation_id"] == a["animation_id"])
        if a["owner"] != old["owner"] or (a["animation_id"] != animation and a != old):
            raise ValueError("Derived catalog changed unrelated memberships")
    return result, dict(parent_catalog_sha256=sha(parent_catalog), target_animation=animation,
        unchanged_animations=len(animations) - 1, target_resource_count=len(old_rows),
        replaced_resrefs=sorted(targets), residual_records=residual_proofs,
        parent_shards_reused=len(parent["shards"]), new_shards=len(shards) - len(parent["shards"]),
        coverage_identical=True, unrelated_routes_identical=True, residual_record_bytes_identical=True,
        replacement_source_content_geometry_cycles_identical=True, source_identity_aliases=source_aliases)
