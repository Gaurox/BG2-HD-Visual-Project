from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pipeline/scripts"
INSTALL = SCRIPTS / "Install-CreatureSprite-XN-Catalog-Test.ps1"
RESTORE = SCRIPTS / "Restore-CreatureSprite-XN-Catalog-Test.ps1"
RUNTIME = SCRIPTS / "Install-IEE-Runtime-Test.ps1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class ThinCatalogInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix=".thin-install-", dir=ROOT / "sprite"))
        self.game = self.root / "game"
        self.run = self.root / "run"
        self.generation = self.run / "generations/generation-one"
        self.build = self.generation / "build"
        self.payload = self.build / "iee-assets/creature-sprites"
        self.game_payload = self.game / "iee-assets/creature-sprites"
        self.payload.mkdir(parents=True)
        self.game_payload.mkdir(parents=True)
        self.run.mkdir(exist_ok=True)
        (self.game / "BaldurReal.exe").write_bytes(b"game-exe")
        (self.game / "InfinityEngine-Enhancer.dll").write_bytes(b"stable-runtime")
        (self.game / "InfinityEngine-Enhancer.ini").write_bytes(
            b"[Shaders]\r\nUnrelated = true\r\n"
        )
        (self.game_payload / "CreatureSprites-XN.catalog").write_bytes(
            b"previous-catalog"
        )

        self.runtime_source = self.root / "stable-runtime.dll"
        self.runtime_source.write_bytes(b"stable-runtime")
        self.runtime_manifest = self.root / "runtime.json"
        write_json(
            self.runtime_manifest,
            {
                "schema": "bg2-upscale-runtime-capabilities-v1",
                "runtime_id": "stable-water-and-sprites-v1",
                "game_profile": {
                    "baldur_real_sha256": sha256(self.game / "BaldurReal.exe")
                },
                "dll": {
                    "path": str(self.runtime_source),
                    "sha256": sha256(self.runtime_source),
                },
                "capabilities": {
                    "creature_sprite_xn_catalog": {
                        "catalog_versions": [2],
                        "shard_registry_versions": [5],
                        "frame_storage": ["XPRESS_HUFF-or-raw-per-frame-v1"],
                    }
                },
            },
        )

        self.catalog = self.payload / "CreatureSprites-XN.catalog"
        self.catalog.write_bytes(b"new-catalog")
        self.shard_a_sha256 = hashlib.sha256(b"source-a").hexdigest().upper()
        self.shard_b_sha256 = hashlib.sha256(b"source-b").hexdigest().upper()
        self.shard_a = "CreatureSprites-XN-" + self.shard_a_sha256 + ".registry"
        self.shard_b = "CreatureSprites-XN-" + self.shard_b_sha256 + ".registry"
        (self.payload / self.shard_a).write_bytes(b"source-a")
        (self.payload / self.shard_b).write_bytes(b"source-b")
        (self.game_payload / self.shard_a).write_bytes(b"source-a")
        build_manifest = self.build / "build-manifest.json"
        write_json(
            build_manifest,
            {
                "schema": "bg2-upscale-creature-sprite-xn-catalog-pack-v1",
                "generation_id": "GENERATION-ONE",
                "registry_layout": "catalog",
                "registry_catalog": "iee-assets/creature-sprites/CreatureSprites-XN.catalog",
                "registry_catalog_version": 2,
                "registry_catalog_shard_version": 5,
                "registry_catalog_frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
                "registry_catalog_sha256": sha256(self.catalog),
                "registry_catalog_bytes": self.catalog.stat().st_size,
                "animation_ids": ["0x7F0D"],
                "shards": [
                    {
                        "registry": f"iee-assets/creature-sprites/{self.shard_a}",
                        "sha256": self.shard_a_sha256,
                    },
                    {
                        "registry": f"iee-assets/creature-sprites/{self.shard_b}",
                        "sha256": self.shard_b_sha256,
                    },
                ],
            },
        )
        write_json(
            self.run / "current-generation.json",
            {
                "schema": "bg2-upscale-creature-sprite-xn-catalog-current-generation-v1",
                "generation_id": "GENERATION-ONE",
                "generation_dir": str(self.generation),
                "build_manifest": "build/build-manifest.json",
            },
        )
        self.job = self.root / "job.json"
        write_json(
            self.job,
            {
                "schema": "bg2-upscale-creature-sprite-xn-catalog-job-v1",
                "job_id": "fake-catalog",
                "paths": {"game_root": str(self.game), "run_dir": str(self.run)},
                "compatibility": {
                    "baldur_real_sha256": sha256(self.game / "BaldurReal.exe")
                },
            },
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def run_ps(self, script: Path, *arguments: str, check: bool = True):
        executable = shutil.which("pwsh.exe") or shutil.which("powershell.exe")
        self.assertIsNotNone(executable)
        command = [
            str(executable),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *map(str, arguments),
        ]
        return subprocess.run(
            command, cwd=ROOT, text=True, capture_output=True, check=check
        )

    def make_derived_job(self) -> tuple[Path, Path, Path]:
        parent_manifest = self.build / "build-manifest.json"
        parent_value = json.loads(parent_manifest.read_text(encoding="utf-8"))
        parent_value["job_file"] = str(self.job)
        parent_value["job_sha256"] = sha256(self.job)
        write_json(parent_manifest, parent_value)
        derived_run = self.root / "derived-run"
        generation = derived_run / "generations/derived-generation"
        build = generation / "build"
        payload = build / "iee-assets/creature-sprites"
        payload.mkdir(parents=True)
        catalog = payload / "CreatureSprites-XN.catalog"
        catalog.write_bytes(b"derived-catalog")
        (payload / self.shard_a).write_bytes(b"source-a")
        (payload / self.shard_b).write_bytes(b"source-b")
        self.derived_shard_sha256 = hashlib.sha256(
            b"derived-only"
        ).hexdigest().upper()
        self.derived_shard = (
            "CreatureSprites-XN-" + self.derived_shard_sha256 + ".registry"
        )
        (payload / self.derived_shard).write_bytes(b"derived-only")
        derived_job = self.root / "derived-job.json"
        parent_pointer = self.run / "current-generation.json"
        write_json(
            derived_job,
            {
                "schema": "bg2-upscale-reboutcx-derived-catalog-job-v1",
                "job_id": "fake-reboutcx-catalog",
                "installable": False,
                "target_scale": 2,
                "paths": {
                    "parent_pointer": str(parent_pointer),
                    "run_dir": str(derived_run),
                },
                "parent": {
                    "pointer_sha256": sha256(parent_pointer),
                },
            },
        )
        manifest = build / "build-manifest.json"
        write_json(
            manifest,
            {
                "schema": "bg2-upscale-reboutcx-derived-catalog-build-v1",
                "status": "built-offline-verified",
                "installable": False,
                "generation_id": "DERIVED-GENERATION",
                "registry_catalog": "iee-assets/creature-sprites/CreatureSprites-XN.catalog",
                "registry_scale": 2,
                "registry_catalog_sha256": sha256(catalog),
                "registry_catalog_bytes": catalog.stat().st_size,
                "animations": [{"animation_id": "0x7F0D"}],
                "shards": [
                    {
                        "registry": f"iee-assets/creature-sprites/{self.shard_a}",
                        "sha256": self.shard_a_sha256,
                    },
                    {
                        "registry": f"iee-assets/creature-sprites/{self.shard_b}",
                        "sha256": self.shard_b_sha256,
                    },
                    {
                        "registry": f"iee-assets/creature-sprites/{self.derived_shard}",
                        "sha256": self.derived_shard_sha256,
                    },
                ],
                "storage": {
                    "shard_registry_version": 5,
                    "frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
                },
                "parent": {
                    "generation_id": "GENERATION-ONE",
                    "pointer": str(parent_pointer),
                    "pointer_sha256": sha256(parent_pointer),
                    "build_manifest": str(parent_manifest),
                    "build_manifest_sha256": sha256(parent_manifest),
                    "catalog_sha256": sha256(self.catalog),
                },
            },
        )
        pointer = derived_run / "current-generation.json"
        write_json(
            pointer,
            {
                "schema": "bg2-upscale-reboutcx-derived-catalog-current-v1",
                "generation_id": "DERIVED-GENERATION",
                "job_sha256": sha256(derived_job),
                "generation_dir": str(generation),
                "build_manifest": "build/build-manifest.json",
                "build_manifest_sha256": sha256(manifest),
                "catalog_sha256": sha256(catalog),
            },
        )
        return derived_job, manifest, pointer

    def test_runtime_install_and_restore_are_independent(self) -> None:
        live = self.game / "InfinityEngine-Enhancer.dll"
        live.write_bytes(b"previous-runtime")
        state_root = self.root / "runtime-state"
        self.run_ps(
            RUNTIME,
            "-Mode", "Install",
            "-Manifest", self.runtime_manifest,
            "-GameRoot", self.game,
            "-StateRoot", state_root,
        )
        self.assertEqual(live.read_bytes(), b"stable-runtime")
        self.run_ps(
            RUNTIME,
            "-Mode", "Restore",
            "-GameRoot", self.game,
            "-StateRoot", state_root,
        )
        self.assertEqual(live.read_bytes(), b"previous-runtime")

    def test_catalog_install_skips_existing_shards_and_never_touches_runtime(self) -> None:
        live = self.game / "InfinityEngine-Enhancer.dll"
        runtime_before = live.read_bytes()
        ini = self.game / "InfinityEngine-Enhancer.ini"
        ini_before = ini.read_bytes()
        catalog_target = self.game_payload / "CreatureSprites-XN.catalog"
        self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
        )
        self.assertEqual(live.read_bytes(), runtime_before)
        self.assertEqual(catalog_target.read_bytes(), b"new-catalog")
        self.assertEqual((self.game_payload / self.shard_a).read_bytes(), b"source-a")
        self.assertEqual((self.game_payload / self.shard_b).read_bytes(), b"source-b")
        self.assertIn(b"EnableCreatureSpriteUpscaleTest = true", ini.read_bytes())
        state = json.loads(
            (self.run / "ingame-installation/active-test.json").read_text()
        )
        self.assertEqual(state["schema"], "bg2-upscale-creature-sprite-catalog-install-v2")
        self.assertEqual(state["shards_copied"], 1)
        self.run_ps(RESTORE, "-JobFile", self.job)
        self.assertEqual(live.read_bytes(), runtime_before)
        self.assertEqual(catalog_target.read_bytes(), b"previous-catalog")
        self.assertEqual(ini.read_bytes(), ini_before)
        self.assertEqual((self.game_payload / self.shard_b).read_bytes(), b"source-b")
        self.assertFalse((self.run / "ingame-installation/active-test.json").exists())

    def test_catalog_rejects_another_live_runtime(self) -> None:
        (self.game / "InfinityEngine-Enhancer.dll").write_bytes(b"wrong-runtime")
        result = self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime stable", result.stderr)

    def test_catalog_installer_accepts_delta_jobs(self) -> None:
        job = json.loads(self.job.read_text(encoding="utf-8"))
        job["schema"] = "bg2-upscale-creature-sprite-xn-catalog-delta-job-v1"
        write_json(self.job, job)
        result = self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
        )
        self.assertIn("verified", result.stdout)

    def test_derived_catalog_verify_only_resolves_xbr_environment(self) -> None:
        derived_job, _manifest, _pointer = self.make_derived_job()
        ini_before = (self.game / "InfinityEngine-Enhancer.ini").read_bytes()
        catalog_before = (
            self.game_payload / "CreatureSprites-XN.catalog"
        ).read_bytes()
        result = self.run_ps(
            INSTALL,
            "-JobFile", derived_job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
        )
        self.assertIn("verified", result.stdout)
        self.assertIn("DERIVED-GENERATION", result.stdout)
        self.assertEqual(
            (self.game / "InfinityEngine-Enhancer.ini").read_bytes(), ini_before
        )
        self.assertEqual(
            (self.game_payload / "CreatureSprites-XN.catalog").read_bytes(),
            catalog_before,
        )

    def test_derived_catalog_rejects_changed_parent_contract(self) -> None:
        derived_job, manifest, pointer = self.make_derived_job()
        value = json.loads(manifest.read_text(encoding="utf-8"))
        value["parent"]["build_manifest_sha256"] = "0" * 64
        write_json(manifest, value)
        pointer_value = json.loads(pointer.read_text(encoding="utf-8"))
        pointer_value["build_manifest_sha256"] = sha256(manifest)
        write_json(pointer, pointer_value)
        result = self.run_ps(
            INSTALL,
            "-JobFile", derived_job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("parent", result.stderr)

    def test_derived_catalog_install_requires_explicit_switch(self) -> None:
        derived_job, _manifest, _pointer = self.make_derived_job()
        ini_before = (self.game / "InfinityEngine-Enhancer.ini").read_bytes()
        catalog_target = self.game_payload / "CreatureSprites-XN.catalog"
        catalog_before = catalog_target.read_bytes()
        result = self.run_ps(
            INSTALL,
            "-JobFile", derived_job,
            "-RuntimeManifest", self.runtime_manifest,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("EnableDerivedInstall", result.stderr)
        self.assertEqual(
            (self.game / "InfinityEngine-Enhancer.ini").read_bytes(), ini_before
        )
        self.assertEqual(catalog_target.read_bytes(), catalog_before)

    def test_derived_verify_uses_xbr_shared_receipt_and_runtime(self) -> None:
        derived_job, _manifest, _pointer = self.make_derived_job()
        self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
        )
        result = self.run_ps(
            INSTALL,
            "-JobFile", derived_job,
            "-VerifyOnly",
        )
        self.assertIn("verified", result.stdout)
        self.assertIn("GENERATION-ONE", result.stdout)
        derived_state = (
            self.root
            / "derived-run/ingame-installation/active-test.json"
        )
        self.assertFalse(derived_state.exists())
        self.assertTrue(
            (self.run / "ingame-installation/active-test.json").is_file()
        )

    def test_already_installed_requires_live_catalog_hash(self) -> None:
        self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
        )
        result = self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
        )
        self.assertIn("already-installed", result.stdout)
        (self.game_payload / "CreatureSprites-XN.catalog").write_bytes(b"corrupt")
        result = self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Catalogue actif divergent", result.stderr)

    def test_verify_rejects_corrupt_existing_target_shard(self) -> None:
        (self.game_payload / self.shard_a).write_bytes(b"corrupt")
        result = self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("corrompu ou concurrent", result.stderr)

    def test_verify_rejects_corrupt_source_shard(self) -> None:
        (self.payload / self.shard_b).write_bytes(b"corrupt")
        result = self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("shard source", result.stderr)

    def test_verify_rejects_active_ini_divergence(self) -> None:
        self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
        )
        ini = self.game / "InfinityEngine-Enhancer.ini"
        ini.write_text(
            ini.read_text(encoding="utf-8").replace(
                "CreatureSpriteFilter = Nearest",
                "CreatureSpriteFilter = CatmullRom",
            ),
            encoding="utf-8",
        )
        result = self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CreatureSpriteFilter", result.stderr)

    def test_derived_round_trip_restores_xbr_and_keeps_inert_shard(self) -> None:
        derived_job, _manifest, _pointer = self.make_derived_job()
        self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
        )
        state_path = self.run / "ingame-installation/active-test.json"
        ini = self.game / "InfinityEngine-Enhancer.ini"
        catalog_target = self.game_payload / "CreatureSprites-XN.catalog"
        xbr_ini = ini.read_bytes()
        xbr_catalog = catalog_target.read_bytes()
        xbr_state = state_path.read_bytes()

        result = self.run_ps(
            INSTALL,
            "-JobFile", derived_job,
            "-RuntimeManifest", self.runtime_manifest,
            "-EnableDerivedInstall",
        )
        self.assertIn("installed-pending-qa", result.stdout)
        self.assertEqual(catalog_target.read_bytes(), b"derived-catalog")
        active = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(active["generation_id"], "DERIVED-GENERATION")
        inert_shard = self.game_payload / self.derived_shard
        self.assertEqual(inert_shard.read_bytes(), b"derived-only")

        result = self.run_ps(RESTORE, "-JobFile", derived_job)
        self.assertIn("restored", result.stdout)
        self.assertEqual(ini.read_bytes(), xbr_ini)
        self.assertEqual(catalog_target.read_bytes(), xbr_catalog)
        self.assertEqual(state_path.read_bytes(), xbr_state)
        self.assertEqual(inert_shard.read_bytes(), b"derived-only")

        result = self.run_ps(RESTORE, "-JobFile", derived_job)
        self.assertIn("not-active", result.stdout)
        self.assertEqual(ini.read_bytes(), xbr_ini)
        self.assertEqual(catalog_target.read_bytes(), xbr_catalog)
        self.assertEqual(state_path.read_bytes(), xbr_state)

    def test_interrupted_transaction_is_read_only_in_verify_then_recovered(self) -> None:
        derived_job, _manifest, _pointer = self.make_derived_job()
        self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
        )
        state_path = self.run / "ingame-installation/active-test.json"
        ini = self.game / "InfinityEngine-Enhancer.ini"
        catalog_target = self.game_payload / "CreatureSprites-XN.catalog"
        xbr_ini = ini.read_bytes()
        xbr_catalog = catalog_target.read_bytes()
        xbr_state = state_path.read_bytes()
        backup = self.run / "ingame-installation/backups/interrupted"
        backup.mkdir(parents=True)
        ini_backup = backup / "InfinityEngine-Enhancer.ini"
        catalog_backup = backup / "CreatureSprites-XN.catalog"
        state_backup = backup / "previous-active-test.json"
        ini_backup.write_bytes(xbr_ini)
        catalog_backup.write_bytes(xbr_catalog)
        state_backup.write_bytes(xbr_state)
        write_json(
            state_path,
            {
                "schema": "bg2-upscale-creature-sprite-catalog-install-v2",
                "status": "installing",
                "transaction_id": "interrupted",
                "job_file": str(derived_job),
                "job_id": "fake-reboutcx-catalog",
                "generation_id": "DERIVED-GENERATION",
                "game_root": str(self.game),
                "runtime_id": "stable-water-and-sprites-v1",
                "runtime_manifest": str(self.runtime_manifest),
                "catalog_relative_path": "iee-assets/creature-sprites/CreatureSprites-XN.catalog",
                "catalog_sha256": hashlib.sha256(
                    b"derived-catalog"
                ).hexdigest().upper(),
                "catalog_existed_before": True,
                "catalog_backup": "CreatureSprites-XN.catalog",
                "catalog_backup_sha256": sha256(catalog_backup),
                "ini_backup": "InfinityEngine-Enhancer.ini",
                "ini_backup_sha256": sha256(ini_backup),
                "backup_root": str(backup),
                "previous_active_state": "previous-active-test.json",
                "previous_active_state_sha256": sha256(state_backup),
                "creature_sprite_filter": "Nearest",
            },
        )
        ini.write_bytes(b"interrupted-ini")
        catalog_target.write_bytes(b"interrupted-catalog")

        result = self.run_ps(
            INSTALL,
            "-JobFile", derived_job,
            "-RuntimeManifest", self.runtime_manifest,
            "-VerifyOnly",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Transaction catalogue", result.stderr)
        self.assertEqual(ini.read_bytes(), b"interrupted-ini")
        self.assertEqual(catalog_target.read_bytes(), b"interrupted-catalog")

        result = self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
        )
        self.assertIn("already-installed", result.stdout)
        self.assertEqual(ini.read_bytes(), xbr_ini)
        self.assertEqual(catalog_target.read_bytes(), xbr_catalog)
        self.assertEqual(state_path.read_bytes(), xbr_state)

    def test_restore_rejects_corrupt_backup_before_writing(self) -> None:
        derived_job, _manifest, _pointer = self.make_derived_job()
        self.run_ps(
            INSTALL,
            "-JobFile", self.job,
            "-RuntimeManifest", self.runtime_manifest,
        )
        self.run_ps(
            INSTALL,
            "-JobFile", derived_job,
            "-RuntimeManifest", self.runtime_manifest,
            "-EnableDerivedInstall",
        )
        state_path = self.run / "ingame-installation/active-test.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        backup_catalog = Path(state["backup_root"]) / state["catalog_backup"]
        backup_catalog.write_bytes(b"corrupt-backup")
        ini = self.game / "InfinityEngine-Enhancer.ini"
        catalog_target = self.game_payload / "CreatureSprites-XN.catalog"
        active_ini = ini.read_bytes()
        active_catalog = catalog_target.read_bytes()
        active_state = state_path.read_bytes()

        result = self.run_ps(
            RESTORE,
            "-JobFile", derived_job,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("catalogue de transaction", result.stderr)
        self.assertEqual(ini.read_bytes(), active_ini)
        self.assertEqual(catalog_target.read_bytes(), active_catalog)
        self.assertEqual(state_path.read_bytes(), active_state)

    def test_legacy_restore_does_not_restore_its_runtime_dll(self) -> None:
        backup = self.run / "ingame-installation/backups/legacy"
        backup.mkdir(parents=True)
        (backup / "old.ini").write_bytes(b"old-ini")
        (backup / "old.catalog").write_bytes(b"old-catalog")
        (backup / "old.dll").write_bytes(b"obsolete-runtime")
        state = {
            "schema": "bg2-upscale-creature-sprite-xn-catalog-ingame-test-v1",
            "generation_id": "legacy",
            "game_root": str(self.game),
            "backup_root": str(backup),
            "targets": [
                {
                    "relative_path": "InfinityEngine-Enhancer.dll",
                    "role": "runtime-dll",
                    "existed_before": True,
                    "backup_path": str(backup / "old.dll"),
                },
                {
                    "relative_path": "InfinityEngine-Enhancer.ini",
                    "role": "runtime-ini",
                    "existed_before": True,
                    "backup_path": str(backup / "old.ini"),
                },
                {
                    "relative_path": "iee-assets/creature-sprites/CreatureSprites-XN.catalog",
                    "role": "catalog",
                    "existed_before": True,
                    "backup_path": str(backup / "old.catalog"),
                },
            ],
        }
        write_json(self.run / "ingame-installation/active-test.json", state)
        self.run_ps(RESTORE, "-JobFile", self.job)
        self.assertEqual(
            (self.game / "InfinityEngine-Enhancer.dll").read_bytes(), b"stable-runtime"
        )
        self.assertEqual(
            (self.game / "InfinityEngine-Enhancer.ini").read_bytes(), b"old-ini"
        )
        self.assertEqual(
            (self.game_payload / "CreatureSprites-XN.catalog").read_bytes(),
            b"old-catalog",
        )


if __name__ == "__main__":
    unittest.main()
