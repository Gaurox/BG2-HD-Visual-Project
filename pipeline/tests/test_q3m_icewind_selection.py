"""Regression scope for native Icewind aliases, equipment and unavailable IDs."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import icewind_native_refs,validate_selection

class NativeIcewindSelection(unittest.TestCase):
    def selection(self):
        return json.loads((ROOT/'docs/measurements/q3m-icewind-full-x2-20261006-v1/selection.json').read_text(encoding='utf-8'))

    def test_complete_native_stock_selection(self):
        s=self.selection();validate_selection(s,'monster_icewind')
        self.assertEqual(len(s['witnesses']),40)
        self.assertEqual(len({ref for w in s['witnesses'] for ref in w['refs']}),1051)
        self.assertEqual(set(s['native_source_absent_animation_ids']),{'0xE060','0xE0D0','0xE261','0xE262'})

    def test_missing_native_id_declaration_is_rejected(self):
        s=self.selection();s['native_source_absent_animation_ids'].remove('0xE060')
        with self.assertRaisesRegex(ValueError,'native-source-absent'):validate_selection(s,'monster_icewind')

    def test_native_body_attack3_east_and_equipment_are_distinct(self):
        # Constructor 0x30F4D6 binds A2E; EquipWeapon 0x3259E1 binds A3E.
        refs=['MTANA2E','MTANA3E','MTANG11','MTANINV','MTANSA3E','MTANCDE','MTANSTW']
        self.assertEqual(icewind_native_refs('MTAN',refs),['MTANA2E','MTANSA3E'])

    def test_native_palette_variants_are_explicit(self):
        byid={w['animation_id']:w for w in self.selection()['witnesses']}
        for aid,palette in [('0xE27F','MBOA_BR'),('0xE28A','MTRO_DK'),('0xE292','METN_GH')]:
            self.assertEqual(byid[aid]['palette_override']['resref'],palette)
            self.assertEqual(byid[aid]['native_kind'],0)
        self.assertEqual(byid['0xE020']['refs'],byid['0xE090']['refs'])

if __name__=='__main__':unittest.main()
