from __future__ import annotations

import json
import shutil
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

import install_shader_suite_candidate as transaction  # noqa: E402


class ShaderSuiteCandidateTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.game = self.root / "game"
        self.source = self.root / "source"
        self.baseline = self.root / "baseline"
        self.candidate = self.root / "candidate"
        self.backups = self.root / "backups"
        self.game.mkdir()
        self.source.mkdir()
        self.baseline.mkdir()
        (self.game / "BaldurReal.exe").write_bytes(b"game")
        for index, name in enumerate(transaction.TARGET_SHADERS):
            stem = name.removesuffix(".glsl")
            (self.source / name).write_text(
                f"// {name}\n"
                "uniform lowp float uIeeShaderSuiteEnabled;\n"
                f"void main() {{ gl_FragColor = vec4({index}.0); }} // {stem}\n",
                encoding="utf-8",
            )
        self.before_seam = (
            "// fpSEAM.glsl\n"
            "uniform lowp float uIeeShaderSuiteEnabled;\n"
            "void main() { gl_FragColor = vec4(0.0); }\n"
        ).encode()
        (self.baseline / "fpSEAM.glsl").write_bytes(self.before_seam)
        game_override = self.game / transaction.OVERRIDE_DIRECTORY
        game_override.mkdir()
        (game_override / "fpSEAM.glsl").write_bytes(self.before_seam)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def prepare(self) -> Path:
        return transaction.prepare_candidate(
            self.source,
            self.candidate,
            baseline_override=self.baseline,
        )

    def install(self) -> transaction.OperationResult:
        self.prepare()
        return transaction.install_candidate(
            self.candidate,
            game_root=self.game,
            backup_root=self.backups,
            process_checker=lambda: [],
        )

    def test_prepare_install_verify_and_source_independent_restore(self) -> None:
        result = self.install()
        self.assertEqual(result.status, "installed")
        self.assertEqual(set(result.files), set(transaction.TARGET_SHADERS))
        receipt = transaction.verify_transaction(result.receipt_path, self.game)
        self.assertEqual(receipt["status"], "installed")
        shutil.rmtree(self.candidate)

        restored = transaction.restore_from_receipt(
            result.receipt_path,
            game_root=self.game,
            process_checker=lambda: [],
        )
        self.assertEqual(restored["status"], "restored")
        override = self.game / transaction.OVERRIDE_DIRECTORY
        self.assertEqual((override / "fpSEAM.glsl").read_bytes(), self.before_seam)
        for name in transaction.TARGET_SHADERS:
            if name != "fpSEAM.glsl":
                self.assertFalse((override / name).exists())
        transaction.verify_transaction(result.receipt_path, self.game)

    def test_verify_only_writes_nothing(self) -> None:
        self.prepare()
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
            (self.game / transaction.OVERRIDE_DIRECTORY / "fpSEAM.glsl").read_bytes(),
            self.before_seam,
        )

    def test_prepare_requires_complete_canonical_d3_suite(self) -> None:
        (self.source / transaction.TARGET_SHADERS[0]).unlink()
        with self.assertRaisesRegex(transaction.TransactionError, "incomplète"):
            self.prepare()
        name = transaction.TARGET_SHADERS[0]
        (self.source / name).write_text(
            f"// {name}\nuniform lowp float uIeeShaderSuiteEnabled;\n"
            "void main() { gl_FragColor = vec4(0.0); }\n",
            encoding="utf-8",
        )
        (self.source / "unexpected.glsl").write_text("void main(){}", encoding="utf-8")
        with self.assertRaisesRegex(transaction.TransactionError, "non géré"):
            self.prepare()

    def test_install_rejects_candidate_reduced_after_prepare(self) -> None:
        manifest_path = self.prepare()
        missing = transaction.TARGET_SHADERS[0]
        (self.candidate / transaction.OVERRIDE_DIRECTORY / missing).unlink()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"] = [row for row in manifest["files"] if row["name"] != missing]
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(transaction.TransactionError, "incomplète"):
            transaction.install_candidate(
                self.candidate,
                game_root=self.game,
                backup_root=self.backups,
                process_checker=lambda: [],
            )

    def test_verify_rejects_receipt_reduced_after_install(self) -> None:
        result = self.install()
        assert result.receipt_path is not None
        receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
        receipt["managed_files"] = receipt["managed_files"][1:]
        receipt["files"] = receipt["files"][1:]
        result.receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(transaction.TransactionError, "inventaire du reçu invalide"):
            transaction.verify_transaction(result.receipt_path, self.game)

    def test_unknown_or_case_changed_game_collision_is_rejected(self) -> None:
        self.prepare()
        target = self.game / transaction.OVERRIDE_DIRECTORY / "fpDraw.glsl"
        target.write_text("third-party", encoding="utf-8")
        with self.assertRaisesRegex(transaction.TransactionError, "collision"):
            transaction.install_candidate(
                self.candidate,
                game_root=self.game,
                backup_root=self.backups,
                process_checker=lambda: [],
            )

        target.unlink()
        wrong_case = self.game / transaction.OVERRIDE_DIRECTORY / "FPSPRITE.glsl"
        wrong_case.write_text("third-party", encoding="utf-8")
        with self.assertRaisesRegex(transaction.TransactionError, "non canonique"):
            transaction.install_candidate(
                self.candidate,
                game_root=self.game,
                backup_root=self.backups,
                process_checker=lambda: [],
            )

    def test_running_game_blocks_install_and_restore(self) -> None:
        self.prepare()
        with self.assertRaisesRegex(transaction.TransactionError, "BaldurReal.exe"):
            transaction.install_candidate(
                self.candidate,
                game_root=self.game,
                backup_root=self.backups,
                process_checker=lambda: ["BaldurReal.exe"],
            )
        result = transaction.install_candidate(
            self.candidate,
            game_root=self.game,
            backup_root=self.backups,
            process_checker=lambda: [],
        )
        with self.assertRaisesRegex(transaction.TransactionError, "InfinityLoader.exe"):
            transaction.restore_from_receipt(
                result.receipt_path,
                game_root=self.game,
                process_checker=lambda: ["InfinityLoader.exe"],
            )

    def test_external_change_and_tampered_payload_are_rejected(self) -> None:
        result = self.install()
        changed = self.game / transaction.OVERRIDE_DIRECTORY / "fpDraw.glsl"
        changed.write_text("external", encoding="utf-8")
        with self.assertRaisesRegex(transaction.TransactionError, "divergent"):
            transaction.restore_from_receipt(
                result.receipt_path,
                game_root=self.game,
                process_checker=lambda: [],
            )

        changed.write_bytes((self.source / "fpDraw.glsl").read_bytes())
        payload = (
            result.receipt_path.parent
            / transaction.PAYLOAD_DIRECTORY
            / transaction.OVERRIDE_DIRECTORY
            / "fpDraw.glsl"
        )
        payload.write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(transaction.TransactionError, "payload candidat corrompu"):
            transaction.verify_transaction(result.receipt_path, self.game)

    def test_partial_install_failure_rolls_back_all_shaders(self) -> None:
        self.prepare()
        real_atomic_copy = transaction.atomic_copy

        def fail_font(
            source: Path, target: Path, expected: transaction.FileSnapshot
        ) -> None:
            if target == self.game / transaction.OVERRIDE_DIRECTORY / "fpFONT.glsl":
                raise OSError("fixture")
            real_atomic_copy(source, target, expected)

        with mock.patch.object(transaction, "atomic_copy", side_effect=fail_font):
            with self.assertRaisesRegex(transaction.TransactionError, "état initial restauré"):
                transaction.install_candidate(
                    self.candidate,
                    game_root=self.game,
                    backup_root=self.backups,
                    process_checker=lambda: [],
                )
        override = self.game / transaction.OVERRIDE_DIRECTORY
        self.assertEqual((override / "fpSEAM.glsl").read_bytes(), self.before_seam)
        for name in transaction.TARGET_SHADERS:
            if name != "fpSEAM.glsl":
                self.assertFalse((override / name).exists())
        receipt = next(self.backups.glob(f"*/{transaction.RECEIPT_NAME}"))
        self.assertEqual(
            transaction.verify_transaction(receipt, self.game)["status"],
            "rolled-back",
        )


if __name__ == "__main__":
    unittest.main()
