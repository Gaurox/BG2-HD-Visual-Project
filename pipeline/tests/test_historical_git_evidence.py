from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import verify_historical_git_evidence as evidence  # noqa: E402


class HistoricalGitEvidenceTests(unittest.TestCase):
    def test_every_declared_migration_matches_exact_bytes(self) -> None:
        migrations = evidence.read_migrations()
        self.assertEqual(len(migrations), 10)
        for entry in migrations:
            self.assertEqual(
                evidence.verify_reference(entry["path"], entry["sha256"]),
                entry,
            )

    def test_unknown_or_tampered_hash_is_rejected(self) -> None:
        self.assertIsNone(
            evidence.verify_reference(
                "animations/index/animation_upscale_registry.csv",
                "0" * 64,
            )
        )


if __name__ == "__main__":
    unittest.main()
