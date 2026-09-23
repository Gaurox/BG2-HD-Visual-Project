"""Weather adapter source contracts; no GL context or game resources."""
import importlib.util
from pathlib import Path
import unittest

ENGINE = Path(__file__).resolve().parents[2] / 'engine/InfinityEngine-Enhancer/source-patchee'


class WaterToneShaderTests(unittest.TestCase):
    def test_generated_output_and_native_fallback(self):
        spec = importlib.util.spec_from_file_location('water_tone', ENGINE / 'tools/build_water_tone_shader.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = module.render_shader()
        self.assertEqual(source, (ENGINE / 'assets/override/fpTone.glsl').read_text(encoding='utf-8'))
        self.assertIn('uIeeWaterOverlayStrength <= 0.0', source)
        self.assertIn('gl_FragColor = vec4(mix(c.rgb, tone, uColorTone.a), c.a);', source)
        self.assertIn('texColor = ieeWaterTimelineSample(vTc);', source)
        self.assertNotIn('vRef', source)
        self.assertNotIn('bool isBorderColor', source)

    def test_weather_routing_remains_identity_and_material_gated(self):
        source = (ENGINE / 'src/iee/shader_probe.cpp').read_text(encoding='utf-8')
        scope = source[source.index('void prepare_water_overlay_draw('):]
        self.assertIn('record->second.fragmentShaderName != "fpTone"', scope)
        # Tone pass: swamp material, or an explicit zero-strength timeline (AR1600 30 fps).
        self.assertIn('route->supports_pass(tonePass)', scope)
        registry = (ENGINE / 'src/iee/water_route2_registry.h').read_text(encoding='utf-8')
        self.assertIn('(!tonePass || materialId == 5 || temporal_only())', registry)
        self.assertIn('hooks::route2_water_overlay_match(', scope)


if __name__ == '__main__':
    unittest.main()
