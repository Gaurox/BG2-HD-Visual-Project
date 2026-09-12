"""Source contracts for owned rain resources; does not replace ingame QA."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT/'engine/InfinityEngine-Enhancer/source-patchee'


class WaterRainRoutingTests(unittest.TestCase):
    def test_reads_owned_alternate_and_keeps_registry_gate(self):
        source = (ENGINE/'src/iee/area_state.cpp').read_text(encoding='utf-8')
        start = source.index('std::optional<water_route2::Match> route2_water_overlay_match')
        source = source[start:source.index('void refresh_wed_cache',start)]
        self.assertIn('offsetof(game::CInfTileResourcePrefix, rainResource)', source)
        self.assertIn('variants{wrapper, rainResource}', source)
        self.assertIn('water_route2::match(query)', source)
        self.assertIn('glName != texture', source)
        self.assertIn('identityLogs[weather]', source)
        self.assertNotIn('WTSWAMR', source)

    def test_weather_prefix_layout(self):
        source = (ENGINE/'src/iee/game/runtime_types_x64.h').read_text(encoding='utf-8')
        self.assertIn('offsetof(CInfTileResourcePrefix, rainResource) == 0x20', source)

    def test_production_keeps_global_rain_unmodified(self):
        source = (ROOT/'pipeline/scripts/build_wtswam_rain_repair.py').read_text(encoding='utf-8')
        self.assertIn("DRY, WET = 'WSWPIL', 'WSWPILR'", source)
        self.assertIn('common.upscale_anchors', source)
        self.assertIn('common.interpolate', source)
        self.assertIn("registry['entries'][:15] == original['entries'][:15]", source)


if __name__ == '__main__':
    unittest.main()
