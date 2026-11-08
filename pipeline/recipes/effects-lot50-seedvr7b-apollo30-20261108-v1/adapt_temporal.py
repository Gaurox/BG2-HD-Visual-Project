"""Create isolated lot50 producer from established lot33, with explicit replacements."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
source=ROOT/'pipeline/recipes/effects-lot33-native-impacts-20261017-v1/temporal.py'
text=source.read_text(encoding='utf-8')
def replace(old,new):
    global text
    assert old in text,old[:120]
    text=text.replace(old,new)
replace("BATCH = ROOT / 'effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1'","BATCH = ROOT / 'effects/batches/lot50-seedvr7b-apollo30-20261108-v1'")
replace('from scipy.ndimage import distance_transform_edt','from scipy.ndimage import distance_transform_edt\nimport support')
replace('        assert count > 0','        if count == 0: continue')
replace('            keys = distinct_keys(slots, identities, blank, closed)\n            assert keys\n            sources = phase_sources(keys, count, closed)',
        '            keys, sources, samples = support.sources(slots, identities, closed)\n            assert keys')
replace("'keyframes': keys, 'phase_sources': sources,","'keyframes': keys, 'phase_sources': sources, 'apollo_samples': samples,")
replace("'apollo8-cycle-retimed-duration-preserved'","'apollo8-native-anchors-holds-preserved'")
start=text.index('def apollo(plan, variant, images):')
end=text.index('\n\ndef produce(a):',start)
text=text[:start]+'''def apollo(plan, variant, images):
    return support.apollo(plan,variant,images,interpolation,save)
'''+text[end:]
replace("'sigma_x4':1.2,'inner_feather_x4':feather,","'sigma_x4':a['sigma_x4'],'inner_feather_x4':feather,'feather_policy':'per-component thickness bounded; components maxradius<=4x4 unchanged',")
replace("'retiming':'all exact repeated native poses removed within each cycle, including nonconsecutive repeats; distinct poses stretched over unchanged native cycle duration; loop closing endpoint not emitted twice',",
        "'retiming':'native15FPS anchors preserved at30FPS; adjacent equal inference inputs condensed with holds restored at exact slots; nonadjacent occurrences retained; no blank trimming or uniform stretching',")
replace("'tools':[interpolation.evidence(ROOT,'producer',snapshot)]}","'tools':[interpolation.evidence(ROOT,'producer',snapshot),interpolation.evidence(ROOT,'support',HERE/'support.py')], 'green_index':a.get('green_index'), 'source_alpha_derivation':'spatial source export authoritative; green exception explicitly bound'}")
replace("        normal_masks = {k: native_alpha(k) for k in images}","        normal_masks = {k: images[k][:,:,3].copy() for k in images}")
replace("                with Image.open(files[phase]) as im:rgb=np.asarray(im.convert('RGB')).copy()","                with Image.open(files[v['apollo_samples'][phase]]) as im:rgb=np.asarray(im.convert('RGB')).copy()[:ch*4,:cw*4]")
replace('            final=apply_geometry_preserving_rgb_gaussian(rgba,1.2)\n            if feather: final,_=apply_inner_contour_fade(final,feather,\'premultiplied\')',
        "            final=apply_geometry_preserving_rgb_gaussian(rgba,a['sigma_x4']) if a['sigma_x4'] else rgba.copy()\n            factor=support.feather_factor(alpha,feather)\n            if feather:final=np.rint(final.astype(np.float32)*factor[:,:,None]).astype(np.uint8)")
replace('            factor = smoothstep((distance - 1.0) / feather) if feather else np.ones(alpha.shape)',
        '            factor = support.feather_factor(alpha,feather)')
replace("            records.append({'frame':index", "            neutral_meta={}\n            if a['profile']=='H':\n                neutral=support.neutral(straight);neutral_path=frames_root/(stem+'-normal-neutral.rgba');neutral_path.write_bytes(neutral.tobytes())\n                neutral_meta={'neutral_raw_rgba_x4':'frames-rgba/'+neutral_path.name,'neutral_raw_rgba_x4_sha256':workflow.sha256_file(neutral_path)}\n            records.append({**neutral_meta,'frame':index")
start=text.index("        if not v['constant_native_cycle']:")
end=text.index("        result={k:value",start)
text=text[:start]+'''        # Native holds and invisible reserves may repeat; anchors are checked independently.
        for phase in range(0,len(indices),2):
            left,right,fraction=v['phase_sources'][phase]
            assert fraction==0 and left==v['native_slots'][phase//2]
'''+text[end:]
replace("        chosen=max(options,key=lambda v:v['loop_closed']);primary.append(chosen)",
        "        chosen=max(options,key=lambda v:v['loop_closed']) if options else None;primary.append(chosen)")
replace("    native=[[mapping[i] for i in v['native_frame_indices']] for v in primary]\n    timeline=[[mapping[i] for i in v['timeline_frame_indices']] for v in primary]",
        "    native=[[mapping[i] for i in v['native_frame_indices']] if v else [] for v in primary]\n    timeline=[[mapping[i] for i in v['timeline_frame_indices']] if v else [] for v in primary]")
replace("padded=cycle+[cycle[-1]]*(maximum-len(cycle))","padded=cycle+[(cycle[-1] if cycle else 0)]*(maximum-len(cycle))")
replace("'cycle_profiles':[v['id'] for v in primary]","'cycle_profiles':[v['id'] if v else None for v in primary]")
replace("'visible_adjacent_duplicates':0,","'native_anchor_policy':'original ticks preserved; native holds allowed',")
replace("'timeline_frame_indices_by_cycle':timeline,","'timeline_frame_indices_by_cycle':timeline,'empty_native_cycles':[i for i,c in enumerate(native) if not c],")
replace("'retiming':'native15FPS", "'retiming':'native15FPS")
out=HERE/'temporal.py'
assert not out.exists()
out.write_text(text,encoding='utf-8')
print('Isolated temporal producer created.')
