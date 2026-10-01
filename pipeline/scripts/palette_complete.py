"""Complete the scoped 0x6110 Q3m K6 x2/x4 experiment; never install or accept QA."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time

import numpy as np

import palette_frac_encode as encoder
import palette_registry as v6
import run_creature_sprite_x2 as registry
from palette_oracle import read_bam_p8
from palette_p2 import P1, golden
from palette_p3 import ROOT, relative, sha, write_json
from palette_p3_catalog import derive, write_complete_x4_catalog
from reboutcx_batch import load_model, prepare_inference_rgb
from reboutcx_batch_p12 import infer_float_crops
from reboutcx_cache_p12 import frame_key
from reboutcx_multipal import inference_context, save_npz
from workspace_paths import get_path


def independent_lut(palettes):
    """Scalar class intervals and arithmetic, independent of the encoder decoder."""
    result = np.empty((len(palettes), 256, 8, 4), np.uint8)
    for n in range(256):
        terminal = n < 4 or (n < 88 and (n - 4) % 12 == 11) or (n >= 88 and (n - 88) % 8 == 7)
        successor = n if terminal else n + 1
        for f in range(8):
            for p, palette in enumerate(palettes):
                for c in range(3):
                    result[p, n, f, c] = ((8 - f) * int(palette[n, c]) + f * int(palette[successor, c]) + 4) // 8
                result[p, n, f, 3] = palette[n, 3]
    return result


class Oracle:
    """Bounded native-test chunks; complete frame tables including unreferenced frames."""
    def __init__(self, directory, palettes):
        self.directory, self.palettes = directory, palettes
        directory.mkdir()
        self.lut = independent_lut(palettes)
        self.records, self.count, self.stream = [], 0, None

    def close_chunk(self):
        if self.stream is not None:
            self.stream.seek(12); self.stream.write(struct.pack("<I", self.count))
            self.stream.close()
            self.records.append(dict(path=self.path.name, frames=self.count, sha256=sha(self.path)))
            self.stream = None

    def append(self, resource):
        lookup = {}
        for sequence, cycle in enumerate(resource["cycles"]):
            for slot, index in enumerate(cycle):
                lookup.setdefault(index, (sequence, slot))
        if not lookup:
            raise ValueError("Source has no native cycle slots")
        fallback = next(iter(lookup.values()))
        for index, frame in enumerate(resource["frames"]):
            if self.stream is None or self.count == 60000:
                self.close_chunk()
                self.count = 0
                self.path = self.directory / f"decoder-oracle-{len(self.records):02d}.bin"
                self.stream = self.path.open("xb")
                self.stream.write(struct.pack("<8sII", b"IEEQ3P1\0", len(self.palettes), 0))
                self.stream.write(self.palettes.tobytes())
            sequence, slot = lookup.get(index, fallback)
            if index not in lookup:
                sequence |= 0x80000000
            i, f = frame["I"], frame["F"]
            self.stream.write(struct.pack("<8s4I", resource["resref"].encode().ljust(8, b"\0"),
                                          index, sequence, slot, i.size))
            for p in range(len(self.palettes)):
                self.stream.write(hashlib.sha256(self.lut[p, i, f].tobytes()).digest())
            self.count += 1


class PixelProcessor:
    def __init__(self, output, fitting, context, workers, scale=2):
        import torch
        from chainner_ext import ResizeFilter, resize
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.set_num_threads(4)
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True)
        if scale not in (2, 4):
            raise ValueError("Unsupported Q3m scale")
        self.output, self.fitting, self.scale = output, fitting, scale
        self.identity = hashlib.sha256(json.dumps(context, sort_keys=True).encode() + fitting.tobytes()
            + (b"/direct-x4" if scale == 4 else b"")).digest()
        self.descriptor, self.versions = load_model(get_path("reboutcx_model", required=True), device="cuda:0", fp16=True)
        self.resize, self.box = resize, ResizeFilter.Box
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.stats = Counter()
        self.scalepix = get_path("mmpx_scalepix", required=True)
        self.cache = output / "work/encoded"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.p1_targets = json.loads((P1 / "target-index.json").read_text())["references"]
        self.p1_frames = json.loads((P1 / "experiment.json").read_text())["frames"]

    def key(self, frame):
        return frame_key(frame, None, self.identity).hex()

    def path(self, frame):
        return self.cache / (self.key(frame) + ".npz")

    def encode(self, key, guide, targets):
        encoded = encoder.encode_variants(guide, targets, self.fitting, ks=(6,))["Q3m-k6"]
        save_npz(self.cache / (key + ".npz"), guide=guide, I=encoded["I"], F=encoded["F"], dep=encoded["dep_mask"])

    def process(self, frames):
        unique = {}
        for frame in frames:
            key = self.key(frame)
            if not (self.cache / (key + ".npz")).exists():
                unique.setdefault(key, frame)
        self.stats["logical_frames"] += len(frames)
        self.stats["new_pixel_keys"] += len(unique)
        guides, pending = {}, {}
        for key, frame in unique.items():
            if prepare_inference_rgb(frame, self.fitting[0]) is None or (frame.indices.shape == (1, 1) and int(frame.indices[0, 0]) == 2):
                guide = np.repeat(np.repeat(frame.indices, self.scale, 0), self.scale, 1)
                save_npz(self.cache / (key + ".npz"), guide=guide, I=guide, F=np.zeros_like(guide),
                         dep=encoder.dependency_mask(guide, np.zeros_like(guide)))
                self.stats["special_pixel_keys"] += 1
            else:
                pending[key] = frame
        keys = list(pending)
        for start in range(0, len(keys), 64):
            selected = keys[start:start + 64]
            outputs = registry.run_xbr([pending[k] for k in selected], self.scalepix, "node", registry.direct_upscale_contract(self.scale))
            for key, (w, h, rgba) in zip(selected, outputs, strict=True):
                frame = pending[key]
                provenance = registry.xbr_provenance_indices(frame, self.scale) if registry.has_duplicate_used_rgba_indices(frame) else None
                guide, _ = registry.map_output(frame, rgba, provenance)
                guides[key] = guide.reshape(h, w)
        groups = defaultdict(list)
        for key, frame in pending.items():
            canvas = ((frame.height + 31) // 32 * 32, (frame.width + 31) // 32 * 32)
            groups[canvas].extend((key, frame, p) for p in range(6))
        completed, tasks = {}, []
        names = ["REF", "DEFAULT", "LATIN1", "LATIN2", "LATIN3", "LATIN4"]
        for canvas, requests in sorted(groups.items()):
            for start in range(0, len(requests), 86):
                batch = requests[start:start + 86]
                rgb = [prepare_inference_rgb(frame, self.fitting[p]) for _, frame, p in batch]
                crops, _ = infer_float_crops(self.descriptor, rgb, canvas=canvas, fp16=True)
                self.stats["neural_targets"] += len(batch)
                for (key, frame, p), crop in zip(batch, crops, strict=True):
                    pixels = crop if self.scale == 4 else self.resize(crop, (frame.width * 2, frame.height * 2), self.box, False)
                    target = np.ascontiguousarray(np.clip(pixels, 0, 1), dtype=np.float32)
                    original_key = f"{frame.resref}_{frame.index:04d}"
                    if original_key in self.p1_frames:
                        with np.load(P1 / self.p1_targets[names[p]][original_key], allow_pickle=False) as expected:
                            if not np.array_equal(target, expected[f"x{self.scale}"]):
                                raise ValueError(f"Fixed86 inference changed the P1 target: {original_key}/{names[p]}")
                        self.stats["p1_targets_bit_exact"] += 1
                    targets = completed.setdefault(key, {})
                    targets[p] = target
                    if len(targets) == 6:
                        tasks.append(self.pool.submit(self.encode, key, guides.pop(key), np.stack([targets[n] for n in range(6)])))
                        del completed[key]
                    if len(tasks) >= 16:
                        tasks.pop(0).result()
        for task in tasks:
            task.result()
        if completed or guides:
            raise ValueError("Incomplete six-palette encoding batch")


def source_frames(ref, bam):
    result = []
    if bam["transparent"] != 0:
        raise ValueError("Character V6 requires source transparency index 0")
    for frame in bam["frames"]:
        i = frame["indices"]
        h, w = i.shape
        if not h or not w or i.size >= 65535:
            raise ValueError(f"Unsupported source geometry: {ref}/{frame['index']}")
        rgba = np.empty((h, w, 4), np.uint8)
        rgba[:, :, :3] = bam["palette_rgb"][i]
        rgba[:, :, 3] = np.where(i == 0, 0, 255)
        result.append(registry.SourceFrame(ref, frame["index"], w, h, frame["center_x"], frame["center_y"],
                                           0, i, bam["palette_rgb"], rgba.tobytes()))
    return result


def verify_inference_context(context, frozen):
    if context == frozen:
        return dict(identical=True)
    comparable = json.loads(json.dumps(context))
    comparable["kernels"]["reboutcx_batch.py"] = frozen["kernels"]["reboutcx_batch.py"]
    if comparable != frozen:
        raise ValueError("P1 model/inference environment changed")
    # P0 added native MPALETTE alias validation after P1. That job loader is
    # not invoked here; require every other AST node to remain identical.
    previous = subprocess.check_output(["git", "show", "a810a779^:pipeline/scripts/reboutcx_batch.py"], cwd=ROOT)
    if hashlib.sha256(previous).hexdigest() != frozen["kernels"]["reboutcx_batch.py"]:
        raise ValueError("Frozen P1 kernel revision changed")
    current = (ROOT / "pipeline/scripts/reboutcx_batch.py").read_bytes()
    def pixel_ast(raw):
        tree = ast.parse(raw.decode("utf-8"))
        tree.body = [n for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name == "load_palette_profiles")]
        return ast.dump(tree, include_attributes=False)
    if pixel_ast(previous) != pixel_ast(current):
        raise ValueError("P1 pixel inference code changed")
    return dict(identical=False, only_changed_function="load_palette_profiles", other_ast_nodes_identical=True,
                p1_sha256=frozen["kernels"]["reboutcx_batch.py"], current_sha256=context["kernels"]["reboutcx_batch.py"])


def complete(output, parent_pointer, runtime_source, workers, resume=False, scale=2):
    started = time.monotonic()
    if scale not in (2, 4):
        raise ValueError("Unsupported Q3m scale")
    if output.exists() and (not resume or (output / "coverage.json").exists()):
        raise ValueError("Use a new full experiment; prior runs remain immutable")
    pointer = json.loads(parent_pointer.read_text())
    parent_manifest_path = ROOT / pointer["generation_dir"] / pointer["build_manifest"]
    if sha(parent_manifest_path).upper() != pointer["build_manifest_sha256"].upper():
        raise ValueError("Pinned parent manifest changed")
    parent_manifest = json.loads(parent_manifest_path.read_text())
    parent_catalog = parent_manifest_path.parent / parent_manifest["registry_catalog"]
    parent = registry.read_sealed_catalog_index(parent_catalog, pointer["catalog_sha256"])
    refs = sorted(r["resref"] for r in parent["directory"] if r["animation_id"] == "0x6110")
    with (ROOT / "sprite/index/extractions.csv").open(encoding="utf-8-sig") as stream:
        sources = {r["bam_resref"]: r for r in csv.DictReader(stream) if r["bam_resref"] in refs}
    if len(refs) != 656 or set(sources) != set(refs):
        raise ValueError("Incomplete pinned 0x6110 source coverage")
    experiment = json.loads((P1 / "experiment.json").read_text())
    context = inference_context()
    kernel_compatibility = verify_inference_context(context, experiment["inference"])
    palettes = golden()[0]
    fitting = palettes[:6, :, :3].copy()
    fitting[:, 0] = (0, 255, 0)  # Exact neutral source palette; Realize clears entry 0 only at decode.
    output.mkdir(parents=True, exist_ok=True)
    recipe = dict(animation_id="0x6110", scale=scale, method="Q3m", k=6,
        boundary_mixing=False, dithering=False, inference=context, kernel_compatibility=kernel_compatibility,
        palettes=experiment["palettes"][:6],
        parent_catalog_sha256=sha(parent_catalog), source_sha256={r:sources[r]["canonical_sha256"] for r in refs})
    if (output / "recipe.json").exists():
        if json.loads((output / "recipe.json").read_text()) != recipe:
            raise ValueError("Working run recipe changed")
    else:
        write_json(output / "recipe.json", recipe)
    (output / ".gitignore").write_text("candidate/\nwork/\ncaptures/\ningame-runtime/\n*/generation/iee-assets/\n*/ingame-installation/\nactive-session.json\n", encoding="utf-8")
    (output / ".gitattributes").write_text("*.json -text whitespace=cr-at-eol\n", encoding="utf-8")
    processor = PixelProcessor(output, fitting, context, workers, scale)
    leaves = output / "work/leaves"; leaves.mkdir(exist_ok=True)
    oracle_directory = output / "work/oracles"
    if oracle_directory.exists():
        oracle_directory = output / "work" / f"oracles-{time.time_ns()}"
    oracle = Oracle(oracle_directory, palettes)
    working_oracle = Oracle(output / "work" / f"working-set-{time.time_ns()}", palettes) if scale == 4 else None
    first_resource = None
    reports, replacements, canonical_sources, p1_checked = [], [], {}, set()
    try:
        for number, ref in enumerate(refs, 1):
            source = sources[ref]
            canonical = ROOT / source["canonical_file"]
            if sha(canonical).upper() != source["canonical_sha256"].upper():
                raise ValueError(f"Canonical source changed: {ref}")
            canonical_sources[ref] = canonical
            bam = read_bam_p8(canonical.read_bytes())
            frames = source_frames(ref, bam)
            processor.process(frames)
            records = []
            for frame in frames:
                with np.load(processor.path(frame), allow_pickle=False) as encoded:
                    guide, i, f, dep = [encoded[n].copy() for n in ("guide", "I", "F", "dep")]
                encoder.check_contract(guide, i, f, dep)
                key = f"{ref}_{frame.index:04d}"
                if key in experiment["frames"]:
                    with np.load(P1 / "encoded" / (key + f"-x{scale}.npz"), allow_pickle=False) as expected:
                        if any(not np.array_equal(value, expected["Q3m-k6_" + name]) for name, value in (("I", i), ("F", f), ("dep", dep))):
                            raise ValueError(f"Full encoding changed frozen P1 bytes: {key}")
                    p1_checked.add(key)
                representatives = np.full(256, 65535, np.uint16)
                values, offsets = np.unique(frame.indices, return_index=True)
                representatives[values] = offsets
                records.append(dict(geometry=(frame.width, frame.height, frame.center_x, frame.center_y, 0),
                                    representatives=representatives, guide=guide, I=i, F=f, dep=dep))
            resource = dict(resref=ref, source_sha256=source["canonical_sha256"], frames=records,
                            cycles=[c["frame_indices"] for c in bam["cycles"]])
            leaf = leaves / f"{ref}.registry"
            if leaf.exists():
                info = v6.inspect(leaf)
            else:
                leaf.with_suffix(".registry.part").unlink(missing_ok=True)
                info = v6.write(leaf, scale, [resource])
            if info["scale"] != scale:
                raise ValueError("Working shard scale changed")
            readback = v6.inspect(leaf, include_frames=True)["frame_data"][0]
            if readback["cycles"] != resource["cycles"] or readback["source_sha256"] != source["canonical_sha256"].lower():
                raise ValueError(f"Source/cycles roundtrip changed: {ref}")
            for a, b in zip(records, readback["frames"], strict=True):
                if (a["geometry"] != b["geometry"] or not np.array_equal(a["representatives"], b["representatives"]) or
                    a["I"].tobytes() != b["I"] or (a["F"].tobytes() if np.any(a["F"]) else b"") != b["F"]):
                    raise ValueError(f"Plane/geometry roundtrip changed: {ref}")
            oracle.append(resource)
            if working_oracle is not None:
                first = dict(resource, frames=records[:1])
                working_oracle.append(first)
                if first_resource is None:
                    first_resource = first
            replacements.append(leaf)
            reports.append(dict(resref=ref, frames=len(records), source_sha256=source["canonical_sha256"],
                registry_sha256=info["sha256"], registry_bytes=info["registry_bytes"],
                fractional_frames=info["fractional_frame_count"], fraction_bytes=info["fraction_bytes"],
                fractional_pixels=sum(int(np.count_nonzero(f["F"])) for f in records),
                decoded_pixels=sum(int(f["I"].size) for f in records), roundtrip_identical=True))
            print(f"complete {number}/{len(refs)} {ref} frames={len(records)} fractional={info['fractional_frame_count']} elapsed={time.monotonic()-started:.1f}s", flush=True)
    finally:
        oracle.close_chunk()
        if working_oracle is not None:
            if first_resource is not None:
                working_oracle.append(first_resource)
            working_oracle.close_chunk()
        processor.pool.shutdown(wait=True)
    if p1_checked != set(experiment["frames"]):
        raise ValueError("Frozen P1 sample coverage changed")
    label = f"x{scale}-q3m-k6"
    generation = output / label / "generation"
    assets = generation / "iee-assets/creature-sprites"
    if scale == 2:
        info, preservation = derive(parent_catalog, parent_manifest, replacements, assets, canonical_sources=canonical_sources)
    else:
        info, preservation = write_complete_x4_catalog(replacements, assets, expected_resrefs=refs)
    write_json(generation / "preservation.json", preservation)
    build = dict(schema="bg2-upscale-creature-sprite-xn-catalog-pack-v1", generation_id=label,
        registry_layout="catalog", registry_scale=scale, registry_catalog_version=2,
        registry_catalog_shard_version=0 if scale == 2 else 6,
        registry_catalog_shard_versions=[5, 6] if scale == 2 else [6],
        registry_catalog_frame_storage="mixed-v5-v6-components-v1" if scale == 2 else "q3m-u8-per-plane-v1",
        registry_catalog_frame_storages=["XPRESS_HUFF-or-raw-per-frame-v1", "q3m-u8-per-plane-v1"] if scale == 2 else ["q3m-u8-per-plane-v1"],
        registry_catalog="iee-assets/creature-sprites/CreatureSprites-XN.catalog",
        registry_catalog_sha256=info["sha256"], registry_catalog_bytes=info["registry_catalog_bytes"],
        animation_ids=[a["animation_id"] for a in info["animations"]], shards=info["shards"],
        registry_catalog_logical_component_digests=info["logical_component_digests"],
        registry_catalog_logical_content_sha256=info["logical_content_sha256"], storage={k:info[k] for k in
        ("shard_registry_versions" if scale == 2 else "shard_registry_version", "frame_storage", "stored_index_bytes", "compressed_frame_count", "raw_frame_count")})
    build[f"required_q3m_x{scale}_decoded_shard_bytes"] = max(r["decoded_pixels"]+r["fraction_bytes"] for r in reports)
    write_json(generation / "build-manifest.json", build)
    write_json(output / label / "current-generation.json", dict(
        schema="bg2-upscale-creature-sprite-xn-catalog-current-generation-v1", generation_id=label,
        generation_dir=relative(generation), build_manifest="build-manifest.json"))
    runtime = json.loads(runtime_source.read_text())
    dll = ROOT / runtime["dll"]["path"]
    if sha(dll) != runtime["dll"]["sha256"]:
        raise ValueError("Verified P3 DLL changed")
    (output / "candidate").mkdir()
    target = output / "candidate/InfinityEngine-Enhancer.dll"; shutil.copyfile(dll, target)
    runtime["runtime_id"] = output.name; runtime["dll"]["path"] = relative(target)
    write_json(output / "runtime.json", runtime)
    write_json(output / f"{label}.job.json", dict(schema="bg2-upscale-creature-sprite-xn-catalog-job-v1",
        job_id=f"{output.name}-{label}", paths=dict(game_root="config://bg2ee_game_root", run_dir=relative(output / label)),
        compatibility=dict(baldur_real_sha256=runtime["game_profile"]["baldur_real_sha256"])))
    write_json(output / "session.json", dict(schema="bg2-upscale-character-palette-p3-session-v1", status="prepared",
        animation_id="0x6110", scale=scale, method="Q3m", k=6, boundary_mixing=False, filter="Nearest",
        resources=len(reports), frames=sum(r["frames"] for r in reports), runtime_dll_sha256=sha(target),
        ingame_validated=False, visual_qa_accepted=False))
    write_json(output / "coverage.json", dict(schema="bg2-upscale-character-palette-complete-v1", status="generated-not-native-verified",
        resources=reports, resource_count=len(reports), frames=sum(r["frames"] for r in reports),
        decoded_pixels=sum(r["decoded_pixels"] for r in reports), fractional_pixels=sum(r["fractional_pixels"] for r in reports),
        p1_samples_byte_identical=len(p1_checked), processing=dict(processor.stats),
        oracle_directory=relative(oracle_directory), oracles=oracle.records,
        catalog_sha256=info["sha256"], parent_shards_reused=preservation["parent_shards_reused"],
        shards=info["shard_count"], unrelated_routes_identical=preservation["unrelated_routes_identical"],
        elapsed_seconds=time.monotonic()-started, visual_qa_accepted=False))
    if working_oracle is not None:
        write_json(output / "working-set-oracles.json", dict(directory=relative(working_oracle.directory), oracles=working_oracle.records,
            resources=len(reports), first_BAM_repeated=True))
    print(json.dumps(dict(status="generated", run=relative(output), frames=sum(r["frames"] for r in reports))), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--parent-pointer", type=Path, default=ROOT / "sprite/catalogs/creature-x2-reboutcx/runs/catalog-reboutcx-playable-characters-p13-v1/current-generation.json")
    parser.add_argument("--runtime", type=Path, default=P1.parent / "palette-q3m-p3-20261001-v2/runtime.json")
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=4)
    parser.add_argument("--scale", type=int, choices=(2, 4), default=2)
    parser.add_argument("--resume", action="store_true", help="Resume an unsealed working run with the same recipe")
    args = parser.parse_args()
    complete(args.output.resolve(), args.parent_pointer.resolve(), args.runtime.resolve(), args.workers, args.resume, args.scale)
