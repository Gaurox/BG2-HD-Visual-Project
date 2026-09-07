from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw


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
        rgb_root = self.frames / "rgb"
        rgb_root.mkdir()
        alpha_root = self.frames / "alpha"
        alpha_root.mkdir()
        frames = []
        for index in range(6):
            name = f"frame_{index:03d}.png"
            image = Image.new("RGB", (64, 64), (1, 1, 1))
            ImageDraw.Draw(image).rectangle((24, 24, 39, 39), fill=(255, 96, 48))
            image.save(rgb_root / name, format="PNG")
            Image.new("L", (64, 64), 255).save(alpha_root / name, format="PNG")
            frames.append(
                {
                    "frame": index,
                    "source_size": [64, 64],
                    "centre": [32, 32],
                    "canvas_offset": [0, 0],
                    "file": name,
                    "rgb_sha256": sha256(rgb_root / name),
                    "alpha_sha256": sha256(alpha_root / name),
                }
            )
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
            raw.write_bytes(bytes([index, index, index, 255]) * (256 * 256))
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
                "rgb": rgb_root.relative_to(self.root).as_posix(),
                "alpha": alpha_root.relative_to(self.root).as_posix(),
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

    def _write_runtime_geometry(self) -> Path:
        geometry_path = self.run.parent.parent / "runtime-geometry-v1.json"
        geometry = {
            "schema": pack.RUNTIME_GEOMETRY_SCHEMA,
            "resref": self.resref,
            "source_bam_sha256": sha256(
                self.root / f"effects/ressources/{self.resref}/source.bam"
            ),
            "observation": {"method": "test fixture"},
            "frames": [
                {
                    "frame": index,
                    "logical_size_x1": [24, 16],
                    "crop_box_x1": [20, 24, 44, 40],
                    "runtime_centre_x1": [12, 8],
                }
                for index in range(6)
            ],
            "observed_slots": [
                {
                    "cycle": 0,
                    "slot": index,
                    "frame": index,
                    "logical_size_x1": [24, 16],
                }
                for index in range(6)
            ],
        }
        geometry_path.write_text(json.dumps(geometry), encoding="utf-8")
        return geometry_path

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

    def test_crops_payload_to_measured_geometry_and_preserves_anchor(self) -> None:
        geometry_path = self._write_runtime_geometry()
        with mock.patch.object(pack, "REPO_ROOT", self.root):
            descriptor, frames_x1, spatial = pack.validate_input(self.resref, self.run)
            geometry, evidence = pack.validate_runtime_geometry(
                self.resref, frames_x1, geometry_path
            )
            record, assets = pack.build_pack_record(
                self.resref, frames_x1, spatial, self.spatial, geometry
            )
            registry = pack.REGISTRY_MAGIC + pack.struct.pack("<IIII", 1, 4, 1, 0) + record
            output = self.root / "engine/assets/effects-measured"
            manifest = pack.write_pack(
                output,
                registry,
                assets,
                descriptor,
                frames_x1,
                spatial,
                runtime_geometry_evidence=evidence,
            )

        self.assertEqual(pack.struct.unpack_from("<II", record, 16), (24, 16))
        self.assertEqual((output / assets[0]["asset"]).stat().st_size, 96 * 64 * 4)
        self.assertEqual(manifest["frames"][0]["crop_box_x1"], [20, 24, 44, 40])
        self.assertEqual(manifest["frames"][0]["runtime_centre_x1"], [12, 8])
        self.assertNotIn("_payload", manifest["frames"][0])
        self.assertEqual(manifest["source"]["runtime_geometry"]["path"], geometry_path.relative_to(self.root).as_posix())

    def test_contains_full_frame_and_neutralises_rgb_under_runtime_alpha(self) -> None:
        geometry_path = self._write_runtime_geometry()
        geometry_payload = json.loads(geometry_path.read_text(encoding="utf-8"))
        geometry_payload["alpha_policy"] = {
            "mode": "source-rgb-luminance",
            "luminance_low": 3,
            "luminance_high": 16,
            "rgb_alpha_mode": "premultiply",
        }
        for frame in geometry_payload["frames"]:
            frame.pop("crop_box_x1")
            frame["mapping"] = {
                "mode": "contain",
                "source_box_x1": [0, 0, 64, 64],
                "destination_box_x1": [4, 0, 20, 16],
            }
        geometry_path.write_text(json.dumps(geometry_payload), encoding="utf-8")

        with mock.patch.object(pack, "REPO_ROOT", self.root):
            _, frames_x1, spatial = pack.validate_input(self.resref, self.run)
            geometry, _ = pack.validate_runtime_geometry(self.resref, frames_x1, geometry_path)
            _, assets = pack.build_pack_record(
                self.resref, frames_x1, spatial, self.spatial, geometry
            )

        payload = assets[1]["_payload"]
        transparent = 0
        opaque = 0
        for offset in range(0, len(payload), 4):
            alpha = payload[offset + 3]
            if alpha == 0:
                transparent += 1
                self.assertEqual(payload[offset:offset + 3], b"\0\0\0")
            elif alpha == 255:
                opaque += 1
        self.assertGreater(transparent, 0)
        self.assertGreater(opaque, 0)
        self.assertEqual(assets[1]["mapping"]["mode"], "contain")

    def test_applies_premultiplied_radial_mask_to_cropped_light(self) -> None:
        geometry_path = self._write_runtime_geometry()
        geometry_payload = json.loads(geometry_path.read_text(encoding="utf-8"))
        geometry_payload["alpha_policy"] = {
            "mode": "runtime-radial",
            "outer_radius_x_x1": 12,
            "outer_radius_y_x1": 8,
            "inner_fraction": 0.3,
            "rgb_alpha_mode": "premultiply",
        }
        geometry_path.write_text(json.dumps(geometry_payload), encoding="utf-8")

        with mock.patch.object(pack, "REPO_ROOT", self.root):
            _, frames_x1, spatial = pack.validate_input(self.resref, self.run)
            geometry, _ = pack.validate_runtime_geometry(self.resref, frames_x1, geometry_path)
            _, assets = pack.build_pack_record(
                self.resref, frames_x1, spatial, self.spatial, geometry
            )

        payload = assets[1]["_payload"]
        centre = (32 * 96 + 48) * 4
        self.assertEqual(payload[3], 0)
        self.assertEqual(payload[:3], b"\0\0\0")
        self.assertEqual(payload[centre + 3], 255)
        self.assertEqual(assets[1]["mapping"]["mode"], "crop")

    def test_derives_premultiplied_alpha_from_runtime_rgb_luminance(self) -> None:
        payload = bytes(
            [
                0, 0, 0, 255,
                255, 255, 255, 255,
                54, 54, 54, 128,
            ]
        )
        transformed = pack.transform_rgba(
            payload,
            [3, 1],
            [0, 0, 3, 1],
            [3, 1],
            [0, 0, 3, 1],
            scale=1,
            alpha_policy={
                "mode": "runtime-rgb-luminance",
                "luminance_low": 8,
                "luminance_high": 100,
                "rgb_alpha_mode": "premultiply",
            },
        )

        self.assertEqual(transformed[:4], b"\0\0\0\0")
        self.assertEqual(transformed[4:8], b"\xff\xff\xff\xff")
        self.assertGreater(transformed[11], 0)
        self.assertLess(transformed[11], 128)
        self.assertEqual(transformed[8], (54 * transformed[11] + 127) // 255)

    def test_contracts_runtime_luminance_alpha_by_requested_x4_radius(self) -> None:
        payload = bytes(
            [
                255, 255, 255, 0,
                255, 255, 255, 255,
                255, 255, 255, 0,
            ]
        )
        transformed = pack.transform_rgba(
            payload,
            [3, 1],
            [0, 0, 3, 1],
            [3, 1],
            [0, 0, 3, 1],
            scale=1,
            alpha_policy={
                "mode": "runtime-rgb-luminance",
                "luminance_low": 0,
                "luminance_high": 1,
                "alpha_erode_radius_x4": 1,
                "rgb_alpha_mode": "premultiply",
            },
        )

        self.assertEqual(transformed, b"\0" * len(payload))

    def test_bounded_gaussian_alpha_does_not_expand_the_eroded_support(self) -> None:
        payload = bytes(
            [
                255, 255, 255, 0,
                255, 255, 255, 255,
                255, 255, 255, 0,
            ]
        )
        transformed = pack.transform_rgba(
            payload,
            [3, 1],
            [0, 0, 3, 1],
            [3, 1],
            [0, 0, 3, 1],
            scale=1,
            alpha_policy={
                "mode": "runtime-rgb-luminance",
                "luminance_low": 0,
                "luminance_high": 1,
                "alpha_gaussian_sigma_x4": 0.6,
                "rgb_alpha_mode": "premultiply",
            },
        )

        self.assertEqual(transformed[:4], b"\0" * 4)
        self.assertEqual(transformed[-4:], b"\0" * 4)

    def test_accepts_external_luminance_policy_bound_to_the_source_bam(self) -> None:
        policy_path = self.root / "effects/alpha-policies/TESTFX-emissive-v1.json"
        policy_path.parent.mkdir(parents=True)
        policy_path.write_text(
            json.dumps(
                {
                    "schema": pack.ALPHA_POLICY_SCHEMA,
                    "resref": self.resref,
                    "source_bam_sha256": sha256(
                        self.root / f"effects/ressources/{self.resref}/source.bam"
                    ),
                    "alpha_policy": {
                        "mode": "runtime-rgb-luminance",
                        "luminance_low": 8,
                        "luminance_high": 100,
                        "rgb_alpha_mode": "premultiply",
                    },
                }
            ),
            encoding="utf-8",
        )
        with mock.patch.object(pack, "REPO_ROOT", self.root):
            _, frames_x1, spatial = pack.validate_input(self.resref, self.run)
            alpha_policy, evidence = pack.validate_external_alpha_policy(
                self.resref, frames_x1, policy_path
            )
            _, assets = pack.build_pack_record(
                self.resref, frames_x1, spatial, self.spatial, alpha_policy=alpha_policy
            )

        self.assertEqual(evidence["path"], policy_path.relative_to(self.root).as_posix())
        self.assertEqual(assets[0]["alpha_policy"], alpha_policy)
        self.assertIsInstance(assets[0]["_payload"], bytes)

    def test_rejects_geometry_without_measurement_for_each_slot(self) -> None:
        geometry_path = self._write_runtime_geometry()
        geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
        geometry["observed_slots"].pop()
        geometry_path.write_text(json.dumps(geometry), encoding="utf-8")
        with mock.patch.object(pack, "REPO_ROOT", self.root):
            _, frames_x1, _ = pack.validate_input(self.resref, self.run)
            with self.assertRaisesRegex(RuntimeError, "chaque slot"):
                pack.validate_runtime_geometry(self.resref, frames_x1, geometry_path)


if __name__ == "__main__":
    unittest.main()
