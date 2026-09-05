from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pipeline" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_animation_upscale_30fps_v2 as runtime_v2  # noqa: E402


CORE_PATH = ROOT / "pipeline" / "area-animation-area-test" / "area_animation_area_test.py"
SPEC = importlib.util.spec_from_file_location("area_animation_area_test", CORE_PATH)
assert SPEC is not None and SPEC.loader is not None
transaction = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = transaction
SPEC.loader.exec_module(transaction)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


class AreaAnimationAreaTestTransactionTests(unittest.TestCase):
    def make_game(self, root: Path) -> tuple[Path, Path]:
        game = root / "game"
        areas = game / "iee-assets" / "areas"
        areas.mkdir(parents=True)
        (game / "chitin.key").write_bytes(b"key")
        (game / "InfinityEngine-Enhancer.dll").write_bytes(b"development-renderer")
        (game / "InfinityEngine-Enhancer.ini").write_text(
            "[Shaders]\nEnableAreaAnimationX4 = true\n", encoding="utf-8"
        )
        return game, areas

    def make_pack(self, root: Path, area_id: str = "AR0001", marker: int = 17) -> Path:
        pack = root / area_id
        pack.mkdir(parents=True)
        asset_name = runtime_v2.asset_name("TESTA", 0)
        asset_path = pack / asset_name
        asset_path.write_bytes(bytes([marker]) * 64)
        asset = {"name": asset_name, "bytes": 64, "sha256": sha256(asset_path)}
        resource = {
            "resref": "TESTA",
            "frame_count": 1,
            "cycle_count": 1,
            "geometry_mode": "uniform",
            "frames": [
                {
                    "frame": 0,
                    "logical_size_x1": [1, 1],
                    "physical_size_x4": [4, 4],
                    "centre_x1": [0, 0],
                    "asset": asset_name,
                    "bytes": 64,
                    "sha256": asset["sha256"],
                }
            ],
            "assets": [asset],
            "cycles": [{"cycle": 0, "native_frame_indices": [0], "timeline_frame_indices": []}],
            "playback_mode": "Native",
            "native_fps": {"numerator": 0, "denominator": 0},
            "target_fps": {"numerator": 0, "denominator": 0},
        }
        registry = runtime_v2.registry_v2_from_resources(
            [resource], runtime_v2.LEGACY_REGISTRY_VERSION
        )
        registry_path = pack / runtime_v2.REGISTRY_NAME
        registry_path.write_bytes(registry)
        manifest = {
            "schema": runtime_v2.PACK_SCHEMA,
            "status": "completed",
            "scale": 4,
            "registry_version": runtime_v2.LEGACY_REGISTRY_VERSION,
            "runtime_contract": {
                "feature": "TimedTimeline",
                "clock": "QPC-pause-aware",
                "registry_version": runtime_v2.LEGACY_REGISTRY_VERSION,
            },
            "registry": runtime_v2.REGISTRY_NAME,
            "registry_sha256": sha256(registry_path),
            "registry_bytes": len(registry),
            "resource_count": 1,
            "frame_count": 1,
            "timed_resources": [],
            "area_id": area_id,
            "raw_bytes": 64,
            "runtime_budget_enforced": True,
            "base_assets": [],
            "new_assets": [],
            "resources": [resource],
        }
        (pack / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return pack

    def install(self, pack: Path, game: Path, backups: Path, **kwargs: object) -> object:
        return transaction.install_area_pack(
            pack,
            game_root=game,
            backup_root=backups,
            process_checker=lambda: [],
            **kwargs,
        )

    def restore(self, backup: Path, game: Path, **kwargs: object) -> object:
        return transaction.restore_from_receipt(
            backup,
            game_root=game,
            process_checker=lambda: [],
            **kwargs,
        )

    def test_verify_only_never_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, areas = self.make_game(root)
            target = areas / "AR0001"
            target.mkdir()
            (target / "legacy.bin").write_bytes(b"previous")
            other = areas / "AR0002"
            other.mkdir()
            (other / "sentinel.bin").write_bytes(b"other-area")
            pack = self.make_pack(root / "pack-root")
            backups = root / "backups"
            before = tree_bytes(root)

            result = self.install(pack, game, backups, verify_only=True)

            self.assertEqual(result.status, "verified-only")
            self.assertEqual(tree_bytes(root), before)
            self.assertFalse(backups.exists())

    def test_install_absent_zone_and_restore_absence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, areas = self.make_game(root)
            other = areas / "AR0002"
            other.mkdir()
            (other / "sentinel.bin").write_bytes(b"other-area")
            other_before = tree_bytes(other)
            pack = self.make_pack(root / "pack-root")
            backups = root / "backups"

            result = self.install(pack, game, backups)

            self.assertEqual(result.status, "installed")
            self.assertIsNotNone(result.receipt_path)
            target = areas / "AR0001"
            self.assertEqual(
                {path.name for path in target.iterdir()},
                {runtime_v2.REGISTRY_NAME, runtime_v2.asset_name("TESTA", 0)},
            )
            self.assertEqual(tree_bytes(other), other_before)

            restored = self.restore(result.receipt_path, game)

            self.assertEqual(restored["status"], "restored")
            self.assertFalse(target.exists())
            self.assertEqual(tree_bytes(other), other_before)

    def test_replace_existing_zone_and_restore_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, areas = self.make_game(root)
            target = areas / "AR0001"
            target.mkdir()
            (target / "legacy-a.bin").write_bytes(b"previous-a")
            (target / "legacy-b.bin").write_bytes(b"previous-b")
            before = tree_bytes(target)
            pack = self.make_pack(root / "pack-root", marker=42)

            result = self.install(pack, game, root / "backups")
            self.assertEqual(result.status, "installed")
            self.assertNotEqual(tree_bytes(target), before)

            self.restore(result.receipt_path, game)
            self.assertEqual(tree_bytes(target), before)

    def test_corrupted_source_is_refused_without_backup_or_target_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, areas = self.make_game(root)
            target = areas / "AR0001"
            target.mkdir()
            (target / "legacy.bin").write_bytes(b"previous")
            pack = self.make_pack(root / "pack-root")
            (pack / runtime_v2.asset_name("TESTA", 0)).write_bytes(b"corrupted")
            before = tree_bytes(root)
            backups = root / "backups"

            with self.assertRaisesRegex(transaction.TransactionError, "pack runtime v2 invalide|asset runtime"):
                self.install(pack, game, backups)

            self.assertEqual(tree_bytes(root), before)
            self.assertFalse(backups.exists())

    def test_failures_around_bascule_roll_back_exactly(self) -> None:
        for failure_point in ("before-switch", "after-target-moved", "after-install-published"):
            with self.subTest(failure_point=failure_point), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                game, areas = self.make_game(root)
                target = areas / "AR0001"
                target.mkdir()
                (target / "legacy.bin").write_bytes(b"previous")
                before = tree_bytes(target)
                pack = self.make_pack(root / "pack-root")
                backups = root / "backups"

                def fail_at_requested_point(point: str) -> None:
                    if point == failure_point:
                        raise OSError(f"synthetic failure: {point}")

                with self.assertRaisesRegex(transaction.TransactionError, "état initial restauré"):
                    self.install(pack, game, backups, failure_hook=fail_at_requested_point)

                self.assertEqual(tree_bytes(target), before)
                receipt_path = next(backups.glob(f"*/{transaction.RECEIPT_NAME}"))
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                self.assertEqual(receipt["status"], "rolled-back")
                self.assertFalse(
                    any(path.name.startswith(transaction.TRANSIENT_PREFIX) for path in areas.iterdir())
                )

    def test_restore_refuses_drifted_installed_zone(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, areas = self.make_game(root)
            pack = self.make_pack(root / "pack-root")
            result = self.install(pack, game, root / "backups")
            target = areas / "AR0001"
            registry = target / runtime_v2.REGISTRY_NAME
            registry.write_bytes(b"external-change")

            with self.assertRaisesRegex(transaction.TransactionError, "état installé divergent"):
                self.restore(result.receipt_path, game)

            self.assertEqual(registry.read_bytes(), b"external-change")

    def test_restore_verify_only_never_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, _areas = self.make_game(root)
            result = self.install(self.make_pack(root / "pack-root"), game, root / "backups")
            before = tree_bytes(root)

            receipt = self.restore(result.receipt_path, game, verify_only=True)

            self.assertEqual(receipt["status"], "installed")
            self.assertEqual(tree_bytes(root), before)

    def test_restore_refuses_tampered_receipt_or_backup_without_writing(self) -> None:
        for tamper in ("receipt", "backup"):
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                game, areas = self.make_game(root)
                target = areas / "AR0001"
                target.mkdir()
                (target / "legacy.bin").write_bytes(b"previous")
                result = self.install(self.make_pack(root / "pack-root"), game, root / "backups")
                target_before_restore = tree_bytes(target)

                if tamper == "receipt":
                    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
                    receipt["installed"]["files"][0]["bytes"] += 1
                    result.receipt_path.write_text(
                        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                    )
                    expected_error = "empreinte"
                else:
                    (result.receipt_path.parent / "previous" / "legacy.bin").write_bytes(b"tampered")
                    expected_error = "sauvegarde précédente divergente"

                with self.assertRaisesRegex(transaction.TransactionError, expected_error):
                    self.restore(result.receipt_path, game)
                self.assertEqual(tree_bytes(target), target_before_restore)

    def test_switching_receipt_recovers_when_target_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, areas = self.make_game(root)
            target = areas / "AR0001"
            target.mkdir()
            (target / "legacy.bin").write_bytes(b"previous")
            before = tree_bytes(target)
            result = self.install(self.make_pack(root / "pack-root"), game, root / "backups")
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            receipt["status"] = "switching"
            result.receipt_path.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            transaction.safe_remove_tree(target, areas, target.name)

            restored = self.restore(result.receipt_path, game)

            self.assertEqual(restored["status"], "restored")
            self.assertEqual(tree_bytes(target), before)

    def test_backup_root_inside_source_pack_is_refused_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, _areas = self.make_game(root)
            pack = self.make_pack(root / "pack-root")
            before = tree_bytes(root)

            with self.assertRaisesRegex(transaction.TransactionError, "BackupRoot"):
                self.install(pack, game, pack / "install-backups")

            self.assertEqual(tree_bytes(root), before)

    def test_powershell_entrypoints_use_only_the_fixture_game(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell indisponible")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, areas = self.make_game(root)
            pack = self.make_pack(root / "pack-root")
            backups = root / "backups"
            installer = ROOT / "pipeline" / "scripts" / "Install-AreaAnimation-AreaTest.ps1"
            restorer = ROOT / "pipeline" / "scripts" / "Restore-AreaAnimation-AreaTest.ps1"
            command = [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(installer),
                "-AreaPack",
                str(pack),
                "-GameRoot",
                str(game),
                "-BackupRoot",
                str(backups),
            ]

            verified = subprocess.run(command + ["-VerifyOnly"], capture_output=True, text=True)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertFalse((areas / "AR0001").exists())
            installed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            backup = next(backups.glob("*/install-backup.json")).parent

            restore_command = [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(restorer),
                "-BackupPath",
                str(backup),
                "-GameRoot",
                str(game),
            ]
            verified_restore = subprocess.run(
                restore_command + ["-VerifyOnly"], capture_output=True, text=True
            )
            self.assertEqual(verified_restore.returncode, 0, verified_restore.stderr)
            restored = subprocess.run(restore_command, capture_output=True, text=True)
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertFalse((areas / "AR0001").exists())

    def test_ini_or_process_precondition_refuses_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, _areas = self.make_game(root)
            pack = self.make_pack(root / "pack-root")
            backups = root / "backups"
            (game / "InfinityEngine-Enhancer.ini").write_text(
                "[Shaders]\nEnableAreaAnimationX4 = true\nEnableAreaAnimationX4 = true\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(transaction.TransactionError, "exactement"):
                self.install(pack, game, backups)
            self.assertFalse(backups.exists())

            (game / "InfinityEngine-Enhancer.ini").write_text(
                "[Shaders]\nEnableAreaAnimationX4 = true\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(transaction.TransactionError, "InfinityLoader.exe"):
                transaction.install_area_pack(
                    pack,
                    game_root=game,
                    backup_root=backups,
                    process_checker=lambda: ["InfinityLoader.exe"],
                )
            self.assertFalse(backups.exists())


if __name__ == "__main__":
    unittest.main()
