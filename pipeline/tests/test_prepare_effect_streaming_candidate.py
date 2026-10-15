from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine/InfinityEngine-Enhancer/source-patchee/tools"))
from prepare_effect_streaming_candidate import candidate_ini, prepare


class EffectStreamingCandidateTests(unittest.TestCase):
    def test_preserves_character_shader_and_user_budgets(self):
        baseline = ("[Shaders]\r\nEnableEffectAnimationX4 = true\r\n"
                    "CreatureSpriteFilter = Nearest\r\nEffectCpuCacheMiB = 1024\r\n"
                    "EnableEffectAnimationStreaming = false\r\n"
                    "[ShaderSuite]\r\nCharacterAlpha = SilhouetteAlphaAA\r\n")
        result = candidate_ini(baseline)
        self.assertIn("EnableEffectAnimationStreaming = true\r\n", result)
        self.assertIn("EffectCpuCacheMiB = 1024\r\n", result)
        self.assertIn("CreatureSpriteFilter = Nearest\r\n", result)
        self.assertTrue(result.endswith("[ShaderSuite]\r\nCharacterAlpha = SilhouetteAlphaAA\r\n"))
        self.assertEqual(result.count("EffectCpuCacheMiB"), 1)
        self.assertIn("EnableEffectAnimationStreaming = false", candidate_ini(result, "eager"))

    def test_candidate_only_and_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / "baseline.ini"
            original = b"\xef\xbb\xbf[Shaders]\nCreatureSpriteFilter = Nearest\n"
            baseline.write_bytes(original)
            dll = root / "InfinityEngine-Enhancer.dll"
            dll.write_bytes(b"synthetic DLL fixture")
            report = prepare(dll, baseline, root / "candidate")
            self.assertFalse(report["installed"])
            self.assertFalse(report["assets_changed"])
            self.assertEqual(baseline.read_bytes(), original)
            self.assertEqual((root / "candidate" / dll.name).read_bytes(), dll.read_bytes())
            self.assertTrue((root / "candidate/InfinityEngine-Enhancer.ini").read_bytes().startswith(b"\xef\xbb\xbf"))
            with self.assertRaisesRegex(ValueError, "not empty"):
                prepare(dll, baseline, root / "candidate")


if __name__ == "__main__":
    unittest.main()
