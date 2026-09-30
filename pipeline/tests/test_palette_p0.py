import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline/scripts"))
from palette_p0 import compare_json


class HistoricalComparisonTests(unittest.TestCase):
    def test_nested_comparison_counts_differences_without_rounding(self):
        same = {"summary": {"Q3": [.12, 3, None]}, "palette": "REF"}
        self.assertEqual(compare_json(same, same), {"numeric_leaves": 2, "different_leaves": 0, "max_abs_delta": 0})
        changed = {"summary": {"Q3": [.125, 3, None]}, "palette": "REF"}
        self.assertEqual(compare_json(same, changed)["different_leaves"], 1)
        self.assertGreater(compare_json(same, changed)["max_abs_delta"], 0)

    def test_missing_result_never_passes(self):
        with self.assertRaisesRegex(ValueError, "keys differ"):
            compare_json({"old": 1}, {})
        with self.assertRaisesRegex(ValueError, "lengths differ"):
            compare_json([1, 2], [1])


if __name__ == "__main__":
    unittest.main()
