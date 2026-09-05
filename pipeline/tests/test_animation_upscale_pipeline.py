from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import upscale_animation_frames as pipeline  # noqa: E402


class FakeComfyClient:
    def __init__(self, server: str, poll_seconds: float, timeout_seconds: float) -> None:
        self.source: Path | None = None
        self.scale = 1
        self.save_id = ""

    def preflight(self) -> dict:
        return {"devices": [{"name": "fake-device"}]}

    def upload(self, source: Path, subfolder: str) -> str:
        self.source = source
        return source.name

    def queue(self, prompt: dict) -> str:
        resize = next(node for node in prompt.values() if node.get("class_type") == "ResizeImageMaskNode")
        self.scale = int(resize["inputs"]["resize_type.multiplier"])
        self.save_id = next(
            node_id for node_id, node in prompt.items() if node.get("class_type") == "SaveImage"
        )
        return "fake-prompt"

    def wait_history(self, prompt_id: str) -> dict:
        return {"outputs": {self.save_id: {"images": [{"filename": "fake.png"}]}}}

    def download(self, image_info: dict, destination: Path) -> None:
        assert self.source is not None
        with Image.open(self.source) as opened:
            image = opened.convert("RGB")
        image = image.resize(
            (image.width * self.scale, image.height * self.scale),
            Image.Resampling.NEAREST,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="PNG")


class AnimationUpscalePipelineTests(unittest.TestCase):
    def test_variable_geometry_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rgb_dir = root / "rgb"
            alpha_dir = root / "alpha"
            rgb_dir.mkdir()
            alpha_dir.mkdir()
            for index in range(2):
                name = f"frame_{index:03d}.png"
                Image.new("RGB", (4, 4), (40 + index, 80, 120)).save(rgb_dir / name)
                Image.new("L", (4, 4), 255).save(alpha_dir / name)

            frame_manifest = root / "frames.json"
            frame_manifest.write_text(
                json.dumps({
                    "schema": "bg2-upscale-animation-frames-x1-v1",
                    "aligned_canvas_size": [4, 4],
                    "geometry_mode": "per-frame",
                    "frames": [
                        {
                            "frame": 0,
                            "file": "frame_000.png",
                            "source_size": [2, 3],
                            "centre": [1, 3],
                            "canvas_offset": [1, 0],
                        },
                        {
                            "frame": 1,
                            "file": "frame_001.png",
                            "source_size": [4, 4],
                            "centre": [2, 4],
                            "canvas_offset": [0, 0],
                        },
                    ],
                }),
                encoding="utf-8",
            )
            output = root / "output"
            arguments = [
                str(rgb_dir),
                str(alpha_dir),
                str(output),
                "--frame-manifest",
                str(frame_manifest),
                "--scale",
                "2",
                "--pad",
                "1",
            ]
            with mock.patch.object(pipeline, "ComfyClient", FakeComfyClient):
                pipeline.main(arguments)

            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["geometry_mode"], "per-frame")
            self.assertEqual(manifest["frames"][0]["logical_size_x1"], [2, 3])
            self.assertEqual(manifest["frames"][0]["physical_size_xn"], [4, 6])
            self.assertEqual(manifest["frames"][1]["physical_size_xn"], [8, 8])
            self.assertEqual((output / "raw_rgba" / "frame_000.rgba").stat().st_size, 4 * 6 * 4)
            self.assertEqual((output / "raw_rgba" / "frame_001.rgba").stat().st_size, 8 * 8 * 4)

            manifest_hash = pipeline.sha256_file(output / "manifest.json")
            with mock.patch.object(pipeline, "ComfyClient", side_effect=AssertionError("no GPU call")):
                pipeline.main(arguments + ["--resume"])
            self.assertEqual(manifest_hash, pipeline.sha256_file(output / "manifest.json"))

            tampered = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            tampered["frames"][0]["logical_size_x1"] = [4, 4]
            (output / "manifest.json").write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "logical_size_x1"):
                pipeline.main(arguments + ["--resume"])


if __name__ == "__main__":
    unittest.main()
