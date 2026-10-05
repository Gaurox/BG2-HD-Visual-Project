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

    def test_nine_parts_parallel_match_serial_and_preserve_outside_band(self):
        from concurrent.futures import ThreadPoolExecutor
        from palette_q3m_partners import Profile
        from palette_work_plan import file_sha
        rng=np.random.default_rng(31)
        fitting=rng.integers(0,256,(6,256,3),dtype=np.uint8)
        source=np.column_stack((fitting[0,:,::-1],np.zeros(256,np.uint8)))
        geometries=[(12,12,-x*12,-y*12,0) for y in range(3) for x in range(3)]
        target=rng.random((6,72,72,3),dtype=np.float32);templates=[];works={}
        for n,a in enumerate(geometries):
            guide=rng.integers(0,256,(24,24),dtype=np.uint8);guide[0,:3]=[0,1,2]
            profile=Profile(0,source,fitting);fraction=np.zeros_like(guide)
            old=dict(guide=guide,I=guide.copy(),F=fraction,dep=profile.dependencies(guide,fraction))
            weight=seams.strength(a,geometries);roi=(weight>0)&(profile.classes[guide]>=3)
            row=dict(key=f'part{n}',geometry=a)
            templates.append((n,row,old,weight,roi))
            works[row['key']]=dict(targets=rng.random((6,24,24,3),dtype=np.float32))
        def original_targets(item,roi):return item['targets'][:,roi,:]
        with tempfile.TemporaryDirectory() as temporary:
            results=[]
            for workers in (1,8):
                work=Path(temporary)/str(workers);profile=Profile(0,source,fitting)
                shared=(target,0,0,'recipe','context',work,works,original_targets)
                jobs=[((n,dict(profile=profile),row,old,weight,roi),shared)
                      for n,row,old,weight,roi in templates]
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    nodes=list(pool.map(seams.repair_part,jobs))
                results.append(nodes)
                for node,(_,row,old,_,roi) in zip(nodes,templates):
                    self.assertGreater(node['changed_pixels'],0)
                    path=work/'encoded'/(node['encoded_key']+'.npz')
                    self.assertEqual(file_sha(path),node['encoded_sha256'])
                    with np.load(path) as data:
                        self.assertTrue(np.array_equal(data['guide'],old['guide']))
                        for plane in ('I','F'):
                            self.assertTrue(np.array_equal(data[plane][~roi],old[plane][~roi]))
            self.assertEqual(results[0],results[1])

if __name__=='__main__':unittest.main()
