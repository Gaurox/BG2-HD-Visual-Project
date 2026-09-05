from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_animation_runtime_pack as runtime_pack  # noqa: E402
import run_animation_interpolation as interpolation  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AnimationInterpolationPipelineTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> tuple[Path, Path, Path, Path]:
        frames_x1 = root / "frames-x1"
        upscale = root / "upscale-x4"
        rgb_dir = upscale / "rgb"
        alpha_dir = upscale / "alpha"
        rgba_dir = upscale / "rgba"
        for directory in (frames_x1, rgb_dir, alpha_dir, rgba_dir):
            directory.mkdir(parents=True)

        x1_frames = []
        upscale_frames = []
        colours = [(255, 0, 0), (0, 255, 0)]
        for index, colour in enumerate(colours):
            rgb = Image.new("RGB", (8, 4), colour)
            alpha = Image.new("L", (8, 4), 255)
            rgba = Image.merge("RGBA", (*rgb.split(), alpha))
            rgb_path = rgb_dir / f"frame_{index:03d}.png"
            alpha_path = alpha_dir / f"frame_{index:03d}.png"
            rgba_path = rgba_dir / f"frame_{index:03d}.png"
            rgb.save(rgb_path)
            alpha.save(alpha_path)
            rgba.save(rgba_path)
            x1_frames.append({"frame": index, "source_size": [2, 1], "centre": [1, 1]})
            upscale_frames.append({
                "frame": index,
                "logical_size_x1": [2, 1],
                "physical_size_xn": [8, 4],
                "centre_x1": [1, 1],
                "runtime_crop_box_xn": [0, 0, 8, 4],
                "rgb_xn": f"rgb/{rgb_path.name}",
                "alpha_xn": f"alpha/{alpha_path.name}",
                "aligned_rgba_xn": f"rgba/{rgba_path.name}",
            })
        frames_manifest = frames_x1 / "manifest.json"
        frames_manifest.write_text(json.dumps({
            "frame_count": 2,
            "frames": x1_frames,
            "cycles": [{"cycle": 0, "frame_indices": [0, 0, 1, 1]}],
            "geometry_mode": "uniform",
        }), encoding="utf-8")
        upscale_manifest = upscale / "manifest.json"
        upscale_manifest.write_text(json.dumps({
            "status": "completed",
            "scale": 4,
            "geometry_mode": "uniform",
            "frames": upscale_frames,
        }), encoding="utf-8")

        base = root / "base-pack"
        base.mkdir()
        runtime_frames = []
        for index, colour in enumerate(colours):
            raw = bytes((*colour, 255)) * 32
            name = runtime_pack.asset_name("TESTA", index)
            path = base / name
            path.write_bytes(raw)
            runtime_frames.append({
                "frame": index,
                "logical_size_x1": [2, 1],
                "physical_size_x4": [8, 4],
                "centre_x1": [1, 1],
                "asset": name,
                "sha256": sha(path),
                "bytes": len(raw),
            })
        resource = {
            "resref": "TESTA",
            "frame_count": 2,
            "cycle_count": 1,
            "geometry_mode": "uniform",
            "frames": runtime_frames,
            "cycles": [{"cycle": 0, "frame_indices": [0, 0, 1, 1]}],
            "assets": [{"name": item["asset"], "sha256": item["sha256"], "bytes": item["bytes"]} for item in runtime_frames],
        }
        registry = runtime_pack.registry_from_resources([resource])
        registry_path = base / runtime_pack.REGISTRY_NAME
        registry_path.write_bytes(registry)
        (base / "manifest.json").write_text(json.dumps({
            "schema": runtime_pack.PACK_SCHEMA,
            "status": "completed",
            "scale": 4,
            "registry": runtime_pack.REGISTRY_NAME,
            "registry_sha256": sha(registry_path),
            "registry_bytes": registry_path.stat().st_size,
            "resource_count": 1,
            "frame_count": 2,
            "resources": [resource],
        }), encoding="utf-8")
        return frames_manifest, upscale_manifest, base, root / "returned"

    def test_plan_audit_and_build_patch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frames_manifest, upscale_manifest, base, returned = self.make_fixture(root)
            context = interpolation.load_context(
                resref="TESTA",
                frames_manifest_path=frames_manifest,
                upscale_manifest_path=upscale_manifest,
                base_pack_path=base,
                slot_fps=12,
            )
            plan = interpolation.public_plan(context)
            self.assertEqual(plan["recommendation"]["interpolated_frame_count"], 4)
            self.assertEqual(plan["source_video"]["frame_count"], 2)
            self.assertEqual(plan["source_video"]["fps"], 6)

            work = root / "work"
            work.mkdir()
            handoff = {
                "schema": interpolation.HANDOFF_SCHEMA,
                "status": "prepared",
                "plan": plan,
                "inputs": {
                    "frames_manifest": frames_manifest.as_posix(),
                    "frames_manifest_sha256": sha(frames_manifest),
                    "upscale_manifest": upscale_manifest.as_posix(),
                    "upscale_manifest_sha256": sha(upscale_manifest),
                    "base_pack": base.as_posix(),
                    "base_pack_manifest_sha256": sha(base / "manifest.json"),
                    "base_registry_sha256": sha(base / runtime_pack.REGISTRY_NAME),
                },
                "source_assets": interpolation.source_asset_hashes(context),
                "return_contract": plan["return_contract"],
            }
            interpolation.write_json(work / "handoff.json", handoff)

            returned.mkdir()
            for index, colour in enumerate([(255, 0, 0), (170, 85, 0), (85, 170, 0), (0, 255, 0)]):
                Image.new("RGB", (8, 4), colour).save(returned / f"returned_{index:03d}.png")
            intake = interpolation.audit_returned_frames(work, returned)
            self.assertEqual(intake["frame_count"], 4)
            self.assertEqual(len(intake["adjacent_rgb_mae"]), 4)

            patch = interpolation.build_patch(work, work / "runtime-patch", resume=False)
            self.assertEqual(patch["frame_count"], 4)
            self.assertEqual(patch["resource"]["cycles"][0]["frame_indices"], [0, 1, 2, 3])
            self.assertTrue((work / "runtime-patch" / runtime_pack.REGISTRY_NAME).is_file())
            resumed = interpolation.build_patch(work, work / "runtime-patch", resume=True)
            self.assertEqual(resumed["target_registry_sha256"], patch["target_registry_sha256"])


    def test_rate_text_is_exact(self) -> None:
        self.assertEqual(interpolation.rate_text(15), "15")
        self.assertEqual(interpolation.rate_text(5.0), "5")
        self.assertEqual(interpolation.rate_text(7.5), "15/2")

    def test_alpha_phase_map_rounds_to_nearest_and_wraps(self) -> None:
        context = {"source_video_indices": list(range(9)), "target_frame_count": 27}
        expected = [0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4,
                    5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 0]
        self.assertEqual(interpolation.alpha_phase_map(context), expected)

    def test_alpha_phase_map_follows_cycle_order(self) -> None:
        context = {"source_video_indices": [2, 0, 1], "target_frame_count": 6}
        self.assertEqual(interpolation.alpha_phase_map(context), [2, 0, 0, 1, 1, 2])

    def test_build_patch_prefers_the_deterministic_phase_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frames_manifest, upscale_manifest, base, returned = self.make_fixture(root)
            context = interpolation.load_context(
                resref="TESTA",
                frames_manifest_path=frames_manifest,
                upscale_manifest_path=upscale_manifest,
                base_pack_path=base,
                slot_fps=12,
            )
            plan = interpolation.public_plan(context)
            work = root / "work"
            work.mkdir()
            interpolation.write_json(work / "handoff.json", {
                "schema": interpolation.HANDOFF_SCHEMA,
                "status": "prepared",
                "plan": plan,
                "inputs": {
                    "frames_manifest": frames_manifest.as_posix(),
                    "frames_manifest_sha256": sha(frames_manifest),
                    "upscale_manifest": upscale_manifest.as_posix(),
                    "upscale_manifest_sha256": sha(upscale_manifest),
                    "base_pack": base.as_posix(),
                    "base_pack_manifest_sha256": sha(base / "manifest.json"),
                    "base_registry_sha256": sha(base / runtime_pack.REGISTRY_NAME),
                },
                "source_assets": interpolation.source_asset_hashes(context),
                "return_contract": plan["return_contract"],
            })

            returned.mkdir()
            for index, colour in enumerate([(255, 0, 0), (170, 85, 0), (85, 170, 0), (0, 255, 0)]):
                Image.new("RGB", (8, 4), colour).save(returned / f"returned_{index:03d}.png")
            interpolation.audit_returned_frames(work, returned)

            phase_map = interpolation.alpha_phase_map(context)
            self.assertEqual(phase_map, [0, 1, 1, 0])
            (work / "interpolation").mkdir()
            interpolation.write_json(work / "interpolation" / "interpolation.json", {
                "schema": interpolation.INTERPOLATION_SCHEMA,
                "status": "completed",
                "handoff_sha256": sha(work / "handoff.json"),
                "alpha_phase_map": phase_map,
            })

            patch = interpolation.build_patch(work, work / "runtime-patch", resume=False)
            self.assertEqual([frame["alpha_source_frame"] for frame in patch["frames"]], phase_map)
            # The colour search would have paired the middle frames differently.
            self.assertEqual([frame["alpha_nearest_rgb_frame"] for frame in patch["frames"]], [0, 0, 1, 1])
            self.assertTrue(all(frame["alpha_phase_source"] == "deterministic" for frame in patch["frames"]))

    def test_build_patch_falls_back_to_image_matching(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frames_manifest, upscale_manifest, base, returned = self.make_fixture(root)
            context = interpolation.load_context(
                resref="TESTA",
                frames_manifest_path=frames_manifest,
                upscale_manifest_path=upscale_manifest,
                base_pack_path=base,
                slot_fps=12,
            )
            plan = interpolation.public_plan(context)
            work = root / "work"
            work.mkdir()
            interpolation.write_json(work / "handoff.json", {
                "schema": interpolation.HANDOFF_SCHEMA,
                "status": "prepared",
                "plan": plan,
                "inputs": {
                    "frames_manifest": frames_manifest.as_posix(),
                    "frames_manifest_sha256": sha(frames_manifest),
                    "upscale_manifest": upscale_manifest.as_posix(),
                    "upscale_manifest_sha256": sha(upscale_manifest),
                    "base_pack": base.as_posix(),
                    "base_pack_manifest_sha256": sha(base / "manifest.json"),
                    "base_registry_sha256": sha(base / runtime_pack.REGISTRY_NAME),
                },
                "source_assets": interpolation.source_asset_hashes(context),
                "return_contract": plan["return_contract"],
            })
            returned.mkdir()
            for index, colour in enumerate([(255, 0, 0), (170, 85, 0), (85, 170, 0), (0, 255, 0)]):
                Image.new("RGB", (8, 4), colour).save(returned / f"returned_{index:03d}.png")
            interpolation.audit_returned_frames(work, returned)

            patch = interpolation.build_patch(work, work / "runtime-patch", resume=False)
            self.assertEqual([frame["alpha_source_frame"] for frame in patch["frames"]], [0, 0, 1, 1])
            self.assertTrue(all(frame["alpha_phase_source"] == "nearest-rgb" for frame in patch["frames"]))


if __name__ == "__main__":
    unittest.main()
