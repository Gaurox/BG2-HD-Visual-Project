from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import build_effect_runtime_pack as pack  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class EffectRuntimePackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.resref = "TESTFX"
        self.run_id = "spatial-test"
        self.run = self.root / f"effects/ressources/{self.resref}/runs/{self.run_id}"
        self.frames = self.run / "00-frames-x1"
        self.spatial = self.run / "01-spatial-x4"
        self.frames.mkdir(parents=True)
        self.spatial.mkdir(parents=True)
        self._write_fixture()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_fixture(self) -> None:
        source = self.root / f"effects/ressources/{self.resref}/source.bam"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"stock-bam")
        frames = [
            {
                "frame": index,
                "source_size": [64, 64],
                "file": f"frame_{index:03d}.png",
            }
            for index in range(6)
        ]
        frames_manifest = {
            "schema": pack.FRAME_SCHEMA,
            "source_sha256": sha256(source),
            "frame_count": 6,
            "frames": frames,
            "cycles": [{"cycle": 0, "frame_indices": list(range(6))}],
        }
        frame_manifest_path = self.frames / "manifest.json"
        frame_manifest_path.write_text(json.dumps(frames_manifest), encoding="utf-8")
        scaled_frames = []
        for index in range(6):
            raw = self.spatial / f"raw_rgba/frame_{index:03d}.rgba"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(bytes([index]) * (256 * 256 * 4))
            scaled_frames.append(
                {
                    "frame": index,
                    "logical_size_x1": [64, 64],
                    "physical_size_xn": [256, 256],
                    "raw_rgba_xn": raw.relative_to(self.spatial).as_posix(),
                    "raw_rgba_xn_sha256": sha256(raw),
                }
            )
        spatial_manifest = {
            "schema": pack.SPATIAL_SCHEMA,
            "status": "completed",
            "scale": 4,
            "source": {
                "frame_manifest": self.frames.relative_to(self.root).joinpath("manifest.json").as_posix(),
                "frame_manifest_sha256": sha256(frame_manifest_path),
            },
            "frames": scaled_frames,
        }
        spatial_path = self.spatial / "manifest.json"
        spatial_path.write_text(json.dumps(spatial_manifest), encoding="utf-8")
        descriptor = {
            "schema_version": 1,
            "domain": "effects",
            "run_id": self.run_id,
            "asset_ids": [f"effects:bam:{self.resref}"],
            "pipeline": {"id": "effects.spatial-x4.v1"},
            "outputs": [
                {
                    "role": "spatial-manifest",
                    "path": spatial_path.relative_to(self.root).as_posix(),
                    "sha256": sha256(spatial_path),
                }
            ],
            "result": {"sealed": True, "status": "completed"},
        }
        (self.run / "run.json").write_text(json.dumps(descriptor), encoding="utf-8")

    def test_builds_exact_registry_and_payload_from_sealed_spatial_run(self) -> None:
        with mock.patch.object(pack, "REPO_ROOT", self.root):
            descriptor, frames_x1, spatial = pack.validate_input(self.resref, self.run)
            record, assets = pack.build_pack_record(self.resref, frames_x1, spatial, self.spatial)
            registry = pack.REGISTRY_MAGIC + pack.struct.pack("<IIII", 1, 4, 1, 0) + record
            output = self.root / "engine/assets/effects"
            output.mkdir(parents=True)
            output.joinpath("README.md").write_text("generated test pack\n", encoding="utf-8")
            manifest = pack.write_pack(output, registry, assets, descriptor, frames_x1, spatial)

        self.assertEqual(manifest["registry_magic"], "IEEEFX4")
        self.assertEqual(manifest["frame_count"], 6)
        self.assertEqual((output / pack.REGISTRY_NAME).read_bytes(), registry)
        self.assertEqual(
            {asset["asset"] for asset in manifest["frames"]},
            {f"EFX4-TESTFX-frame{index:03d}.rgba" for index in range(6)},
        )

    def test_rejects_unsealed_spatial_run(self) -> None:
        descriptor_path = self.run / "run.json"
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        descriptor["result"]["sealed"] = False
        descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
        with mock.patch.object(pack, "REPO_ROOT", self.root):
            with self.assertRaisesRegex(RuntimeError, "non scellé"):
                pack.validate_input(self.resref, self.run)


if __name__ == "__main__":
    unittest.main()
