"""Seal explicit two-colour approval and observed HD/palette evidence."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone
import copy
import gzip
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from projectile_tracking import validate_tracking,read_csv
PLAN=ROOT/'projectiles/analysis/residual-four-20261110-v1'
INSTALL=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-residual-four-20261110-v1'
OUT=ROOT/'projectiles/analysis/residual-four-colours-accepted-20261110-v1'
DECISION='ok les 2 tests sont bons, valide-les, maj le suivi et committe'
EV=(OUT/'acceptance.json').relative_to(ROOT).as_posix()


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def save(p,d):
    with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not OUT.exists(),'Use a new acceptance version'
    game=get_path('bg2ee_game_root',required=True);installed=load(INSTALL/'installation.json')
    assert sha(game/'InfinityEngine-Enhancer.dll')==installed['dll']['sha256']
    cutoff=datetime.fromisoformat(installed['installed_utc'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=1))).strftime('[%Y-%m-%d %H:%M:%S')
    names=['SHWATER','SPBOOM'];selected=[];rows=[];bindings={n:[] for n in names};inputs=[];dropped=[]
    for p in sorted(game.glob('InfinityEngine-Enhancer*.log')):
        matched=False
        for line in p.read_text(encoding='utf-8',errors='replace').splitlines():
            if line[:20]<cutoff:continue
            if 'traceDropped=' in line:
                dropped.extend(map(int,re.findall(r'traceDropped=(\d+)',line)))
            if not any('resref='+n+' ' in line for n in names):continue
            if 'EFX_STREAM_ROW' in line or 'EFX_PALETTE_BOUND' in line:
                selected.append(line);matched=True
            if 'EFX_STREAM_ROW' in line:
                values=dict(re.findall(r'(\w+)=([^ ]+)',line))
                if values.get('swap')=='false':rows.append(values)
            if 'EFX_PALETTE_BOUND' in line:
                for n in names:
                    if 'resref='+n+' ' in line:bindings[n].append(line)
        if matched:inputs.append(dict(path='config://bg2ee_game_root/'+p.name,sha256=sha(p),bytes=p.stat().st_size))
    summary={}
    for n in names:
        draws=[v for v in rows if v['resref']==n and v.get('paused')=='false']
        hd=[v for v in draws if v.get('hd')=='true' and v.get('outcome')=='0']
        assert hd and bindings[n] and any(int(v['phase'])%2 for v in hd),(n,'Missing current runtime evidence')
        summary[n]=dict(HD_draws=len(hd),masked_HD_draws=sum(v.get('masked')=='true' for v in hd),
            odd_HD_draws=sum(int(v['phase'])%2 for v in hd),phases=sorted({int(v['phase']) for v in hd}),
            outcomes=dict(Counter(v['outcome'] for v in draws)),palette_bindings=bindings[n],
            limits='Observed representative colour and sampled phases/masks only; no all-owner/colour/full-motion claim.')
    before_path=ROOT/'projectiles/index/work-tracking.json';before_raw=before_path.read_bytes();before=json.loads(before_raw);after=copy.deepcopy(before)
    OUT.mkdir(parents=True)
    (OUT/'tracking-before.json').write_bytes(before_raw);(OUT/'CLUA-tested.md').write_bytes((PLAN/'CLUA.md').read_bytes())
    (OUT/'trace-selected.txt.gz').write_bytes(gzip.compress(('\n'.join(selected)+'\n').encode('utf-8'),mtime=0))
    save(OUT/'trace-summary.json',dict(resources=summary,local_cutoff=cutoff,source_logs=inputs,
        maximum_traceDropped=max(dropped,default=0),limits=['Sampled telemetry,not an exhaustive trace.','outcome0=HD;outcome1=CpuNotReady;cold-cache native fallback is retained.','draw row ok=false is not a rejection;that field describes swap events.']))
    save(OUT/'acceptance.json',dict(schema='bg2-projectile-scoped-acceptance-v1',status='accepted-two-observed-colour-variants',
        user_decision=DECISION,decision_date='2026-11-10',recorded_utc=datetime.now(timezone.utc).isoformat(),
        observed_variants=['SHWATER6 red/ID138 viaSPPR207','SPBOOM67 gold/ID142 viaSPWM110'],
        installed_dll_sha256=installed['dll']['sha256'],installation=(INSTALL/'installation.json').relative_to(ROOT).as_posix(),
        tested_commands=dict(path=(OUT/'CLUA-tested.md').relative_to(ROOT).as_posix(),sha256=sha(OUT/'CLUA-tested.md')),
        palette_HD_bindings_observed=True,HD_and_native_mask_and_odd_phases_observed=True,
        technical_other_variants_qualification_retained=True,FLMSTRK_and_SPDIMDR_new_live_draw_claimed=False,
        whole_chain_QA_claimed=False,repeat_tests_requested=0,new_inference=0,release_changed=False))
    for ident,name,palette in [(138,'SHWATER','SHWATER6'),(142,'SPBOOM','MPALETTE67')]:
        node=after['engine_projectiles'][str(ident)];previous=node.get('qa',{});ev=previous.get('evidence',[])
        if isinstance(ev,str):ev=[ev]
        node['qa']=dict(state='accepted-observed-components',evidence=list(dict.fromkeys(ev+[EV])),reviewed_on='2026-11-10',
            scope=[f'{name}/{palette},nativeID{ident}: explicit visual approval plus palette/HD/mask/odd-phase telemetry.'],
            limits='Representative colour only;no all-variants/owners/cycles/native-motion/release approval.',
            latest_manual_feedback=dict(text=DECISION,evidence=EV))
        node['integration']['residual_four_runtime'].update(state='accepted-observed-colour-route',
            acceptance=EV,live_HD_draw_observed=True)
        shared=after.setdefault('shared_component_route_QA',{}).setdefault(name,dict(state='accepted-observed-coloured-component-route'))
        shared.setdefault('palette_variant_QA',{})[str(ident)]=dict(state='accepted-observed-colour-route',palette=palette,evidence=[EV],
            reuse_policy='Exact source/pack/compatible blend,geometry,timing and source-specific palette contract;other colours stay technically qualified,not individually observed.')
    for ident in [120,123,126,129,132,135,138,141,142,143,144]:
        node=after['engine_projectiles'][str(ident)]
        if ident not in (138,142):node['integration']['residual_four_runtime'].update(state='qualified-installed-shared-colour-evidence',acceptance=EV)
    after['runtime_route_installations']['residual-four-20261110-v1'].update(state='four-families-qualified-two-colours-accepted',
        acceptance=EV,remaining_manual_variants=[],repeat_visual_tests_requested=0)
    for ns in ('projectiles','engine_projectiles'):
        for n,node in before[ns].items():
            if ns!='engine_projectiles' or n not in ('138','142'):assert node.get('qa')==after[ns][n].get('qa')
            for k in ('installation','release'):assert node.get(k)==after[ns][n].get(k)
    validate_tracking(after,{r['resref'] for r in read_csv(ROOT/'projectiles/index/resources.csv')})
    before_path.write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print('Two colours accepted;all other QA/install/release preserved;no retests requested.')


if __name__=='__main__':main()
