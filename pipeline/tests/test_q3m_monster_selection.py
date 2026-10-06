"""Native short palette and large-frame transport for the complete Monster lot."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from q3m_family_witnesses import bmp_palette, native_representatives, guide_batch


class MonsterTransportTests(unittest.TestCase):
    def bitmap(self, count):
        palette = np.zeros((count, 4), np.uint8)
        palette[:, 2] = np.arange(count, dtype=np.uint8)
        offset = 54 + count * 4
        header = struct.pack('<2sIHHI', b'BM', offset + 4, 0, 0, offset)
        dib = struct.pack('<IiiHHIIiiII', 40, 1, 1, 1, 8, 0, 4, 0, 0, count, count)
        return header + dib + palette.tobytes() + bytes(4), palette

    def test_short_palette_preserves_native_tail_and_never_reads_pixel_bytes(self):
        raw, palette = self.bitmap(252)
        raw = raw[:-4] + bytes([255, 254, 253, 252])
        source = np.zeros((256, 4), np.uint8)
        actual = bmp_palette(raw, source)
        np.testing.assert_array_equal(actual[:252], palette)
        self.assertFalse(np.any(actual[252:]))

    def test_unresolved_short_palette_tail_fails(self):
        raw, _ = self.bitmap(252)
        with self.assertRaisesRegex(ValueError, 'requires native tail'):
            bmp_palette(raw)
        source = np.zeros((256, 4), np.uint8)
        source[254, 0] = 1
        with self.assertRaisesRegex(ValueError, 'unresolved native tail'):
            bmp_palette(raw, source)

    def test_truncated_palette_fails(self):
        raw, _ = self.bitmap(256)
        with self.assertRaisesRegex(ValueError, 'truncated'):
            bmp_palette(raw[:100])

    def test_large_native_frame_representatives_round_trip(self):
        indices = np.zeros((240, 320), np.uint8)
        indices[3, 17] = 255
        reps = native_representatives(indices)
        self.assertEqual(int(reps[255]), 977)
        self.assertEqual(int(indices.flat[int(reps[255])]), 255)

    def test_large_offset_cannot_silently_wrap(self):
        indices = np.zeros((240, 320), np.uint8)
        indices.flat[70000] = 255
        with self.assertRaisesRegex(ValueError, 'refusing truncation'):
            native_representatives(indices)

    def test_fast_injective_and_duplicate_guides_match_original_provenance(self):
        from run_creature_sprite_x2 import SourceFrame,run_xbr,direct_upscale_contract,map_output,xbr_provenance_indices
        from workspace_paths import get_path
        rng=np.random.default_rng(32)
        for duplicate in (False,True):
            rgb=rng.integers(0,256,(256,3),dtype=np.uint8)
            if duplicate:rgb[4]=rgb[3]
            indices=rng.integers(0,6,(11,13),dtype=np.uint8)
            rgba=np.dstack((rgb[indices],np.where(indices==0,0,255).astype(np.uint8))).tobytes()
            frame=SourceFrame('PROBE',0,13,11,0,0,0,indices,rgb,rgba)
            scalepix=get_path('mmpx_scalepix',required=True)
            rendered=run_xbr([frame],scalepix,'node',direct_upscale_contract(2))[0][2]
            expected=map_output(frame,rendered,xbr_provenance_indices(frame,2))[0].reshape(22,26)
            actual=guide_batch((['key'],[frame],scalepix))[0][1]
            np.testing.assert_array_equal(actual,expected)

    def test_shared_pixel_pack_matches_acquired_catalog_and_native_oracle_bytes(self):
        import q3m_family_witnesses as q
        from palette_q3m_partners import Profile
        from run_creature_sprite_x2 import SourceFrame
        rgb=np.column_stack((np.arange(256,dtype=np.uint8),np.arange(256,dtype=np.uint8)[::-1],np.zeros(256,np.uint8)))
        bgra=np.column_stack((rgb[:,::-1],np.zeros(256,np.uint8)))
        profile=Profile(0,bgra,np.repeat(rgb[None],6,axis=0))
        indices=np.array([[0,1,2],[3,4,5],[6,7,8]],np.uint8)
        guide=np.repeat(np.repeat(indices,2,0),2,1);code=np.zeros_like(guide);code[guide>=3]=3
        frame=SourceFrame('PROBE',0,3,3,0,0,0,indices,rgb,b'')
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);encoded=directory/'encoded.npz'
            q.save(encoded,guide=guide,I=guide,F=code,dep=profile.dependencies(guide,code))
            works={'same':dict(frame=frame,profile=profile,encoded_path=encoded)}
            rows=[dict(key='same',geometry=(3,3,x,-x,0)) for x in (0,2)]
            first=dict(resref='PROBE1',source_sha256='00'*32,frames=rows,cycles=[[0,1,0]],profile=profile,
                       witness=dict(animation_id='0x7300',owner=3))
            resources=[first,dict(first,resref='PROBE2'),dict(first,witness=dict(animation_id='0x7301',owner=3))]
            result=q.pack(resources,works,directory/'pack')
            # Frozen hashes from the acquired producer before memoization:
            # same pixels, two centres/resources, and a native variant alias.
            self.assertEqual(result['catalog_sha256'],'7d58793157e22b0e226a61b7a2b768910757270b44a7a342aa070c325066fd83')
            self.assertEqual(result['oracle_sha256'],'60c799d00ab6755897537bf76243d5626a562e50296baee9135c98e38d2b126f')
            self.assertEqual([leaf['sha256'] for leaf in result['leaves']],
                             ['B164A6ACB82932EAA747D4330EDB94599B87F33B572720B98B8D4D2DF3A83BAF',
                              '6055544EC5790CF8BA90879824734B4535E38B286DC1EC8C6E6AA4352AC9ECE3'])
            self.assertEqual(result['unique_pixel_oracles'],1)
            # A variant adds its own world component before reusing an earlier
            # INV-like component. Native memberships must stay strictly sorted.
            from run_creature_sprite_x2 import read_sealed_catalog_index
            variant=dict(animation_id='0x7301',owner=3)
            canonical=q.pack([first,dict(first,resref='PROBE2'),dict(first,resref='PROBE3',witness=variant),
                              dict(first,witness=variant)],works,directory/'canonical')
            catalog=read_sealed_catalog_index(directory/'canonical/CreatureSprites-XN.catalog',canonical['catalog_sha256'])
            self.assertEqual(catalog['animations'][1]['component_indices'],[0,2])


if __name__ == '__main__':
    unittest.main()
