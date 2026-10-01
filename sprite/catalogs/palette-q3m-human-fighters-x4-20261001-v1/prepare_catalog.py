"""Merge the two native-verified Q3m x4 packs without changing any V6 byte."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

RUN = Path(__file__).resolve().parent
ROOT = next(p for p in RUN.parents if (p / "pipeline/scripts/ThinInstall.ps1").is_file())
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import run_creature_sprite_x2 as registry

MALE = ROOT / "sprite/families/playable-characters/6100-human-male-fighter/research/palette-q3m-series-20261001-v1"
FEMALE = ROOT / "sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p3-20261001-v5-full-x4-6110"
GENERATION = RUN / "generation"
ASSETS = GENERATION / "iee-assets/creature-sprites"
VIEW = ROOT / "sprite/.work/q3m-human-fighters-x4-20261001-v1"
GENERATION_ID = RUN.name


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def relative(path):
    return Path(path).relative_to(ROOT).as_posix()


def main():
    assert not GENERATION.exists() and not VIEW.exists(), "Use a new immutable run"
    male_proof = read(MALE / "x4-verification.json")
    female_proof = read(FEMALE / "verification.json")
    male_metadata = read(ROOT / "sprite/.work/q3m-6100-20261001-v1/x4/pack.json")["catalog"]
    female_metadata = read(FEMALE / "x4-q3m-k6/generation/build-manifest.json")
    male_control = read(MALE / "native-control.json")
    female_working = next(r for r in female_proof["native_pack_tests"] if r["group"] == "working-set")
    male_working = next(r for r in male_proof["native_pack_tests"] if r["group"] == "working-set")
    sources = [
        dict(animation="0x6100", frames=180337, proof=male_proof,
             proof_path=MALE / "x4-verification.json",
             catalog=ROOT / male_proof["catalog"] / registry.XN_REGISTRY_CATALOG_FILENAME,
             logical=male_metadata["logical_component_digests"],
             executable=ROOT / male_control["executable"], executable_sha=male_control["executable_sha256"],
             oracle=MALE / "x4-working-set-oracles" / male_working["oracle"]["path"],
             oracle_sha=male_working["oracle"]["sha256"]),
        dict(animation="0x6110", frames=178360, proof=female_proof,
             proof_path=FEMALE / "verification.json",
             catalog=FEMALE / "x4-q3m-k6/generation" / female_metadata["registry_catalog"],
             logical=female_metadata["registry_catalog_logical_component_digests"],
             executable=ROOT / "build/palette-q3m-p3-20261001-v5-x4/cmake/Release/iee_palette_fraction_tests.exe",
             executable_sha=female_proof["native_test_executable_sha256"],
             oracle=ROOT / "build/p3-6110-v5-x4-native/oracles/working-set-0.bin",
             oracle_sha=female_working["oracle"]["sha256"]),
    ]
    for source in sources:
        proof = source["proof"]
        assert proof["status"] == "passed-offline-ready-for-manual-game"
        assert (proof["animation_id"], proof["scale"], proof["method"], proof["k"], proof["frames"], proof["resource_count"]) == (
            source["animation"], 4, "Q3m", 6, source["frames"], 656)
        assert not proof["boundary_mixing"] and not proof["dithering"]
        assert sha(source["catalog"]) == proof["catalog_sha256"].upper()
        source["index"] = registry.read_sealed_catalog_index(source["catalog"], proof["catalog_sha256"])
        index = source["index"]
        assert index["scale"] == 4 and index["total_resources"] == 656 and index["total_frames"] == source["frames"]
        assert [a["animation_id"] for a in index["animations"]] == [source["animation"]]
        assert index["animations"][0]["owner"] == 1
        assert len(source["logical"]) == len(index["components"])
        assert sha(source["executable"]) == source["executable_sha"].upper()
        assert sha(source["oracle"]) == source["oracle_sha"].upper()

    ASSETS.mkdir(parents=True)
    VIEW.mkdir(parents=True)
    (RUN / "captures").mkdir()
    animations, components, shards, directory, logical = [], [], [], [], []
    by_digest, bindings = {}, []
    for source in sources:
        index = source["index"]
        component_map, shard_map = {}, {}
        for old in index["components"]:
            old_index = old["index"]
            assert old["shard_count"] == 1, "This scoped merge expects one native BAM per component"
            old_shard_index = old["shard_start"]
            shard = index["shards"][old_shard_index]
            original = source["catalog"].parent / Path(shard["registry"]).name
            assert original.stat().st_size == shard["registry_bytes"] and sha(original) == shard["sha256"].upper()
            with original.open("rb") as stream:
                magic, version, scale, count, owner = struct.unpack("<8s4I", stream.read(24))
            assert magic == registry.XN_REGISTRY_MAGIC and (version, scale, count, owner) == (
                6, 4, 1, registry.CATALOG_SHARD_ANIMATION_SENTINEL)
            digest = old["digest"]
            if digest in by_digest:
                new_index = by_digest[digest]
                new_shard_index = components[new_index]["shard_start"]
                assert shards[new_shard_index]["sha256"] == shard["sha256"]
                assert logical[new_index] == source["logical"][old_index]
            else:
                new_index, new_shard_index = len(components), len(shards)
                copied = copy.deepcopy(old)
                copied.update(index=new_index, shard_start=new_shard_index)
                components.append(copied)
                shards.append(copy.deepcopy(shard))
                logical.append(source["logical"][old_index])
                by_digest[digest] = new_index
                os.link(original, ASSETS / original.name)
                os.link(original, VIEW / original.name)
            component_map[old_index] = new_index
            shard_map[old_shard_index] = new_shard_index
        old_animation = index["animations"][0]
        animations.append(dict(animation_id=source["animation"], owner=1,
                               component_indices=sorted({component_map[c] for c in old_animation["component_indices"]})))
        for row in index["directory"]:
            entry = copy.deepcopy(row)
            entry.update(component_index=component_map[row["component_index"]], shard_index=shard_map[row["shard_index"]])
            directory.append(entry)
        bindings.append(dict(animation_id=source["animation"], frames=source["frames"], resources=656,
            verification=relative(source["proof_path"]), verification_sha256=sha(source["proof_path"]),
            source_catalog=relative(source["catalog"]), source_catalog_sha256=sha(source["catalog"]),
            all_v6_bytes_identical=True))
        print(json.dumps(dict(phase="verified-and-linked", animation=source["animation"], resources=656)), flush=True)

    result = registry.write_registry_catalog_index(ASSETS / registry.XN_REGISTRY_CATALOG_FILENAME, 4,
        animations, components, shards, directory, logical,
        dict(shard_registry_version=6, frame_storage="q3m-u8-per-plane-v1"))
    os.link(ASSETS / registry.XN_REGISTRY_CATALOG_FILENAME, VIEW / registry.XN_REGISTRY_CATALOG_FILENAME)
    merged = registry.read_sealed_catalog_index(VIEW / registry.XN_REGISTRY_CATALOG_FILENAME, result["sha256"])
    assert [a["animation_id"] for a in merged["animations"]] == ["0x6100", "0x6110"]
    assert len(merged["directory"]) == 1312
    for source in sources:
        def route(index, row):
            return (row["animation_id"], row["resref"], index["components"][row["component_index"]]["digest"],
                    index["shards"][row["shard_index"]]["sha256"], row["resource_ordinal"])
        before = sorted(route(source["index"], row) for row in source["index"]["directory"])
        after = sorted(route(merged, row) for row in merged["directory"] if row["animation_id"] == source["animation"])
        assert before == after, source["animation"]

    build = dict(schema="bg2-upscale-creature-sprite-xn-catalog-pack-v1", generation_id=GENERATION_ID,
        registry_layout="catalog", registry_scale=4, registry_catalog_version=2,
        registry_catalog_shard_version=6, registry_catalog_shard_versions=[6],
        registry_catalog_frame_storage="q3m-u8-per-plane-v1", registry_catalog_frame_storages=["q3m-u8-per-plane-v1"],
        registry_catalog="iee-assets/creature-sprites/" + registry.XN_REGISTRY_CATALOG_FILENAME,
        registry_catalog_sha256=result["sha256"], registry_catalog_bytes=result["registry_catalog_bytes"],
        animation_ids=["0x6100", "0x6110"], shards=result["shards"],
        registry_catalog_logical_component_digests=logical,
        registry_catalog_logical_content_sha256=result["logical_content_sha256"],
        storage=dict(shard_registry_version=6, frame_storage="q3m-u8-per-plane-v1"),
        required_q3m_x4_decoded_shard_bytes=max(2 * s["index_bytes"] for s in shards))
    write(GENERATION / "build-manifest.json", build)
    write(RUN / "current-generation.json", dict(schema="bg2-upscale-creature-sprite-xn-catalog-current-generation-v1",
        generation_id=GENERATION_ID, generation_dir=relative(GENERATION), build_manifest="build-manifest.json"))
    runtime = read(FEMALE / "runtime.json")
    write(RUN / "x4-q3m-k6.job.json", dict(schema="bg2-upscale-creature-sprite-xn-catalog-job-v1", job_id=GENERATION_ID,
        paths=dict(game_root="config://bg2ee_game_root", run_dir=relative(RUN)),
        compatibility=dict(baldur_real_sha256=runtime["game_profile"]["baldur_real_sha256"])))
    native = []
    for source in sources:
        print(json.dumps(dict(phase="native-combined-working-set", animation=source["animation"])), flush=True)
        command = [str(source["executable"]), "--pack-complete", str(VIEW), str(source["oracle"])]
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        log = RUN / "captures" / f"{source['animation']}-native.log"
        with log.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(process.stdout + process.stderr)
        if process.returncode:
            raise RuntimeError(process.stdout + process.stderr)
        metrics = json.loads(process.stdout.splitlines()[-1])
        assert metrics["pack_frames"] == 657 and metrics["palettes"] == 18
        assert metrics["peak_resident_I_F_bytes"] <= 134217728 and metrics["peak_metadata_bytes"] <= 134217728
        native.append(dict(animation_id=source["animation"], executable=relative(source["executable"]),
            executable_sha256=sha(source["executable"]), oracle=relative(source["oracle"]), oracle_sha256=sha(source["oracle"]),
            metrics=metrics, log_sha256=sha(log)))
    write(RUN / "verification.json", dict(schema="bg2-q3m-human-fighters-x4-merged-verification-v1",
        status="passed-offline-ready-for-install", scale=4, method="Q3m", k=6, boundary_mixing=False, dithering=False,
        source_bindings=bindings, source_routes_identical=True, all_source_shards_verified=True,
        animation_ids=["0x6100", "0x6110"], directory_entries=1312, shards=len(shards),
        frames_per_animation=dict(male=180337, female=178360), unique_stored_frames=result["total_frames"],
        catalog_sha256=result["sha256"], catalog_bytes=result["registry_catalog_bytes"],
        active_pack_bytes=result["registry_catalog_bytes"] + sum(s["registry_bytes"] for s in shards),
        build_manifest_sha256=sha(GENERATION / "build-manifest.json"), preparation_script_sha256=sha(Path(__file__)),
        required_q3m_x4_decoded_shard_bytes=build["required_q3m_x4_decoded_shard_bytes"],
        required_shard_limit_is_conservative_I_plus_F_upper_bound=True,
        runtime_manifest=relative(FEMALE / "runtime.json"), runtime_manifest_sha256=sha(FEMALE / "runtime.json"),
        runtime_dll_sha256=runtime["dll"]["sha256"].upper(), native_combined_working_sets=native,
        ingame_validated=False, visual_qa_accepted=False,
        limitations=["Existing full native proofs retained because V6 bytes are unchanged; combined routes tested on all BAMs.",
                     "Oracle alpha is synthetic; live effects and GL remain manual game QA."]))
    print(json.dumps(dict(phase="ready-for-install", shards=len(shards), catalog_sha256=result["sha256"])), flush=True)


if __name__ == "__main__":
    main()
