"""Source guards only; these do not replace GL compilation or ingame QA."""
from pathlib import Path
import unittest


ENGINE = Path(__file__).resolve().parents[2] / "engine/InfinityEngine-Enhancer/source-patchee"


class WaterRoute2ShaderContractTests(unittest.TestCase):
    def test_identity_resolves_engine_slot_to_live_gl_name(self):
        source = (ENGINE / "src/iee/area_state.cpp").read_text(encoding="utf-8")
        begin = source.index("float route2_water_overlay_strength")
        scope = source[begin:source.index("void refresh_wed_cache", begin)]
        self.assertIn("water_route2::match(query)", scope)
        self.assertIn("wed->overlays[slot].coverageCells", scope)
        self.assertIn("validatedTextureTable +", scope)
        self.assertIn("core::safe_read(descriptor, glName)", scope)
        self.assertIn("glName == texture", scope)
        self.assertNotIn("candidate.texture == texture", scope)
        self.assertNotIn("DrawBindTexture", scope)

    def test_route2_preserves_alpha_and_mixes_only_underlay_rgb(self):
        source = (ENGINE / "assets/override/fpSEAM.glsl").read_text(encoding="utf-8")
        begin = source.index("// Mix only U with P")
        end = source.index("\n\t\telse", begin)
        branch = source[begin:end]
        self.assertIn("mix(texColor.rgb, ieeLinearToSrgb(water), waterMask)", branch)
        self.assertNotIn("texColor.a =", branch)
        self.assertIn("uIeeWaterOverlayStrength > 0.0", source)
        self.assertIn("uIeeWaterRoute2 < 0.5 && uIeeEnabled > 0.5", source)
        self.assertIn("uIeeEnabled > 1.5 && uIeeWaterRoute2 < 0.5", source)

    def test_route2_accepts_only_water_and_sewage_material_cells(self):
        source = (ENGINE / "assets/override/fpSEAM.glsl").read_text(encoding="utf-8")
        begin = source.index("if (uIeeWaterRoute2 > 0.5)")
        end = source.index("else if (uIeeEnabled > 0.5", begin)
        route2_gate = source[begin:end]
        self.assertIn("cellMode > 0.5 && cellMode < 1.5", route2_gate)
        self.assertIn("cellMode > 3.5 && cellMode < 4.5", route2_gate)
        self.assertNotIn("cellMode > 4.5", route2_gate)

    def test_routing_is_at_actual_gl_draw_and_resets_afterwards(self):
        source = (ENGINE / "src/iee/shader_probe.cpp").read_text(encoding="utf-8")
        begin = source.index("struct WaterOverlayUniformScope")
        end = source.index("void forget_shader", begin)
        scope = source[begin:end]
        self.assertIn("~WaterOverlayUniformScope() noexcept", scope)
        self.assertIn("gl.glUniform1f(strength, 0.0f)", scope)
        self.assertIn("hooks::route2_water_overlay_strength", scope)
        self.assertLess(scope.index("prepare_water_overlay_draw(waterUniforms)"),
                        scope.index("g_glDrawArraysHook.original()(mode, first, count)"))


if __name__ == "__main__":
    unittest.main()
