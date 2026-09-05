from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import inject_build as transaction  # noqa: E402


def write_tis(path: Path, pages: list[int]) -> None:
    payload = bytearray(b"TIS V1  ")
    payload.extend(struct.pack("<IIII", len(pages), 12, 24, 256))
    for page in pages:
        payload.extend(struct.pack("<III", page, 0, 0))
    path.write_bytes(payload)


def write_pvrz(path: Path, marker: bytes) -> None:
    decoded = b"PVR\x03" + marker * 1024
    path.write_bytes(struct.pack("<I", len(decoded)) + zlib.compress(decoded, 6))


class MapBuildTransactionTests(unittest.TestCase):
    def make_layout(self, root: Path) -> tuple[Path, Path, Path, Path]:
        game = root / "game"
        override = game / "override"
        build = root / "build"
        backups = root / "backups"
        override.mkdir(parents=True)
        build.mkdir()
        write_tis(build / "ARTEST.TIS", [0, 1])
        write_pvrz(build / "ATEST00.PVRZ", b"new-zero")
        write_pvrz(build / "ATEST01.PVRZ", b"new-one")
        return game, override, build, backups

    def test_install_and_restore_are_exact_and_receipted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, override, build, backups = self.make_layout(root)
            write_tis(override / "ARTEST.TIS", [0, 2])
            write_pvrz(override / "ATEST00.PVRZ", b"old-zero")
            write_pvrz(override / "ATEST02.PVRZ", b"stale-two")
            before = {
                path.name: path.read_bytes()
                for path in override.iterdir()
                if path.is_file()
            }

            result = transaction.install_build(
                "artest",
                build,
                game_root=game,
                backup_root=backups,
                process_checker=lambda: [],
            )

            self.assertEqual(result.status, "installed")
            self.assertEqual(result.retired_files, ("ATEST02.PVRZ",))
            self.assertIsNotNone(result.receipt_path)
            self.assertEqual(
                {path.name for path in override.iterdir()},
                {"ARTEST.TIS", "ATEST00.PVRZ", "ATEST01.PVRZ"},
            )
            for source in build.iterdir():
                self.assertEqual((override / source.name).read_bytes(), source.read_bytes())
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema"], transaction.RECEIPT_SCHEMA)
            self.assertEqual(receipt["status"], "installed")
            self.assertRegex(receipt["before_set_sha256"], r"^[A-F0-9]{64}$")
            self.assertRegex(receipt["installed_set_sha256"], r"^[A-F0-9]{64}$")
            self.assertEqual(receipt["retired_inventory"], ["ATEST02.PVRZ"])
            transaction.verify_transaction(result.receipt_path, game)

            restored = transaction.restore_from_receipt(
                result.receipt_path,
                game,
                process_checker=lambda: [],
            )

            self.assertEqual(restored["status"], "restored")
            self.assertEqual(
                {path.name: path.read_bytes() for path in override.iterdir()},
                before,
            )
            transaction.verify_transaction(result.receipt_path, game)

    def test_source_inventory_mismatch_is_rejected_before_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, override, build, backups = self.make_layout(root)
            (build / "ATEST01.PVRZ").unlink()

            with self.assertRaisesRegex(transaction.TransactionError, "inventaire PVRZ divergent"):
                transaction.install_build(
                    "ARTEST",
                    build,
                    game_root=game,
                    backup_root=backups,
                    process_checker=lambda: [],
                )

            self.assertEqual(list(override.iterdir()), [])
            self.assertFalse(backups.exists())

    def test_restore_refuses_divergent_installed_state_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, override, build, backups = self.make_layout(root)
            write_pvrz(override / "ATEST00.PVRZ", b"old-zero")
            result = transaction.install_build(
                "ARTEST",
                build,
                game_root=game,
                backup_root=backups,
                process_checker=lambda: [],
            )
            (override / "ATEST00.PVRZ").write_bytes(b"user-change")
            untouched = (override / "ATEST01.PVRZ").read_bytes()

            with self.assertRaisesRegex(transaction.TransactionError, "état installed divergent"):
                transaction.restore_from_receipt(
                    result.receipt_path,
                    game,
                    process_checker=lambda: [],
                )

            self.assertEqual((override / "ATEST00.PVRZ").read_bytes(), b"user-change")
            self.assertEqual((override / "ATEST01.PVRZ").read_bytes(), untouched)

    def test_restore_refuses_an_unreceipted_page_in_the_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, override, build, backups = self.make_layout(root)
            result = transaction.install_build(
                "ARTEST",
                build,
                game_root=game,
                backup_root=backups,
                process_checker=lambda: [],
            )
            write_pvrz(override / "ATEST99.PVRZ", b"external-page")

            with self.assertRaisesRegex(transaction.TransactionError, "inventaire PVRZ"):
                transaction.restore_from_receipt(
                    result.receipt_path,
                    game,
                    process_checker=lambda: [],
                )

            self.assertTrue((override / "ATEST99.PVRZ").exists())
            self.assertEqual(
                json.loads(result.receipt_path.read_text(encoding="utf-8"))["status"],
                "installed",
            )

    def test_failed_install_rolls_back_the_complete_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, override, build, backups = self.make_layout(root)
            write_tis(override / "ARTEST.TIS", [0])
            write_pvrz(override / "ATEST00.PVRZ", b"old-zero")
            before = {
                path.name: path.read_bytes()
                for path in override.iterdir()
                if path.is_file()
            }
            real_atomic_copy = transaction.atomic_copy
            build_copy_count = 0

            def fail_second_build_copy(source: Path, target: Path, expected: object) -> None:
                nonlocal build_copy_count
                if source.parent == build:
                    build_copy_count += 1
                    if build_copy_count == 2:
                        raise OSError("synthetic copy failure")
                real_atomic_copy(source, target, expected)

            with mock.patch.object(
                transaction, "atomic_copy", side_effect=fail_second_build_copy
            ):
                with self.assertRaisesRegex(transaction.TransactionError, "état initial restauré"):
                    transaction.install_build(
                        "ARTEST",
                        build,
                        game_root=game,
                        backup_root=backups,
                        process_checker=lambda: [],
                    )

            self.assertEqual(
                {path.name: path.read_bytes() for path in override.iterdir()},
                before,
            )
            receipt_path = next(backups.glob(f"*/{transaction.RECEIPT_NAME}"))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "rolled-back")

    def test_prepared_receipt_recovers_a_mixed_interrupted_install(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, override, build, backups = self.make_layout(root)
            write_pvrz(override / "ATEST00.PVRZ", b"old-zero")
            original_zero = (override / "ATEST00.PVRZ").read_bytes()
            result = transaction.install_build(
                "ARTEST",
                build,
                game_root=game,
                backup_root=backups,
                process_checker=lambda: [],
            )
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            receipt["status"] = "prepared"
            result.receipt_path.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (override / "ATEST00.PVRZ").write_bytes(original_zero)

            restored = transaction.restore_from_receipt(
                result.receipt_path,
                game,
                process_checker=lambda: [],
            )

            self.assertEqual(restored["status"], "restored")
            self.assertEqual((override / "ATEST00.PVRZ").read_bytes(), original_zero)
            self.assertFalse((override / "ARTEST.TIS").exists())
            self.assertFalse((override / "ATEST01.PVRZ").exists())

    def test_active_process_refuses_install_and_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, override, build, backups = self.make_layout(root)
            with self.assertRaisesRegex(transaction.TransactionError, "InfinityLoader.exe"):
                transaction.install_build(
                    "ARTEST",
                    build,
                    game_root=game,
                    backup_root=backups,
                    process_checker=lambda: ["InfinityLoader.exe"],
                )
            self.assertEqual(list(override.iterdir()), [])
            self.assertFalse(backups.exists())

            result = transaction.install_build(
                "ARTEST",
                build,
                game_root=game,
                backup_root=backups,
                process_checker=lambda: [],
            )
            with self.assertRaisesRegex(transaction.TransactionError, "BaldurReal.exe"):
                transaction.restore_from_receipt(
                    result.receipt_path,
                    game,
                    process_checker=lambda: ["BaldurReal.exe"],
                )

    def test_interrupted_restore_is_resumable_from_mixed_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, override, build, backups = self.make_layout(root)
            write_tis(override / "ARTEST.TIS", [0, 2])
            write_pvrz(override / "ATEST00.PVRZ", b"old-zero")
            write_pvrz(override / "ATEST02.PVRZ", b"old-two")
            before = {
                path.name: path.read_bytes()
                for path in override.iterdir()
                if path.is_file()
            }
            result = transaction.install_build(
                "ARTEST",
                build,
                game_root=game,
                backup_root=backups,
                process_checker=lambda: [],
            )
            real_atomic_copy = transaction.atomic_copy
            restore_copy_count = 0

            def fail_second_restore_copy(
                source: Path, target: Path, expected: object
            ) -> None:
                nonlocal restore_copy_count
                if source.parent.name == "files":
                    restore_copy_count += 1
                    if restore_copy_count == 2:
                        raise OSError("synthetic restore failure")
                real_atomic_copy(source, target, expected)

            with mock.patch.object(
                transaction, "atomic_copy", side_effect=fail_second_restore_copy
            ):
                with self.assertRaisesRegex(OSError, "synthetic restore failure"):
                    transaction.restore_from_receipt(
                        result.receipt_path,
                        game,
                        process_checker=lambda: [],
                    )

            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "recovery-required")
            restored = transaction.restore_from_receipt(
                result.receipt_path,
                game,
                process_checker=lambda: [],
            )
            self.assertEqual(restored["status"], "restored")
            self.assertEqual(
                {path.name: path.read_bytes() for path in override.iterdir()},
                before,
            )

    def test_receipt_state_tampering_is_rejected_before_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game, override, build, backups = self.make_layout(root)
            result = transaction.install_build(
                "ARTEST",
                build,
                game_root=game,
                backup_root=backups,
                process_checker=lambda: [],
            )
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            receipt["files"][0]["installed"]["bytes"] += 1
            result.receipt_path.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            installed_before_attempt = {
                path.name: path.read_bytes()
                for path in override.iterdir()
                if path.is_file()
            }

            with self.assertRaisesRegex(transaction.TransactionError, "empreinte"):
                transaction.restore_from_receipt(
                    result.receipt_path,
                    game,
                    process_checker=lambda: [],
                )

            self.assertEqual(
                {path.name: path.read_bytes() for path in override.iterdir()},
                installed_before_attempt,
            )


if __name__ == "__main__":
    unittest.main()
