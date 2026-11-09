from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import projectile_tracking as tracking


class ProjectileTrackingTest(unittest.TestCase):
    def pro(self):
        data = bytearray(768)
        data[:8] = b'PRO V1.0'
        struct.pack_into('<H', data, 8, 3)
        return data

    def test_native_offsets_and_secondary_convention_remain_separate(self):
        data = self.pro()
        data[0x104:0x10c] = b'SPMAGMIS'
        struct.pack_into('<H', data, 0x134, 0x301)
        struct.pack_into('<H', data, 0x214, 36)
        struct.pack_into('<H', data, 0x21a, 37)
        data[0x217] = 255
        parsed = tracking.parse_pro(bytes(data))
        self.assertEqual(parsed['smoke_animation_id'], 0x301)
        self.assertEqual(parsed['secondary_raw'], 36)
        self.assertEqual(parsed['explosion_projectile_raw'], 37)
        self.assertEqual(parsed['resources'][0][2], 'SPMAGMIS')

    def test_disabled_shadow_and_unused_palette_are_not_model_jobs(self):
        parsed = tracking.parse_pro(bytes(self.pro()))
        self.assertEqual(tracking.dependency_activity(parsed, 'shadow-animation')[0], 'disabled')
        self.assertEqual(tracking.dependency_activity(parsed, 'palette')[0], 'metadata')
        self.assertEqual(tracking.existing_action(True, [], False), 'native-mask-no-ai')
        self.assertEqual(tracking.existing_action(False, [{'kind': 'spatial-only'}]), 'reuse-existing-output')
        self.assertEqual(tracking.existing_action(False, [], True), 'resume-existing-work')

    def test_native_children_use_distinct_file_index_conventions(self):
        # Native constructor + factory proofs, not old snapshot expectations:
        # SPKLARRE201 -> SHAREA6/ID201, not SHAREA2/ID202;
        # LIGHTCHA241 -> NEWBOLT1/ID240, not SPHOLYMT/ID241.
        self.assertEqual(tracking.projectile_child_id('secondary-projectile', 201), 201)
        self.assertEqual(tracking.projectile_child_id('secondary-projectile', 0), 0)
        self.assertEqual(tracking.projectile_child_id('explosion-projectile', 241), 240)
        self.assertEqual(tracking.projectile_child_id('explosion-projectile', 38), 37)
        self.assertEqual(tracking.projectile_child_id('explosion-projectile', 23), 22)
        self.assertIsNone(tracking.projectile_child_id('explosion-projectile', 0))

    def test_ability_offsets_are_not_the_same_for_items_and_spells(self):
        for fmt, size, field in [('SPL', 40, 0x26), ('ITM', 56, 0x2a)]:
            data = bytearray(0x72 + size)
            data[:4] = (fmt + ' ').encode()
            struct.pack_into('<IH', data, 0x64, 0x72, 1)
            struct.pack_into('<H', data, 0x72 + field, 68)
            self.assertEqual(tracking.ability_projectiles(bytes(data), fmt), [(0, 0x72 + field, 68)])
            struct.pack_into('<H', data, 0x68, 2)
            with self.assertRaises(ValueError):
                tracking.ability_projectiles(bytes(data), fmt)

    def test_missing_ids_are_not_called_hardcoded_graphics(self):
        self.assertEqual(tracking.hardcoded_label(13), 'unmapped-or-missing-id')
        self.assertEqual(tracking.hardcoded_label(67), 'magic-missile-count-variant')
        self.assertEqual(tracking.hardcoded_label(78), 'invisible-travel')
        self.assertEqual(tracking.ids_entries(b'IDS\r\n0x24 MAGICMIS\r\n036 MAGICMIS'), {36: 'MAGICMIS'})

    def test_existing_snapshot_is_rejected_before_any_analysis(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'projectiles/analysis/keep-v1').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                tracking.refresh(root, 'keep-v1')

    def test_tracking_cannot_silently_promote_qa_from_a_bam_status(self):
        data = {'schema': 'bg2-projectiles-work-tracking-v1',
                'projectiles': {'ARROW': {'qa': {'state': 'accepted'}}}}
        with self.assertRaisesRegex(ValueError, 'Explicit evidence'):
            tracking.validate_tracking(data, {'ARROW'})
        data['projectiles']['ARROW']['qa']['evidence'] = 'local-decision.json'
        tracking.validate_tracking(data, {'ARROW'})
        with self.assertRaisesRegex(ValueError, 'Unknown PRO'):
            tracking.validate_tracking(data, {'OTHER'})

    def test_component_visual_qa_does_not_promote_native_projectile_qa(self):
        node = {'qa': {'state': 'not-assessed'}, 'component_visual_qa': {'batch': {
            'state': 'accepted-assets-only', 'evidence': ['effects/acceptance.json'],
            'assets': ['ARARROW'], 'reviewed_on': '2026-11-09',
            'limits': 'Primary VVC only; no native PRO test.'}}}
        data = {'schema': 'bg2-projectiles-work-tracking-v1', 'projectiles': {'ARROW': node}}
        tracking.validate_tracking(data, {'ARROW'})
        self.assertEqual(node['qa'], {'state': 'not-assessed'})
        node['component_visual_qa']['batch']['state'] = 'accepted'
        with self.assertRaisesRegex(ValueError, 'component visual QA'):
            tracking.validate_tracking(data, {'ARROW'})
        node['component_visual_qa']['batch']['state'] = 'accepted-assets-only'
        node['component_visual_qa']['batch']['evidence'] = []
        with self.assertRaisesRegex(ValueError, 'component visual QA'):
            tracking.validate_tracking(data, {'ARROW'})


if __name__ == '__main__':
    unittest.main()
