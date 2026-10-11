"""Install only AM0902L SeedVR on AR0902, with transactional backup and active tracking."""
from build import ROOT, OUT, TAG, REF, v, rel
import csv, io, sys
from pathlib import Path
sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
import area_animation_area_test as installer
import merge_area_pack_resources as merge
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic
from workspace_paths import get_path

RUN='am0902l-seedvr7b-x4-30fps-context-20261011-v1'
AREA='AR0902'
PACKROOT=ROOT/'animations/packs-par-zone'/RUN
WRAPPER=ROOT/'animations/ressources/AM0902L/runs'/RUN

def payload(path):
    return {p.name:v.sha256_file(p) for p in sorted(path.iterdir()) if p.is_file() and p.name!='manifest.json'}

def main():
    installer.ensure_game_stopped(installer.running_game_processes)
    trial=v.load_json(OUT/'manifest.json');assert trial['status']=='completed'
    source=ROOT/trial['final_pack']
    assert v.sha256_file(source/'manifest.json')==trial['final_pack_manifest_sha256']
    game=get_path('bg2ee_game_root');live=game/'iee-assets/areas'/AREA
    lock=v.load_json(ROOT/'animations/index/area-pack-lock.json')
    previous=ROOT/lock['areas'][AREA]['build']['leaf']
    assert set(lock['areas'][AREA]['resources'])=={REF}
    before=payload(live);assert before==payload(previous),'Active AR0902 differs from its locked source'
    previous_resource=v.validate_v2_pack(previous)[1][0]
    incoming_resource=v.validate_v2_pack(source)[1][0]
    assert previous_resource['cycles']==incoming_resource['cycles']
    assert previous_resource['native_fps']==incoming_resource['native_fps']
    assert previous_resource['target_fps']==incoming_resource['target_fps']
    assert len(incoming_resource['frames'])==64
    for old,new in zip(previous_resource['frames'],incoming_resource['frames']):
        assert all(old[k]==new[k] for k in ('frame','logical_size_x1','physical_size_x4','centre_x1'))
    protected={name:v.sha256_file(game/name) for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini')}
    override=game/'override'/(AREA+'.ARE')
    override_before=v.sha256_file(override) if override.exists() else None
    merge.merge([str(source)+'::'+REF],AREA,PACKROOT,False)
    leaf=PACKROOT/AREA
    assert {r['resref'] for r in v.validate_v2_pack(leaf)[1]}=={REF}
    installer.install_area_pack(leaf,game_root=game,verify_only=True)
    WRAPPER.mkdir(parents=True,exist_ok=False)
    v.write_json(WRAPPER/'manifest.json',dict(schema='bg2-upscale-animation-visual-treatment-v1',status='completed',
        created_utc=v.utc_now(),resrefs=[REF],resref=REF,source_run=rel(OUT),source_run_manifest_sha256=v.sha256_file(OUT/'manifest.json'),
        source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
        output_split_root=rel(PACKROOT),output_manifest_sha256=v.sha256_file(PACKROOT/'manifest.json'),
        recipe=dict(spatial='SeedVR2 7B INT8 LAB x4, seed20261011, pad32; contextual RGB seam bands',
            temporal='Apollo8 synchronized whole',target_fps=30,inner_feather_x4=2,native_duration_seconds=8/15,
            geometry='native four-tile recut; native centres and lookup preserved'),
        qa_status='pending-ingame',release_status='not-selected'))
    result=installer.install_area_pack(leaf,game_root=game,backup_root=ROOT/'backups/animations/area-tests')
    assert result.status=='installed' and not result.dropped
    assert payload(live)==payload(leaf)
    assert all(v.sha256_file(game/name)==digest for name,digest in protected.items())
    assert (v.sha256_file(override) if override.exists() else None)==override_before
    installer.record_lock(AREA,leaf,game)
    finish_tracking(result.receipt_path,previous)

def finish_tracking(transaction_receipt,previous):
    import area_pack_state
    game=get_path('bg2ee_game_root');live=game/'iee-assets/areas'/AREA;leaf=PACKROOT/AREA
    transaction=v.load_json(transaction_receipt)
    assert transaction['status']=='installed' and transaction['area_id']==AREA
    assert Path(transaction['source_pack']['root']).resolve()==leaf.resolve()
    assert v.sha256_file(leaf/'manifest.json')==transaction['source_pack']['manifest']['sha256']
    assert payload(live)==payload(leaf)
    active=v.load_json(ROOT/'animations/index/area-pack-lock.json')['areas'][AREA]
    assert area_pack_state.recipe_signatures(active)=={k:val['sig'] for k,val in active['resources'].items()}
    assert set(active['resources'])=={REF}
    protected={Path(val['path']).name:val['sha256'] for val in transaction['runtime_observed'].values()}
    assert all(v.sha256_file(game/name)==digest for name,digest in protected.items())
    before={f['name']:f['sha256'] for f in transaction['before']['files']}
    assert payload(previous)==before
    receipt=OUT/'installation.json'
    v.write_json(receipt,dict(schema='bg2-upscale-animation-installation-v1',status='installed',installed_utc=v.utc_now(),
        resref=REF,area_id=AREA,selected_run=rel(WRAPPER),source_pack=rel(leaf),
        source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),receipt=rel(transaction_receipt),
        previous_pack=rel(previous),before_payload=before,installed_payload=payload(live),
        incoming_files=len(payload(live)),incoming_bytes=sum(p.stat().st_size for p in live.iterdir() if p.is_file()),
        native_geometry_lookup_and_timing_preserved=True,runtime_unchanged=protected,native_are_unchanged=True,
        qa_status='pending-ingame',release_status='not-selected'))
    with animation_authority_lock(ROOT):
        registry=ROOT/'animations/index/animation_upscale_registry.csv'
        rows=list(csv.DictReader(registry.open(encoding='utf-8-sig',newline='')))
        row=next(row for row in rows if row['resref']==REF)
        assert row['status']=='à-valider' and not row['qa_decision']
        row.update(selected_run=rel(WRAPPER),correction_id=RUN,notes=
            'SeedVR2 7B INT8 LAB x4 contextuel/Apollo8 30fps installé sur AR0902 le 2026-10-11, remplacement ReboutCX demandé. '
            '64frames, 4cycles ×16phases, durée0,533333s et géométrie native conservées; aucun doublon. '
            f'Reçu {rel(receipt)}; QA ingame en attente; release non sélectionnée.')
        buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows);write_atomic(registry,buffer.getvalue())
    (OUT/'CLUA.md').write_text('# AM0902L SeedVR 7B x4 — AR0902\n\n```lua\nC:MoveToArea("AR0902")\nC:Eval(\'JumpToPoint([1171.811])\',0)\n```\n',encoding='utf-8')
    print('INSTALLED AM0902L SeedVR / AR0902: 65 files authenticated; geometry/timing unchanged; QA pending',flush=True)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='finish-tracking':finish_tracking(Path(sys.argv[2]),Path(sys.argv[3]))
    else:main()
