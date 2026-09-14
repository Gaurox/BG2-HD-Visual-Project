from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import reboutcx_full as full  # noqa: E402
from run_creature_sprite_x2 import SourceFrame  # noqa: E402


def make_frame(resref: str) -> SourceFrame:
    palette = np.zeros((256, 3), dtype=np.uint8)
    palette[0] = (0, 255, 0)
    palette[3] = (180, 40, 20)
    indices = np.asarray([[0, 3]], dtype=np.uint8)
    rgba = np.empty((1, 2, 4), dtype=np.uint8)
    rgba[..., :3] = palette[indices]
    rgba[..., 3] = np.where(indices == 0, 0, 255).astype(np.uint8)
    return SourceFrame(resref, 0, 2, 1, 1, -2, 0, indices, palette, rgba.tobytes())


class ReboutCXFullRegistryTests(unittest.TestCase):
    def test_render_contract_digest_separates_character_layers_and_palettes(self) -> None:
        classes = {"transparent": [0], "material": list(range(1, 256))}
        base = {
            "runtime_profile": "character-bg2ee-2.7.3.0",
            "layer": "body",
            "null_frame_marker": 2,
            "reboutcx": {"model_sha256": "A", "target_scale": 2},
        }
        palette = {"id": "fixed", "profiles": [{"name": "reference", "sha256": "B"}]}
        body = full.render_contract_digest(base, classes, palette)
        weapon = full.render_contract_digest({**base, "layer": "weapon"}, classes, palette)
        changed_palette = full.render_contract_digest(
            base,
            classes,
            {"id": "fixed", "profiles": [{"name": "reference", "sha256": "C"}]},
        )
        self.assertNotEqual(body, weapon)
        self.assertNotEqual(body, changed_palette)
        self.assertEqual(body, full.render_contract_digest(base, classes, palette))

    def test_component_preserves_native_cycles_and_can_be_cloned_by_resref(self) -> None:
        payload = np.asarray([[0, 0, 3, 3], [0, 0, 3, 3]], dtype=np.uint8)
        evidence = [{"indices_sha256": hashlib.sha256(payload.tobytes()).hexdigest().upper()}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.bamc"
            source_path.write_bytes(b"source")
            source = {
                "source": {"name": "TEST"},
                "source_path": source_path,
                "frames": [make_frame("TEST")],
                "cycles": [
                    {"index": 0, "frame_indices": [0, 0]},
                    {"index": 1, "frame_indices": []},
                ],
            }
            first = root / "TEST.registry"
            with first.open("wb") as stream:
                full.write_component_header(
                    stream,
                    animation_id=0x7F02,
                    resref="TEST",
                    source_sha256=full.sha256_file(source_path),
                    frame_count=1,
                    cycle_count=2,
                )
                full.write_frame_record(stream, source["frames"][0], payload)
                full.write_cycles(stream, source["cycles"])
            info = full.validate_component_registry(
                first,
                animation_id=0x7F02,
                resource=source,
                frame_manifest=evidence,
            )
            self.assertEqual(info["scale"], 2)
            self.assertEqual(info["frame_count"], 1)
            self.assertEqual(info["resource_count"], 1)

            clone = root / "COPY.registry"
            full.copy_component_for_resref(first, clone, "COPY")
            copied = {
                **source,
                "source": {"name": "COPY"},
                "frames": [make_frame("COPY")],
            }
            clone_info = full.validate_component_registry(
                clone,
                animation_id=0x7F02,
                resource=copied,
                frame_manifest=evidence,
            )
            self.assertNotEqual(info["sha256"], clone_info["sha256"])


if __name__ == "__main__":
    unittest.main()
