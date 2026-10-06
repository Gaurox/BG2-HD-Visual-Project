"""Record three user-accepted retests on v1; prepare MFIE-only successor."""
import csv,datetime,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;PARENT=HERE.parent/'q3m-monster-stability-x2-20261007-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
assert not(HERE/'current-generation.json').exists()
game=get_path('bg2ee_game_root',required=True);gen=load(PARENT/'current-generation.json');baseline=load(PARENT/'baseline.json')
runtime=load(HERE/'runtime.json');assert load(HERE/'runtime-verification.json')['passed']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
for r in baseline['preserved']:assert file_sha(game/r['relative_path']).upper()==r['sha256'].upper()
accepted=['0x7F0B','0x7F2C','0x7F36'];qa_path=ROOT/'sprite/index/qa-decisions/monsters/2026-10-07-accepted-three-monster-stability-retests-q3m-v7-x2-nearest-v2.json';assert not qa_path.exists()
cat=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',gen['catalog']['sha256'])
routes=sorted((r for r in cat['directory'] if r['animation_id'] in accepted),key=lambda r:(r['animation_id'],r['resref']))
shards=[cat['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
inventory=HERE/'accepted-asset-scope.csv'
with inventory.open('x',encoding='utf-8',newline='') as out:
    writer=csv.writer(out,lineterminator='\n');writer.writerow(['animation_id','resref','registry','sha256','frame_count','resource_ordinal'])
    for r in routes:
        s=cat['shards'][r['shard_index']];writer.writerow([r['animation_id'],r['resref'],s['registry'],s['sha256'],s['frame_count'],r['resource_ordinal']])
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',recorded_on='2026-10-07',
    recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),timezone='Europe/Paris',
    scope=dict(kind='installed-native-family-partial-retest',engine_family='monster',animation_ids=accepted,models=3,colour_variants=3,
        excluded_animation_ids=['0x7314'],scale=2,SDF=False,resources=len(shards),resource_bindings=len(routes)),
    visual_qa=dict(result='pass',authority='user',user_statement='ok pour les 3 derniers. le premier est toujours vanilla. tu peux voir les logs',
        context='7F0B MGCL /7F2C NSOL /7F36 NSHD retested with Monster stability v1',accepted_as_installed=True,full_lot_explicitly_confirmed=False),
    runtime_contract=dict(runtime=gen['runtime'],dll=gen['dll'],catalogue_sha256=gen['catalog']['sha256'],owner=3,world_filter='Nearest',
        colour='Q3m K6 four partners/eight levels x2',metadata_wait=True,native_loop_clamp=True,SDF=False),
    asset_scope=dict(inventory=identity(inventory),physical_leaf_count=len(shards),binding_count=len(routes),catalogue=gen['catalog'],physical_leaf_hashes_verified=len(shards)),
    provenance=dict(installed_generation=identity(PARENT/'current-generation.json'),installed_verification=identity(PARENT/'installed-verification.json'),
        session_evidence=identity(HERE/'session-evidence.txt')),release=False)
write_json(qa_path,qa)
prior=load(PARENT/'partial-QA.json');allaccepted=sorted(prior['accepted_ids']+accepted);assert len(set(allaccepted))==76
qa_refs=[prior['qa_reference'],qa_path.relative_to(ROOT).as_posix()]
write_json(HERE/'partial-QA.json',dict(accepted_ids=allaccepted,qa_references=qa_refs,remaining_user_QA_ids=['0x7314'],
    MFIE_v1_still_vanilla=True,MFIE_v2_ingame_QA=False))
write_json(HERE/'analysis.json',dict(session_evidence=identity(HERE/'session-evidence.txt'),installed_generation=identity(PARENT/'current-generation.json'),
    confirmed='7314 metadata ready; Monster Render reached; target Realize=1, captured=0; no MFIE composition',
    three_retests_user_accepted=accepted,source_palette_entries=252,
    unresolved_live_detail='v1 log lacks native kind/count/colors; exact palette refusal not known',
    tested_guard_gap='v1 rejects 256-entry CVidPalette if unused final four entries differ from zero profile padding',
    candidate='7314 only: compare exact252 prefix if advertised252or256 and frame dependencies exclude all tail indices; bounded trace',release=False))
baseline.update(parent_generation=identity(PARENT/'current-generation.json'),parent_dll_sha256=gen['dll']['sha256'])
write_json(HERE/'baseline.json',baseline)
gen.update(schema='bg2-monster-mfie-runtime-successor-candidate-v2',dll=runtime['dll'],runtime=identity(HERE/'runtime.json'),
    parent_generation=identity(PARENT/'current-generation.json'),runtime_verification=identity(HERE/'runtime-verification.json'),
    partial_visual_QA=dict(decisions=[identity(ROOT/p) for p in qa_refs]),
    short_palette_dependency_proof=identity(PARENT/'short-palette-dependencies.json'),runtime_changed=True,ingame_QA=False,release=False)
write_json(HERE/'current-generation.json',gen)
print(json.dumps(dict(prepared=True,visual_accepted_ids=76,remaining=['0x7314'])),flush=True)
