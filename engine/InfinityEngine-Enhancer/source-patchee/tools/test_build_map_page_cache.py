"""Builder contract tests; PVR validation is separately tested in iee_tests."""
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from build_map_page_cache import build
from write_map_page_preload_bindings import write_bindings


class CacheBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "override"
        self.source.mkdir()
        self.output = self.root / "private"
        # Base x4 TIS plus active water overlay; all entries include alternate
        # tiles, repeated page numbers and a negative (solid-color) page.
        wed = bytearray(32 + 3 * 24)
        wed[:8] = b"WED V1.3"
        struct.pack_into("<I", wed, 8, 3)
        struct.pack_into("<I", wed, 16, 32)
        struct.pack_into("<HH8sHHII", wed, 32, 80, 60, b"AR0900", 0, 0, 0, 0)
        struct.pack_into("<HH8sHHII", wed, 56, 1, 1, b"YFU4T6", 0, 0, 0, 0)
        (self.source / "AR0900.WED").write_bytes(wed)
        for name, pages in (("AR0900", (0, 1, 1, -1)), ("YFU4T6", (0,))):
            data = b"TIS V1  " + struct.pack("<4I", len(pages), 12, 24, 256)
            data += b"".join(struct.pack("<iii", page, 0, 0) for page in pages)
            (self.source / (name + ".TIS")).write_bytes(data)
        for page in ("A090000", "A090001", "YU4T600"):
            (self.source / (page + ".PVRZ")).write_bytes(struct.pack("<I", 116) + b"fixture")
        self.processes = patch("build_map_page_cache.running_game_processes", return_value=[])
        self.processes.start()
        self.addCleanup(self.processes.stop)
        self.validator = patch("build_map_page_cache.subprocess.run", return_value=SimpleNamespace(stdout="ready"))
        self.validator.start()
        self.addCleanup(self.validator.stop)

    def run_build(self):
        return build(self.source, self.output, Path("validator.exe"))

    def test_x4_overlay_union_and_independent_copies(self):
        result = self.run_build()
        self.assertEqual(list(result["pages"]), ["A090000", "A090001", "YU4T600"])
        self.assertEqual(result["overlays"], ["AR0900", "YFU4T6", "-"])
        for name in result["pages"]:
            source = self.source / (name + ".PVRZ")
            target = self.output / (name + ".b1pvrz")
            self.assertEqual(source.read_bytes(), target.read_bytes())
            self.assertFalse(source.samefile(target))
            self.assertEqual(target.stat().st_nlink, 1)
        self.assertTrue((self.output / "pages.index").is_file())
        self.assertEqual(json.loads((self.output / "manifest.json").read_text())["area"], "AR0900")
        with self.assertRaises(ValueError):
            self.run_build()

    def test_missing_dependency_never_publishes_index(self):
        (self.source / "YU4T600.PVRZ").unlink()
        with self.assertRaises(ValueError):
            self.run_build()
        self.assertFalse((self.output / "pages.index").exists())

    def test_preload_bindings_preserve_cache_and_tile_identity(self):
        self.run_build()
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        target = self.root / "preload.index"
        self.assertEqual(write_bindings(self.output, target), 3)
        self.assertEqual(target.read_text().splitlines(), ["IEE_PRELOAD_BINDINGS_V1 AR0900",
            "PAGE A090000 AR0900 0 0", "PAGE A090001 AR0900 1 1", "PAGE YU4T600 YFU4T6 0 0"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})
        with self.assertRaises(FileExistsError):
            write_bindings(self.output, target)

    def test_preload_rejects_inconsistent_cache(self):
        self.run_build()
        index = self.output / "pages.index"
        index.write_text(index.read_text().replace("A090001", "A090099"))
        target = self.root / "preload.index"
        with self.assertRaises(ValueError):
            write_bindings(self.output, target)
        self.assertFalse(target.exists())

    def test_preload_rejects_wrong_page_or_tile(self):
        self.run_build()
        path = self.output / "manifest.json"
        manifest = json.loads(path.read_text())
        for changes in ({"page": 2}, {"first_tile": -1}, {"tis": "AR0300"}):
            invalid = json.loads(json.dumps(manifest))
            invalid["pages"]["A090000"].update(changes)
            path.write_text(json.dumps(invalid))
            target = self.root / "preload.index"
            with self.assertRaises(ValueError):
                write_bindings(self.output, target)
            self.assertFalse(target.exists())

    def test_invalid_size_never_publishes_index(self):
        (self.source / "A090000.PVRZ").write_bytes(struct.pack("<I", 0xffffffff) + b"fixture")
        with self.assertRaises(ValueError):
            self.run_build()
        self.assertFalse((self.output / "pages.index").exists())

    def test_no_cache_inside_override(self):
        self.output = self.source / "private"
        with self.assertRaises(ValueError):
            self.run_build()

    def test_running_game_rejected_before_source_read(self):
        with patch("build_map_page_cache.running_game_processes", return_value=["Baldur.exe"]):
            with self.assertRaises(RuntimeError):
                self.run_build()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
