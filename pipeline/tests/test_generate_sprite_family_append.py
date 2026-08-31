from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from pipeline.scripts import generate_sprite_family_append as generator


class SpriteFamilyAppendGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.token = uuid.uuid4().hex[:10]
        self.jobs = generator.VALIDATION_DIR
        self.jobs.mkdir(parents=True, exist_ok=True)
        self.root = Path(
            tempfile.mkdtemp(prefix="sprite-family-append-", dir=generator.PROJECT_ROOT / "pipeline" / "tests")
        )
        self.families = self.root / "sprite_families.csv"
        self.template = self.jobs / f"test-{self.token}-mgo1-xbr2x.json"
        self.member = (
            generator.FAMILIES_ROOT
            / "monster-icewind"
            / "e4xx-goblins"
            / "e410-mgo2-goblin-bow"
            / "jobs"
            / "x2-nearest-v1.json"
        )
        self.catalog = self.jobs / f"test-{self.token}-catalog-base-xbr2x.json"
        self.append = (
            generator.CATALOG_JOBS_ROOT
            / f"append-e410-mgo2-goblin-bow-test-{self.token}-v1.json"
        )
        self._write_json(self.template, self._member_payload("0xE400", "MGO1", self.template.stem))
        self._write_families()

    def tearDown(self) -> None:
        for path in (self.template, self.member, self.catalog, self.append):
            path.unlink(missing_ok=True)
        for directory in (
            self.member.parent,
            self.member.parent.parent,
            self.member.parent.parent.parent,
            self.member.parent.parent.parent.parent,
        ):
            try:
                directory.rmdir()
            except OSError:
                pass
        shutil.rmtree(self.root, ignore_errors=True)

    def _relative(self, path: Path) -> str:
        return path.relative_to(generator.PROJECT_ROOT).as_posix()

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _member_payload(self, animation_id: str, prefix: str, job_id: str) -> dict[str, object]:
        asset_id = job_id.replace("-", "_")
        return {
            "schema": generator.JOB_SCHEMA,
            "job_id": job_id,
            "animation": {
                "name": f"Test {prefix}",
                "id": animation_id,
                "bam_prefix": prefix,
                "runtime_profile": "monster-icewind-bg2ee-2.7.3.0",
            },
            "paths": {
                "game_root": "config://bg2ee_game_root",
                "source_dir": f"pipeline/tests/{self.root.name}/{asset_id}/source",
                "run_dir": f"pipeline/tests/{self.root.name}/{asset_id}/runs/xbr2x-x2",
                "scalepix": "config://mmpx_scalepix",
                "engine_source": f"pipeline/tests/{self.root.name}/engine/source",
                "engine_build": f"pipeline/tests/{self.root.name}/engine/build",
            },
            "compatibility": {"baldur_real_sha256": "A" * 64},
            "runtime": {
                "cmake_generator": "Visual Studio 16 2019",
                "cmake_arch": "x64",
                "no_filter_comparison": True,
            },
            "qa": {"areas": ["AR0602"], "creatures": ["ICGOB03"]},
        }

    def _write_families(self, *, eligible: bool = True) -> None:
        fields = [
            "family_id",
            "animation_id",
            "ids_symbol",
            "runtime_profile",
            "layer_kind",
            "variant_kind",
            "variant_value",
            "bam_prefix",
            "resource_count",
            "frame_count",
            "pipeline_ready",
            "runtime_supported",
            "override_collision",
            "blocker",
        ]
        rows = [
            {
                "family_id": "0xE400:body:base-resref:MGO1:MGO1",
                "animation_id": "0xE400",
                "ids_symbol": "GOBLIN_AXE",
                "runtime_profile": "monster-icewind-bg2ee-2.7.3.0",
                "layer_kind": "body",
                "variant_kind": "base-resref",
                "variant_value": "MGO1",
                "bam_prefix": "MGO1",
                "resource_count": "20",
                "frame_count": "1528",
                "pipeline_ready": "yes",
                "runtime_supported": "yes",
                "override_collision": "",
                "blocker": "",
            },
            {
                "family_id": "0xE410:body:base-resref:MGO2:MGO2",
                "animation_id": "0xE410",
                "ids_symbol": "GOBLIN_BOW",
                "runtime_profile": "monster-icewind-bg2ee-2.7.3.0",
                "layer_kind": "body",
                "variant_kind": "base-resref",
                "variant_value": "MGO2",
                "bam_prefix": "MGO2",
                "resource_count": "20",
                "frame_count": "1376",
                "pipeline_ready": "yes" if eligible else "no",
                "runtime_supported": "yes",
                "override_collision": "",
                "blocker": "" if eligible else "fixture-blocker",
            },
        ]
        with self.families.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_member_comes_from_exact_ready_inventory_family(self) -> None:
        result = generator.generate_member(
            destination=self.member,
            template_path=self.template,
            families_path=self.families,
            family_id="0xE410:body:base-resref:MGO2:MGO2",
            name="Gobelin archer",
            qa_areas=["AR0602"],
            qa_creatures=["FSGOBL"],
            dry_run=False,
        )

        self.assertEqual(result["status"], "family-member-job-created")
        self.assertFalse(result["pixels_produced"])
        member = json.loads(self.member.read_text(encoding="utf-8"))
        self.assertEqual(member["animation"]["id"], "0xE410")
        self.assertEqual(member["animation"]["bam_prefix"], "MGO2")
        self.assertEqual(member["animation"]["runtime_profile"], "monster-icewind-bg2ee-2.7.3.0")
        self.assertEqual(member["upscale"], generator.DIRECT_X2_METHOD)
        self.assertEqual(member["paths"]["game_root"], "config://bg2ee_game_root")
        self.assertEqual(member["paths"]["scalepix"], "config://mmpx_scalepix")
        self.assertEqual(
            member["paths"]["source_dir"],
            "sprite/families/monster-icewind/e4xx-goblins/e410-mgo2-goblin-bow/source/stock",
        )
        self.assertEqual(
            member["paths"]["run_dir"],
            "sprite/families/monster-icewind/e4xx-goblins/e410-mgo2-goblin-bow/runs/x2-nearest-v1",
        )
        self.assertEqual(
            member["qa"],
            {
                "areas": ["AR0602"],
                "creatures": ["FSGOBL"],
                "required_bam_prefixes": ["MGO2"],
            },
        )

    def test_layout_uses_the_approved_monster_group_and_identity(self) -> None:
        family = generator.load_inventory_family(
            self.families, "0xE410:body:base-resref:MGO2:MGO2"
        )
        self.assertEqual(
            generator.member_layout(family)["family_directory"],
            "sprite/families/monster-icewind/e4xx-goblins/e410-mgo2-goblin-bow",
        )

    def test_unready_inventory_family_is_rejected_before_publication(self) -> None:
        self._write_families(eligible=False)

        with self.assertRaisesRegex(RuntimeError, "is not eligible"):
            generator.generate_member(
                destination=self.member,
                template_path=self.template,
                families_path=self.families,
                family_id="0xE410:body:base-resref:MGO2:MGO2",
                name=None,
                qa_areas=["AR0602"],
                qa_creatures=["FSGOBL"],
                dry_run=False,
            )
        self.assertFalse(self.member.exists())

    def test_flat_member_destination_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "families/monster-icewind/e4xx-goblins"):
            generator.generate_member(
                destination=self.jobs / f"test-{self.token}-mgo2-xbr2x.json",
                template_path=self.template,
                families_path=self.families,
                family_id="0xE410:body:base-resref:MGO2:MGO2",
                name=None,
                qa_areas=["AR0602"],
                qa_creatures=["FSGOBL"],
                dry_run=True,
            )

    def test_catalog_append_keeps_identity_and_run_dir_while_adding_one_animation(self) -> None:
        generator.generate_member(
            destination=self.member,
            template_path=self.template,
            families_path=self.families,
            family_id="0xE410:body:base-resref:MGO2:MGO2",
            name="Gobelin archer",
            qa_areas=["AR0602"],
            qa_creatures=["FSGOBL"],
            dry_run=False,
        )
        base = {
            "schema": generator.CATALOG_JOB_SCHEMA,
            "job_id": "test-catalog-xbr2x",
            "name": "Catalogue test MGO1",
            "members": [self._relative(self.template)],
            "paths": {
                "game_root": "config://bg2ee_game_root",
                "run_dir": f"pipeline/tests/{self.root.name}/catalog/runs/xbr2x-x2",
                "engine_source": f"pipeline/tests/{self.root.name}/engine/source",
                "engine_build": f"pipeline/tests/{self.root.name}/engine/build",
            },
            "compatibility": {"baldur_real_sha256": "A" * 64},
            "runtime": {"cmake_generator": "Visual Studio 16 2019", "cmake_arch": "x64"},
            "upscale": dict(generator.DIRECT_X2_METHOD),
            "qa": {
                "animations": [
                    {
                        "animation_id": "0xE400",
                        "name": "Gobelin hache",
                        "areas": ["AR0602"],
                        "creatures": ["ICGOB03"],
                    }
                ]
            },
        }
        self._write_json(self.catalog, base)

        result = generator.generate_catalog_append(
            destination=self.append,
            base_catalog_path=self.catalog,
            member_path=self.member,
            name="Catalogue test MGO1 et MGO2",
            families_path=self.families,
            require_prepared=False,
            dry_run=False,
        )

        self.assertEqual(result["status"], "catalog-append-job-created")
        self.assertEqual(result["added_animation_id"], "0xE410")
        appended = json.loads(self.append.read_text(encoding="utf-8"))
        self.assertEqual(appended["job_id"], base["job_id"])
        self.assertEqual(appended["paths"]["run_dir"], base["paths"]["run_dir"])
        self.assertEqual(appended["paths"]["game_root"], "config://bg2ee_game_root")
        self.assertEqual(
            appended["paths"]["engine_build"],
            generator.CATALOG_ENGINE_BUILD_ROOT,
        )
        self.assertEqual(appended["members"], [self._relative(self.template), self._relative(self.member)])
        self.assertEqual(appended["qa"]["animations"][-1]["animation_id"], "0xE410")
        self.assertEqual(
            appended["qa"]["animations"][-1]["required_bam_prefixes"],
            ["MGO2"],
        )
        self.assertEqual(json.loads(self.catalog.read_text(encoding="utf-8")), base)

    def test_catalog_append_accepts_inventory_sealed_character_aggregate(self) -> None:
        leaf = self.jobs / f"test-{self.token}-character-body.json"
        aggregate = self.jobs / f"test-{self.token}-character-complete.json"
        self.addCleanup(leaf.unlink, missing_ok=True)
        self.addCleanup(aggregate.unlink, missing_ok=True)
        leaf_payload = self._member_payload("0x6110", "CHFB1", leaf.stem)
        leaf_payload["animation"].update(
            {
                "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                "armor_code": 1,
                "runtime_profile": "character-bg2ee-2.7.3.0",
            }
        )
        leaf_payload["upscale"] = dict(generator.DIRECT_X2_METHOD)
        self._write_json(leaf, leaf_payload)
        aggregate_payload = {
            "schema": generator.ARMOR_SET_SCHEMA,
            "job_id": f"test-{self.token}-character-complete",
            "animation": {
                "name": "Character complete",
                "id": "0x6110",
                "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                "runtime_profile": "character-bg2ee-2.7.3.0",
            },
            "members": [self._relative(leaf)],
            "paths": {
                "game_root": "config://bg2ee_game_root",
                "run_dir": f"pipeline/tests/{self.root.name}/character-aggregate/run",
                "engine_source": f"pipeline/tests/{self.root.name}/engine/source",
                "engine_build": f"pipeline/tests/{self.root.name}/engine/build-character",
            },
            "compatibility": {"baldur_real_sha256": "A" * 64},
            "runtime": {"cmake_generator": "Visual Studio 16 2019", "cmake_arch": "x64"},
            "qa": {
                "areas": ["AR0602"],
                "creatures": ["PLAYER1"],
                "required_bam_prefixes": ["CHFB1"],
            },
            "upscale": dict(generator.DIRECT_X2_METHOD),
            "inventory": {
                "families_csv": self._relative(self.families),
                "families_csv_sha256": hashlib.sha256(
                    self.families.read_bytes()
                ).hexdigest().upper(),
                "animation_id": "0x6110",
                "included_family_count": 1,
                "excluded_families": [],
            },
        }
        self._write_json(aggregate, aggregate_payload)
        base = {
            "schema": generator.CATALOG_JOB_SCHEMA,
            "job_id": "test-catalog-xbr2x",
            "name": "Catalogue test MGO1",
            "members": [self._relative(self.template)],
            "paths": {
                "game_root": "config://bg2ee_game_root",
                "run_dir": f"pipeline/tests/{self.root.name}/catalog/runs/xbr2x-x2",
                "engine_source": f"pipeline/tests/{self.root.name}/engine/source",
                "engine_build": f"pipeline/tests/{self.root.name}/engine/build",
            },
            "compatibility": {"baldur_real_sha256": "A" * 64},
            "runtime": {"cmake_generator": "Visual Studio 16 2019", "cmake_arch": "x64"},
            "upscale": dict(generator.DIRECT_X2_METHOD),
            "qa": {
                "animations": [
                    {
                        "animation_id": "0xE400",
                        "name": "Gobelin hache",
                        "areas": ["AR0602"],
                        "creatures": ["ICGOB03"],
                    }
                ]
            },
        }
        self._write_json(self.catalog, base)

        result = generator.generate_catalog_append(
            destination=self.append,
            base_catalog_path=self.catalog,
            member_path=aggregate,
            name="Catalogue test Character",
            families_path=self.families,
            require_prepared=False,
            dry_run=False,
        )

        self.assertEqual(result["added_member_kind"], "character-complete")
        self.assertIsNone(result["added_family_id"])
        appended = json.loads(self.append.read_text(encoding="utf-8"))
        self.assertEqual(
            appended["qa"]["animations"][-1]["required_bam_prefixes"],
            ["CHFB1"],
        )

    def test_catalog_qa_refresh_makes_legacy_requirements_explicit(self) -> None:
        base = {
            "schema": generator.CATALOG_JOB_SCHEMA,
            "job_id": "test-catalog-xbr2x",
            "name": "Legacy QA catalog",
            "members": [self._relative(self.template)],
            "paths": {
                "game_root": "config://bg2ee_game_root",
                "run_dir": f"pipeline/tests/{self.root.name}/catalog/runs/xbr2x-x2",
                "engine_source": f"pipeline/tests/{self.root.name}/engine/source",
                "engine_build": f"pipeline/tests/{self.root.name}/engine/build",
            },
            "compatibility": {"baldur_real_sha256": "A" * 64},
            "runtime": {"cmake_generator": "Visual Studio 16 2019", "cmake_arch": "x64"},
            "upscale": dict(generator.DIRECT_X2_METHOD),
            "qa": {
                "animations": [
                    {
                        "animation_id": "0xE400",
                        "name": "Gobelin hache",
                        "areas": ["AR0602"],
                        "creatures": ["ICGOB03"],
                    }
                ]
            },
        }
        self._write_json(self.catalog, base)
        refresh = (
            generator.CATALOG_JOBS_ROOT
            / f"qa-refresh-test-{self.token}-v1.json"
        )
        self.addCleanup(refresh.unlink, missing_ok=True)

        result = generator.generate_catalog_qa_refresh(
            destination=refresh,
            base_catalog_path=self.catalog,
            name="Explicit QA catalog",
            dry_run=False,
        )

        self.assertEqual(result["status"], "catalog-qa-refresh-created")
        payload = json.loads(refresh.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["qa"]["animations"][0]["required_bam_prefixes"],
            ["MGO1"],
        )
        self.assertEqual(
            payload["paths"]["engine_build"],
            generator.CATALOG_ENGINE_BUILD_ROOT,
        )


if __name__ == "__main__":
    unittest.main()
