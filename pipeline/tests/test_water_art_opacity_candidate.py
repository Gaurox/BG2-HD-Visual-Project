"""Paired authored-art policy guards; no game, asset generation or installation."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "water_art_registry_generator",
    ROOT / "engine/InfinityEngine-Enhancer/source-patchee/tools/generate_water_route2_registry.py",
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def fixture():
    return {
        "id": "night", "wed": {"resref": "AR0300N", "overlay_slots": ["AR0300N", "WTLAKE"],
                                  "grid": {"width": 80, "height": 60}, "sha256": "0" * 64},
        "base_tis": {"resref": "AR0300N", "bytes": 63912, "sha256": "0" * 64,
                     "tile_count": 5324, "pages": []},
        "overlay": {"slot": 1, "tis_resref": "WTLAKE", "tis_bytes": 456,
                    "tis_sha256": "0" * 64, "tile_count": 36, "tile_dimension": 256, "pages": []},
        "approved_strength": 0.7, "material_id": 1, "overlay_coverage_cells": 1266,
        "allow_stock_wed_when_override_absent": False,
        "local_art_opacity": {"mode": "paired-primary-texture-secondary-draw",
                              "source_draw_alpha": 128, "target_draw_alpha": 160,
                              "primary_texture_alpha": 160, "secondary_tile_ids": [4800, 5323]},
    }


def generated(entry):
    with patch.object(GENERATOR, "load_registry", return_value=({"version": 3}, {"entries": [entry]})):
        return GENERATOR.generate(Path("unused"))


class WaterArtOpacityCandidateTests(unittest.TestCase):
    def test_generates_explicit_secondary_roles_and_paired_alpha(self):
        output = generated(fixture())
        self.assertIn("kSecondaryArtTiles0{{4800, 5323}}", output)
        self.assertIn("kSecondaryArtTiles0, 128, 160", output)

    def test_absent_policy_stays_native(self):
        entry = fixture()
        del entry["local_art_opacity"]
        self.assertNotIn("kSecondaryArtTiles", generated(entry))

    def test_rejects_unpaired_or_malformed_policy(self):
        for field, value in [
            ("primary_texture_alpha", 128), ("target_draw_alpha", 256),
            ("source_draw_alpha", 0), ("secondary_tile_ids", []),
            ("secondary_tile_ids", [4800, 4800]), ("secondary_tile_ids", [5324]),
            ("secondary_tile_ids", [5323, 4800]), ("mode", "global"),
        ]:
            with self.subTest(field=field, value=value):
                entry = fixture()
                entry["local_art_opacity"][field] = value
                with self.assertRaises(RuntimeError):
                    generated(entry)

    def test_requires_exact_override_wed_hash(self):
        entry = fixture()
        entry["allow_stock_wed_when_override_absent"] = True
        with self.assertRaises(RuntimeError):
            generated(entry)
