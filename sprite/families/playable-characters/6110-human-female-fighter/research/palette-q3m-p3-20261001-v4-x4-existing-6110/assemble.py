"""Assemble existing 0x6110 x4 assets; no inference, installation or QA acceptance."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import time
import zlib

RUN = Path(__file__).resolve().parent
ROOT = next(p for p in RUN.parents if (p / "pipeline/scripts/palette_registry.py").is_file())
sys.path.insert(0, str(ROOT / "pipeline/scripts"))

import numpy as np

import palette_registry as v6
import run_creature_sprite_x2 as registry
from palette_complete import Oracle
from palette_frac_encode import dependency_mask
from palette_oracle import read_bam_p8
from palette_p2 import P1, golden
from palette_p3_catalog import record_sha, source_contract, write_v5_subset


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def relative(path):
    return Path(path).relative_to(ROOT).as_posix()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read_v5(record, *, first_only=False):
    """Read authenticated V5 bytes with the existing Windows XPRESS decoder."""
    with Path(record["path"]).open("rb") as stream:
        stream.seek(record["offset"])
        raw = stream.read(record["bytes"])
    assert len(raw) == record["bytes"] and record["storage_version"] == 5 and record["scale"] == 4
    count, cycle_count = struct.unpack_from("<II", raw, 40)
    frames, cursor = [], 48
    with registry.WindowsXpressHuffCodec(compress=False) as decoder:
        for n in range(count):
            header = raw[cursor:cursor + 528]
            geometry = struct.unpack_from("<HHhhB", header)
            stored = struct.unpack_from("<I", header, 12)[0]
            payload = raw[cursor + 528:cursor + 528 + stored]
            cursor += 528 + stored
            if first_only and n:
                continue
            w, h, *_ = geometry
            plane = decoder.decode(payload, w * h * 16) if header[9] == 1 else payload
            assert len(plane) == w * h * 16
            indices = np.frombuffer(plane, np.uint8).reshape(h * 4, w * 4).copy()
            frames.append(dict(geometry=geometry,
                representatives=np.frombuffer(header, "<u2", count=256, offset=16).copy(),
                I=indices, F=np.zeros_like(indices)))
    cycles = []
    for _ in range(cycle_count):
        slots = struct.unpack_from("<I", raw, cursor)[0]
        cursor += 4
        cycles.append(np.frombuffer(raw, "<u4", count=slots, offset=cursor).tolist())
        cursor += slots * 4
    assert cursor == len(raw)
    return dict(resref=record["resref"], source_sha256=raw[8:40].hex(), frames=frames, cycles=cycles)


def main():
    generation = RUN / "x4-existing/generation"
    destination = generation / "iee-assets/creature-sprites"
    assert not generation.exists() or not any(p.is_file() for p in generation.rglob("*")), "Use a new output"
    legacy = ROOT / "sprite/families/playable-characters/6110-human-female-fighter/family-runs/reboutcx-x4-visual-catalog-v2"
    manifest_path = legacy / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    parent_catalog = legacy / "build" / manifest["registry_catalog"]
    parent = registry.read_sealed_catalog_index(parent_catalog, manifest["registry_catalog_sha256"])
    assert parent["scale"] == 4 and len(parent["animations"]) == 1
    assert parent["animations"][0]["animation_id"] == "0x6110" and parent["animations"][0]["owner"] == 1
    experiment = json.loads((P1 / "experiment.json").read_text())
    samples = sorted((P1 / "encoded").glob("*-x4.npz"))
    assert len(samples) == 144
    target_refs = {p.stem.rsplit("_", 1)[0] for p in samples}
    assert len(target_refs) == 12
    sample_by_key = {p.stem[:-3]: p for p in samples}
    palettes, *_ = golden()
    destination.mkdir(parents=True, exist_ok=True)
    work = RUN / "work" / f"assembly-{time.time_ns()}"
    work.mkdir(parents=True)
    full_oracle = Oracle(work / "replaced-oracles", palettes)
    working_oracle = Oracle(work / "working-set-oracles", palettes)
    replacement_resources, parent_parts, all_records = [], [], {}
    sample_proofs, source_proofs, unchanged_plane_hashes = [], [], {}
    for number, shard in enumerate(parent["shards"]):
        path = parent_catalog.parent / Path(shard["registry"]).name
        info = registry.inspect_registry(path, include_resource_records=True)
        assert info["version"] == 5 and info["scale"] == 4
        for key in ("sha256", "crc32", "resource_count", "frame_count", "index_bytes", "registry_bytes"):
            assert info[key] == shard[key], (path, key)
        parent_parts.append((path, info))
        for record in info["resource_records"]:
            ref = record["resref"]
            assert ref not in all_records
            all_records[ref] = record
            if ref not in target_refs:
                resource = read_v5(record, first_only=True)
                working_oracle.append(resource)
                continue
            resource = read_v5(record)
            canonical = ROOT / experiment["sources"][ref]["canonical_bam"]
            plain = canonical.read_bytes()
            assert sha(canonical).lower() == experiment["sources"][ref]["sha256"]
            if hashlib.sha256(plain).hexdigest() != resource["source_sha256"]:
                packed = canonical.with_suffix(".bamc")
                raw = packed.read_bytes()
                assert sha(packed).lower() == resource["source_sha256"]
                assert raw[:8] == b"BAMCV1  " and struct.unpack_from("<I", raw, 8)[0] == len(plain)
                assert zlib.decompress(raw[12:]) == plain
            bam = read_bam_p8(plain)
            assert resource["cycles"] == [c["frame_indices"] for c in bam["cycles"]]
            assert len(resource["frames"]) == len(bam["frames"])
            source_proofs.append(dict(resref=ref, registry_source_sha256=resource["source_sha256"],
                canonical_bam_sha256=sha(canonical), source_content_identical=True))
            for index, frame in enumerate(resource["frames"]):
                src = bam["frames"][index]
                h, w = src["indices"].shape
                assert frame["geometry"] == (w, h, src["center_x"], src["center_y"], bam["transparent"])
                for primary in np.unique(src["indices"]):
                    position = int(frame["representatives"][primary])
                    assert position < w * h and src["indices"].flat[position] == primary
                key = f"{ref}_{index:04d}"
                if key not in sample_by_key:
                    unchanged_plane_hashes[key] = hashlib.sha256(frame["I"].tobytes()).hexdigest()
                    continue
                sample = sample_by_key[key]
                guide_path = P1 / "guides" / sample.name
                with np.load(sample, allow_pickle=False) as data, np.load(guide_path, allow_pickle=False) as guide:
                    frame.update(I=data["Q3m-k6_I"].copy(), F=data["Q3m-k6_F"].copy(),
                        dep=data["Q3m-k6_dep"].copy(), guide=guide["guide"].copy())
                # V6 reads live palette dependencies directly; a selected ramp shade
                # need not occur as a primary index in the native source pixels.
                sample_proofs.append(dict(key=key, encoded_sha256=sha(sample), guide_sha256=sha(guide_path)))
            full_oracle.append(resource)
            first = dict(resource, frames=[resource["frames"][0]])
            working_oracle.append(first)
            replacement_resources.append(resource)
        print(f"Authenticated x4 shard {number + 1}/{len(parent['shards'])}", flush=True)
    full_oracle.close_chunk()
    working_oracle.close_chunk()
    assert len(sample_proofs) == 144 and len(all_records) == 656
    assert {r["resref"] for r in replacement_resources} == target_refs

    components, shards, directory, logical = [], [], [], []
    reused, unchanged_records = 0, []

    def append_component(info, leaf):
        index = len(components)
        assert index == len(shards)
        shards.append(info)
        components.append(dict(index=index,
            digest=registry.catalog_component_digest(4, [registry.catalog_shard_entry_bytes(info, leaf)]),
            shard_start=index, shard_count=1,
            **{key: info[key] for key in ("resource_count", "frame_count", "index_bytes", "registry_bytes")}))
        logical.append(registry.catalog_source_component_sha256(4,
            sorted(info["resource_records"], key=lambda record: record["resref"])))
        for ordinal, ref in enumerate(info["resources"]):
            directory.append(dict(animation_id="0x6110", resref=ref, component_index=index,
                                  shard_index=index, resource_ordinal=ordinal))

    for source, info in parent_parts:
        residual = [r for r in info["resource_records"] if r["resref"] not in target_refs]
        if not residual:
            continue
        if len(residual) == len(info["resource_records"]):
            leaf = destination / source.name
            os.link(source, leaf)
            reused += 1
        else:
            temporary = destination / f"residual-{len(shards):04d}.part"
            info = write_v5_subset(temporary, residual, 4)
            leaf = destination / registry.catalog_shard_filename(info["sha256"])
            temporary.rename(leaf)
            info = registry.inspect_registry(leaf, include_resource_records=True)
        unchanged_records.extend(dict(resref=r["resref"], sha256=record_sha(r)) for r in info["resource_records"])
        append_component(info, leaf)

    replacement_resources.sort(key=lambda r: r["resref"])
    temporary = destination / "q3m-144.part"
    info = v6.write(temporary, 4, replacement_resources)
    leaf = destination / registry.catalog_shard_filename(info["sha256"])
    temporary.rename(leaf)
    checked = v6.inspect(leaf, include_resource_records=True, include_frames=True)
    for resource, decoded in zip(replacement_resources, checked["frame_data"], strict=True):
        assert resource["resref"] == decoded["resref"]
        assert resource["source_sha256"] == decoded["source_sha256"] and resource["cycles"] == decoded["cycles"]
        assert source_contract(all_records[resource["resref"]]) == source_contract(next(
            r for r in checked["resource_records"] if r["resref"] == resource["resref"]))
        for n, (expected, readback) in enumerate(zip(resource["frames"], decoded["frames"], strict=True)):
            assert expected["geometry"] == readback["geometry"]
            assert expected["representatives"].tobytes() == readback["representatives"].astype("<u2").tobytes()
            assert expected["I"].tobytes() == readback["I"]
            fraction = expected["F"]
            assert (fraction.tobytes() if np.any(fraction) else b"") == readback["F"]
            assert dependency_mask(expected["I"], fraction).tobytes() == readback["dep"]
            key = f"{resource['resref']}_{n:04d}"
            if key in unchanged_plane_hashes:
                assert hashlib.sha256(readback["I"]).hexdigest() == unchanged_plane_hashes[key] and not readback["F"]
    append_component(checked, leaf)
    for proof in unchanged_records:
        assert proof["sha256"] == record_sha(all_records[proof["resref"]])
    assert len(unchanged_records) == 644

    storage = dict(shard_registry_version=0, shard_registry_versions=[5, 6], frame_storage="mixed-v5-v6-components-v1")
    result = registry.write_registry_catalog_index(destination / registry.XN_REGISTRY_CATALOG_FILENAME, 4,
        [dict(animation_id="0x6110", owner=1, component_indices=list(range(len(components))))],
        components, shards, directory, logical, storage)
    assert result["total_resources"] == 656 and result["total_frames"] == 178360
    assert {r["resref"] for r in parent["directory"]} == {r["resref"] for r in directory}
    registry.inspect_registry_catalog(destination / registry.XN_REGISTRY_CATALOG_FILENAME)
    native_view = ROOT / "build/p3-6110-v4-x4-native/creature-sprites"
    assert not native_view.exists()
    native_view.mkdir(parents=True)
    for source in destination.iterdir():
        target = native_view / source.name
        os.link(source, target)
        assert source.samefile(target) and sha(source) == sha(target)

    build = dict(schema="bg2-upscale-creature-sprite-xn-catalog-pack-v1", generation_id="x4-existing-q3m144",
        registry_layout="catalog", registry_scale=4, registry_catalog_version=2,
        registry_catalog_shard_version=0, registry_catalog_shard_versions=[5, 6],
        registry_catalog_frame_storage="mixed-v5-v6-components-v1",
        registry_catalog_frame_storages=["XPRESS_HUFF-or-raw-per-frame-v1", "q3m-u8-per-plane-v1"],
        registry_catalog="iee-assets/creature-sprites/CreatureSprites-XN.catalog",
        registry_catalog_sha256=result["sha256"], registry_catalog_bytes=result["registry_catalog_bytes"],
        animation_ids=["0x6110"], shards=result["shards"])
    write_json(generation / "build-manifest.json", build)
    write_json(RUN / "x4-existing/current-generation.json", dict(
        schema="bg2-upscale-creature-sprite-xn-catalog-current-generation-v1",
        generation_id=build["generation_id"], generation_dir=relative(generation), build_manifest="build-manifest.json"))
    write_json(RUN / "x4-existing.job.json", dict(schema="bg2-upscale-creature-sprite-xn-catalog-job-v1",
        job_id=RUN.name, paths=dict(game_root="config://bg2ee_game_root", run_dir=relative(RUN / "x4-existing")),
        compatibility=dict(baldur_real_sha256="B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57")))
    write_json(RUN / "coverage.json", dict(schema="bg2-upscale-existing-x4-q3m-samples-v1", scale=4,
        animation_id="0x6110", resources=656, frames=178360, q3m_samples=144, legacy_reboutcx_frames=178216,
        v6_resources=len(replacement_resources), v6_frames=checked["frame_count"], unchanged_v5_resources=644,
        parent_manifest=relative(manifest_path), parent_manifest_sha256=sha(manifest_path),
        parent_catalog_sha256=sha(parent_catalog), catalog_sha256=result["sha256"],
        reused_shards=reused, shards=result["shard_count"], source_geometry_cycles_identical=True,
        unchanged_v5_records_byte_identical=True, non_sampled_v6_I_byte_identical=True,
        q3m_I_F_dep_byte_identical=True, source_identities=source_proofs, samples=sample_proofs,
        unchanged_records=unchanged_records,
        complete_replacement_oracles=[dict(r, path=relative(full_oracle.directory / r["path"])) for r in full_oracle.records],
        working_set_oracles=[dict(r, path=relative(working_oracle.directory / r["path"])) for r in working_oracle.records],
        native_read_view=relative(native_view),
        other_animations="native BAM while isolated x4 catalog is active", visual_qa_accepted=False,
        ingame_validated=False, boundary_mixing=False, dithering=False, inference_performed=False))
    print(json.dumps(dict(status="assembled", resources=656, frames=178360,
        q3m_samples=144, replacement_frames=checked["frame_count"], catalog_sha256=result["sha256"])), flush=True)


if __name__ == "__main__":
    main()
