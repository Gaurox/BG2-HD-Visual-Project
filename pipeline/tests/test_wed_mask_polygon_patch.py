from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_wed_mask_polygon_patch as patcher  # noqa: E402


def make_wed() -> tuple[bytes, bytes]:
    overlay_offset = 0x20
    secondary_offset = 0x38
    wall_group_offset = 0x4C
    polygon_offset = 0x50
    polygon_count = 2
    lookup_offset = polygon_offset + polygon_count * patcher.POLYGON_SIZE
    vertex_offset = lookup_offset + 2
    existing_vertices = [(10, 10), (20, 10), (15, 20)]
    data = bytearray(vertex_offset + len(existing_vertices) * 4)
    data[:8] = patcher.WED_SIGNATURE
    struct.pack_into("<IIII", data, 0x08, 1, 0, overlay_offset, secondary_offset)
    struct.pack_into("<HH", data, overlay_offset, 10, 7)
    struct.pack_into(
        "<IIIII",
        data,
        secondary_offset,
        polygon_count,
        polygon_offset,
        vertex_offset,
        wall_group_offset,
        lookup_offset,
    )
    struct.pack_into("<HH", data, wall_group_offset, 0, 1)
    empty_polygon = struct.pack("<IIBBHHHH", 0, 0, 1, 255, 65535, 0, 65535, 0)
    data[polygon_offset: polygon_offset + patcher.POLYGON_SIZE] = empty_polygon
    struct.pack_into(
        "<IIBBHHHH", data, polygon_offset + patcher.POLYGON_SIZE,
        0, 3, 9, 255, 10, 20, 10, 20,
    )
    struct.pack_into("<H", data, lookup_offset, 1)
    for index, point in enumerate(existing_vertices):
        struct.pack_into("<hh", data, vertex_offset + index * 4, *point)
    return bytes(data), empty_polygon


class WedMaskPolygonPatchTests(unittest.TestCase):
    def test_mask_becomes_one_quantized_world_polygon(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            mask_path = Path(temporary) / "mask.png"
            image = Image.new("L", (640, 480), 255)
            ImageDraw.Draw(image).polygon(
                [(0, 240), (160, 80), (320, 240), (480, 400), (0, 480)], fill=0
            )
            image.save(mask_path)

            vertices, details = patcher.mask_to_world_polygon(
                mask_path, (100, 200), 4, 127, 0.75
            )

            self.assertGreaterEqual(len(vertices), 4)
            self.assertTrue(all(x >= 100 and y >= 200 for x, y in vertices))
            self.assertGreaterEqual(details["intersection_over_union"], 0.95)
            patcher.validate_polygon(vertices)

    def test_rejects_non_grayscale_or_disconnected_mask(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            color_path = Path(temporary) / "color.png"
            Image.new("RGB", (4, 4), (255, 0, 0)).save(color_path)
            with self.assertRaisesRegex(ValueError, "niveaux de gris"):
                patcher.mask_to_world_polygon(color_path, (0, 0), 1, 127, 0)

            split_path = Path(temporary) / "split.png"
            split = Image.new("L", (8, 8), 255)
            split.putpixel((1, 1), 0)
            split.putpixel((6, 6), 0)
            split.save(split_path)
            with self.assertRaisesRegex(ValueError, "une seule composante"):
                patcher.mask_to_world_polygon(split_path, (0, 0), 1, 127, 0)

    def test_adds_polygon_lookup_and_vertices_without_changing_old_vertices(self) -> None:
        source, empty_polygon = make_wed()
        source_layout = patcher.parse_wed_layout(source)
        vertices = [(1, 1), (8, 1), (8, 8), (1, 8)]

        output, details = patcher.add_wall_polygon(
            source,
            polygon_index=0,
            expected_polygon=empty_polygon,
            wall_groups=[patcher.WallGroupExpectation(0, 0, 1)],
            vertices=vertices,
        )

        output_layout = patcher.parse_wed_layout(output)
        self.assertEqual(output_layout.lookup_count, source_layout.lookup_count + 1)
        self.assertEqual(output_layout.vertex_count, source_layout.vertex_count + 4)
        self.assertEqual(struct.unpack_from("<HH", output, output_layout.wall_group_offset), (0, 2))
        self.assertEqual(
            struct.unpack_from("<HH", output, output_layout.lookup_offset), (0, 1)
        )
        polygon = struct.unpack_from("<IIBBHHHH", output, output_layout.polygon_offset)
        self.assertEqual(polygon[:4], (3, 4, 0x09, 0xFF))
        old_vertex_bytes = source[source_layout.vertex_offset:]
        self.assertEqual(
            output[
                output_layout.vertex_offset:
                output_layout.vertex_offset + len(old_vertex_bytes)
            ],
            old_vertex_bytes,
        )
        self.assertEqual(details["lookup_entries_added"], 1)

    def test_rejects_stale_slot_or_group(self) -> None:
        source, empty_polygon = make_wed()
        vertices = [(1, 1), (8, 1), (8, 8), (1, 8)]
        with self.assertRaisesRegex(ValueError, "octets source différents"):
            patcher.add_wall_polygon(
                source, 0, bytes(patcher.POLYGON_SIZE),
                [patcher.WallGroupExpectation(0, 0, 1)], vertices,
            )
        with self.assertRaisesRegex(ValueError, "plage 0:1"):
            patcher.add_wall_polygon(
                source, 0, empty_polygon,
                [patcher.WallGroupExpectation(0, 2, 3)], vertices,
            )

    def test_rejects_self_intersection(self) -> None:
        with self.assertRaisesRegex(ValueError, "auto-intersecte"):
            patcher.validate_polygon([(0, 0), (10, 10), (0, 10), (10, 0)])


if __name__ == "__main__":
    unittest.main()
