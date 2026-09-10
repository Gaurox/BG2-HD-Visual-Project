from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "engine" / "InfinityEngine-Enhancer" / "source-patchee"
TOOL = ENGINE / "tools" / "build_shader_suite.py"

SPEC = importlib.util.spec_from_file_location("build_shader_suite", TOOL)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ShaderSuiteBuilderTests(unittest.TestCase):
    def test_target_set_is_limited_to_d6_creature_contracts(self) -> None:
        self.assertEqual(
            MODULE.TARGETS,
            ("fpDraw.glsl", "fpSprite.glsl", "fpSELECT.glsl"),
        )

    def test_tracked_outputs_are_current_and_engine_compatible(self) -> None:
        for name in MODULE.TARGETS:
            with self.subTest(name=name):
                rendered = MODULE.render_shader(name)
                tracked = (MODULE.OUTPUT / name).read_text(encoding="utf-8")
                self.assertEqual(rendered, tracked)
                self.assertNotIn(MODULE.COMMON_TOKEN, rendered)
                self.assertNotIn("#version", rendered)
                self.assertIn("IEE_CREATURE_STYLE_CONTRACT_V1", rendered)

    def test_each_template_has_one_common_part_token(self) -> None:
        for name in MODULE.TARGETS:
            with self.subTest(name=name):
                template = (MODULE.TEMPLATES / name).read_text(encoding="utf-8")
                self.assertEqual(template.count(MODULE.COMMON_TOKEN), 1)


if __name__ == "__main__":
    unittest.main()
