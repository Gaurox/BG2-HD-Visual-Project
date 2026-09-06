"""Tests synthétiques du compositeur de patch; aucun média BG2 réel n'est requis."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from pipeline.map_patch_compositor import area, core


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic_map() -> np.ndarray:
    y, x = np.indices((112, 128))
    return np.stack(((x * 17 + y * 3) % 251, (x * 5 + y * 19) % 253, (x * 11 + y * 7) % 241), axis=2).astype(np.uint8)


class MapPatchCompositorTests(unittest.TestCase):
    def config(self) -> dict:
        value = core.load_config()
        value["registration"].update({
            "coarse_max_dimension_px": 128,
            "scale_min": 0.97,
            "scale_max": 1.03,
            "scale_steps": 3,
            "candidate_count": 3,
            "refine_translation_px": 3.0,
            "min_coarse_score": -1.0,
            "min_peak_ratio": 1.0,
            "min_inlier_fraction": 0.0,
            "max_rmse": 1.0,
        })
        value["object_mask"].update({
            "delta_e_floor": 4.0,
            "minimum_component_area_px": 4,
            "opening_radius_px": 0,
            "closing_radius_px": 0,
        })
        value["blend"].update({
            "dilation_px": 1,
            "fade_width_px": 2.0,
            "gaussian_sigma_px": 0.5,
            "edge_guard_px": 1,
            "minimum_coverage_px": 4,
        })
        value["color"].update({"enabled": False})
        core.validate_config(value)
        return value

    def write_pair(self, directory: Path) -> tuple[Path, Path, tuple[int, int, int, int]]:
        image = synthetic_map()
        x0, y0, width, height = 46, 38, 36, 34
        image[y0 + 11:y0 + 23, x0 + 12:x0 + 25] = (155, 28, 20)
        patch = image[y0:y0 + height, x0:x0 + width].copy()
        patch[11:23, 12:25] = (20, 120, 220)
        map_path = directory / "map.png"
        patch_path = directory / "patch.png"
        Image.fromarray(image, mode="RGB").save(map_path)
        Image.fromarray(patch, mode="RGB").save(patch_path)
        return map_path, patch_path, (x0, y0, width, height)

    def test_defaults_validate(self) -> None:
        config = self.config()
        self.assertEqual(config["schema"], core.CONFIG_SCHEMA)
        self.assertLess(config["registration"]["scale_min"], config["registration"]["scale_max"])

    def test_inspect_preserves_input_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path, patch_path, _ = self.write_pair(root)
            map_hash, patch_hash = sha256(map_path), sha256(patch_path)
            report = core.inspect_inputs(map_path, patch_path)
            self.assertEqual(report["map"]["format"], "PNG")
            self.assertEqual(report["patch"]["mode"], "RGB")
            self.assertEqual(sha256(map_path), map_hash)
            self.assertEqual(sha256(patch_path), patch_hash)

    def test_compose_creates_new_run_and_preserves_outside_mask(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path, patch_path, _ = self.write_pair(root)
            config_path = root / "config.json"
            config_path.write_text(json.dumps(self.config()), encoding="utf-8")
            map_hash, patch_hash = sha256(map_path), sha256(patch_path)
            run = root / "new-run"
            manifest = core.compose(map_path, patch_path, run, config_path)
            self.assertEqual(manifest["status"], "completed")
            self.assertTrue((run / "run.json").is_file())
            self.assertFalse((root / "new-run.partial").exists())
            self.assertEqual(sha256(map_path), map_hash)
            self.assertEqual(sha256(patch_path), patch_hash)
            result_path = run / manifest["outputs"]["image"]["path"]
            result = np.asarray(Image.open(result_path).convert("RGB"))
            source = np.asarray(Image.open(map_path).convert("RGB"))
            blend = np.asarray(Image.open(run / "control" / "blend-mask-map.png")) > 0
            self.assertTrue(np.array_equal(result[~blend], source[~blend]))
            self.assertGreater(manifest["metrics"]["output"]["changed_pixel_count"], 0)

    def test_existing_output_run_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            map_path, patch_path, _ = self.write_pair(root)
            config_path = root / "config.json"
            config_path.write_text(json.dumps(self.config()), encoding="utf-8")
            run = root / "existing"
            run.mkdir()
            with self.assertRaisesRegex(core.CompositeError, "déjà présent"):
                core.compose(map_path, patch_path, run, config_path)

    def test_blend_rejects_a_rectangular_edge(self) -> None:
        config = self.config()
        core_mask = np.zeros((24, 24), dtype=bool)
        core_mask[0:6, 8:16] = True
        with self.assertRaisesRegex(core.CompositeError, "bord rectangulaire"):
            core._blend_mask(core_mask, config)

    def test_lossy_map_is_refused_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image = Image.fromarray(synthetic_map(), mode="RGB")
            map_path = root / "map.jpg"
            patch_path = root / "patch.png"
            image.save(map_path, format="JPEG")
            image.crop((12, 12, 48, 48)).save(patch_path, format="PNG")
            with self.assertRaisesRegex(core.CompositeError, "avec perte"):
                core.inspect_inputs(map_path, patch_path)

    def test_area_workflow_creates_derived_run_then_reversible_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            area_id = "AR1234"
            map_path, patch_path, _ = self.write_pair(root)
            base = root / "maps" / area_id / "runs" / "base-x4"
            assembled = base / "tuiles-principales" / "03_assemble" / "base.png"
            assembled.parent.mkdir(parents=True)
            assembled.write_bytes(map_path.read_bytes())
            (base / "run.json").write_text(json.dumps({
                "run_id": "base-x4",
                "area_id": area_id,
                "outputs": {"tuiles-principales": {"assembled": {"path": str(assembled.relative_to(root))}}},
            }), encoding="utf-8")
            (root / "areas.csv").write_text("area_id,runs\nAR1234,base-x4\n", encoding="utf-8")
            config_path = root / "config.json"
            config_path.write_text(json.dumps(self.config()), encoding="utf-8")

            plan = area.area_plan(area_id, patch_path, config_path, root=root)
            self.assertEqual(plan["base"]["kind"], "areas-csv-base")
            manifest = area.apply_area_patch(area_id, patch_path, config_path, root=root)
            self.assertEqual(manifest["area_id"], area_id)
            self.assertEqual(manifest["run_kind"], "map-patch-composite")
            selection = area.select_area_patch(area_id, manifest["run_id"], root=root)
            self.assertEqual(selection["selected"]["run_id"], manifest["run_id"])
            resolved = area.resolve_area_source(area_id, root=root)
            self.assertEqual(resolved.source_kind, "current-patch-selection")
            self.assertTrue(resolved.source_path.is_file())
            self.assertTrue(assembled.is_file())
