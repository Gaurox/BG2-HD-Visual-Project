"""Seal phase-5 local production/native proof; no domain QA, active catalog or release write."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from palette_monster_work_plan import require


def read(path):return json.loads(path.read_text())


def seal(pack,production_directory):
    output=HERE/'verification.json';require(not output.exists(),'final phase-5 record is immutable')
    manifest=read(pack/'pack.json');native=read(HERE/'work/native/verification.json')
    resume=read(HERE/'work/resume.json')
    production=[read(production_directory/(a+'.json')) for a in ('0x7F30','0x7F07','0x7F02')]
    pause=read(HERE/'pause.json')
    originals=[read(HERE/'work/production'/(a+'.json')) for a in ('0x7F30','0x7F07')]
    pilot=read(ROOT/'docs/measurements/q3m-monster-pilot-x2-20261003-v1/verification.json')
    phase3=read(ROOT/'docs/measurements/q3m-monster-phase3-x2-20261003-v1/verification.json')
    require(native['status']==resume['status']=='passed' and native['frames']==manifest['frames']==20925 and
            native['cycles']==manifest['cycles']==2288 and native['cycle_slots']==manifest['cycle_slots']==41217,
            'incomplete production/native proof')
    require(all(p['cache_namespace']==resume['namespace']==manifest['cache_namespace'] for p in production),
            'production/cache recipe differs')
    runtime_sources={p:sha for p,sha in phase3['source_sha256'].items()
                     if p.startswith('engine/') and '/src/' in p}
    require(all(file_sha(ROOT/p)==sha for p,sha in runtime_sources.items()),'sealed candidate runtime source changed')
    require(file_sha(ROOT/pilot['runtime']['candidate']['path'])==pilot['runtime']['candidate']['sha256'],
            'sealed runtime candidate changed')
    require(file_sha(ROOT/'docs/measurements/q3m-monster-pilot-x2-20261003-v1/assemble.py')==
            pilot['source_sha256']['docs/measurements/q3m-monster-pilot-x2-20261003-v1/assemble.py'],'acquired verifier changed')
    groups=[]
    for p in production:
        saved=next(r for r in pause['families'] if r['animation_id']==p['animation_id'])
        require(p['stats'].get('cache_hits',0)==saved['saved_work'] and
                p['stats']['selected_work']==saved['total_work'],'resume diverges from pause snapshot')
        before_model=saved.get('new_model_work',saved.get('saved_model_work',0))
        new_model=before_model+p['stats'].get('model_work',0)
        new_special=saved.get('new_special_work',saved.get('saved_special_work',0))+p['stats'].get('special_work',0)
        resources=[r for r in manifest['resources'] if r['animation_id']==p['animation_id']]
        groups.append(dict(animation_id=p['animation_id'],resources=len(resources),
                           frames=sum(r['native_frames'] for r in resources),cycles=sum(r['cycles'] for r in resources),
                           cycle_slots=sum(r['cycle_slots'] for r in resources),
                           native_unreferenced_frames=sum(r['native_unreferenced_frames'] for r in resources),
                           new_model_results_in_phase5=new_model,new_special_results_in_phase5=new_special,
                           phase4_results_reused=saved.get('existing_phase4_hits',0),
                           before_pause=saved,resumed_production=p))
    previews=[]
    for folder in sorted((pack/'previews').iterdir()):
        path=folder/'preview.png'
        previews.append(dict(animation_id=folder.name,path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path),
                             metadata=read(folder/'preview.json'),
                             status='agent-inspected-static-comparison-only' if folder.name!='0x7F30' else 'static-comparison-generated',
                             QA_accepted=False))
    report=dict(schema='bg2-monster-q3m-complete-phase5-verification-v1',phase=5,
                status='complete-produced-isolated-native-host-verified-not-installed',
                completed_at_utc=datetime.now(timezone.utc).isoformat(),
                recipe=dict(scale=2,k=6,dithering=False,boundary_mixing=False,world_downscale='BOX',
                            profiles=[2,3,4,5,6,7],decode_rule=2,format='V6',owner=3),
                families=groups,pack=manifest,pack_manifest_sha256=file_sha(pack/'pack.json'),
                production_history=dict(original_completed_reports=originals,pause_snapshot=pause,
                                        resume_directory=production_directory.relative_to(ROOT).as_posix(),
                                        new_model_results=sum(g['new_model_results_in_phase5'] for g in groups),
                                        new_special_results=sum(g['new_special_results_in_phase5'] for g in groups),
                                        phase4_results_reused=272,
                                        neural_target_evaluations_exact=None,
                                        note='Interrupted attempt may include unsaved targets; count persisted results, not total GPU evaluations.'),
                native=native,cache_resume=resume,runtime=pilot['runtime'],previews=previews,
                bodhi_visual_proof_reused=pilot['preview'],
                source_sha256={p.relative_to(ROOT).as_posix():file_sha(p) for p in sorted(HERE.glob('*.py'))},
                preservation=pilot['preservation'],
                QA_accepted=False,ingame_validated=False,
                next_step=dict(phase=6,action='integrate three complete Monster families into a new catalog candidate',
                               preserve_character_animations=78,preserve_paperdolls=81,installation_phase=7))
    write_json(output,report)
    print({k:report[k] for k in ('status','completed_at_utc','next_step')})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pack',type=Path,required=True)
    p.add_argument('--production',type=Path,default=HERE/'work/production-resume-v1')
    a=p.parse_args();seal(a.pack.resolve(),a.production.resolve())
