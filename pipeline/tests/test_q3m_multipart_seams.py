import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import q3m_multipart_seams as seams


class ContextualSeamsTests(unittest.TestCase):
    def parts(self):
        fitting=np.zeros((6,256,3),np.uint8)
        profile=SimpleNamespace(kind=0,fitting=fitting)
        witness=dict(family='monster_quadrant',animation_id='0x1000',refs=['P1','P2'],multipart_groups=[['P1','P2']])
        parts=[dict(witness=witness,resref=ref,profile=profile,cycles=[[0,0]],
            frames=[dict(key=key,geometry=(12,12,cx,0),frame_index=0)])
            for ref,key,cx in [('P1','a',0),('P2','b',-12)]]
        return parts,dict(witnesses=[witness])

    def test_shared_segment_and_empty_parts(self):
        a=(12,12,0,0);b=(12,6,-12,-3)
        weight=seams.strength(a,[a,b,(0,0,0,0)])
        self.assertFalse(weight[:6].any());self.assertFalse(weight[18:].any())
        self.assertFalse(weight[:,:16].any());self.assertTrue((weight[6:18,-1]==1).all())
        self.assertTrue(np.array_equal(weight.T,seams.strength(a,[a,(6,12,-3,-12)])))

    def test_context_dedup_includes_neighbour_pixels_and_geometry(self):
        parts,selection=self.parts();contexts,bindings=seams.context_plan(parts,selection)
        self.assertEqual((len(contexts),len(bindings)),(1,2))
        old=set(contexts)
        parts[1]['frames'][0]['geometry']=(12,12,-12,-1)
        self.assertNotEqual(old,set(seams.context_plan(parts,selection)[0]))
        parts[1]['frames'][0]['key']='other'
        self.assertNotEqual(old,set(seams.context_plan(parts,selection)[0]))

    def test_conflicting_frame_alias_fails(self):
        parts,selection=self.parts();parts[1]['cycles']=[[0,1]]
        parts[1]['frames'].append(dict(key='c',geometry=(12,12,-12,0),frame_index=1))
        with self.assertRaisesRegex(ValueError,'different neighbours'):
            seams.context_plan(parts,selection)

    def test_palette_mismatch_fails(self):
        parts,selection=self.parts();parts[1]['profile']=copy.deepcopy(parts[1]['profile'])
        parts[1]['profile'].fitting[0,3,0]=1
        with self.assertRaisesRegex(ValueError,'Different native tile palettes'):
            seams.context_plan(parts,selection)

    def test_no_context_for_overlay_family(self):
        parts,selection=self.parts();w=selection['witnesses'][0]
        w['family']='monster_layered';w.pop('multipart_groups')
        self.assertEqual(seams.context_plan(parts,selection),({},{}))

    def test_plan_reads_no_gpu_cache(self):
        parts,selection=self.parts()
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary)/'selection.json';p.write_text(json.dumps(selection))
            report=seams.apply_context(parts,{},p,Path(temporary)/'absent-cache','plan')
            self.assertEqual(report['contexts'],1)
            self.assertFalse((Path(temporary)/'absent-cache').exists())
        self.assertNotIn('torch',sys.modules)

    def test_shadow_context_resume_and_missing_checkpoint(self):
        from palette_q3m_partners import Profile
        from palette_work_plan import file_sha
        parts,selection=self.parts()
        fitting=np.random.default_rng(1).integers(0,256,(6,256,3),dtype=np.uint8)
        profile=Profile(0,np.column_stack((fitting[0,:,::-1],np.zeros(256,np.uint8))),fitting)
        for part in parts:part['profile']=profile
        with tempfile.TemporaryDirectory() as temporary:
            cache=Path(temporary);p=cache/'selection.json';p.write_text(json.dumps(selection))
            (cache/'backend.json').write_text(json.dumps(dict(model_sha256='unused-shadow-only')))
            encoder=file_sha(Path(seams.__file__).with_name('palette_q3m_partners.py'))
            encoded=cache/'encoded'/encoder;encoded.mkdir(parents=True)
            guide=np.ones((24,24),np.uint8);fraction=np.zeros_like(guide)
            for key in ('a','b'):
                np.savez_compressed(encoded/(key+'.npz'),guide=guide,I=guide,F=fraction,dep=profile.dependencies(guide,fraction))
            works={key:dict(profile=profile) for key in ('a','b')}
            produced=seams.apply_context(parts,works,p,cache,'run')
            self.assertEqual(produced['new_neural_targets'],0)
            resumed=seams.apply_context(parts,works,p,cache,'bind')
            self.assertEqual(resumed['context_cache_hits'],1)
            checkpoint=next((cache/'multipart-seams').glob('*/contexts/*.json'))
            checkpoint.unlink()
            with self.assertRaisesRegex(ValueError,'Missing contextual checkpoint'):
                seams.apply_context(parts,works,p,cache,'bind')
        self.assertNotIn('torch',sys.modules)

if __name__=='__main__':unittest.main()
