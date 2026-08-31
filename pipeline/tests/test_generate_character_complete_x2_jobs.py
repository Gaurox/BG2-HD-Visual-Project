from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from pipeline.scripts import generate_character_complete_x2_jobs as generator


class CharacterCompleteX2JobGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        tests_root = generator.PROJECT_ROOT / "pipeline" / "tests"
        self.root = Path(tempfile.mkdtemp(prefix="character-jobs-", dir=tests_root))
        token = uuid.uuid4().hex[:10]
        self.character_root = generator.CHARACTER_ROOT / f"6110-test-{token}"
        self.template_workspace = self.character_root / "body-chfb1"
        self.template_workspace.joinpath("jobs").mkdir(parents=True)
        self.families = self.root / "sprite_families.csv"
        self.template = self.template_workspace / "jobs" / "hero-chfb1-xbr2x.json"
        self.aggregate = (
            self.character_root
            / "family-runs"
            / "complete-x2-nearest"
            / "jobs"
            / "hero-complete-xbr2x.json"
        )
        self._write_json(self.template, self._template_job())

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.character_root, ignore_errors=True)

    def _relative(self, path: Path) -> str:
        return path.relative_to(generator.PROJECT_ROOT).as_posix()

    def _template_job(self) -> dict[str, object]:
        workspace_paths = generator.character_workspace_paths(
            self.template_workspace, "hero-chfb1-xbr2x", 2, "0x6110"
        )
        return {
            "schema": generator.JOB_SCHEMA,
            "job_id": "hero-chfb1-xbr2x",
            "animation": {
                "name": "Hero",
                "id": "0x6110",
                "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                "armor_code": 1,
                "bam_prefix": "CHFB1",
                "runtime_profile": "character-bg2ee-2.7.3.0",
            },
            "paths": {
                "game_root": "config://bg2ee_game_root",
                "scalepix": "config://mmpx_scalepix",
                "engine_source": f"{self._relative(self.root)}/engine/source",
                **workspace_paths,
            },
            "compatibility": {"baldur_real_sha256": "A" * 64},
            "runtime": {
                "cmake_generator": "Visual Studio 16 2019",
                "cmake_arch": "x64",
                "no_filter_comparison": True,
            },
            "qa": {"areas": ["ar0602"], "creatures": ["player1"]},
        }

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def _family_rows(self) -> list[dict[str, str]]:
        common = {
            "animation_id": "0x6110",
            "ids_symbol": "FIGHTER_FEMALE_HUMAN",
            "runtime_profile": "character-bg2ee-2.7.3.0",
            "runtime_supported": "yes",
            "pipeline_ready": "yes",
            "override_collision": "",
            "blocker": "",
        }
        return [
            {
                **common,
                "family_id": "body-1",
                "layer_kind": "body",
                "variant_value": "1",
                "item_resrefs": "",
                "bam_prefix": "CHFB1",
                "resource_count": "23",
                "frame_count": "10323",
                "registry_estimated_bytes": "25000000",
            },
            {
                **common,
                "family_id": "helmet-h0",
                "layer_kind": "helmet",
                "variant_value": "H0",
                "item_resrefs": "ZZHELM;AAHELM;AAHELM",
                "bam_prefix": "WQNH0",
                "resource_count": "14",
                "frame_count": "2709",
                "registry_estimated_bytes": "3000000",
            },
            {
                **common,
                "family_id": "weapon-fs",
                "layer_kind": "weapon",
                "variant_value": "FS",
                "item_resrefs": "SW1H60;FBLADE",
                "bam_prefix": "WQNFS",
                "resource_count": "11",
                "frame_count": "5378",
                "registry_estimated_bytes": "241886244",
                "blocker": "",
            },
            {
                **common,
                "family_id": "helmet-yw",
                "layer_kind": "helmet",
                "variant_value": "YW",
                "item_resrefs": "WINGS01B",
                "bam_prefix": "WQNYW",
                "resource_count": "0",
                "frame_count": "0",
                "registry_estimated_bytes": "24",
                "blocker": "no-bam-resources;resource-limit",
            },
        ]

    def _write_families(self, rows: list[dict[str, str]] | None = None) -> None:
        selected = rows or self._family_rows()
        fields = [
            "family_id",
            "animation_id",
            "ids_symbol",
            "runtime_profile",
            "runtime_supported",
            "pipeline_ready",
            "override_collision",
            "layer_kind",
            "variant_value",
            "item_resrefs",
            "bam_prefix",
            "resource_count",
            "frame_count",
            "registry_estimated_bytes",
            "blocker",
        ]
        with self.families.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(selected)

    def _plan(self, force: bool = False) -> generator.GenerationPlan:
        return generator.make_plan(
            project_root=generator.PROJECT_ROOT,
            families_path=self.families,
            character_root=self.character_root,
            template_path=self.template,
            aggregate_path=self.aggregate,
            animation_id="0x6110",
            job_stem="hero",
            force=force,
        )

    def test_generates_missing_jobs_reuses_prefix_and_excludes_only_empty_family(self) -> None:
        self._write_families()

        plan = self._plan()

        self.assertEqual([path.name for path in plan.reused_jobs], [self.template.name])
        self.assertEqual(
            [path.name for path in plan.generated_jobs],
            ["hero-aahelm-wqnh0-xbr2x.json", "hero-fblade-wqnfs-xbr2x.json"],
        )
        self.assertEqual(plan.member_set_families, ("WQNFS",))
        self.assertEqual(
            plan.aggregate_payload["members"],
            [
                self._relative(self.template),
                self._relative(
                    self.character_root
                    / "aahelm-wqnh0"
                    / "jobs"
                    / "hero-aahelm-wqnh0-xbr2x.json"
                ),
                self._relative(
                    self.character_root
                    / "fblade-wqnfs"
                    / "jobs"
                    / "hero-fblade-wqnfs-xbr2x.json"
                ),
            ],
        )
        self.assertEqual(
            plan.aggregate_payload["inventory"]["excluded_families"][0]["bam_prefix"],
            "WQNYW",
        )
        self.assertEqual(
            plan.aggregate_payload["inventory"]["member_registry_set_families"],
            ["WQNFS"],
        )
        self.assertEqual(
            plan.aggregate_payload["qa"]["required_bam_prefixes"],
            ["CHFB1", "WQNH0", "WQNFS"],
        )
        self.assertEqual(
            plan.aggregate_payload["qa"]["required_items"],
            ["AAHELM", "FBLADE"],
        )
        generated_by_prefix = {
            write.payload["animation"]["bam_prefix"]: write.payload
            for write in plan.writes
            if write.path != self.aggregate
        }
        self.assertEqual(
            generated_by_prefix["WQNH0"]["paths"]["game_root"],
            "config://bg2ee_game_root",
        )
        self.assertEqual(
            generated_by_prefix["WQNH0"]["paths"]["scalepix"],
            "config://mmpx_scalepix",
        )
        self.assertEqual(
            plan.aggregate_payload["paths"]["game_root"],
            "config://bg2ee_game_root",
        )
        self.assertEqual(
            generated_by_prefix["WQNH0"]["animation"]["layer"]["item_resref"],
            "AAHELM",
        )
        self.assertEqual(
            generated_by_prefix["WQNFS"]["animation"]["layer"]["item_resref"],
            "FBLADE",
        )
        self.assertEqual(generated_by_prefix["WQNFS"]["upscale"], generator.DIRECT_X2_METHOD)

        result = generator.apply_plan(plan)

        self.assertFalse(result["pixels_produced"])
        self.assertEqual(result["member_registry_set_families"], ["WQNFS"])
        aggregate = json.loads(self.aggregate.read_text(encoding="utf-8"))
        self.assertEqual(aggregate["upscale"], generator.DIRECT_X2_METHOD)
        self.assertEqual(len(aggregate["members"]), 3)
        for member_text in aggregate["members"]:
            member_path = generator.PROJECT_ROOT / member_text
            self.assertEqual(member_path.parent.name, "jobs")
            self.assertIn(self.character_root, member_path.parents)
        self.assertFalse((self.root / "template" / "source").exists())

    def test_existing_aggregate_blocks_all_publication_without_force(self) -> None:
        self._write_families()
        sentinel = {"do_not_replace": True}
        self._write_json(self.aggregate, sentinel)

        with self.assertRaisesRegex(RuntimeError, "aggregate job already exists"):
            self._plan(force=False)

        self.assertEqual(json.loads(self.aggregate.read_text(encoding="utf-8")), sentinel)
        self.assertFalse((self.character_root / "aahelm-wqnh0").exists())
        self.assertFalse((self.character_root / "fblade-wqnfs").exists())

    def test_force_replaces_aggregate_but_still_reuses_existing_prefix_job(self) -> None:
        self._write_families()
        existing = self._template_job()
        existing["job_id"] = "custom-existing-helmet-xbr2x"
        existing["animation"] = {
            "name": "Existing helmet",
            "id": "0x6110",
            "ids_symbol": "FIGHTER_FEMALE_HUMAN",
            "layer": {"kind": "helmet", "item_resref": "ZZHELM"},
            "bam_prefix": "WQNH0",
            "runtime_profile": "character-bg2ee-2.7.3.0",
        }
        existing_path = (
            self.character_root
            / "zzhelm-wqnh0"
            / "jobs"
            / "custom-existing-helmet-xbr2x.json"
        )
        existing["paths"].update(
            generator.character_workspace_paths(
                existing_path.parent.parent,
                "custom-existing-helmet-xbr2x",
                2,
                "0x6110",
            )
        )
        self._write_json(existing_path, existing)
        self._write_json(self.aggregate, {"stale": True})

        plan = self._plan(force=True)

        self.assertIn(existing_path.resolve(), plan.reused_jobs)
        self.assertNotIn(
            self.character_root
            / "aahelm-wqnh0"
            / "jobs"
            / "hero-aahelm-wqnh0-xbr2x.json",
            plan.generated_jobs,
        )
        generator.apply_plan(plan)
        self.assertEqual(
            json.loads(self.aggregate.read_text(encoding="utf-8"))["members"][1],
            self._relative(existing_path),
        )

    def test_duplicate_existing_x2_prefix_is_rejected(self) -> None:
        self._write_families()
        duplicate = self._template_job()
        duplicate["job_id"] = "duplicate-body-xbr2x"
        duplicate_path = (
            self.character_root / "duplicate-body" / "jobs" / "duplicate-body-xbr2x.json"
        )
        duplicate_path.parent.mkdir(parents=True)
        self._write_json(duplicate_path, duplicate)

        with self.assertRaisesRegex(RuntimeError, "multiple compatible x2 jobs use BAM prefix CHFB1"):
            self._plan()

    def test_inventory_row_order_does_not_change_member_order(self) -> None:
        rows = self._family_rows()
        self._write_families(list(reversed(rows)))

        plan = self._plan()

        self.assertEqual(
            [Path(value).name for value in plan.aggregate_payload["members"]],
            [
                "hero-chfb1-xbr2x.json",
                "hero-aahelm-wqnh0-xbr2x.json",
                "hero-fblade-wqnfs-xbr2x.json",
            ],
        )

    def test_nonempty_blocked_family_is_rejected(self) -> None:
        rows = self._family_rows()
        rows[1]["blocker"] = "bam-override-collision"
        self._write_families(rows)

        with self.assertRaisesRegex(
            RuntimeError, "WQNH0 is not pipeline-ready: bam-override-collision"
        ):
            self._plan()

    def test_oversized_family_does_not_reuse_a_legacy_member(self) -> None:
        self._write_families()
        legacy = self._template_job()
        legacy["job_id"] = "legacy-wqnfs-xbr2x"
        legacy["animation"] = {
            "name": "Legacy oversized weapon",
            "id": "0x6110",
            "ids_symbol": "FIGHTER_FEMALE_HUMAN",
            "layer": {"kind": "weapon", "item_resref": "FBLADE"},
            "bam_prefix": "WQNFS",
            "runtime_profile": "character-bg2ee-2.7.3.0",
        }
        legacy_path = (
            self.character_root / "legacy-wqnfs" / "jobs" / "legacy-wqnfs-xbr2x.json"
        )
        legacy_path.parent.mkdir(parents=True)
        self._write_json(legacy_path, legacy)

        with self.assertRaisesRegex(RuntimeError, "WQNFS requires explicit xN"):
            self._plan()


if __name__ == "__main__":
    unittest.main()
