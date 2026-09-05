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

import benchmark_pvrz_decode as benchmark  # noqa: E402


class BenchmarkPvrzDecodeTests(unittest.TestCase):
    def test_load_and_benchmark_valid_streams(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, decoded in enumerate((b"A" * 64, b"BC" * 48)):
                (root / f"ATEST{index:02d}.PVRZ").write_bytes(
                    struct.pack("<I", len(decoded)) + zlib.compress(decoded, 9)
                )

            result = benchmark.benchmark_dataset(
                benchmark.load_dataset(root), iterations=2
            )

            self.assertEqual(result["pages"], 2)
            self.assertEqual(result["decoded_bytes"], 160)
            self.assertEqual(result["iterations"], 2)
            self.assertEqual(len(result["maximum_page_ms_samples"]), 2)

    def test_invalid_decoded_size_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            decoded = b"payload"
            (root / "ATEST00.PVRZ").write_bytes(
                struct.pack("<I", len(decoded) + 1) + zlib.compress(decoded)
            )

            with self.assertRaisesRegex(ValueError, "taille décodée incohérente"):
                benchmark.load_dataset(root)


if __name__ == "__main__":
    unittest.main()
