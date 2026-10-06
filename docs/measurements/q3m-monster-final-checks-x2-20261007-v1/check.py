"""No inference/game write: native bank audit + reusable-work correction plan."""
import csv,hashlib,json,runpy,struct,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'sprite/.work/q3m-runtime-tools-20261003-v1')]
from workspace_paths import get_path
from palette_work_plan import file_sha,write_json
from q3m_family_witnesses import source_plan
import run_creature_sprite_x2 as registry
import palette_partner_registry as leaves
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
PARENT=HERE.parent/'q3m-mfie-native-palettes-x2-20261007-v3'
gen=load(PARENT/'current-generation.json');game=get_path('bg2ee_game_root',required=True)
assert not(HERE/'checks.json').exists();WORK.mkdir(parents=True,exist_ok=True)
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==gen['catalog']['sha256']
log=(game/'InfinityEngine-Enhancer.log').read_bytes();lines=log.decode('utf-8-sig').splitlines()
start=max(i for i,s in enumerate(lines) if 'Infinity Engine Enhancer initializing' in s);session=lines[start:]
evidence=[s for s in session if any(x in s for x in ('initializing','0x7312','0x7313','0x7314'))]
(HERE/'session-evidence.txt').write_text('\n'.join(evidence)+'\n',encoding='utf-8',newline='\n')
assert any('MFIE_PALETTE ' in s and 'accepted=true' in s for s in session)
assert any('Composing creature sprite MFIE' in s and 'animation=0x7314' in s for s in session)
selection=load(HERE.parent/'q3m-monster-full-x2-20261006-v2/selection.json')
selection['witnesses']=[w for w in selection['witnesses'] if w['animation_id'] in ('0x7312','0x7313')]
selection['scope']='prepared native bank correction for two IDs only; no inference/installation'
idx=registry.KeyIndex(game);bmps=idx.resource_map(1);bams=idx.resource_map(1000);palettes={}
native={r['animation_id']:r for r in csv.DictReader((ROOT/'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig'))}
for w in selection['witnesses']:
    ini=json.loads(native[w['animation_id']]['ini_sections_json']);w.pop('palette_override');w['palette_overrides_by_bank']={}
    for bank in '12':
        ref=ini['monster']['palette'+bank];raw,_=idx.resolve(bmps[ref]);assert (struct.unpack_from('<I',raw,46)[0] or 256)==256
        w['palette_overrides_by_bank'][bank]=dict(resref=ref,sha256=hashlib.sha256(raw).hexdigest());palettes[ref]=raw[54:54+1024]
write_json(HERE/'correction-selection.json',selection)
resources,works,plan=source_plan(HERE/'correction-selection.json','monster',animation_ids=['0x7312','0x7313'])
assert len(resources)==27 and plan['physical_frames']==11774
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';namespace=file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')
hits=sum((cache/'encoded'/namespace/(key+'.npz')).exists() for key in works)
write_json(HERE/'correction-plan.json',dict(**plan,compatible_encoded_hits=hits,missing_encoded=len(works)-hits,
    inference_started=False,installation=False,runtime_change_required=False,scope=['0x7312','0x7313']))
assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites';cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256'])
items=[];oracle=WORK/'banks.oracle'
with oracle.open('wb') as out:
    out.write(struct.pack('<8sI',b'IEEBANK1',len(resources)))
    for r in resources:
        aid=r['witness']['animation_id'];ref=r['resref'];route=next(d for d in cat['directory'] if d['animation_id']==aid and d['resref']==ref)
        shard=cat['shards'][route['shard_index']];p=game/shard['registry'];assert file_sha(p).upper()==shard['sha256']
        res=leaves.inspect(p,include_frames=True)['resources'][route['resource_ordinal']]
        raw,_=idx.resolve(bams[ref]);bam,_=registry.canonical_bam(raw)
        cycles=[c['frame_indices'] for c in registry.bam_cycles(bam)]
        assert cycles==r['cycles']==res['cycles'] and res['frame_count']==len(r['frames'])
        assert res['source_sha256']==hashlib.sha256(bam).hexdigest()
        primary=palettes[r['witness']['palette_overrides_by_bank']['1']['resref']]
        secondary=palettes[r['witness']['palette_overrides_by_bank']['2']['resref']]
        out.write(struct.pack('<I8sII',int(aid,16),ref.encode().ljust(8,b'\0'),len(r['frames']),len(cycles))+primary+secondary)
        for cycle in cycles:out.write(struct.pack('<I',len(cycle))+struct.pack(f'<{len(cycle)}I',*cycle))
        expected=res['profile'].source.tobytes();correct=r['profile'].source.tobytes()
        items.append(dict(animation_id=aid,resref=ref,frames=res['frame_count'],installed_leaf_sha256=shard['sha256'],
            cycles_exact_native_BAM=True,installed_source_palette_matches_native_bank=(expected==correct)))
ns=runpy.run_path(str(PARENT/'verify.py'));ns['compile_probe'].__globals__.update(HERE=HERE,WORK=WORK)
exe=ns['compile_probe']('bank-check',HERE/'check_banks.cpp')
with(HERE/'bank-check.log').open('w',encoding='utf-8') as stream:subprocess.run([str(exe),str(assets),str(oracle)],stdout=stream,stderr=subprocess.STDOUT,check=True)
result=json.loads((HERE/'bank-check.log').read_text().splitlines()[-1]);assert result['G2_defect_confirmed']
for d in gen['partial_visual_QA']['decisions']:assert file_sha(ROOT/d['path'])==d['sha256']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256'] and file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==gen['catalog']['sha256']
write_json(HERE/'checks.json',dict(audit_completed=True,installed_generation=gen,session_begin=session[0][:25],log_sha256=hashlib.sha256(log).hexdigest(),
    MFIE_live_native_palette_accepted=True,MFIE_live_HD_composition_observed=True,
    live_observed_follow_up_IDs=[aid for aid in ('0x7312','0x7313') if any(aid in s for s in session)],
    native_bank_guard=result,resources=items,affected_animation_ids=['0x7312','0x7313'],
    defect='G2 fixed-palette guard rejects actual native palette2 for every frame; installed profile incorrectly uses palette1',
    native_G1_G2_selection_reference=PARENT.relative_to(ROOT).as_posix()+'/native-bank-selection.txt',
    wrong_G2_bindings=14,prepared_correction_reference=HERE.relative_to(ROOT).as_posix()+'/correction-plan.json',
    GPU_inference_started=False,game_files_changed=False,ingame_follow_up_failure_observed=False,release=False))
print(json.dumps(dict(audit_completed=True,native_guard=result,compatible_hits=hits,missing_encoded=len(works)-hits)),flush=True)
