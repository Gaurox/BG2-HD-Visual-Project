from __future__ import annotations

import hashlib
import json
import copy
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_animation_runtime_pack as runtime_v1  # noqa: E402
import run_animation_upscale_30fps_v2 as pipeline  # noqa: E402
import build_manual_alpha_mask_30fps_v2 as manual_mask  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AnimationUpscale30FpsV2Tests(unittest.TestCase):
    def test_nearest_opaque_dilate_replaces_hidden_chroma(self) -> None:
        source = Image.new("RGBA", (3, 1), (0, 255, 0, 0))
        source.putpixel((1, 0), (120, 70, 50, 255))

        rgb, replaced = pipeline.nearest_opaque_dilate(source)

        self.assertEqual(replaced, 2)
        self.assertEqual(list(rgb.getdata()), [(120, 70, 50)] * 3)

    def make_fixture(self, root: Path, cycle: list[int] | None = None) -> tuple[Path, Path]:
        resref = "TESTA"
        cycle = cycle or [0, 1]
        run = root / "spatial-run"
        frames_root = run / "resources" / resref / "01_frames_x1"
        upscale_root = run / "resources" / resref / "02_upscale_x4"
        aligned_root = upscale_root / "aligned_rgba"
        rgb_root = upscale_root / "rgb"
        for directory in (frames_root, aligned_root, rgb_root):
            directory.mkdir(parents=True)

        colours = [(220, 20, 10), (10, 40, 230)]
        alpha_values = [64, 192]
        upscale_frames = []
        for index, (colour, alpha_value) in enumerate(zip(colours, alpha_values, strict=True)):
            rgb = Image.new("RGB", (8, 4), colour)
            rgba = Image.new("RGBA", (8, 4), (*colour, alpha_value))
            rgb_path = rgb_root / f"frame_{index:03d}.png"
            aligned_path = aligned_root / f"frame_{index:03d}.png"
            rgb.save(rgb_path)
            rgba.save(aligned_path)
            upscale_frames.append({
                "frame": index,
                "logical_size_x1": [2, 1],
                "physical_size_xn": [8, 4],
                "centre_x1": [1, 1],
                "runtime_crop_box_xn": [0, 0, 8, 4],
                "rgb_xn": f"rgb/{rgb_path.name}",
                "rgb_xn_sha256": sha(rgb_path),
                "aligned_rgba_xn": f"aligned_rgba/{aligned_path.name}",
                "aligned_rgba_xn_sha256": sha(aligned_path),
            })

        (frames_root / "manifest.json").write_text(json.dumps({
            "schema": runtime_v1.FRAME_SCHEMA,
            "frame_count": 2,
            "geometry_mode": "uniform",
            "cycles": [{"cycle": 0, "frame_indices": cycle}],
        }), encoding="utf-8")
        (upscale_root / "manifest.json").write_text(json.dumps({
            "schema": runtime_v1.UPSCALE_SCHEMA,
            "status": "completed",
            "scale": 4,
            "aligned_canvas_size_x1": [2, 1],
            "frames": upscale_frames,
        }), encoding="utf-8")
        (run / "manifest.json").write_text(json.dumps({
            "schema": runtime_v1.RUN_SCHEMA,
            "status": "completed",
            "request": {"scale": 4},
            "resources": [{
                "resref": resref,
                "status": "completed",
                "frames_x1": f"resources/{resref}/01_frames_x1",
                "upscale": f"resources/{resref}/02_upscale_x4",
            }],
        }), encoding="utf-8")

        pack = root / "base-pack"
        pack.mkdir()
        runtime_frames = []
        for index, (colour, alpha_value) in enumerate(zip(colours, alpha_values, strict=True)):
            name = runtime_v1.asset_name(resref, index)
            path = pack / name
            path.write_bytes(bytes((*colour, alpha_value)) * (8 * 4))
            runtime_frames.append({
                "frame": index,
                "logical_size_x1": [2, 1],
                "physical_size_x4": [8, 4],
                "centre_x1": [1, 1],
                "asset": name,
                "sha256": sha(path),
                "bytes": path.stat().st_size,
            })
        resource = {
            "resref": resref,
            "frame_count": 2,
            "cycle_count": 1,
            "geometry_mode": "uniform",
            "frames": runtime_frames,
            "cycles": [{"cycle": 0, "frame_indices": cycle}],
            "assets": [
                {"name": frame["asset"], "sha256": frame["sha256"], "bytes": frame["bytes"]}
                for frame in runtime_frames
            ],
        }
        registry = runtime_v1.registry_from_resources([resource])
        registry_path = pack / runtime_v1.REGISTRY_NAME
        registry_path.write_bytes(registry)
        (pack / "manifest.json").write_text(json.dumps({
            "schema": runtime_v1.PACK_SCHEMA,
            "status": "completed",
            "scale": 4,
            "registry": runtime_v1.REGISTRY_NAME,
            "registry_sha256": sha(registry_path),
            "registry_bytes": registry_path.stat().st_size,
            "resource_count": 1,
            "frame_count": 2,
            "resources": [resource],
        }), encoding="utf-8")
        (pack / "install-backups").mkdir()
        return run, pack

    @staticmethod
    def fake_external_command(command: list[str], *, environment: dict[str, str] | None = None) -> None:
        destination = Path(command[-1])
        if destination.name == "out_%04d.png":
            source_pattern = Path(command[command.index("-i") + 1])
            source_root = source_pattern.parent
            inputs = sorted(source_root.glob("in_*.png"))
            output_root = destination.parent
            output_root.mkdir(parents=True, exist_ok=True)
            input_framerate = command[command.index("-framerate") + 1]
            numerator, *denominator = input_framerate.split("/", maxsplit=1)
            input_fps = float(numerator) / float(denominator[0]) if denominator else float(numerator)
            subdivisions = round(30 / input_fps)
            output_index = 0
            for left_path, right_path in zip(inputs[:-1], inputs[1:], strict=True):
                with Image.open(left_path) as left_opened, Image.open(right_path) as right_opened:
                    left = left_opened.convert("RGB")
                    right = right_opened.convert("RGB")
                    left.save(output_root / f"out_{output_index:04d}.png")
                    output_index += 1
                    for subphase in range(1, subdivisions):
                        Image.blend(left, right, subphase / subdivisions).save(
                            output_root / f"out_{output_index:04d}.png")
                        output_index += 1
            with Image.open(inputs[-1]) as last:
                last.convert("RGB").save(output_root / f"out_{output_index:04d}.png")
            return
        destination.write_bytes(("fake-video:" + destination.name).encode("ascii"))

    def test_build_resume_approval_and_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_run, base_pack = self.make_fixture(root)
            plan = pipeline.build_plan(source_run, base_pack, ["TESTA"])
            self.assertEqual(plan["targets"][0]["added_intermediate_frames"], 2)
            self.assertEqual(plan["targets"][0]["cycles"][0]["timeline_frame_indices"],
                             [0, 2, 1, 3])

            fake_topaz = root / "fake-topaz.exe"
            fake_topaz.write_bytes(b"test")
            model_dir = root / "models"
            model_dir.mkdir()
            (model_dir / "apo-8.json").write_text("{}", encoding="utf-8")
            output = root / "temporal-run"
            with mock.patch.object(pipeline, "run_checked", side_effect=self.fake_external_command):
                manifest = pipeline.build_run(
                    source_run, base_pack, output, ["TESTA"], plan["plan_sha256"],
                    fake_topaz, model_dir, "apo-8", "-2", "ffmpeg", False,
                )

            self.assertEqual(manifest["qa_status"], "pending-explicit-user-approval")
            pack_manifest, resources = pipeline.validate_v2_pack(output / "03_runtime_pack")
            self.assertEqual(pack_manifest["registry_version"], 3)
            self.assertEqual(resources[0]["frame_count"], 4)
            self.assertEqual(resources[0]["playback_mode"], "TimedTimeline")
            registry = (output / "03_runtime_pack" / pipeline.REGISTRY_NAME).read_bytes()
            self.assertEqual(struct.unpack_from("<IIII", registry, 8), (3, 4, 1, 0))

            first_middle = pipeline.rgba_from_raw(
                output / "03_runtime_pack" / "AAX4-TESTA-frame002.rgba", [8, 4]
            )
            second_middle = pipeline.rgba_from_raw(
                output / "03_runtime_pack" / "AAX4-TESTA-frame003.rgba", [8, 4]
            )
            self.assertEqual(set(first_middle.getchannel("A").tobytes()), {64})
            self.assertEqual(set(second_middle.getchannel("A").tobytes()), {192})

            with mock.patch.object(pipeline, "run_checked", side_effect=AssertionError("no rerun")):
                resumed = pipeline.build_run(
                    source_run, base_pack, output, ["TESTA"], plan["plan_sha256"],
                    fake_topaz, model_dir, "apo-8", "-2", "ffmpeg", True,
                )
            self.assertEqual(resumed["registry_sha256"], manifest["registry_sha256"])

            run_hash = sha(output / "manifest.json")
            approval = pipeline.approve_run(output, run_hash, ["TESTA"])
            self.assertEqual(approval["status"], "accepted")
            self.assertEqual(approval["run_manifest_sha256"], run_hash)

            powershell = shutil.which("pwsh") or shutil.which("powershell")
            if powershell:
                project_root = Path(__file__).resolve().parents[2]
                installer = project_root / "pipeline" / "scripts" / "Install-AreaAnimations-30fps-V2.ps1"
                restorer = project_root / "pipeline" / "scripts" / "Restore-AreaAnimations-30fps-V2.ps1"
                game = root / "game"
                game_assets = game / "iee-assets"
                game_assets.mkdir(parents=True)
                original_dll = b"original-dll"
                original_ini = b"[Shaders]\r\nEnableAreaAnimationX4 = false\r\n"
                (game / "InfinityEngine-Enhancer.dll").write_bytes(original_dll)
                (game / "InfinityEngine-Enhancer.ini").write_bytes(original_ini)
                shutil.copyfile(base_pack / pipeline.REGISTRY_NAME,
                                game_assets / pipeline.REGISTRY_NAME)
                base_manifest = json.loads((base_pack / "manifest.json").read_text(encoding="utf-8"))
                for asset in base_manifest["resources"][0]["assets"]:
                    shutil.copyfile(base_pack / asset["name"], game_assets / asset["name"])
                runtime_dll = root / "runtime-v2.dll"
                runtime_dll.write_bytes(b"runtime-v2-dll")
                backups = root / "backups"
                install_command = [
                    powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(installer),
                    "-RunRoot", str(output), "-DllPath", str(runtime_dll),
                    "-GameRoot", str(game), "-BackupRoot", str(backups),
                ]
                verify = subprocess.run(install_command + ["-VerifyOnly"], capture_output=True, text=True)
                self.assertEqual(verify.returncode, 0, verify.stderr)
                self.assertFalse((game_assets / "AAX4-TESTA-frame002.rgba").exists())
                install = subprocess.run(install_command, capture_output=True, text=True)
                self.assertEqual(install.returncode, 0, install.stderr)
                self.assertEqual((game / "InfinityEngine-Enhancer.dll").read_bytes(), b"runtime-v2-dll")
                self.assertEqual(sha(game_assets / pipeline.REGISTRY_NAME), manifest["registry_sha256"])
                self.assertTrue((game_assets / "AAX4-TESTA-frame002.rgba").is_file())
                backup = next(backups.glob("30fps-v2-backup-*"))
                restore_command = [
                    powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(restorer),
                    "-BackupPath", str(backup), "-GameRoot", str(game),
                ]
                verify_restore = subprocess.run(
                    restore_command + ["-VerifyOnly"], capture_output=True, text=True
                )
                self.assertEqual(verify_restore.returncode, 0, verify_restore.stderr)
                restore = subprocess.run(restore_command, capture_output=True, text=True)
                self.assertEqual(restore.returncode, 0, restore.stderr)
                self.assertEqual((game / "InfinityEngine-Enhancer.dll").read_bytes(), original_dll)
                self.assertEqual((game / "InfinityEngine-Enhancer.ini").read_bytes(), original_ini)
                self.assertFalse((game_assets / "AAX4-TESTA-frame002.rgba").exists())

            review_path = output / manifest["reviews"][0]["file"]
            review_path.write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "review .*V2 modifiée"):
                pipeline.validate_run(output)

    def test_rejects_plan_change_and_base_rgb_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_run, base_pack = self.make_fixture(root)
            plan = pipeline.build_plan(source_run, base_pack, ["TESTA"])
            with self.assertRaisesRegex(RuntimeError, "hash de plan non approuvé"):
                pipeline.build_run(
                    source_run, base_pack, root / "output", ["TESTA"], "0" * 64,
                    root / "missing.exe", root / "missing-models", "apo-8", "-2",
                    "ffmpeg", False,
                )
            asset = base_pack / "AAX4-TESTA-frame000.rgba"
            raw = bytearray(asset.read_bytes())
            raw[0] ^= 1
            asset.write_bytes(raw)
            with self.assertRaisesRegex(RuntimeError, "asset runtime v1 incohérent"):
                pipeline.build_plan(source_run, base_pack, ["TESTA"])

    def test_collapses_uniform_duplicate_holds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_run, base_pack = self.make_fixture(root, [0, 0, 1, 1])
            plan = pipeline.build_plan(
                source_run, base_pack, ["TESTA"], collapse_uniform_duplicate_holds=True,
            )
            target = plan["targets"][0]
            cycle = target["cycles"][0]
            self.assertEqual(cycle["timing_strategy"], "collapse-uniform-duplicate-holds")
            self.assertEqual(cycle["interpolation_input_frame_indices"], [0, 1])
            self.assertEqual(cycle["hold_slots"], 2)
            self.assertEqual(cycle["phases_per_transition"], 4)
            self.assertEqual(target["added_intermediate_frames"], 6)
            self.assertEqual(target["output_frame_count"], 8)
            self.assertEqual(cycle["timeline_frame_indices"], [0, 2, 3, 4, 1, 5, 6, 7])
            self.assertEqual(cycle["duration_seconds"], 4 / 15)

            fake_topaz = root / "fake-topaz.exe"
            fake_topaz.write_bytes(b"test")
            model_dir = root / "models"
            model_dir.mkdir()
            (model_dir / "apo-8.json").write_text("{}", encoding="utf-8")
            output = root / "deheld-run"
            with mock.patch.object(pipeline, "run_checked", side_effect=self.fake_external_command):
                manifest = pipeline.build_run(
                    source_run, base_pack, output, ["TESTA"], plan["plan_sha256"],
                    fake_topaz, model_dir, "apo-8", "-2", "ffmpeg", False,
                    collapse_uniform_duplicate_holds=True,
                )

            pack_manifest, resources = pipeline.validate_v2_pack(output / "03_runtime_pack")
            self.assertEqual(pack_manifest["registry_version"], 3)
            self.assertEqual(resources[0]["frame_count"], 8)
            self.assertEqual(resources[0]["cycles"][0]["timeline_frame_indices"],
                             [0, 2, 3, 4, 1, 5, 6, 7])
            report = json.loads((output / "work" / "TESTA" / "cycle_000" / "cycle.json").read_text())
            self.assertEqual(report["topaz"]["input_framerate"], "15/2")
            self.assertEqual(len(report["intermediate_frames"]), 6)
            self.assertEqual([item["subphase"] for item in report["intermediate_frames"]],
                             [1, 2, 3, 1, 2, 3])
            self.assertEqual(manifest["timed_resources"], ["TESTA"])

    def test_manual_mask_replaces_anchors_and_restores(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_run, base_pack = self.make_fixture(root)
            plan = pipeline.build_plan(source_run, base_pack, ["TESTA"])
            fake_topaz = root / "fake-topaz.exe"
            fake_topaz.write_bytes(b"test")
            model_dir = root / "models"
            model_dir.mkdir()
            (model_dir / "apo-8.json").write_text("{}", encoding="utf-8")
            temporal_run = root / "temporal-run"
            with mock.patch.object(pipeline, "run_checked", side_effect=self.fake_external_command):
                pipeline.build_run(
                    source_run, base_pack, temporal_run, ["TESTA"], plan["plan_sha256"],
                    fake_topaz, model_dir, "apo-8", "-2", "ffmpeg", False,
                )

            mask = root / "mask.png"
            Image.new("L", (8, 4), 0).save(mask)
            masked_run = root / "masked-run"
            with mock.patch.object(pipeline, "run_checked", side_effect=self.fake_external_command):
                manifest = manual_mask.build(temporal_run, "TESTA", mask, masked_run, "ffmpeg")
            pack_manifest, resources = pipeline.validate_v2_pack(masked_run / "03_runtime_pack")
            self.assertEqual(len(pack_manifest["replacement_assets"]), 2)
            self.assertEqual(len(pack_manifest["new_assets"]), 2)
            self.assertEqual(resources[0]["frame_count"], 4)
            self.assertEqual(set(pipeline.rgba_from_raw(
                masked_run / "03_runtime_pack" / "AAX4-TESTA-frame000.rgba", [8, 4]
            ).getchannel("A").tobytes()), {0})
            self.assertEqual(manifest["manual_alpha_patch"]["targets"][0]["masked_frame_count"], 4)
            mask_record = manifest["manual_alpha_patch"]
            self.assertEqual(mask_record["mask_storage"], "run-relative-v1")
            self.assertEqual(
                mask_record["targets"][0]["mask_source"],
                "manual-mask/TESTA/source.png",
            )
            sealed_mask = masked_run / "manual-mask" / "TESTA" / "source.png"
            self.assertEqual(sha(sealed_mask), mask_record["targets"][0]["mask_sha256"])

            sealed_bytes = sealed_mask.read_bytes()
            sealed_mask.write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "masque manuel modifié"):
                pipeline.validate_run(masked_run)
            sealed_mask.write_bytes(sealed_bytes)

            run_hash = sha(masked_run / "manifest.json")
            pipeline.approve_run(masked_run, run_hash, ["TESTA"])
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            if powershell:
                project_root = Path(__file__).resolve().parents[2]
                installer = project_root / "pipeline" / "scripts" / "Install-AreaAnimations-30fps-V2.ps1"
                restorer = project_root / "pipeline" / "scripts" / "Restore-AreaAnimations-30fps-V2.ps1"
                game = root / "game"
                assets = game / "iee-assets"
                assets.mkdir(parents=True)
                (game / "InfinityEngine-Enhancer.dll").write_bytes(b"original-dll")
                (game / "InfinityEngine-Enhancer.ini").write_bytes(b"[Shaders]\r\n")
                shutil.copyfile(base_pack / pipeline.REGISTRY_NAME, assets / pipeline.REGISTRY_NAME)
                for frame in json.loads((base_pack / "manifest.json").read_text())["resources"][0]["frames"]:
                    shutil.copyfile(base_pack / frame["asset"], assets / frame["asset"])
                runtime_dll = root / "runtime-v2.dll"
                runtime_dll.write_bytes(b"runtime-v2-dll")
                backups = root / "backups"
                install_command = [
                    powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(installer),
                    "-RunRoot", str(masked_run), "-DllPath", str(runtime_dll),
                    "-GameRoot", str(game), "-BackupRoot", str(backups),
                ]
                installed = subprocess.run(install_command, capture_output=True, text=True)
                self.assertEqual(installed.returncode, 0, installed.stderr)
                self.assertEqual(set(pipeline.rgba_from_raw(
                    assets / "AAX4-TESTA-frame000.rgba", [8, 4]
                ).getchannel("A").tobytes()), {0})
                backup = next(backups.glob("30fps-v2-backup-*"))
                restore_command = [
                    powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(restorer),
                    "-BackupPath", str(backup), "-GameRoot", str(game),
                ]
                restored = subprocess.run(restore_command, capture_output=True, text=True)
                self.assertEqual(restored.returncode, 0, restored.stderr)
                self.assertEqual(set(pipeline.rgba_from_raw(
                    assets / "AAX4-TESTA-frame000.rgba", [8, 4]
                ).getchannel("A").tobytes()), {64})
                self.assertFalse((assets / "AAX4-TESTA-frame002.rgba").exists())

    def test_adopt_clock_patch_and_runtime_only_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _source_run, base_pack = self.make_fixture(root)
            base_manifest, resources, _sources = pipeline.load_base_pack(base_pack)
            resource = copy.deepcopy(resources[0])
            patch_root = root / "clock-patch"
            patch_root.mkdir()
            new_frames = []
            for index, colour in enumerate(((120, 30, 80), (80, 30, 120)), start=2):
                name = runtime_v1.asset_name("TESTA", index)
                path = patch_root / name
                path.write_bytes(bytes((*colour, 255)) * (8 * 4))
                new_frames.append({
                    "frame": index,
                    "phase": (index - 2) * 2 + 1,
                    "asset": name,
                    "logical_size_x1": [2, 1],
                    "physical_size_x4": [8, 4],
                    "bytes": path.stat().st_size,
                    "sha256": sha(path),
                })
                resource["frames"].append({
                    "frame": index,
                    "logical_size_x1": [2, 1],
                    "physical_size_x4": [8, 4],
                    "centre_x1": [1, 1],
                    "asset": name,
                    "sha256": sha(path),
                    "bytes": path.stat().st_size,
                })
                resource["assets"].append({"name": name, "sha256": sha(path), "bytes": path.stat().st_size})
            resource["frame_count"] = 4
            resource["playback_mode"] = "TimedTimeline"
            resource["native_fps"] = pipeline.rate_record(pipeline.NATIVE_FPS)
            resource["target_fps"] = pipeline.rate_record(pipeline.TARGET_FPS)
            resource["cycles"][0]["timeline_frame_indices"] = [0, 2, 1, 3]
            registry = pipeline.registry_v2_from_resources(
                [resource], pipeline.LEGACY_REGISTRY_VERSION)
            registry_path = patch_root / pipeline.REGISTRY_NAME
            registry_path.write_bytes(registry)
            base_resource = resources[0]
            (patch_root / "manifest.json").write_text(json.dumps({
                "schema": "bg2-upscale-area-animation-runtime-clock-patch-v1",
                "status": "completed",
                "resref": "TESTA",
                "scale": 4,
                "registry_version": 2,
                "playback_mode": "TimedTimeline",
                "native_fps": [15, 1],
                "target_fps": [30, 1],
                "native_cycle_slots": 2,
                "timeline_phases": 4,
                "timeline_frame_indices": [0, 2, 1, 3],
                "base_registry_sha256": base_manifest["registry_sha256"],
                "base_registry_bytes": base_manifest["registry_bytes"],
                "target_registry": pipeline.REGISTRY_NAME,
                "target_registry_sha256": sha(registry_path),
                "target_registry_bytes": registry_path.stat().st_size,
                "base_frames": [
                    {"frame": frame["frame"], "asset": frame["asset"],
                     "bytes": frame["bytes"], "sha256": frame["sha256"]}
                    for frame in base_resource["frames"]
                ],
                "new_frames": new_frames,
            }), encoding="utf-8")
            promoted = root / "promoted-v2"
            manifest = pipeline.adopt_clock_patch(base_pack, patch_root, promoted, False)
            self.assertEqual(manifest["timed_resources"], ["TESTA"])
            self.assertEqual(manifest["registry_version"], 3)
            self.assertNotEqual(manifest["registry_sha256"], sha(registry_path))
            pipeline.validate_v2_pack(promoted)

            plan = pipeline.build_plan(None, base_pack, ["TESTA"])
            self.assertEqual(plan["input_mode"], "runtime-uniform-base")
            self.assertEqual(plan["targets"][0]["base_frame_count"], 2)
            self.assertEqual(plan["targets"][0]["added_intermediate_frames"], 2)
            with self.assertRaisesRegex(RuntimeError, "déjà TimedTimeline"):
                pipeline.build_plan(None, promoted, ["TESTA"])


class NormaliseResrefTests(unittest.TestCase):
    def test_accepts_underscore_resref(self) -> None:
        # Infinity Engine resrefs allow underscores (FIRE_1, FIRE_4, FIRE_4GS).
        # The V1 pipeline and the runtime already handle them; only this
        # normaliser used to reject them via str.isalnum().
        self.assertEqual(pipeline.normalise_resref("fire_4"), "FIRE_4")
        self.assertEqual(pipeline.normalise_resref("FIRE_4GS"), "FIRE_4GS")

    def test_rejects_empty_overlong_and_path_characters(self) -> None:
        for bad in ("", "   ", "____", "AM_07000X", "AM/0700", "AM.0700", "AM 0700"):
            with self.assertRaises(RuntimeError):
                pipeline.normalise_resref(bad)


if __name__ == "__main__":
    unittest.main()
