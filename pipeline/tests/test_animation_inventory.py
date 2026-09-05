from __future__ import annotations

import csv
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import extract_area_animations as inventory  # noqa: E402
import run_animation_upscale as upscale  # noqa: E402
import split_animation_pack_by_area as splitter  # noqa: E402


class AnimationInventoryTests(unittest.TestCase):
    @staticmethod
    def make_area(records: list[dict[str, object]]) -> bytes:
        offset = 0x100
        data = bytearray(offset + len(records) * inventory.ARE_ANIMATION_SIZE)
        data[:8] = b"AREAV1.0"
        struct.pack_into("<II", data, 0xAC, len(records), offset)
        for index, record in enumerate(records):
            position = offset + index * inventory.ARE_ANIMATION_SIZE
            name = str(record.get("name", f"animation-{index}")).encode("cp1252")
            data[position:position + min(32, len(name))] = name[:32]
            struct.pack_into("<hh", data, position + 0x20,
                             int(record.get("x", 10)), int(record.get("y", 20)))
            resref = str(record["resref"]).encode("ascii")
            data[position + 0x28:position + 0x28 + len(resref)] = resref
            struct.pack_into("<HHI", data, position + 0x30,
                             int(record.get("sequence", 0)),
                             int(record.get("frame", 0)), int(record.get("flags", 1)))
            palette = str(record.get("palette", "")).encode("ascii")
            data[position + 0x40:position + 0x40 + len(palette)] = palette
        return bytes(data)

    def test_parse_area_classifies_bam_wbm_pvrz_and_external_palette(self) -> None:
        data = self.make_area([
            {
                "resref": "PALBAM",
                "flags": 1 | inventory.FLAG_EXTERNAL_PALETTE,
                "palette": "PLT_Mage",
            },
            {"resref": "MOVIE", "flags": 1 | inventory.FLAG_WBM_RESREF},
            {"resref": "DIRECT", "flags": 1 | inventory.FLAG_PVRZ_RESREF},
        ])

        rows = inventory.parse_area("ARTEST", data)

        self.assertEqual([row["resource_kind"] for row in rows], ["BAM", "WBM", "PVRZ"])
        self.assertEqual(rows[0]["resource_resref"], "PALBAM")
        self.assertEqual(rows[0]["palette_mode"], "external")
        self.assertEqual(rows[0]["palette_resref"], "PLT_MAGE")
        self.assertEqual(rows[1]["palette_mode"], "embedded")
        self.assertEqual(rows[1]["palette_resref"], "")

    def test_parse_area_rejects_ambiguous_kind_and_empty_external_palette(self) -> None:
        with self.assertRaisesRegex(ValueError, "WBM et PVRZ"):
            inventory.parse_area("ARTEST", self.make_area([{
                "resref": "BROKEN",
                "flags": inventory.FLAG_WBM_RESREF | inventory.FLAG_PVRZ_RESREF,
            }]))
        with self.assertRaisesRegex(ValueError, "palette externe"):
            inventory.parse_area("ARTEST", self.make_area([{
                "resref": "BROKEN",
                "flags": inventory.FLAG_EXTERNAL_PALETTE,
            }]))

    @staticmethod
    def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_bam_selection_and_area_split_exclude_non_bam_and_external_palette(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            animations = Path(temporary) / "animations"
            resources = [
                {"bam_resref": "ELIGIBLE", "format": "BAM V1", "frames": 1,
                 "max_frame_width": 2, "max_frame_height": 2, "occurrences": 1,
                 "areas": 1, "area_ids": "AR0001", "relative_path": "ressources/ELIGIBLE",
                 "sha256": ""},
                {"bam_resref": "PALBAM", "format": "BAM V1", "frames": 1,
                 "max_frame_width": 2, "max_frame_height": 2, "occurrences": 1,
                 "areas": 1, "area_ids": "AR0001", "relative_path": "ressources/PALBAM",
                 "sha256": ""},
            ]
            self.write_csv(animations / "index" / "ressources.csv", list(resources[0]), resources)
            occurrences = [
                {"area_id": "AR0001", "resource_resref": "ELIGIBLE", "resource_kind": "BAM",
                 "palette_mode": "embedded", "palette_resref": ""},
                {"area_id": "AR0001", "resource_resref": "MOVIE", "resource_kind": "WBM",
                 "palette_mode": "embedded", "palette_resref": ""},
                {"area_id": "AR0001", "resource_resref": "PALBAM", "resource_kind": "BAM",
                 "palette_mode": "external", "palette_resref": "PLT_MAGE"},
                {"area_id": "AR0002", "resource_resref": "DIRECT", "resource_kind": "PVRZ",
                 "palette_mode": "embedded", "palette_resref": ""},
            ]
            occurrence_path = animations / "index" / "occurrences.csv"
            self.write_csv(occurrence_path, list(occurrences[0]), occurrences)
            for resref in ("ELIGIBLE", "PALBAM"):
                source = animations / "ressources" / resref / "source.bam"
                source.parent.mkdir(parents=True)
                source.write_bytes(resref.encode("ascii"))

            with mock.patch.object(upscale, "ANIMATIONS_DIR", animations):
                selected, selected_occurrences, excluded = upscale.load_selection([], ["AR0001"])
                self.assertEqual([item["resref"] for item in selected], ["ELIGIBLE"])
                self.assertEqual(
                    [upscale.occurrence_resref(row) for row in selected_occurrences], ["ELIGIBLE"]
                )
                self.assertEqual(
                    {upscale.exclusion_reason(row) for row in excluded},
                    {"resource-kind-wbm", "external-palette-PLT_MAGE"},
                )
                with self.assertRaisesRegex(RuntimeError, "resource-kind-wbm"):
                    upscale.load_selection(["MOVIE"], [])
                with self.assertRaisesRegex(RuntimeError, "external-palette-PLT_MAGE"):
                    upscale.load_selection(["PALBAM"], [])

            self.assertEqual(splitter.load_area_map(occurrence_path), {"AR0001": {"ELIGIBLE"}})


if __name__ == "__main__":
    unittest.main()
