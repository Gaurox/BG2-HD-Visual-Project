from __future__ import annotations

import csv
import io
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import build_graphics_inventory as inventory  # noqa: E402


class GraphicsInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.outputs = inventory.build_outputs(
            ROOT,
            inventory.DEFAULT_GAME_DIR,
            "ffprobe",
            extract=False,
        )

    def test_generation_is_deterministic(self) -> None:
        second = inventory.build_outputs(
            ROOT,
            inventory.DEFAULT_GAME_DIR,
            "ffprobe",
            extract=False,
        )
        self.assertEqual(self.outputs, second)

    def test_checked_in_outputs_are_current(self) -> None:
        divergent = [
            path.relative_to(ROOT).as_posix()
            for path, payload in self.outputs.items()
            if not path.is_file() or path.read_bytes() != payload
        ]
        self.assertEqual(divergent, [])

    def test_each_manifest_count_matches_unique_csv_assets(self) -> None:
        pairs = (
            ("video_manifest", "video_resources"),
            ("hud_manifest", "hud_resources"),
            ("icon_manifest", "icon_resources"),
            ("cursor_manifest", "cursor_resources"),
            ("effect_manifest", "effect_resources"),
            ("projectile_manifest", "projectile_resources"),
            ("font_manifest", "font_resources"),
            ("ui_manifest", "ui_resources"),
            ("supplemental_manifest", "supplemental_resources"),
        )
        for manifest_name, resources_name in pairs:
            manifest = inventory.json.loads(
                self.outputs[ROOT / inventory.OUTPUT_PATHS[manifest_name]].decode("utf-8")
            )
            payload = self.outputs[ROOT / inventory.OUTPUT_PATHS[resources_name]]
            rows = list(
                csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
            )
            keys = [row["asset_key"] for row in rows]
            self.assertEqual(manifest["asset_count"], len(rows), manifest_name)
            self.assertEqual(len(keys), len(set(keys)), resources_name)
            for row in rows:
                self.assertRegex(row["source_sha256"], r"^[A-F0-9]{64}$")

    def test_dependency_failures_are_explicit(self) -> None:
        for manifest_name, dependencies_name in (
            ("hud_manifest", "hud_dependencies"),
            ("effect_manifest", "effect_dependencies"),
            ("projectile_manifest", "projectile_dependencies"),
            ("ui_manifest", "ui_dependencies"),
        ):
            manifest = inventory.json.loads(
                self.outputs[ROOT / inventory.OUTPUT_PATHS[manifest_name]].decode("utf-8")
            )
            payload = self.outputs[ROOT / inventory.OUTPUT_PATHS[dependencies_name]]
            rows = list(
                csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
            )
            self.assertEqual(
                manifest["missing_dependency_count"],
                sum(row["present"] == "no" for row in rows),
                manifest_name,
            )

    def test_unclassified_resources_are_preserved_as_a_gap(self) -> None:
        coverage = inventory.json.loads(
            self.outputs[ROOT / inventory.OUTPUT_PATHS["graphics_coverage"]].decode(
                "utf-8"
            )
        )
        payload = self.outputs[ROOT / inventory.OUTPUT_PATHS["graphics_unclassified"]]
        rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline="")))
        self.assertEqual(coverage["unclassified_resource_count"], len(rows))
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(row["reason"] == "logical-owner-not-demonstrated" for row in rows))
        self.assertEqual(
            coverage["unclassified_format_counts"],
            {"BAM": len(rows)},
        )

    def test_extracted_paths_are_workspace_relative_and_present(self) -> None:
        for resources_name in (
            "video_resources",
            "hud_resources",
            "icon_resources",
            "cursor_resources",
            "effect_resources",
            "projectile_resources",
            "ui_resources",
            "supplemental_resources",
        ):
            payload = self.outputs[ROOT / inventory.OUTPUT_PATHS[resources_name]]
            rows = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
            for row in rows:
                extracted = row["extracted_path"]
                self.assertFalse(re.match(r"^[A-Za-z]:", extracted), extracted)
                path = ROOT / extracted
                self.assertTrue(path.is_file(), extracted)
                self.assertEqual(
                    inventory.sha256_file(path),
                    row["source_sha256"],
                    extracted,
                )
        font_payload = self.outputs[
            ROOT / inventory.OUTPUT_PATHS["font_resources"]
        ]
        for row in csv.DictReader(
            io.StringIO(font_payload.decode("utf-8-sig"), newline="")
        ):
            for member in inventory.json.loads(row["members_json"]):
                extracted = member["extracted_path"]
                path = ROOT / extracted
                self.assertTrue(path.is_file(), extracted)
                self.assertEqual(inventory.sha256_file(path), member["sha256"], extracted)


if __name__ == "__main__":
    unittest.main()
