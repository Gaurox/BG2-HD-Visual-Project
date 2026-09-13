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
        self.shard_a = "CreatureSprites-XN-" + "A" * 64 + ".registry"
        self.shard_b = "CreatureSprites-XN-" + "B" * 64 + ".registry"
        (self.payload / self.shard_a).write_bytes(b"source-a")
        (self.payload / self.shard_b).write_bytes(b"source-b")
        (self.game_payload / self.shard_a).write_bytes(b"accepted-a")
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
                        "sha256": "A" * 64,
                    },
                    {
                        "registry": f"iee-assets/creature-sprites/{self.shard_b}",
                        "sha256": "B" * 64,
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
        self.assertEqual((self.game_payload / self.shard_a).read_bytes(), b"accepted-a")
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
