"""Build the large mono-BAM pack from already sealed interpolation bytes.

The current native reader permits 4096 backings and 3/4-digit frame names.
The historical lot64 finisher's local 1000 assertion is not a format limit.
No source image, sealed run, QA or installation is modified here.
"""
from pathlib import Path
import argparse
import struct
from temporal import ROOT, BATCH, load, save, rel, validate_pack, write_pack, workflow, make_plan, native_rate

def finish(a,plan,spatial):
    stage=plan.interpolation_root;m=load(stage/'manifest.json');variants=m['timing']['cycles']
    primary=[];alternates=[]
    for c in a['native_cycles']:
        options=[v for v in variants if v['cycle']==c['cycle']]
        chosen=max(options,key=lambda v:v['loop_closed']);primary.append(chosen)
        alternates.extend(v['id'] for v in options if v is not chosen)
    # Deduplicate storage across cycles/modes only; each real cycle retains its
    # own exact 2*S playback phases. Registry tails are unreachable at S slots.
    assets=[];identities={};mapping=[]
    for f in m['frames']:
        identity=(f['raw_rgba_x4_sha256'],tuple(f['physical_size_x4']))
        if identity not in identities:
            index=len(assets);assert index<4096
            identities[identity]=index
            assets.append({'frame':index,'asset':f'EFX4-{a["resref"]}-frame{index:03d}.rgba',
                           'source':rel(stage/f['raw_rgba_x4']),'source_sha256':f['raw_rgba_x4_sha256'],
                           'sha256':f['raw_rgba_x4_sha256'],'bytes':f['bytes'],
                           'logical_size_x1':f['logical_size_x1'],'physical_size_x4':f['physical_size_x4'],
                           'source_centre_x1':f['centre_x1']})
        mapping.append(identities[identity])
    native=[[mapping[i] for i in v['native_frame_indices']] for v in primary]
    timeline=[[mapping[i] for i in v['timeline_frame_indices']] for v in primary]
    maximum=max(map(len,timeline));registry=bytearray(a['resref'].encode('ascii').ljust(8,b'\0'))
    registry.extend(struct.pack('<II',len(assets),len(native)))
    for f in assets:registry.extend(struct.pack('<II',*f['logical_size_x1']))
    for cycle in native:registry.extend(struct.pack(f'<I{len(cycle)}I',len(cycle),*cycle))
    registry.extend(struct.pack('<IIIII',native_rate(a),1,30,1,maximum))
    for cycle in timeline:
        padded=cycle+[cycle[-1]]*(maximum-len(cycle));registry.extend(struct.pack(f'<{maximum}I',*padded))
    timing={'native_fps':[native_rate(a),1],'target_fps':[30,1],'phase_count':maximum,
            'native_frame_indices_by_cycle':native,'timeline_frame_indices_by_cycle':timeline,
            'actual_phase_counts_by_cycle':list(map(len,timeline)),
            'cycle_profiles':[v['id'] for v in primary],'alternate_profiles':alternates,
            'unreachable_tail_policy':'v2 equal-width tables padded only beyond ceil(native duration*30); last 8 FPS interval truncated to exact native duration',
            'render_profile_policy':'premultiplied default pack; straight-alpha companions retained in run; owner render mode routing requires integration review',
            'native_rate_basis':'VVC field' if a['native_fps'] else '15 FPS compatibility default; runtime cadence not measured'}
    pack_root=ROOT/a['pack']
    if not (pack_root/'manifest.json').exists():
        write_pack(pack_root,b'IEEEFX4\0'+struct.pack('<IIII',2,4,1,0)+bytes(registry),assets,
                   load(plan.parent_descriptor),load(ROOT/spatial['source']['frame_manifest']),spatial,
                   registry_version=2,timeline=timing,interpolation_descriptor=load(plan.descriptor_path))
    checked=validate_pack(pack_root)
    workflow.register_run(ROOT,a['resref'],'interpolation',a['interpolation_run'],write=True)
    report={'resref':a['resref'],'passed':True,'spatial_run':a['spatial_run'],'interpolation_run':a['interpolation_run'],
            'pack_builder':rel(Path(__file__)),'pack':a['pack'],'pack_manifest_sha256':checked.manifest_sha256,'native_cycles':len(a['native_cycles']),
            'cycle_mode_variants':len(variants),'phases':len(m['frames']),'backings':len(assets),
            'native_durations_preserved':True,'native_world_geometry_preserved':True,
            'visible_adjacent_duplicates':0,'alternate_playback_profiles':alternates,
            'transparent_control_cycles':[v['id'] for v in variants if v['transparent_native_cycle']],
            'runtime_carrier':m['runtime_carrier'],'raw_bytes':sum(f['bytes'] for f in assets)}
    save(BATCH/'checks'/(a['resref']+'.json'),report)
    print(a['resref'],'PASS',len(m['frames']),'phases',len(variants),'cycle/mode variants',flush=True)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--resref',required=True);args=p.parse_args()
    a=next(a for a in load(BATCH/'batch.json')['assets'] if a['resref']==args.resref)
    plan=make_plan(a)
    assert load(plan.descriptor_path)['result']['sealed']
    checked=workflow.verify_run_descriptor(ROOT,plan.run_root.parent.parent,a['resref'],a['interpolation_run'],stage='interpolation',spatial_run=a['spatial_run'])
    assert checked['ok'],checked
    return finish(a,plan,load(plan.spatial_manifest))

if __name__=='__main__':main()
