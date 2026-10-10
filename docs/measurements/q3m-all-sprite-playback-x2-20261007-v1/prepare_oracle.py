"""Native BAM cycles for every installed leaf; shared routes tested without recomputation."""
import collections,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import write_json,file_sha
from workspace_paths import get_path
import run_creature_sprite_x2 as r
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
g=load(HERE.parent/'q3m-monster-g2-palettes-x2-20261007-v1/current-generation.json')
game=get_path('bg2ee_game_root',required=True);assets=game/'iee-assets/creature-sprites'
assert file_sha(game/'InfinityEngine-Enhancer.dll')==g['dll']['sha256']
cat=r.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',g['catalog']['sha256'])
owners={x['animation_id']:x['owner'] for x in cat['animations']}
groups=collections.defaultdict(list)
for d in cat['directory']:groups[d['shard_index'],d['resource_ordinal'],owners[d['animation_id']]].append(d)
idx=r.KeyIndex(game);bams=idx.resource_map(1000);cache={};preserved=[];target=None
oracle=WORK/'all-native-cycles.oracle';WORK.mkdir(parents=True,exist_ok=True)
with oracle.open('wb') as out:
    out.write(struct.pack('<8sI',b'IEEALL01',len(groups)))
    for i,((si,ordinal,owner),routes) in enumerate(groups.items()):
        s=cat['shards'][si];ref=routes[0]['resref'];assert all(x['resref']==ref for x in routes)
        if ref not in cache:
            raw,_=idx.resolve(bams[ref]);bam,_=r.canonical_bam(raw)
            cycles=[x['frame_indices'] for x in r.bam_cycles(bam)]
            cache[ref]=(struct.unpack_from('<H',bam,8)[0],cycles,hashlib.sha256(bam).hexdigest())
        nf,cycles,sha=cache[ref]
        aids=[int(x['animation_id'],16) for x in routes]
        out.write(struct.pack('<II8sIII',aids[0],owner,ref.encode().ljust(8,b'\0'),nf,len(cycles),len(aids)))
        out.write(struct.pack(f'<{len(aids)}I',*aids))
        for c in cycles:out.write(struct.pack('<I',len(c))+struct.pack(f'<{len(c)}I',*c))
        if 0x6110 in aids and ref=='CHFF4G1':
            target=dict(animation_id='0x6110',resref=ref,sequence=15,slot=12,cycle=cycles[15],
                native_source_sha256=sha,old_strict_rejects=12>=len(cycles[15]),
                native_loop_frame=cycles[15][12%len(cycles[15])],native_clamp_frame=cycles[15][min(12,len(cycles[15])-1)])
        if (i+1)%1500==0:print(json.dumps(dict(stage='oracle',resources=i+1,total=len(groups))),flush=True)
assert target and target['old_strict_rejects']
print(json.dumps(dict(stage='observed-warning-reproduced',**target)),flush=True)
# Pin all physical leaves once. Alias IDs reuse exactly the same native cycles.
for i,s in enumerate(cat['shards']):
    actual=file_sha(game/s['registry']);assert actual.upper()==s['sha256'].upper()
    preserved.append(dict(relative_path=s['registry'],sha256=actual))
    if (i+1)%2500==0:print(json.dumps(dict(stage='pin-assets',files=i+1,total=len(cat['shards']))),flush=True)
for rel in ('iee-assets/creature-sprites/CreatureSprites-XN.catalog','InfinityEngine-Enhancer.ini'):
    preserved.append(dict(relative_path=rel,sha256=file_sha(game/rel)))
log=(game/'InfinityEngine-Enhancer.log').read_text(encoding='utf-8-sig').splitlines()
session=log[max(i for i,v in enumerate(log) if 'Infinity Engine Enhancer initializing' in v):]
snippet=[x for x in session if '[warning]' in x or ('Composing creature sprite' in x and any(a in x for a in ('0x7312','0x7313')))]
(HERE/'last-session-evidence.txt').write_text('\n'.join(snippet)+'\n',encoding='utf-8')
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',parent_dll_sha256=g['dll']['sha256'],
    catalog_sha256=g['catalog']['sha256'],preserved=preserved,changed_files=['InfinityEngine-Enhancer.dll']))
write_json(HERE/'analysis.json',dict(schema='bg2-common-sprite-playback-analysis-v1',
    session_begin=session[0],session_end=session[-1],observed_failure=target,
    animation_ids=sorted(owners),animation_count=len(owners),owners=dict(collections.Counter(owners.values())),
    routes=len(cat['directory']),physical_leaves=len(cat['shards']),unique_native_resources=len(cache),
    oracle_rows=len(groups),oracle_sha256=file_sha(oracle),
    deduplication='one exhaustive playback test per leaf/resource ordinal/owner; all alias IDs checked separately',
    sprites_recalculated=0,ingame_QA=False,release=False))
print(json.dumps(dict(stage='oracle-prepared',ids=len(owners),resources=len(groups),routes=len(cat['directory']))),flush=True)
