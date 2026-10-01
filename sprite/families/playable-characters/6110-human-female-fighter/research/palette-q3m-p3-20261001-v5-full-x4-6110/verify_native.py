"""Authenticate and verify every newly generated Q3m x4 frame with the C++ reader."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

RUN = Path(__file__).resolve().parent
ROOT = next(p for p in RUN.parents if (p / "pipeline/scripts/palette_registry.py").is_file())
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import run_creature_sprite_x2 as registry


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def link(original, target):
    if not target.exists():
        os.link(original, target)
    assert original.samefile(target) and sha(original) == sha(target)


def main():
    proof_path = RUN / "verification.json"
    assert not proof_path.exists(), "A final verification is immutable"
    coverage = json.loads((RUN / "coverage.json").read_text())
    recipe = json.loads((RUN / "recipe.json").read_text())
    assert recipe["scale"] == 4 and recipe["method"] == "Q3m" and recipe["k"] == 6
    assert not recipe["boundary_mixing"] and not recipe["dithering"]
    assert coverage["resource_count"] == 656 and coverage["frames"] == 178360
    assert coverage["p1_samples_byte_identical"] == 144
    prior = RUN.parent / "palette-q3m-p3-20261001-v3-full-6110"
    prior_proof = json.loads((prior / "verification.json").read_text())
    assert sha(prior / "coverage.json") == prior_proof["coverage_sha256"]
    prior_rows = {r["resref"]: r for r in json.loads((prior / "coverage.json").read_text())["resources"]}
    assert set(prior_rows) == {r["resref"] for r in coverage["resources"]}
    for row in coverage["resources"]:
        old = prior_rows[row["resref"]]
        assert row["frames"] == old["frames"] and row["source_sha256"] == old["source_sha256"]
        assert row["decoded_pixels"] == old["decoded_pixels"] * 4
    generation = RUN / "x4-q3m-k6/generation"
    build = json.loads((generation / "build-manifest.json").read_text())
    original_assets = generation / "iee-assets/creature-sprites"
    index = registry.read_sealed_catalog_index(original_assets / "CreatureSprites-XN.catalog", coverage["catalog_sha256"])
    assert index["scale"] == 4 and len(index["shards"]) == 656
    assert [a["animation_id"] for a in index["animations"]] == ["0x6110"]
    assert len(index["directory"]) == 656 and len(index["components"]) == 656
    assert build["registry_catalog_shard_versions"] == [6] and coverage["parent_shards_reused"] == 0
    assert {r["resref"] for r in coverage["resources"]} == {r["resref"] for r in index["directory"]}
    assert all(r["roundtrip_identical"] for r in coverage["resources"])
    short_root = ROOT / "build/p3-6110-v5-x4-native"
    assets = short_root / "creature-sprites"
    assets.mkdir(parents=True, exist_ok=True)
    for original in original_assets.iterdir():
        if original.is_file():
            link(original, assets / original.name)
    oracle_view = short_root / "oracles"
    oracle_view.mkdir(exist_ok=True)
    captures = RUN / "captures"
    captures.mkdir(exist_ok=True)
    executable = ROOT / "build/palette-q3m-p3-20261001-v5-x4/cmake/Release/iee_palette_fraction_tests.exe"
    assert sha(executable) == "723fbe2e9ac96dd24eb8a4fced2791356fdd45dbdf76996813af72655b8756dc"
    runtime = json.loads((RUN / "runtime.json").read_text())
    assert sha(ROOT / runtime["dll"]["path"]) == runtime["dll"]["sha256"]
    assert runtime["capabilities"]["creature_sprite_xn_catalog"]["q3m_x4_decoded_shard_limit_bytes"] >= build["required_q3m_x4_decoded_shard_bytes"]
    working = json.loads((RUN / "working-set-oracles.json").read_text())
    groups = (("complete", coverage["oracle_directory"], coverage["oracles"]),
              ("working-set", working["directory"], working["oracles"]))
    results = []
    for group, directory, oracles in groups:
        for n, oracle in enumerate(oracles):
            original = ROOT / directory / oracle["path"]
            assert sha(original) == oracle["sha256"]
            short = oracle_view / f"{group}-{n}.bin"
            link(original, short)
            command = [str(executable), "--pack-complete", str(assets), str(short)]
            process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            log = captures / f"{group}-{n}-native.log"
            assert not log.exists(), "Keep previous diagnostic logs"
            log.write_text(process.stdout + process.stderr, encoding="utf-8")
            if process.returncode:
                print(process.stdout + process.stderr, flush=True)
                raise RuntimeError(f"Native verification failed: {process.returncode}")
            metrics = json.loads(process.stdout.splitlines()[-1])
            assert metrics["pack_frames"] == oracle["frames"] and metrics["palettes"] == 18
            assert metrics["peak_resident_I_F_bytes"] <= 128 * 1024 * 1024
            assert metrics["peak_metadata_bytes"] <= 128 * 1024 * 1024
            results.append(dict(group=group, oracle=oracle, command=command, native_test=metrics,
                log=log.relative_to(RUN).as_posix(), log_sha256=sha(log)))
            print(json.dumps(dict(group=group, **metrics)), flush=True)
    complete = [r["native_test"] for r in results if r["group"] == "complete"]
    assert sum(r["pack_frames"] for r in complete) == 178360
    assert sum(r["decoded_pixels"] for r in complete) == coverage["decoded_pixels"] * 18
    assert sum(r["native_test"]["pack_frames"] for r in results if r["group"] == "working-set") == 657
    ctest = ROOT / "build/palette-q3m-p3-20261001-v5-x4/cmake/Testing/Temporary/LastTest.log"
    ctest_text = ctest.read_text(encoding="utf-8", errors="replace")
    assert ctest_text.count("Test Passed.") == 2 and '"accepted":10,"rejected":37' in ctest_text
    shutil.copyfile(ctest, captures / "ctest-detail.log")
    source_paths = (
        "pipeline/scripts/palette_complete.py", "pipeline/scripts/palette_frac_encode.py",
        "pipeline/scripts/palette_registry.py", "pipeline/scripts/palette_p3_catalog.py",
        "pipeline/scripts/palette_p2.py", "pipeline/scripts/Start-Palette-Q3m-P3.ps1",
        "pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1",
        "engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp",
        "engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/palette_fraction.h",
        "engine/InfinityEngine-Enhancer/source-patchee/tests/palette_fraction_tests.cpp")
    proof = dict(schema="bg2-upscale-character-palette-complete-verification-v1",
        status="passed-offline-ready-for-manual-game", animation_id="0x6110", scale=4,
        method="Q3m", k=6, boundary_mixing=False, dithering=False,
        resource_count=656, frames=178360, p1_samples_byte_identical=144,
        python_tests_passed=45, ctest_suites_passed=2, native_valid_fixtures=10, native_invalid_fixtures=37,
        native_pack_tests=results, reference_decodings=sum(r["native_test"]["pack_frames"] * 18 for r in results),
        complete_decoded_pixel_comparisons=sum(r["decoded_pixels"] for r in complete),
        decoded_pixel_comparisons=sum(r["native_test"]["decoded_pixels"] for r in results),
        runtime_dll_sha256=runtime["dll"]["sha256"], native_test_executable_sha256=sha(executable),
        catalog_sha256=coverage["catalog_sha256"], required_q3m_x4_decoded_shard_bytes=build["required_q3m_x4_decoded_shard_bytes"],
        resident_I_F_budget_bytes=134217728, metadata_budget_bytes=134217728,
        frozen_x2_source_and_frame_coverage_identical=True, physical_pixel_count_ratio_to_x2=4,
        native_read_view=dict(path=assets.relative_to(ROOT).as_posix(), same_underlying_files=True),
        coverage_sha256=sha(RUN / "coverage.json"), recipe_sha256=sha(RUN / "recipe.json"),
        preservation_sha256=sha(generation / "preservation.json"), ctest_log_sha256=sha(captures / "ctest-detail.log"),
        source_sha256={p: sha(ROOT / p) for p in source_paths}, native_validation_script_sha256=sha(Path(__file__)),
        independent_oracle="palette_complete.Oracle: scalar class intervals and LUT independent of encoder decode",
        legacy_pixels_reused=0, other_animations="native BAM during isolated 0x6110 x4 test",
        ingame_validated=False, visual_qa_accepted=False,
        limitations=["Synthetic oracle alpha; live palette/effects and GL require manual P3 evidence.",
                    "REF P1 regression unchanged: +11.59% x4.",
                    "WINGS01B/YW has no source BAM for 0x6110; inherited absence retained."])
    proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
