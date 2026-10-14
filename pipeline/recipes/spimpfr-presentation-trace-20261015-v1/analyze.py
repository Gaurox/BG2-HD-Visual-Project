"""Analyze actual post-swap SPIMPFR observations, not log emission timestamps."""
from pathlib import Path
import argparse
import json
import re
import statistics
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path


def fields(line):
    result={}
    for key,value in re.findall(r'(\w+)=([^\s;,]+)',line):
        if value in {'true','false'}:result[key]=value=='true'
        else:
            try:result[key]=int(value,0)
            except ValueError:result[key]=value
    return result


def analyze_capture(capture,timeline):
    rows=capture['rows'];header=capture['header'];freq=header['frequency']
    fps=timeline['target_fps'][0]/timeline['target_fps'][1]
    expected=timeline['timeline_frame_indices'];n=len(expected)
    active_ticks=0;previous=None;valid=[];present_intervals=[]
    for row in rows:
        if previous and row['active']>0 and previous['active']>0:
            delta=row['qpc']-previous['qpc']
            if delta>=0:
                active_ticks+=delta
                present_intervals.append(delta*1000/freq)
        row=dict(row,active_ms=active_ticks*1000/freq)
        if row['active']>0 and row['draws']>0 and row['swapOk'] and row['hd'] and row['phase']>=0 and not row['conflict']:
            valid.append(row)
        previous=row
    runs=[]
    for row in valid:
        if not runs or row['phase']!=runs[-1]['phase'] or row['backing']!=runs[-1]['backing']:
            runs.append(dict(phase=row['phase'],backing=row['backing'],active_ms=row['active_ms'],epoch=row['epoch'],presentations=1))
        else:runs[-1]['presentations']+=1
    wrong=[r['epoch'] for r in valid if r['phase']>=n or r['backing']!=expected[r['phase']]]
    skipped=sum(max(0,b['phase']-a['phase']-1) for a,b in zip(runs,runs[1:]))
    backward=sum(b['phase']<a['phase'] for a,b in zip(runs,runs[1:]))
    same_backing_different_phase=sum(a['phase']!=b['phase'] and a['backing']==b['backing'] for a,b in zip(runs,runs[1:]))
    median_presentation=statistics.median(present_intervals) if present_intervals else None
    threshold=1000/fps+1.25*(median_presentation or 0)
    holds=[dict(phase=a['phase'],ms=b['active_ms']-a['active_ms'],presentations=a['presentations']) for a,b in zip(runs,runs[1:])]
    long_holds=[h for h in holds if h['ms']>threshold]
    elapsed=runs[-1]['active_ms']-runs[0]['active_ms'] if len(runs)>1 else 0
    unique_fps=(len(runs)-1)*1000/elapsed if elapsed>0 else 0
    owner_rows=[r for r in rows if r['owner'] and r['active']>0]
    fallbacks=sum(r['draws']>0 and not r['hd'] for r in owner_rows)
    timeline_fallbacks=sum(r['draws']>0 and r['hd'] and r['phase']<0 for r in owner_rows)
    no_draw=sum(r['draws']==0 for r in owner_rows)
    failed_swaps=sum(not r['swapOk'] for r in owner_rows)
    conflicts=sum(bool(r['conflict']) for r in owner_rows)
    middle_gaps=sum(r['active']>0 and (not r['owner'] or not r['draws']) and
        valid[0]['epoch']<=r['epoch']<=valid[-1]['epoch'] for r in rows) if valid else 0
    complete=bool(capture.get('end')) and len(rows)==header['rows'] and not header['overflow'] and not header['droppedOwners']
    cadence_ok=complete and len(runs)>30 and abs(unique_fps-fps)<=fps*.03 and not any([
        wrong,skipped,backward,same_backing_different_phase,long_holds,fallbacks,timeline_fallbacks,no_draw,failed_swaps,conflicts,middle_gaps])
    seen={r['phase'] for r in runs}
    return {'id':header['id'],'capture_complete':complete,'target_fps':fps,
        'successful_hd_presentations':len(valid),'observed_unique_phase_changes':max(0,len(runs)-1),
        'observed_unique_fps':unique_fps,'median_presentation_ms':median_presentation,
        'distinct_phases_seen':len(seen),'expected_phases':n,'missing_phases':sorted(set(range(n))-seen),
        'normal_same_phase_presentations':sum(r['presentations']-1 for r in runs),
        'long_hold_threshold_ms':threshold,'long_holds':long_holds,'phase_skips':skipped,
        'backward_steps':backward,'wrong_backing_epochs':wrong,'same_backing_across_different_phases':same_backing_different_phase,
        'native_fallback_presentations':fallbacks,'owner_without_draw_presentations':no_draw,
        'timeline_fallback_presentations':timeline_fallbacks,'unobserved_active_presentations_between_draws':middle_gaps,
        'failed_swaps':failed_swaps,'conflicting_draw_presentations':conflicts,
        'paused_presentations':sum(r['active']==0 for r in rows),
        'cadence_30_confirmed_for_observed_segment':bool(cadence_ok),
        'all_phases_seen':len(seen)==n,'phase_runs':runs,
        'measurement':'draw submitted after final occlusion and real swap returned; not physical monitor scanout or GPU pixel readback'}


def parse_log(text):
    start=text.rfind('Infinity Engine Enhancer initializing...')
    if start>=0:text=text[start:]
    captures={}
    for line in text.splitlines():
        if 'SPIMPFR_PRESENT_BEGIN ' in line:
            f=fields(line);captures[f['id']]={'header':f,'rows':[]}
        elif 'SPIMPFR_PRESENT_ROW ' in line:
            f=fields(line)
            if f['id'] in captures:captures[f['id']]['rows'].append(f)
        elif 'SPIMPFR_PRESENT_END ' in line:
            f=fields(line)
            if f['id'] in captures:captures[f['id']]['end']=True
    return list(captures.values())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--log',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    game=get_path('bg2ee_game_root',required=True);log=args.log or game/'InfinityEngine-Enhancer.log'
    manifest=json.loads((game/'iee-assets/effects/manifest.json').read_text(encoding='utf-8'))
    resource=next(r for r in manifest['resources'] if r['resref']=='SPIMPFR')
    captures=parse_log(log.read_text(encoding='utf-8',errors='replace'))
    results=[analyze_capture(c,resource['timeline']) for c in captures]
    report={'schema':'bg2-spimpfr-presentation-analysis-v1','log':str(log),'captures':results,
        'status':'captures-analyzed' if captures else 'awaiting-user-game-capture'}
    if args.output:
        if args.output.exists():raise RuntimeError('Existing evidence is immutable; choose a fresh output path')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    compact=json.loads(json.dumps(report))
    for r in compact['captures']:r.pop('phase_runs',None)
    print(json.dumps(compact,indent=2))


if __name__=='__main__':main()
