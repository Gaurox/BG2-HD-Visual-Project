"""Freeze V14 acceptance, disable temporary trace, publish scoped QA decisions."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,os,re,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
from workspace_paths import get_path
from install_renderer_candidate import ensure_game_stopped,running_game_processes
GAME=get_path('bg2ee_game_root',required=True)
OUT=ROOT/'projectiles/analysis/projectile-magique-v14-valide-20261028-v1'
REF=OUT.relative_to(ROOT).as_posix()
INSTALL=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-mask-canvas-20261028-v14'
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):
    with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')

def prepare():
    assert not OUT.exists()
    install=js(INSTALL/'installation.json');assert sha((GAME/'InfinityEngine-Enhancer.dll').read_bytes())==install['dll']['sha256']
    base=js(ROOT/'projectiles/analysis/masque-capture-v14-20261028-v1/log-baseline.json')
    raw=(GAME/'InfinityEngine-Enhancer.log').read_bytes()[base['bytes']:]
    lines=raw.decode('utf-8',errors='replace').splitlines()
    rows=[dict(re.findall(r'(\w+)=([^ ]+)',s)) for s in lines if 'EFX_STREAM_ROW' in s and 'resref=SPMAGMIS ' in s]
    assert len(rows)==28 and all(x['hd']=='true' and x['masked']=='true' and x['outcome']=='0' for x in rows)
    phases=sorted({int(x['phase']) for x in rows});assert phases==list(range(12))
    warnings=[s for s in lines if 'EFX_MASK_FALLBACK' in s or 'EFX_COMPOSITE_REJECT' in s];assert not warnings
    assert max([int(v) for s in lines for v in re.findall(r'traceDropped=(\d+)',s)],default=0)==0
    OUT.mkdir();(OUT/'runtime-session.log').write_bytes(raw)
    save(OUT/'acceptance.json',dict(schema='bg2-projectile-scoped-acceptance-v1',recorded_utc=datetime.now(timezone.utc).isoformat(),
        status='accepted-observed-components',owner='MAGICMIS',asset='SPMAGMIS',renderer='V14',dll=install['dll'],
        user_feedback="c'est validé. maj le suivi et committe",scope='Observed magic-missile flight, HD texture, native mask and animation phases; no universal missile-count/owner/position/release QA',
        first_line=lines[0],last_line=lines[-1],snapshot_sha256=sha(raw),final_draws=28,HD=28,masked=28,
        odd_phase_draws=sum(int(x['phase'])%2 for x in rows),distinct_phases=phases,
        instances=sorted({int(x['serial']) for x in rows}),native_canvas_observed=[64,79],
        mask_composite_rejections=warnings,traceDropped=0,source_crop='Existing64x78 pack -> native64x64 content -> actual64x79 canvas; no image regeneration',
        cadence='Mixed instances; no global cadence measurement inferred',position_interpolation='Deferred PROJ-MOTION-001'))
    before=(GAME/'InfinityEngine-Enhancer.ini').read_bytes();assert before.count(b'EnableEffectStreamingTrace = true')==1
    after=before.replace(b'EnableEffectStreamingTrace = true',b'EnableEffectStreamingTrace = false')
    (OUT/'before-trace-disable.ini').write_bytes(before);(OUT/'candidate-trace-disabled.ini').write_bytes(after)
    save(OUT/'trace-disable-plan.json',dict(before_sha256=sha(before),after_sha256=sha(after),dll=install['dll']['sha256'],only_change='EnableEffectStreamingTrace=true -> false'))
    print('Acceptance frozen:28HD/masked draws,12distinct phases,13odd-phase draws,no rejections')

def disable():
    assert not (OUT/'trace-disabled.json').exists()
    ensure_game_stopped(running_game_processes)
    plan=js(OUT/'trace-disable-plan.json');ini=GAME/'InfinityEngine-Enhancer.ini'
    assert sha(ini.read_bytes())==plan['before_sha256'] and sha((GAME/'InfinityEngine-Enhancer.dll').read_bytes())==plan['dll']
    after=(OUT/'candidate-trace-disabled.ini').read_bytes();assert sha(after)==plan['after_sha256']
    temp=ini.with_name('InfinityEngine-Enhancer.ini.projectile-v14-trace-off.tmp');assert not temp.exists() and temp.resolve().parent==GAME.resolve()
    with temp.open('xb') as f:f.write(after);f.flush();os.fsync(f.fileno())
    os.replace(temp,ini)
    assert sha(ini.read_bytes())==plan['after_sha256'] and sha((GAME/'InfinityEngine-Enhancer.dll').read_bytes())==plan['dll']
    save(OUT/'trace-disabled.json',dict(status='disabled',utc=datetime.now(timezone.utc).isoformat(),before_sha256=plan['before_sha256'],after_sha256=plan['after_sha256'],DLL_unchanged=plan['dll'],other_INI_bytes_unchanged=True,game_loader_stopped=True))
    print('Temporary trace disabled;V14 and every other INI byte preserved')

def publish():
    assert (OUT/'trace-disabled.json').exists()
    path=ROOT/'projectiles/index/work-tracking.json';t=js(path)
    row=t['projectiles']['MAGICMIS'];ref=REF+'/acceptance.json'
    row['historical_evidence'].append(ref)
    row['qa'].update(state='accepted-observed-components',scope=['SPMAGMIS observed V14 HD flight, native mask and12animation phases'],reviewed_on='2026-10-28',
        limits='Observed test only; no every missile-count/owner, position interpolation, complete243 or release QA',latest_manual_feedback=dict(text="c'est validé. maj le suivi et committe",renderer='V14',evidence=ref))
    row['qa']['evidence'].insert(0,ref)
    row['notes']='V14 accepté visuellement :28dessinsfinauxHD/masqués,12phasesdistinctes dont13dessinsdephasesimpaires,0rejetmasque/composition,0traceDropped. Canevasnatif64x79réelcompatibleavecpack64x78viazoneutile64x64enmémoire. Trace temporairecoupée ;QAasset7septembre conservée,pasdevalidationtouscomptes/propriétaires/déplacement/release.'
    path.write_text(json.dumps(t,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    counts=Counter(x.get('qa',{}).get('state','not-assessed') for x in t['projectiles'].values())
    save(OUT/'tracking-update.json',dict(current_visual_scoped=counts['accepted-observed-components'],historical_before_runtime_fix=counts['historical-visual-acceptance-runtime-changed'],static_integration=sum(x.get('integration',{}).get('state')=='verified-static' for x in t['projectiles'].values()),shared_secondary_groups=37,no_new_global_QA=True))
    print('Published MAGICMIS scoped acceptance;29current visual cases,3historical runtime-change cases retained')

if __name__=='__main__':{'prepare':prepare,'disable-trace':disable,'publish':publish}[sys.argv[1]]()
