from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import reboutcx_multipart_qa as multipart  # noqa: E402


class ReboutCXMultipartQATests(unittest.TestCase):
    def test_validation_requires_complete_known_parts(self) -> None:
        job = {
            "multipart_qa": {
                "compositions": [
                    {
                        "name": "test",
                        "part_count": 2,
                        "duration_ms": 100,
                        "steps": [
                            {
                                "parts": [
                                    {"resref": "PARTA", "frame": 0},
                                    {"resref": "MISSING", "frame": 0},
                                ]
                            }
                        ],
                    }
                ]
            }
        }
        with self.assertRaisesRegex(RuntimeError, "unknown multipart frame"):
            multipart.validate_compositions(job, {("PARTA", 0): {}})

    def test_render_composes_parts_and_preserves_step_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            old_root = multipart.PROJECT_ROOT
            multipart.PROJECT_ROOT = root
            try:
                lookup = {}
                colors = {"PARTA": (255, 0, 0, 255), "PARTB": (0, 0, 255, 255)}
                for resref, center_x in (("PARTA", 0), ("PARTB", -1)):
                    files = {}
                    for variant in (
                        "native_x2",
                        "xbr_x2",
                        "reboutcx_raw_x2",
                        "reboutcx_quantized_x2",
                    ):
                        path = root / f"{resref}-{variant}.png"
                        Image.new("RGBA", (2, 2), colors[resref]).save(path)
                        files[variant] = {
                            "path": path.name,
                            "sha256": multipart.sha256_file(path),
                        }
                    lookup[(resref, 0)] = {
                        "resref": resref,
                        "source_frame": 0,
                        "width": 1,
                        "height": 1,
                        "center_x": center_x,
                        "center_y": 0,
                        "files": files,
                    }
                composition = {
                    "name": "two-parts",
                    "duration_ms": 100,
                    "part_count": 2,
                    "steps": [
                        {"label": "first", "keys": [("PARTA", 0), ("PARTB", 0)]},
                        {"label": "second", "keys": [("PARTA", 0), ("PARTB", 0)]},
                    ],
                }
                destination = root / "qa" / "two-parts.gif"
                evidence = multipart.render_composition(composition, lookup, destination)
                with Image.open(destination) as image:
                    self.assertEqual(image.n_frames, 2)
                self.assertEqual(evidence["part_count"], 2)
                self.assertEqual(evidence["panel_size"], [4, 2])
                self.assertEqual(evidence["sha256"], multipart.sha256_file(destination))
            finally:
                multipart.PROJECT_ROOT = old_root


if __name__ == "__main__":
    unittest.main()
