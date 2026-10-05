"""Native complete MultiNew coverage: two layouts and bank-specific palettes."""
import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import validate_selection,guide_batch,target_file,encode_work,save

class MultiNewSelectionTests(unittest.TestCase):
    def setUp(self):
        self.selection=json.loads((ROOT/'docs/measurements/q3m-multi-new-selection-x2-20261005-v1/selection.json').read_text())

    def test_complete_ten_native_ids_both_layouts(self):
        rows=validate_selection(self.selection,'multi_new')
        self.assertEqual(len(rows),10)
        self.assertEqual({len(g) for w in rows for g in w['multipart_groups']},{4,9})
        self.assertEqual(sum(len(w['palette_overrides_by_bank']) for w in rows if 'palette_overrides_by_bank' in w),30)

    def test_wrong_bank_palette_fails(self):
        w=next(w for w in self.selection['witnesses'] if 'palette_overrides_by_bank' in w)
        w['palette_overrides_by_bank']['2']['resref']=w['palette_overrides_by_bank']['1']['resref']
        with self.assertRaisesRegex(ValueError,'bank replacement'):
            validate_selection(self.selection,'multi_new')

    def test_unsuffixed_palette_fails(self):
        w=next(w for w in self.selection['witnesses'] if 'palette_overrides_by_bank' in w)
        w['palette_override']=w.pop('palette_overrides_by_bank')['1']
        with self.assertRaisesRegex(ValueError,'replacement palette'):
            validate_selection(self.selection,'multi_new')

    def test_cross_direction_parts_fail(self):
        w=self.selection['witnesses'][0]
        a,b=w['multipart_groups'][:2]
        a[1],b[1]=b[1],a[1]
        with self.assertRaisesRegex(ValueError,'direction group'):
            validate_selection(self.selection,'multi_new')

    def test_duplicate_group_fails(self):
        w=self.selection['witnesses'][-1]
        w['multipart_groups'].append(copy.deepcopy(w['multipart_groups'][0]))
        with self.assertRaisesRegex(ValueError,'duplicate multipart'):
            validate_selection(self.selection,'multi_new')

    def test_parallel_guides_match_serial_bytes(self):
        import numpy as np
        from concurrent.futures import ProcessPoolExecutor
        from run_creature_sprite_x2 import SourceFrame
        from workspace_paths import get_path
        rng=np.random.default_rng(21);rgb=rng.integers(0,256,(256,3),dtype=np.uint8)
        rgb[4]=rgb[3] # Distinct native indices sharing one RGB must retain provenance.
        indices=rng.integers(0,5,(11,13),dtype=np.uint8)
        rgba=np.dstack((rgb[indices],np.where(indices==0,0,255).astype(np.uint8))).tobytes()
        frame=SourceFrame('PROBE',0,13,11,0,0,0,indices,rgb,rgba)
        batch=(['key'],[frame],get_path('mmpx_scalepix',required=True))
        expected=guide_batch(batch)
        with ProcessPoolExecutor(max_workers=2) as pool:
            actual=list(pool.map(guide_batch,[batch,batch]))
        self.assertTrue(all(np.array_equal(result[0][1],expected[0][1]) for result in actual))

    def test_parallel_encoding_matches_serial_sha256(self):
        import tempfile,numpy as np
        from concurrent.futures import ThreadPoolExecutor
        from palette_q3m_partners import Profile
        from palette_work_plan import file_sha
        rng=np.random.default_rng(41)
        palette=rng.integers(0,256,(256,4),dtype=np.uint8)
        fitting=np.tile(palette[None,:,:3],(6,1,1))
        profile=Profile(0,palette,fitting)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);serial=[];parallel=[]
            for n,(w,h) in enumerate(((13,11),(19,17),(23,13),(31,21))):
                guide=rng.integers(0,256,(h,w),dtype=np.uint8);targets=[]
                for k in range(6):
                    path=root/f'{n}-{k}.npz';save(path,target=rng.random((h,w,3),dtype=np.float32));targets.append(path)
                work=dict(profile=profile,guide=guide,targets=targets,encoded_path=root/f'{n}-serial.npz')
                encode_work(work);serial.append(work['encoded_path'])
                parallel.append(dict(work,encoded_path=root/f'{n}-parallel.npz'))
            cold_profile=Profile(0,palette,fitting)
            for work in parallel:work['profile']=cold_profile
            with ThreadPoolExecutor(max_workers=16) as pool:list(pool.map(encode_work,parallel))
            self.assertEqual([file_sha(p) for p in serial],[file_sha(w['encoded_path']) for w in parallel])

    def test_parallel_target_files_match_serial_sha256(self):
        import tempfile,numpy as np
        from types import SimpleNamespace
        from concurrent.futures import ThreadPoolExecutor
        from palette_work_plan import file_sha
        rng=np.random.default_rng(11)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);parallel=[];serial=[]
            for n,(w,h) in enumerate(((13,11),(37,19),(192,160),(256,224))):
                crop=rng.random((h*4,w*4,3),dtype=np.float32)
                frame=SimpleNamespace(width=w,height=h)
                path=root/(str(n)+'-serial.npz');target_file((path,frame,crop));serial.append(path)
                parallel.append((root/(str(n)+'-parallel.npz'),frame,crop))
            with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(target_file,parallel))
            self.assertEqual([file_sha(p) for p in serial],[file_sha(p) for p,_,_ in parallel])

if __name__=='__main__':unittest.main()
