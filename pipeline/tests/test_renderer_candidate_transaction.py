from __future__ import annotations

import json
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TOOLS = (
    Path(__file__).resolve().parents[2]
    / "engine"
    / "InfinityEngine-Enhancer"
    / "source-patchee"
    / "tools"
)
sys.path.insert(0, str(TOOLS))

import install_renderer_candidate as transaction  # noqa: E402


def fake_x64_dll(marker: bytes) -> bytes:
    payload = bytearray(0x200)
    payload[:2] = b"MZ"
    struct.pack_into("<I", payload, 0x3C, 0x80)
    payload[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", payload, 0x84, 0x8664, 1)
    struct.pack_into("<HH", payload, 0x94, 0xF0, 0x2022)
    struct.pack_into("<H", payload, 0x98, 0x20B)
    payload[0x190 : 0x190 + len(marker)] = marker
    return bytes(payload)


class RendererCandidateTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.game = self.root / "game"
        self.candidate = self.root / "candidate"
        self.backups = self.root / "backups"
        self.game.mkdir()
        self.candidate.mkdir()
        (self.game / "BaldurReal.exe").write_bytes(b"game")
        self.before_dll = fake_x64_dll(b"before")
        self.before_ini = b"[Core]\nPerformanceLogs=false\n"
        self.candidate_dll = fake_x64_dll(b"candidate")
        self.candidate_ini = b"[Core]\nPerformanceLogs=true\n"
        (self.game / transaction.MANAGED_FILES[0]).write_bytes(self.before_dll)
        (self.game / transaction.MANAGED_FILES[1]).write_bytes(self.before_ini)
        (self.candidate / transaction.MANAGED_FILES[0]).write_bytes(
            self.candidate_dll
        )
        (self.candidate / transaction.MANAGED_FILES[1]).write_bytes(
            self.candidate_ini
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def install(self) -> transaction.InstallResult:
        return transaction.install_candidate(
            self.candidate,
            game_root=self.game,
            backup_root=self.backups,
            process_checker=lambda: [],
        )

    def test_install_and_source_independent_restore_are_exact(self) -> None:
        result = self.install()
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[0]).read_bytes(),
            self.candidate_dll,
        )
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[1]).read_bytes(),
            self.candidate_ini,
        )
        receipt = transaction.verify_transaction(result.receipt_path, self.game)
        self.assertEqual(receipt["status"], "installed")
        shutil.rmtree(self.candidate)

        restored = transaction.restore_from_receipt(
            result.receipt_path,
            game_root=self.game,
            process_checker=lambda: [],
        )
        self.assertEqual(restored["status"], "restored")
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[0]).read_bytes(), self.before_dll
        )
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[1]).read_bytes(), self.before_ini
        )
        transaction.verify_transaction(result.receipt_path, self.game)

    def test_restore_removes_files_that_were_initially_absent(self) -> None:
        for name in transaction.MANAGED_FILES:
            (self.game / name).unlink()
        result = self.install()
        transaction.restore_from_receipt(
            result.receipt_path,
            game_root=self.game,
            process_checker=lambda: [],
        )
        for name in transaction.MANAGED_FILES:
            self.assertFalse((self.game / name).exists())

    def test_verify_only_writes_nothing(self) -> None:
        result = transaction.install_candidate(
            self.candidate,
            game_root=self.game,
            backup_root=self.backups,
            verify_only=True,
            process_checker=lambda: [],
        )
        self.assertEqual(result.status, "verified")
        self.assertIsNone(result.receipt_path)
        self.assertFalse(self.backups.exists())
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[0]).read_bytes(), self.before_dll
        )

    def test_candidate_inventory_and_pe_are_fail_closed(self) -> None:
        extra = self.candidate / "extra.txt"
        extra.write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(transaction.TransactionError, "inventaire"):
            transaction.install_candidate(
                self.candidate,
                game_root=self.game,
                backup_root=self.backups,
                process_checker=lambda: [],
            )
        extra.unlink()
        (self.candidate / transaction.MANAGED_FILES[0]).write_bytes(b"not-a-dll")
        with self.assertRaisesRegex(transaction.TransactionError, "en-tête DOS"):
            transaction.install_candidate(
                self.candidate,
                game_root=self.game,
                backup_root=self.backups,
                process_checker=lambda: [],
            )

    def test_running_game_blocks_install_and_restore(self) -> None:
        with self.assertRaisesRegex(transaction.TransactionError, "BaldurReal.exe"):
            transaction.install_candidate(
                self.candidate,
                game_root=self.game,
                backup_root=self.backups,
                process_checker=lambda: ["BaldurReal.exe"],
            )
        result = self.install()
        with self.assertRaisesRegex(transaction.TransactionError, "InfinityLoader.exe"):
            transaction.restore_from_receipt(
                result.receipt_path,
                game_root=self.game,
                process_checker=lambda: ["InfinityLoader.exe"],
            )
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[0]).read_bytes(),
            self.candidate_dll,
        )

    def test_external_target_change_blocks_restore(self) -> None:
        result = self.install()
        (self.game / transaction.MANAGED_FILES[1]).write_bytes(b"external")
        with self.assertRaisesRegex(transaction.TransactionError, "récupération refusée"):
            transaction.restore_from_receipt(
                result.receipt_path,
                game_root=self.game,
                process_checker=lambda: [],
            )
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[1]).read_bytes(), b"external"
        )

    def test_partial_install_failure_rolls_back_exactly(self) -> None:
        real_atomic_copy = transaction.atomic_copy

        def fail_ini_publication(
            source: Path, target: Path, expected: transaction.FileSnapshot
        ) -> None:
            if target == self.game / transaction.MANAGED_FILES[1]:
                raise OSError("fixture install failure")
            real_atomic_copy(source, target, expected)

        with mock.patch.object(
            transaction, "atomic_copy", side_effect=fail_ini_publication
        ):
            with self.assertRaisesRegex(transaction.TransactionError, "état initial restauré"):
                self.install()
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[0]).read_bytes(), self.before_dll
        )
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[1]).read_bytes(), self.before_ini
        )
        receipt_path = next(self.backups.glob(f"*/{transaction.RECEIPT_NAME}"))
        receipt = transaction.verify_transaction(receipt_path, self.game)
        self.assertEqual(receipt["status"], "rolled-back")

    def test_interrupted_restore_is_resumable(self) -> None:
        result = self.install()
        real_atomic_copy = transaction.atomic_copy

        def fail_dll_restore(
            source: Path, target: Path, expected: transaction.FileSnapshot
        ) -> None:
            if (
                target == self.game / transaction.MANAGED_FILES[0]
                and source.parent.name == transaction.BACKUP_DIRECTORY
            ):
                raise OSError("fixture restore failure")
            real_atomic_copy(source, target, expected)

        with mock.patch.object(
            transaction, "atomic_copy", side_effect=fail_dll_restore
        ):
            with self.assertRaisesRegex(transaction.TransactionError, "reprendre"):
                transaction.restore_from_receipt(
                    result.receipt_path,
                    game_root=self.game,
                    process_checker=lambda: [],
                )
        receipt = transaction.verify_transaction(result.receipt_path, self.game)
        self.assertEqual(receipt["status"], "recovery-required")
        restored = transaction.restore_from_receipt(
            result.receipt_path,
            game_root=self.game,
            process_checker=lambda: [],
        )
        self.assertEqual(restored["status"], "restored")
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[0]).read_bytes(), self.before_dll
        )
        self.assertEqual(
            (self.game / transaction.MANAGED_FILES[1]).read_bytes(), self.before_ini
        )

    def test_tampered_payload_or_backup_is_rejected(self) -> None:
        result = self.install()
        receipt_root = result.receipt_path.parent
        payload = receipt_root / transaction.PAYLOAD_DIRECTORY / transaction.MANAGED_FILES[0]
        payload.write_bytes(b"tampered")
        with self.assertRaisesRegex(transaction.TransactionError, "payload candidat corrompu"):
            transaction.verify_transaction(result.receipt_path, self.game)

        payload.write_bytes(self.candidate_dll)
        backup = receipt_root / transaction.BACKUP_DIRECTORY / transaction.MANAGED_FILES[1]
        backup.write_bytes(b"tampered")
        with self.assertRaisesRegex(transaction.TransactionError, "sauvegarde corrompue"):
            transaction.verify_transaction(result.receipt_path, self.game)

    def test_tampered_receipt_and_other_game_are_rejected(self) -> None:
        result = self.install()
        raw = json.loads(result.receipt_path.read_text(encoding="utf-8"))
        raw["files"][0]["before"]["sha256"] = "0" * 64
        result.receipt_path.write_text(
            json.dumps(raw, indent=2) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(transaction.TransactionError, "empreinte"):
            transaction.verify_transaction(result.receipt_path, self.game)

        # Restore the receipt from a fresh transaction before testing game ownership.
        shutil.rmtree(self.backups)
        for name, payload in zip(
            transaction.MANAGED_FILES,
            (self.before_dll, self.before_ini),
            strict=True,
        ):
            (self.game / name).write_bytes(payload)
        result = self.install()
        other_game = self.root / "other-game"
        other_game.mkdir()
        (other_game / "BaldurReal.exe").write_bytes(b"game")
        with self.assertRaisesRegex(transaction.TransactionError, "autre racine de jeu"):
            transaction.verify_transaction(result.receipt_path, other_game)


if __name__ == "__main__":
    unittest.main()
