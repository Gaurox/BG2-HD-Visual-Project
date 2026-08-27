from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_animation_runtime_pack as runtime_pack  # noqa: E402


class AnimationRuntimePackTests(unittest.TestCase):
    def make_run(self, root: Path, resref: str = "TESTA") -> Path:
        run = root / "run"
        frames_x1 = run / "resources" / resref / "01_frames_x1"
        upscale = run / "resources" / resref / "02_upscale_x4"
        raw = upscale / "raw_rgba"
        frames_x1.mkdir(parents=True)
        raw.mkdir(parents=True)

        (frames_x1 / "manifest.json").write_text(
            json.dumps({
                "schema": runtime_pack.FRAME_SCHEMA,
                "frame_count": 2,
                "geometry_mode": "per-frame",
                "cycles": [{"cycle": 0, "frame_indices": [0, 1, 0]}],
            }),
            encoding="utf-8",
        )
        sizes = [(2, 3), (1, 1)]
        upscale_frames = []
        for index, (width, height) in enumerate(sizes):
            path = raw / f"frame_{index:03d}.rgba"
            path.write_bytes(bytes([30 + index]) * (width * 4 * height * 4 * 4))
            upscale_frames.append({
                "frame": index,
                "logical_size_x1": [width, height],
                "physical_size_xn": [width * 4, height * 4],
                "centre_x1": [index, height],
                "raw_rgba_xn": f"raw_rgba/{path.name}",
                "raw_rgba_xn_sha256": runtime_pack.sha256_file(path),
            })
        (upscale / "manifest.json").write_text(
            json.dumps({
                "schema": runtime_pack.UPSCALE_SCHEMA,
                "status": "completed",
                "scale": 4,
                "frames": upscale_frames,
            }),
            encoding="utf-8",
        )
        (run / "manifest.json").write_text(
            json.dumps({
                "schema": runtime_pack.RUN_SCHEMA,
                "status": "completed",
                "request": {"scale": 4},
                "resources": [{
                    "resref": resref,
                    "status": "completed",
                    "frames_x1": f"resources/{resref}/01_frames_x1",
                    "upscale": f"resources/{resref}/02_upscale_x4",
                }],
            }),
            encoding="utf-8",
        )
        return run

    def test_build_validate_and_reject_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = self.make_run(Path(temporary))
            runtime_pack.main([str(run)])
            output = run / "03_runtime_pack"
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["resource_count"], 1)
            self.assertEqual(manifest["frame_count"], 2)
            self.assertEqual(manifest["resources"][0]["geometry_mode"], "per-frame")

            registry = (output / runtime_pack.REGISTRY_NAME).read_bytes()
            self.assertEqual(registry[:8], runtime_pack.REGISTRY_MAGIC)
            self.assertEqual(struct.unpack_from("<IIII", registry, 8), (1, 4, 1, 0))
            self.assertEqual(registry[24:32], b"TESTA\0\0\0")
            self.assertEqual(struct.unpack_from("<II", registry, 32), (2, 1))
            self.assertEqual(struct.unpack_from("<IIII", registry, 40), (2, 3, 1, 1))
            self.assertEqual(struct.unpack_from("<I", registry, 56), (3,))
            self.assertEqual(struct.unpack_from("<III", registry, 60), (0, 1, 0))

            registry_hash = runtime_pack.sha256_file(output / runtime_pack.REGISTRY_NAME)
            runtime_pack.main([str(run), "--resume"])
            self.assertEqual(
                registry_hash,
                runtime_pack.sha256_file(output / runtime_pack.REGISTRY_NAME),
            )
            with self.assertRaisesRegex(RuntimeError, "destination runtime non vide"):
                runtime_pack.main([str(run)])

            asset = output / "AAX4-TESTA-frame001.rgba"
            asset.write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "asset runtime"):
                runtime_pack.main([str(run), "--resume"])

    def test_compose_packs_and_preserve_alpha_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_a = self.make_run(root / "a", "TESTA")
            run_b = self.make_run(root / "b", "TESTB")
            runtime_pack.main([str(run_a)])
            runtime_pack.main([str(run_b)])

            override_root = root / "override"
            raw = override_root / "raw_rgba"
            raw.mkdir(parents=True)
            override_frames = []
            for index in range(2):
                name = runtime_pack.asset_name("TESTA", index)
                path = raw / name
                source = run_a / "03_runtime_pack" / name
                path.write_bytes(bytes([200 + index]) * source.stat().st_size)
                override_frames.append({
                    "frame": index,
                    "runtime_asset": f"raw_rgba/{name}",
                    "runtime_sha256": runtime_pack.sha256_file(path),
                    "runtime_bytes": path.stat().st_size,
                })
            override_manifest = override_root / "manifest.json"
            override_manifest.write_text(json.dumps({
                "schema": "bg2-upscale-animation-alpha-feather-test-v1",
                "status": "completed",
                "resref": "TESTA",
                "scale": 4,
                "frames": override_frames,
            }), encoding="utf-8")

            output = root / "composed"
            runtime_pack.main([
                str(run_a),
                str(output),
                "--include-pack", str(run_b / "03_runtime_pack"),
                "--alpha-override-manifest", str(override_manifest),
            ])
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["resource_count"], 2)
            self.assertEqual(manifest["frame_count"], 4)
            self.assertEqual(
                manifest["composition"]["asset_overrides"][0]["resref"],
                "TESTA",
            )
            self.assertEqual(
                runtime_pack.sha256_file(output / "AAX4-TESTA-frame000.rgba"),
                override_frames[0]["runtime_sha256"],
            )
            registry = (output / runtime_pack.REGISTRY_NAME).read_bytes()
            self.assertEqual(struct.unpack_from("<IIII", registry, 8), (1, 4, 2, 0))

            runtime_pack.main([
                str(run_a),
                str(output),
                "--include-pack", str(run_b / "03_runtime_pack"),
                "--alpha-override-manifest", str(override_manifest),
                "--resume",
            ])

    def test_drops_trailing_empty_bam_cycles(self) -> None:
        # Stock BAM V1 resources such as FIRE_1 declare padding cycles with an
        # empty lookup after cycle 0. The engine registry parser rejects a
        # zero-length cycle, so the builder must trim trailing empty cycles.
        with tempfile.TemporaryDirectory() as temporary:
            run = self.make_run(Path(temporary))
            frame_manifest_path = (
                run / "resources" / "TESTA" / "01_frames_x1" / "manifest.json"
            )
            frame_manifest = json.loads(frame_manifest_path.read_text(encoding="utf-8"))
            frame_manifest["cycles"] = [
                {"cycle": 0, "frame_indices": [0, 1, 0]},
                {"cycle": 1, "frame_indices": []},
                {"cycle": 2, "frame_indices": []},
            ]
            frame_manifest_path.write_text(json.dumps(frame_manifest), encoding="utf-8")

            runtime_pack.main([str(run)])
            output = run / "03_runtime_pack"
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["resources"][0]["cycle_count"], 1)
            self.assertEqual(
                manifest["resources"][0]["cycles"], [{"cycle": 0, "frame_indices": [0, 1, 0]}]
            )

            registry = (output / runtime_pack.REGISTRY_NAME).read_bytes()
            self.assertEqual(struct.unpack_from("<II", registry, 32), (2, 1))
            self.assertEqual(struct.unpack_from("<I", registry, 56), (3,))

            registry_hash = runtime_pack.sha256_file(output / runtime_pack.REGISTRY_NAME)
            runtime_pack.main([str(run), "--resume"])
            self.assertEqual(
                registry_hash,
                runtime_pack.sha256_file(output / runtime_pack.REGISTRY_NAME),
            )

    def test_rejects_resource_with_only_empty_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run = self.make_run(Path(temporary))
            frame_manifest_path = (
                run / "resources" / "TESTA" / "01_frames_x1" / "manifest.json"
            )
            frame_manifest = json.loads(frame_manifest_path.read_text(encoding="utf-8"))
            frame_manifest["cycles"] = [{"cycle": 0, "frame_indices": []}]
            frame_manifest_path.write_text(json.dumps(frame_manifest), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "aucun cycle non vide"):
                runtime_pack.main([str(run)])


if __name__ == "__main__":
    unittest.main()
