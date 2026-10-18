"""Prepare all33 authorized native impacts; sources and old productions untouched."""
from pathlib import Path
import copy
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from export_bam_frames import read_bam,cycle_metadata
from bam_export import decode_bam

BATCH=ROOT/'effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1'
PROPOSAL=ROOT/'effects/batches/lot33-elemental-impacts-proposal-20261017-v1'
DIFFUSE={'SPBOOM','SPRDRASI','SPHORPUF','SPRING','STNKCLDD'}


def main():
    p=json.loads((PROPOSAL/'batch.json').read_text(encoding='utf-8'))
    assets=copy.deepcopy(p['assets'])
    for a in assets:
        name=a['resref']
        a['native_fps']=[]
        a['native_rate_basis']='15 FPS compatibility default for native engine owners; not an instrumented measurement'
        a['playback']='unknown-native-owner; retain independent once and loop variants'
        a['static']=False
        a['inner_feather_x4']=12 if name in DIFFUSE else 0
        a['spatial_run']=f'{name.lower()}-seedvr7b-x4-20261017-v1'
        a['interpolation_run']=f'{name.lower()}-apollo30-native-retimed-20261017-v1'
        a['pack']=f'effects/ressources/{name}/packs/{name.lower()}-7b-x4-apollo30-native-20261017-v1'
        raw=read_bam(ROOT/a['source']);frames,_,_=decode_bam(raw)
        assert cycle_metadata(raw,len(frames))==a['native_cycles']
        a['max_frame_x1']=[max(f[0].shape[1] for f in frames),max(f[0].shape[0] for f in frames)]
        assert not (ROOT/'effects/ressources'/name/'runs'/a['spatial_run']/'run.json').exists()
    batch={'schema':'bg2-effects-production-batch-v1','date':'2026-10-17','assets_count':33,
        'proposal':PROPOSAL.relative_to(ROOT).as_posix()+'/batch.json',
        'spatial_batch':BATCH.relative_to(ROOT).as_posix(),'alias_policy':p['aliases'],
        'authorization':'User: complete33; SeedVR7B x4 and interpolation30; remove duplicate poses and preserve native duration.',
        'native_owner_policy':'Retain once/loop variants per cycle,15FPS compatibility basis; native runtime tint/blend/rate not inferred from index.',
        'assets':assets}
    BATCH.mkdir(parents=True,exist_ok=True)
    for name,value in [('batch.json',batch),('native-duplicate-audit.json',json.loads((PROPOSAL/'native-duplicate-audit.json').read_text()))]:
        path=BATCH/name
        assert not path.exists()
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Prepared33,36RESREF,91cycles, once+loop profiles;28fine masks0 /5diffuse12',flush=True)


if __name__=='__main__':main()
