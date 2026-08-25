import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pipeline" / "scripts"
JOB = ROOT / "sprite" / "jobs" / "dwarf-male-fighter-cdmb1-xbr4x.json"


class CreatureSpriteX4VariantTests(unittest.TestCase):
    def test_job_is_direct_x4_and_fully_parallel(self) -> None:
        job = json.loads(JOB.read_text(encoding="utf-8"))
        self.assertEqual(job["job_id"], "dwarf-male-fighter-cdmb1-xbr4x")
        self.assertEqual(job["animation"]["id"], "0x6102")
        self.assertEqual(job["animation"]["bam_prefix"], "CDMB1")
        self.assertEqual(job["animation"]["armor_code"], 1)
        self.assertEqual(
            job["upscale"],
            {
                "algorithm": "XBR/xbr4X",
                "scale": 4,
                "passes": 1,
                "antialias": False,
                "xbr_blend": False,
            },
        )
        self.assertEqual(
            job["paths"]["source_dir"],
            "sprite/dwarf-male-fighter-cdmb1-x4/source",
        )
        self.assertEqual(
            job["paths"]["run_dir"],
            "sprite/dwarf-male-fighter-cdmb1-x4/runs/xbr4x-x4",
        )
        self.assertIn("cmake-build-character-x4-cdmb1", job["paths"]["engine_build"])
        self.assertNotIn("dwarf-male-fighter-cdmb1-aa", json.dumps(job))

    def test_overlay_transaction_preserves_parent_and_is_reversible(self) -> None:
        installer = (
            SCRIPTS / "Install-CreatureSprite-X4-Variant-Test.ps1"
        ).read_text(encoding="utf-8")
        restorer = (
            SCRIPTS / "Restore-CreatureSprite-X4-Variant-Test.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("parent_active_tests", installer)
        self.assertIn("bg2-upscale-creature-sprite-x4-variant-test-v1", installer)
        self.assertIn("registry_version = 3", installer)
        self.assertIn("algorithm = 'XBR/xbr4X'", installer)
        self.assertIn("EnableCreatureSpriteLinearFiltering", installer)
        self.assertIn("installed-pending-qa", installer)
        self.assertIn("install-preflight-verified", installer)
        self.assertIn("VerifyOnly", restorer)
        self.assertIn("restore-preflight-verified", restorer)
        self.assertIn("original_sha256", restorer)
        self.assertIn("Add-Member -NotePropertyName 'restored_at_utc'", restorer)


if __name__ == "__main__":
    unittest.main()
