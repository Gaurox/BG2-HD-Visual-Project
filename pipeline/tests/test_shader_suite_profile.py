import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOL = (
    ROOT
    / "engine"
    / "InfinityEngine-Enhancer"
    / "source-patchee"
    / "tools"
    / "shader_suite_profile.py"
)
CONTRACT = (
    ROOT
    / "sprite"
    / "catmull-rom"
    / "profiles"
    / "shader-suite-contract-v1.json"
)

SPEC = importlib.util.spec_from_file_location("shader_suite_profile", TOOL)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ShaderSuiteProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = MODULE.load_contract(CONTRACT)

    def test_contract_has_eight_shaders_ten_presets_and_four_witnesses(self) -> None:
        shaders = set(self.contract["interfaces"]) - {"CreatureHD"}
        self.assertEqual(shaders, MODULE.TARGET_SHADERS)
        self.assertEqual(len(self.contract["presets"]), 10)
        self.assertEqual(
            set(self.contract["witness_profiles"]),
            {"BaselineNearest", "BaselineLinear", "CatmullOnlyHD", "Custom"},
        )

    def test_disabled_witnesses_preserve_d1_filter_priority(self) -> None:
        nearest = MODULE.resolve_profile(self.contract, "BaselineNearest")
        linear = MODULE.resolve_profile(self.contract, "BaselineLinear")
        catmull = MODULE.resolve_profile(self.contract, "CatmullOnlyHD")
        self.assertFalse(nearest["global"]["ShaderSuiteEnabled"])
        self.assertEqual(nearest["global"]["CreatureSpriteFilter"], "Nearest")
        self.assertEqual(linear["global"]["CreatureSpriteFilter"], "Linear")
        self.assertEqual(catmull["global"]["CreatureSpriteFilter"], "CatmullRom")
        self.assertTrue(all(not values["Enabled"] for values in nearest["profiles"].values()))

    def test_global_color_component_keeps_video_gamma_and_font_override(self) -> None:
        moderate = MODULE.resolve_profile(self.contract, "Moderate")
        self.assertEqual(moderate["profiles"]["fpSprite"]["Gamma"], 1.02)
        self.assertEqual(moderate["profiles"]["fpYUV"]["Gamma"], 1.632)
        self.assertEqual(moderate["profiles"]["fpYUVGRY"]["Gamma"], 1.632)
        self.assertEqual(moderate["profiles"]["fpFONT"]["Gamma"], 0.8)
        self.assertEqual(moderate["profiles"]["fpDraw"]["Gamma"], 1.02)

    def test_dshaders_base_keeps_distinct_sprite_outline_sizes(self) -> None:
        templates = MODULE.resolve_profile(self.contract, "Templates")
        self.assertEqual(templates["profiles"]["fpSprite"]["OutlineSize"], 2.0)
        self.assertEqual(templates["profiles"]["fpSELECT"]["OutlineSize"], 3.5)
        self.assertEqual(templates["profiles"]["fpSprite"]["OutlineMode"], "Dshaders")
        self.assertEqual(templates["profiles"]["fpSELECT"]["OutlineMode"], "Dshaders")

    def test_author_choice_infinity_ui_applies_only_documented_font_hack(self) -> None:
        profile = MODULE.resolve_profile(self.contract, "AuthorChoiceInfinityUI")
        self.assertEqual(profile["profiles"]["fpFONT"]["Gamma"], 0.8)
        self.assertEqual(profile["profiles"]["fpDraw"]["FontHackGamma"], 0.8)
        self.assertEqual(profile["profiles"]["fpTone"]["FontHackGamma"], 0.0)
        self.assertEqual(profile["profiles"]["fpSprite"]["OutlineSize"], 0.0)
        self.assertEqual(profile["profiles"]["fpSELECT"]["OutlineSize"], 2.5)

    def test_plan_only_does_not_write_and_run_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "resolved.json"
            planned = subprocess.run(
                [sys.executable, str(TOOL), "--profile", "Templates", "--output", str(output)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(planned.returncode, 0, planned.stderr)
            self.assertIn("action=plan-only", planned.stdout)
            self.assertFalse(output.exists())

            written = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--profile",
                    "Templates",
                    "--output",
                    str(output),
                    "--run",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["profile"], "Templates")

            repeated = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--profile",
                    "Templates",
                    "--output",
                    str(output),
                    "--run",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(repeated.returncode, 0)


if __name__ == "__main__":
    unittest.main()
