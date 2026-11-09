"""Final mono-BAM v3 packs: native cycles + explicit once/loop routing; no installation."""
import argparse
import copy
import struct
import subprocess
import time
from temporal import ROOT,BATCH,load,save,rel,workflow
from build_effect_runtime_pack import write_pack
from compose_effect_runtime_packs import validate_pack

PROBE=ROOT/'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'

def build(a):
    name=a['resref'];receipt=BATCH/'runtime-verification'/f'{name}.json'
    if receipt.exists():return load(receipt)
    run=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run'];stage=run/'02-interpolation'
    m=load(stage/'manifest.json');sp=ROOT/m['parent']['spatial_manifest'];s=load(sp)
    initial=validate_pack(ROOT/a['pack']);assets=[{k:v for k,v in f.items() if k not in {'resref','resource_frame'}} for f in initial.frames]
    identities={(f['sha256'],tuple(f['physical_size_x4'])):i for i,f in enumerate(assets)}
    mapping=[identities[(f['raw_rgba_x4_sha256'],tuple(f['physical_size_x4']))] for f in m['frames']]
    cycles=a['native_cycles'];runtime_count=max(c['cycle'] for c in cycles if c['frame_indices'])+1
    assert all(c['frame_indices'] for c in cycles[:runtime_count]),'Interior empty cycle needs separate routing'
    assert all(not c['frame_indices'] for c in cycles[runtime_count:])
    primary=[];once=[]
    for c in cycles[:runtime_count]:
        primary.append(next(v for v in m['timing']['cycles'] if v['cycle']==c['cycle'] and v['loop_closed']))
        once.append(next(v for v in m['timing']['cycles'] if v['cycle']==c['cycle'] and not v['loop_closed']))
    native=[[mapping[i] for i in v['native_frame_indices']] for v in primary]
    timeline=[[mapping[i] for i in v['timeline_frame_indices']] for v in primary]
    once_timeline=[[mapping[i] for i in v['timeline_frame_indices']] for v in once]
    maximum=max(map(len,timeline))
    record=bytearray(name.encode('ascii').ljust(8,b'\0'));record.extend(struct.pack('<II',len(assets),runtime_count))
    for f in assets:record.extend(struct.pack('<II',*f['logical_size_x1']))
    for c in native:record.extend(struct.pack(f'<I{len(c)}I',len(c),*c))
    record.extend(struct.pack('<IIIII',15,1,30,1,maximum))
    for c in timeline:record.extend(struct.pack(f'<{maximum}I',*(c+[c[-1]]*(maximum-len(c)))))
    record.extend(struct.pack('<I',len(once_timeline)))
    for i,c in enumerate(once_timeline):record.extend(struct.pack(f'<II{len(c)}I',i,len(c),*c))
    timing=copy.deepcopy(initial.manifest['timeline'])
    timing.update(native_frame_indices_by_cycle=native,timeline_frame_indices_by_cycle=timeline,
                  actual_phase_counts_by_cycle=list(map(len,timeline)),cycle_profiles=[v['id'] for v in primary],
                  once_timeline_frame_indices_by_cycle=once_timeline,once_cycle_profiles=[v['id'] for v in once],
                  native_source_cycle_count=len(cycles),runtime_cycle_count=runtime_count,
                  excluded_empty_source_cycles=list(range(runtime_count,len(cycles))),
                  empty_cycle_policy='Unchanged source/carrier retains trailing zero-length cycles; runtime registry omits unplayable trailing entries without renumbering playable cycles.',
                  native_clock_policy='Every native tick retained at even30FPS phase; holds and invisible reserves unchanged.')
    output=ROOT/a['final_pack'] if a.get('final_pack') else ROOT/'effects/ressources'/name/'packs'/f'{name.lower()}-magic-x4-apollo30-profiles-20261108-v1'
    if not (output/'manifest.json').exists():
        write_pack(output,b'IEEEFX4\0'+struct.pack('<IIII',3,4,1,0)+record,assets,
                   load(ROOT/'effects/ressources'/name/'runs'/a['spatial_run']/'run.json'),
                   load(ROOT/s['source']['frame_manifest']),s,registry_version=3,timeline=timing,
                   interpolation_descriptor=load(run/'run.json'))
    checked=validate_pack(output)
    contracts=[]
    for v,indices,is_once in [(v,timeline[i],False) for i,v in enumerate(primary)]+[(v,once_timeline[i],True) for i,v in enumerate(once)]:
        native_indices=[indices[slot*2] for slot in range(len(v['native_slots']))]
        for phase,index in enumerate(indices):
            f=m['frames'][v['timeline_frame_indices'][phase]];w,h=f['logical_size_x1'];slot=phase//2
            for ref in (name,name.lower()):contracts.append(f'{ref}\t{slot}\t{w}\t{h}\t{phase}\t{v["cycle"]}\t{native_indices[slot]}\t{index}\t{int(is_once)}')
    contract=BATCH/'contracts'/f'{name}.tsv';contract.parent.mkdir(exist_ok=True)
    contract.write_text('\n'.join(contracts)+'\n',encoding='ascii')
    log=BATCH/'runtime-verification'/f'{name}.log';log.parent.mkdir(exist_ok=True)
    with log.open('w',encoding='utf-8') as f:subprocess.run([str(PROBE),'--catalogue-only',str(output),str(contract)],stdout=f,stderr=subprocess.STDOUT,check=True,cwd=ROOT)
    result=dict(resref=name,passed=True,pack=rel(output),pack_manifest_sha256=checked.manifest_sha256,registry_version=3,
                source_cycles=len(cycles),runtime_cycles=runtime_count,source_empty_cycles_retained=list(range(runtime_count,len(cycles))),
                profiles=len(primary)+len(once),phases=len(m['frames']),backings=len(assets),native_contracts=len(contracts),
                raw_bytes=sum(f['bytes'] for f in assets),source_interpolation_run=a['interpolation_run'],
                catalogue_probe=rel(log),installed=False,qa='pending-user-review')
    save(receipt,result);print(name,'runtime PASS',len(contracts),'contracts',flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');p.add_argument('--resref',action='append');args=p.parse_args()
    for a in load(BATCH/'batch.json')['assets']:
        if args.resref and a['resref'] not in args.resref:continue
        proof=BATCH/'verification'/f'{a["resref"]}.json'
        while args.wait and not proof.exists():time.sleep(3)
        if proof.exists():build(a)
