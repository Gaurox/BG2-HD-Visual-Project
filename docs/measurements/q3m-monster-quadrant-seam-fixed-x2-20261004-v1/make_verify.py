"""Reuse exact native verification and assembly oracle, add full outside-band proof."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent/'q3m-monster-quadrant-full-x2-20261004-v1'
s=(PARENT/'verify.py').read_text()
s=s.replace('from q3m_family_witnesses import source_plan,produce,exclusive,validate_encoded','from common import *')
s=s.replace("resources,works,plan=source_plan(HERE/'selection.json','monster_quadrant');assert plan==prod['plan']","resources,works,summary,contexts,bindings=plan();assert summary==prod['plan']\noriginal_keys,patched=bound_plan(resources,works,contexts,bindings)")
a=s.index("cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'");b=s.index('cat=registry.read_sealed_catalog_index',a)
s=s[:a]+"assert 'torch' not in sys.modules\nresume=dict(context_checkpoint_hits=len(contexts))\nchanged_pixels=0;outside_changed=0;unreferenced=0\n"+s[b:]
s=s.replace("with np.load(encoded/(row['key']+'.npz'),allow_pickle=False) as a:","with np.load(works[row['key']]['encoded_path'],allow_pickle=False) as a:")
anchor="        vals,off=np.unique(works[row['key']]['frame'].indices,return_index=True)"
insert="""        bind=(aid,r['resref'],row['frame_index']);old=old_arrays(original_keys[bind])
        if bind in bindings:
            ck,n=bindings[bind];g=contexts[ck]['geometry'];roi=(strength(g[n],g)>0)&(r['profile'].classes[old['guide']]>=3)
        else:roi=np.zeros(f['I'].shape,bool);unreferenced+=1
        difference=(f['I']!=old['I'])|(f['F']!=old['F']);changed_pixels+=int(difference.sum())
        assert not np.any(difference&~roi),'pixel changed outside approved seam band'
        assert np.array_equal(r['profile'].classes[f['I']],r['profile'].classes[old['guide']]),'native alpha/material classes changed'
"""
assert anchor in s;s=s.replace(anchor,insert+anchor)
s=s.replace("assert frames==12928 and len(empty)==65","assert frames==12928 and len(empty)==65 and unreferenced==272")
s=s.replace("WORK/'runtime-build/Release/iee_palette_partner_tests.exe'","ROOT/'sprite/.work/q3m-monster-quadrant-full-x2-20261004-v1/runtime-build/Release/iee_palette_partner_tests.exe'")
s=s.replace("HERE/'composite_probe.exe'","PARENT/'composite_probe.exe'")
s=s.replace("all_geometry_cycles_profiles_representatives_cache_preserved=True","all_geometry_cycles_profiles_representatives_cache_preserved=True,outside_band_encoded_pixels_unchanged=True,changed_encoded_pixels=changed_pixels,changed_outside_band=0,unreferenced_native_frames_unchanged=unreferenced,alpha_material_classes_unchanged=True,DLL_unchanged=True")
s=s.replace("resume_torch_import_blocked=True","resume_torch_not_imported=True")
s=s.replace("native_composite=composite,empty_cases=empty_cases)","native_composite=composite,empty_cases=empty_cases,changed_encoded_pixels=changed_pixels,changed_outside_band=0)")
(HERE/'verify.py').write_text(s)
compile(s,str(HERE/'verify.py'),'exec');print('Scoped native verification prepared.')
