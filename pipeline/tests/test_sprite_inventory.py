from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "sprite" / "index"
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import build_sprite_inventory as inventory  # noqa: E402


def rows(name: str) -> list[dict[str, str]]:
    with (INDEX / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


class SpriteInventoryTests(unittest.TestCase):
    def test_project_documentation_routes_agents_through_inventory(self) -> None:
        required = {
            ROOT / "README.md": ("sprite/README.md", "sprite/index/"),
            ROOT / "AGENTS.md": ("sprite/index/", "pipeline/tests"),
            ROOT / "sprite" / "README.md": (
                "index/manifest.json",
                "FAMILY_APPEND.md",
                "run_creature_sprite_x2.py",
            ),
            ROOT / "sprite" / "FAMILY_APPEND.md": (
                "sprite_families.csv",
                "generate_sprite_family_append.py",
            ),
            ROOT
            / "sprite"
            / "FOLDER_LAYOUT.md": ("sprite-layout.json", "path-migrations.json"),
            ROOT / "sprite" / "XBR2X_RASTER_CONTRACT.md": (
                "xbr2X",
                "sans anti-alias",
            ),
            ROOT
            / "engine"
            / "InfinityEngine-Enhancer"
            / "source-patchee"
            / "README.md": ("sprite/README.md", "NEAREST"),
        }
        for path, markers in required.items():
            content = path.read_text(encoding="utf-8-sig")
            for marker in markers:
                self.assertIn(marker, content, f"{path} must reference {marker}")

    def test_runtime_classification_is_explicit(self) -> None:
        self.assertEqual(
            inventory.current_runtime(0x6102, "6000", "character"),
            ("character-bg2ee-2.7.3.0", True),
        )
        self.assertEqual(
            inventory.current_runtime(0xE400, "E000", "monster_icewind"),
            ("monster-icewind-bg2ee-2.7.3.0", True),
        )
        self.assertEqual(inventory.current_runtime(0x7F07, "7000", "monster"), ("", False))

    def test_generated_relations_are_closed(self) -> None:
        animations = rows("sprite_animations.csv")
        families = rows("sprite_families.csv")
        resources = rows("sprite_resources.csv")
        items = rows("sprite_items.csv")
        inventory.verify_inventory(animations, families, resources, items)

    def test_known_golem_and_goblin_families(self) -> None:
        families = {row["family_id"]: row for row in rows("sprite_families.csv")}
        golem = families["0x7F07:body:base-resref:MGLC:MGLC"]
        self.assertEqual(golem["resource_count"], "13")
        self.assertEqual(golem["frame_count"], "5994")
        self.assertEqual(golem["runtime_supported"], "no")
        self.assertEqual(golem["blocker"], "runtime-profile-unsupported")

        goblin = families["0xE400:body:base-resref:MGO1:MGO1"]
        self.assertEqual(goblin["resource_count"], "20")
        self.assertEqual(goblin["pipeline_ready"], "yes")

    def test_known_dwarf_character_duplicate_rgba_indices_are_supported(self) -> None:
        selected = {
            row["bam_prefix"]: row
            for row in rows("sprite_families.csv")
            if row["animation_id"] == "0x6102"
            and row["bam_prefix"]
            in {"CDMB1", "CDMB2", "CDMF4", "WQSJ6", "WQSC1", "WQSAX"}
        }
        for prefix in ("CDMB1", "CDMB2", "CDMF4"):
            self.assertGreater(int(selected[prefix]["duplicate_used_rgba_frames"]), 0)
            self.assertEqual(selected[prefix]["blocker"], "")
            self.assertEqual(selected[prefix]["pipeline_ready"], "yes")
        self.assertEqual(selected["WQSJ6"]["pipeline_ready"], "yes")
        self.assertEqual(selected["WQSC1"]["pipeline_ready"], "yes")
        self.assertEqual(selected["WQSAX"]["unexpected_suffixes"], "")
        self.assertEqual(selected["WQSAX"]["pipeline_ready"], "yes")

    def test_known_items_resolve_from_stock_itm(self) -> None:
        items = {row["item_resref"]: row for row in rows("sprite_items.csv")}
        self.assertEqual(items["PLAT04"]["body_armor_code"], "4")
        self.assertEqual(items["HELM01"]["animation_code"], "J6")
        self.assertEqual(items["SHLD13"]["animation_code"], "C1")
        self.assertEqual(items["AX1H13"]["animation_code"], "AX")

    def test_manifest_records_registry_set_contract(self) -> None:
        manifest = json.loads((INDEX / "manifest.json").read_text(encoding="utf-8"))
        limits = manifest["limits"]
        self.assertEqual(
            limits["max_shards_per_registry_set"], inventory.MAX_REGISTRY_SET_SHARDS
        )
        self.assertEqual(
            limits["max_resources_per_registry_set"],
            inventory.MAX_REGISTRY_SET_RESOURCES,
        )
        self.assertEqual(
            limits["max_frames_per_registry_set"],
            inventory.MAX_REGISTRY_SET_FRAMES,
        )
        self.assertEqual(
            limits["max_registry_set_bytes"], inventory.MAX_REGISTRY_SET_BYTES
        )
        self.assertEqual(
            limits["max_lazy_frame_index_bytes"],
            inventory.MAX_LAZY_FRAME_INDEX_BYTES,
        )
        self.assertEqual(
            limits["xbr_output_batch_budget_bytes"],
            inventory.XBR_OUTPUT_BATCH_BUDGET_BYTES,
        )
        self.assertEqual(
            limits["max_registry_bytes_by_scale"],
            {
                str(scale): byte_limit
                for scale, byte_limit in inventory.MAX_REGISTRY_BYTES_BY_SCALE.items()
            },
        )
        registry_set = manifest["registry_contracts"]["registry_set"]
        self.assertEqual(registry_set["magic"], "IEECSNS")
        self.assertEqual(registry_set["member_magic"], "IEECSXN")
        self.assertEqual(
            registry_set["invalid_present_set_policy"],
            "fail-closed-no-monolith-fallback",
        )
        self.assertIn("lazy", registry_set["payload_loading"])

    def test_manifest_records_stock_cre_usage(self) -> None:
        manifest = json.loads((INDEX / "manifest.json").read_text(encoding="utf-8"))
        usage = manifest["stock_cre_usage"]
        self.assertEqual(usage["source"]["resource_type"], "0x03F1")
        self.assertEqual(usage["source"]["animation_id_offset"], 0x28)
        self.assertEqual(usage["cre_versions"], {"CRE V1.0": 4735})
        self.assertEqual(usage["cre_resource_count"], 4735)
        self.assertEqual(usage["animation_id_count"], 279)
        self.assertEqual(usage["zero_animation_id_cre_resource_count"], 2)
        self.assertEqual(usage["nonzero_animation_id_count"], 278)
        self.assertEqual(usage["with_bam_animation_id_count"], 273)
        self.assertEqual(usage["without_bam_animation_id_count"], 6)
        self.assertEqual(usage["without_bam_nonzero_animation_id_count"], 5)
        self.assertEqual(
            usage["without_bam_animation_ids"],
            ["0x0000", "0x0100", "0x7F2B", "0x7F33", "0x7F34", "0xE520"],
        )
        self.assertEqual(usage["fully_pipeline_ready_animation_id_count"], 101)
        self.assertEqual(usage["fully_pipeline_ready_cre_resource_count"], 2400)
        self.assertAlmostEqual(
            usage["fully_pipeline_ready_cre_coverage_percent"], 50.686, places=3
        )
        self.assertEqual(
            usage["runtime_supported_without_bam_animation_ids"], ["0xE520"]
        )
        self.assertEqual(usage["runtime_supported_blocked_animation_id_count"], 0)
        self.assertEqual(usage["runtime_unsupported_animation_id_count"], 177)
        self.assertEqual(usage["runtime_unsupported_nonzero_animation_id_count"], 176)
        self.assertIn("0x0000", usage["runtime_unsupported_animation_ids"])
        self.assertNotIn("0x0000", usage["runtime_unsupported_nonzero_animation_ids"])
        self.assertEqual(
            usage["with_bam_animation_id_count"]
            + usage["without_bam_animation_id_count"],
            usage["animation_id_count"],
        )
        self.assertEqual(
            set(usage["with_bam_animation_ids"])
            | set(usage["without_bam_animation_ids"]),
            set(usage["animation_ids"]),
        )
        self.assertFalse(
            set(usage["with_bam_animation_ids"])
            & set(usage["without_bam_animation_ids"])
        )
        self.assertEqual(
            sum(usage["cre_resources_by_animation_id"].values()),
            usage["cre_resource_count"],
        )
        self.assertEqual(
            set(usage["cre_resources_by_animation_id"]), set(usage["animation_ids"])
        )

    def test_stock_cre_usage_rejects_unknown_cre_version(self) -> None:
        class FakeIndex:
            def resource_map(self, resource_type: int) -> dict[str, object]:
                if resource_type != inventory.CRE_TYPE:
                    raise AssertionError("unexpected resource type")
                return {"BADCRE": object()}

            @staticmethod
            def resolve(_entry: object) -> tuple[bytes, None]:
                return b"CRE V9.9" + b"\0" * 34, None

        with self.assertRaisesRegex(RuntimeError, "unsupported stock CRE version"):
            inventory.build_stock_cre_usage(FakeIndex(), [], [])

    def test_human_female_warrior_fits_x4_set_bounds(self) -> None:
        selected = []
        for resource in rows("sprite_resources.csv"):
            animation_ids = set(filter(None, resource["animation_ids"].split(";")))
            if (
                "0x6110" in animation_ids
                and resource["runtime_relevant"] == "yes"
                and resource["override_collision"] == "no"
                and resource["decode_status"] == "ok"
            ):
                selected.append(resource)

        self.assertGreater(len(selected), inventory.MAX_RESOURCES)
        self.assertLessEqual(len(selected), inventory.MAX_REGISTRY_SET_RESOURCES)
        self.assertLessEqual(
            sum(int(resource["frame_count"]) for resource in selected),
            inventory.MAX_REGISTRY_SET_FRAMES,
        )
        projected_records = [
            inventory.estimate_registry_resource_bytes(resource, 4)
            for resource in selected
        ]
        self.assertGreater(max(projected_records), inventory.maximum_registry_bytes(2))
        self.assertLessEqual(
            max(projected_records), inventory.maximum_registry_bytes(4)
        )
        shards = inventory.partition_registry_resources(
            [
                {"resref": resource["bam_resref"], "bytes": record_bytes}
                for resource, record_bytes in zip(selected, projected_records)
            ],
            maximum_bytes=inventory.maximum_registry_bytes(4),
        )
        self.assertLessEqual(len(shards), inventory.MAX_REGISTRY_SET_SHARDS)
        projected_aggregate = sum(projected_records) + (
            len(shards) * inventory.REGISTRY_HEADER_BYTES
        )
        self.assertGreater(projected_aggregate, inventory.maximum_registry_bytes(4))
        self.assertLessEqual(projected_aggregate, inventory.MAX_REGISTRY_SET_BYTES)

        families = {
            row["bam_prefix"]: row
            for row in rows("sprite_families.csv")
            if row["animation_id"] == "0x6110"
        }
        self.assertGreater(
            int(families["WQNFS"]["registry_estimated_bytes"]),
            inventory.MAX_REGISTRY_BYTES,
        )
        self.assertEqual(families["WQNFS"]["registry_limit_pass"], "yes")
        self.assertEqual(families["WQNFS"]["pipeline_ready"], "yes")
        self.assertEqual(families["WQNFS"]["required_job_contract"], "explicit-xn")
        self.assertEqual(families["WQNFS"]["registry_layout_x2"], "set")
        self.assertEqual(families["WQNFS"]["shard_count_x2"], "2")

        manifest = json.loads((INDEX / "manifest.json").read_text(encoding="utf-8"))
        projection = manifest["registry_set_projections"]["animations"]["0x6110"]
        self.assertEqual(projection["resource_count"], len(selected))
        self.assertEqual(
            projection["frame_count"],
            sum(int(resource["frame_count"]) for resource in selected),
        )
        self.assertTrue(projection["x4"]["fits_set"])
        self.assertEqual(projection["x4"]["shard_count"], len(shards))
        self.assertEqual(
            projection["x4"]["total_registry_bytes"], projected_aggregate
        )
        self.assertEqual(
            projection["x4"]["maximum_resource_bytes"], max(projected_records)
        )
        projected_frame_bytes = max(
            int(resource["native_frame_pixel_count_max"]) * 4 * 4
            for resource in selected
        )
        self.assertEqual(
            projection["x4"]["maximum_frame_index_bytes"], projected_frame_bytes
        )
        self.assertLessEqual(
            projected_frame_bytes, inventory.MAX_LAZY_FRAME_INDEX_BYTES
        )

    def test_registry_set_projection_rejects_frame_larger_than_lazy_cache(self) -> None:
        native_frame_pixels = inventory.MAX_LAZY_FRAME_INDEX_BYTES // 16 + 1
        projection = inventory.build_registry_set_projections(
            [
                {
                    "bam_resref": "TOOBIG",
                    "decode_status": "ok",
                    "runtime_relevant": "yes",
                    "override_collision": "no",
                    "animation_ids": "0x6110",
                    "frame_count": 1,
                    "cycle_count": 1,
                    "cycle_slot_count": 1,
                    "native_pixel_count": native_frame_pixels,
                    "native_frame_pixel_count_max": native_frame_pixels,
                }
            ]
        )["animations"]["0x6110"]

        self.assertTrue(projection["x2"]["fits_set"])
        self.assertFalse(projection["x4"]["fits_set"])
        self.assertEqual(
            projection["x4"]["blocker"], "registry-set-frame-index-size-limit"
        )


if __name__ == "__main__":
    unittest.main()
