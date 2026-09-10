from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from pipeline.scripts import materialize_sprite_sources as materializer


class SpriteSourceMaterializationTests(unittest.TestCase):
    def test_hard_link_reuses_the_same_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "store" / "source.bam"
            destination = root / "family" / "source.bam"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"BAM V1  test")

            materializer._link(source, destination)

            self.assertEqual(destination.read_bytes(), source.read_bytes())
            self.assertTrue(os.path.samefile(source, destination))

    def test_family_lookup_uses_animation_and_prefix(self) -> None:
        job = {
            "job_id": "mage-body-xbr2x",
            "animation": {"id": "0x6200", "bam_prefix": "CHMW1"},
        }
        families = [
            {
                "family_id": "wrong-animation",
                "animation_id": "0x5200",
                "bam_prefix": "CHMW1",
                "pipeline_ready": "yes",
                "blocker": "",
                "override_collision": "",
            },
            {
                "family_id": "human-male-mage-body-1",
                "animation_id": "0x6200",
                "bam_prefix": "CHMW1",
                "pipeline_ready": "yes",
                "blocker": "",
                "override_collision": "",
            },
        ]

        selected = materializer.family_for_job(job, families)

        self.assertEqual(selected["family_id"], "human-male-mage-body-1")

    def test_family_lookup_rejects_ineligible_family(self) -> None:
        job = {
            "job_id": "blocked-xbr2x",
            "animation": {"id": "0x6200", "bam_prefix": "WQLYW"},
        }
        families = [
            {
                "family_id": "blocked",
                "animation_id": "0x6200",
                "bam_prefix": "WQLYW",
                "pipeline_ready": "no",
                "blocker": "no-bam-resources",
                "override_collision": "",
            }
        ]

        with self.assertRaisesRegex(RuntimeError, "famille non éligible"):
            materializer.family_for_job(job, families)


if __name__ == "__main__":
    unittest.main()
