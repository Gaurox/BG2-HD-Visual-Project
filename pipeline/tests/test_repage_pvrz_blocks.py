from __future__ import annotations

import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import repage_pvrz_blocks as repage  # noqa: E402


def write_tis(path: Path, entries: list[tuple[int, int, int]]) -> None:
    payload = bytearray(repage.TIS_SIGNATURE)
    payload.extend(struct.pack("<IIII", len(entries), 12, 24, 64))
    for entry in entries:
        payload.extend(struct.pack("<III", *entry))
    path.write_bytes(payload)


def write_pvrz(path: Path, width: int, height: int, payload: bytes) -> None:
    header = struct.pack(
        "<13I", repage.PVR_MAGIC, 0, 11, 0, 0, 0, height, width, 1, 1, 1, 1, 0
    )
    pvr = header + payload
    path.write_bytes(struct.pack("<I", len(pvr)) + zlib.compress(pvr, 9))


def fixture_page(cell_pixels: int = 72) -> tuple[bytes, list[bytes]]:
    size = cell_pixels * 2
    blocks_per_row = size // 4
    cell_blocks = cell_pixels // 4
    payload = bytearray(blocks_per_row * blocks_per_row * 16)
    cells = []
    for tile in range(4):
        row, column = divmod(tile, 2)
        cell = bytes([tile + 1]) * (cell_blocks * cell_blocks * 16)
        cells.append(cell)
        repage.paste_cell(
            payload,
            cell,
            target_size=size,
            block_bytes=16,
            cell_pixels=cell_pixels,
            column=column,
            row=row,
        )
    return bytes(payload), cells


class RepagePvrzBlocksTests(unittest.TestCase):
    def make_source(self, root: Path) -> tuple[Path, list[bytes]]:
        source = root / "source"
        source.mkdir()
        entries = [(0, 4, 4), (0, 76, 4), (0, 4, 76), (0, 76, 76)]
        write_tis(source / "ARTEST.TIS", entries)
        payload, cells = fixture_page()
        write_pvrz(source / "ATEST00.PVRZ", 144, 144, payload)
        return source, cells

    def test_repage_preserves_each_dxt_cell_byte_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, cells = self.make_source(root)
            output = root / "candidate"

            manifest = repage.repage_directory(
                source,
                output,
                target_size=216,
                padding=4,
                max_pages=1,
                compression_level=9,
            )

            self.assertTrue(manifest["dxt_cells_byte_exact"])
            self.assertEqual(manifest["target_pages"], 1)
            _, tile_dimension, entries = repage.parse_tis(output / "ARTEST.TIS")
            self.assertEqual(
                entries,
                [(0, 4, 4), (0, 76, 4), (0, 148, 4), (0, 4, 76)],
            )
            page, _ = repage.parse_pvr(output / "ATEST00.PVRZ")
            self.assertEqual((page.width, page.height), (216, 216))
            for entry, expected in zip(entries, cells, strict=True):
                self.assertEqual(
                    repage.extract_cell(page, entry[1], entry[2], tile_dimension, 4),
                    expected,
                )
            self.assertTrue((output / repage.MANIFEST_NAME).is_file())

    def test_page_ceiling_is_enforced_before_output_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, _ = self.make_source(root)
            output = root / "candidate"

            with self.assertRaisesRegex(ValueError, "4 pages, plafond 3"):
                repage.repage_directory(
                    source,
                    output,
                    target_size=72,
                    padding=4,
                    max_pages=3,
                    compression_level=9,
                )

            self.assertFalse(output.exists())

    def test_source_inventory_must_match_tis_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, _ = self.make_source(root)
            write_pvrz(source / "ATEST01.PVRZ", 144, 144, fixture_page()[0])
            output = root / "candidate"

            with self.assertRaisesRegex(ValueError, "inventaire PVRZ source divergent"):
                repage.repage_directory(
                    source,
                    output,
                    target_size=216,
                    padding=4,
                    max_pages=2,
                    compression_level=9,
                )

            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
