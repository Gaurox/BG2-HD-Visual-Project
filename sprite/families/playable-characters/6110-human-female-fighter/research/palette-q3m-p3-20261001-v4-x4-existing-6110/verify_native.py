"""Verify the assembled x4 pack with the already-built current C++ reader."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

RUN = Path(__file__).resolve().parent
ROOT = next(p for p in RUN.parents if (p / "pipeline/scripts/palette_registry.py").is_file())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def main():
    proof_path = RUN / "verification.json"
    assert not proof_path.exists(), "A final verification is immutable"
    coverage = json.loads((RUN / "coverage.json").read_text())
    prior = ROOT / "sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p3-20261001-v3-full-6110"
    pinned = json.loads((prior / "verification.json").read_text())
    executable = ROOT / "build/palette-q3m-p3-20261001-v1/cmake/Release/iee_palette_fraction_tests.exe"
    assert sha(executable).lower() == pinned["native_test_executable_sha256"]
    for path in (
        "engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp",
        "engine/InfinityEngine-Enhancer/source-patchee/tests/palette_fraction_tests.cpp",
    ):
        assert sha(ROOT / path).lower() == pinned["source_sha256"][path]
    assets = ROOT / coverage["native_read_view"]
    assert sha(assets / "CreatureSprites-XN.catalog") == coverage["catalog_sha256"]
    oracle_view = assets.parent / "oracles"
    oracle_view.mkdir(exist_ok=True)
    captures = RUN / "captures"
    captures.mkdir(exist_ok=True)
    results = []
    for group in ("complete_replacement_oracles", "working_set_oracles"):
        for n, oracle in enumerate(coverage[group]):
            original = ROOT / oracle["path"]
            assert sha(original).lower() == oracle["sha256"]
            short = oracle_view / f"{group}-{n}.bin"
            if not short.exists():
                os.link(original, short)
            assert original.samefile(short)
            command = [str(executable), "--pack", str(assets), str(short)]
            process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            log = captures / f"{group}-{n}.log"
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
    proof = dict(schema="bg2-upscale-existing-x4-native-verification-v1",
        status="passed-offline-ready-for-manual-game", scale=4, animation_id="0x6110",
        resources=656, frames=178360, q3m_samples=144, legacy_reboutcx_frames=178216,
        native_pack_tests=results,
        reference_decodings=sum(r["native_test"]["pack_frames"] * 18 for r in results),
        decoded_pixel_comparisons=sum(r["native_test"]["decoded_pixels"] for r in results),
        native_test_executable_sha256=sha(executable), coverage_sha256=sha(RUN / "coverage.json"),
        catalog_sha256=coverage["catalog_sha256"],
        source_sha256={p: sha(ROOT / p) for p in (
            "pipeline/scripts/palette_complete.py", "pipeline/scripts/palette_registry.py",
            "engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp",
            "engine/InfinityEngine-Enhancer/source-patchee/tests/palette_fraction_tests.cpp")},
        assembly_sha256=sha(RUN / "assemble.py"), native_validation_script_sha256=sha(Path(__file__)),
        independent_oracle="palette_complete.Oracle: scalar LUT independent of encoder decode",
        unchanged_assets="644 V5 resource records copied byte for byte; other frames of 12 V6 resources retain exact legacy I",
        other_animations="native BAM during isolated 0x6110 x4 test",
        ingame_validated=False, visual_qa_accepted=False)
    proof_path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
