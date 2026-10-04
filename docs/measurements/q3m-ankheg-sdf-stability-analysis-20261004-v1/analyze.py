"""Read the last engine session; retain targeted evidence without editing game files."""
from pathlib import Path
import sys,json,re,hashlib,collections,datetime
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from palette_work_plan import write_json,file_sha
game=get_path('bg2ee_game_root',required=True);path=game/'InfinityEngine-Enhancer.log'
raw=path.read_bytes();all_lines=raw.decode('utf-8-sig',errors='replace').splitlines()
start=max(i for i,l in enumerate(all_lines) if 'Infinity Engine Enhancer initializing...' in l)
session=all_lines[start:];rows=[(start+i+1,l) for i,l in enumerate(session)]
warnings=[dict(line=n,text=l) for n,l in rows if re.search(r'\[(warning|error|critical)\]',l)]
loads=[]
for n,l in rows:
    m=re.search(r'Creature sprite catalog shard (\d+) ready on demand for animation 0x3000, resref (\w+): .*?, (\d+) metadata bytes',l)
    if m:loads.append(dict(line=n,time=l[1:24],shard=int(m[1]),resref=m[2],metadata_bytes=int(m[3])))
draws=[(n,l) for n,l in rows if 'Native occlusion phase0:' in l and 'subject=0x3000,' in l]
draw_kinds=collections.Counter(re.search(r'replacement=(\S+)',l)[1] for _,l in draws)
witnesses=[dict(line=n,text=l) for n,l in rows if 'Q3M_FAMILY_WITNESS animation=3000' in l]
composing=[dict(line=n,text=l) for n,l in rows if 'Composing creature sprite MAK' in l]
last_loading={};transitions=[]
for n,l in draws:
    replacement=re.search(r'replacement=(\S+)',l)[1]
    if not transitions or transitions[-1]['replacement']!=replacement:
        transitions.append(dict(line=n,time=l[1:24],replacement=replacement,text=l))
first_fallback=next((w for w in warnings if 'Registered creature CVidCell frame could not be resolved' in w['text']),None)
targeted=[(n,l) for n,l in rows if 'Infinity Engine Enhancer initializing' in l or
    'Creature sprite xBR catalog ready' in l or 'Shader suite' in l or 'Creature sprite filter' in l or
    'Q3M_FAMILY_WITNESS animation=3000' in l or 'Composing creature sprite MAK' in l or
    'ready on demand for animation 0x3000' in l or re.search(r'\[(warning|error|critical)\]',l)]
transition_lines={d['line'] for d in transitions}
targeted+= [(n,l) for n,l in draws if n in transition_lines]
targeted.sort()
(HERE/'selected-session-evidence.txt').write_text('\n'.join(f'{n}: {l}' for n,l in targeted)+'\n',encoding='utf-8',newline='\n')
generation=json.loads((HERE.parent/'q3m-ankheg-sdf-ingame-x2-20261004-v1/current-generation.json').read_text())
assert file_sha(game/'InfinityEngine-Enhancer.dll')==generation['dll']['sha256']
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==generation['catalog']['sha256']
report=dict(log='config://bg2ee_game_root/InfinityEngine-Enhancer.log',log_sha256=hashlib.sha256(raw).hexdigest(),log_bytes=len(raw),
    session_start_line=start+1,session_first_line=session[0],session_last_line=session[-1],session_lines=len(session),
    warnings=warnings,Ankheg_loads=loads,Ankheg_resident_metadata_observed=sum(x['metadata_bytes'] for x in loads),
    repeated_Ankheg_loads=[r for r,c in collections.Counter(x['resref'] for x in loads).items() if c>1],
    native_occlusion_Ankheg_draws=len(draws),native_occlusion_replacements=dict(draw_kinds),replacement_transitions=transitions,
    family_witnesses=witnesses,first_fallback=first_fallback,first_compositions=composing,
    live_DLL_sha256=generation['dll']['sha256'],live_catalog_sha256=generation['catalog']['sha256'],
    caveat='occlusion trace is sampled/deduplicated; the unresolved warning is process-wide once, not a count of failed frames',
    runtime_changed=False,assets_changed=False,ingame_QA='visual quality praised by user; temporal stability failed')
write_json(HERE/'log-analysis.json',report)
print(json.dumps({k:report[k] for k in ('session_start_line','session_first_line','session_last_line','session_lines','Ankheg_loads','repeated_Ankheg_loads','native_occlusion_replacements','replacement_transitions','family_witnesses','first_fallback')},ensure_ascii=False))
