"""Install the user's selected soft2 contour on AR3000; keep every sibling byte-identical."""
from build import ROOT,OUT,REF,v,rel,PAD_X1
import sys,csv,io
sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
import area_animation_area_test as installer
import merge_area_pack_resources as merge
import area_pack_state as state
from workspace_paths import get_path
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic

AREA='AR3000'
ID='am3000e-contour-soft2-20261011-v1'
PREVIOUS=ROOT/'animations/packs-par-zone/lot5-current-20261011-v1'/AREA
PACKROOT=ROOT/'animations/packs-par-zone'/ID
WRAPPER=ROOT/f'animations/ressources/{REF}/runs'/ID

def payload(path):
    return {p.name:v.sha256_file(p) for p in sorted(path.iterdir()) if p.is_file() and p.name!='manifest.json'}

def main():
    installer.ensure_game_stopped(installer.running_game_processes)
    trial=v.load_json(OUT/'manifest.json');assert trial['status']=='completed'
    source=ROOT/trial['variants']['soft2']['pack']
    assert v.sha256_file(source/'manifest.json')==trial['variants']['soft2']['pack_manifest_sha256']
    game=get_path('bg2ee_game_root');live=game/'iee-assets/areas'/AREA
    before=payload(live);assert before==payload(PREVIOUS),'AR3000 changed since contour comparison'
    assert state.zone_signatures(live)==state.load_lock()['areas'][AREA]['resources']
    old_resources=v.validate_v2_pack(PREVIOUS)[1]
    old=next(r for r in old_resources if r['resref']==REF)
    new=v.validate_v2_pack(source)[1][0]
    assert old['cycles']==new['cycles'] and new['frame_count']==61
    assert all(old[k]==new[k] for k in ('native_fps','target_fps','geometry_mode'))
    for a,b in zip(old['frames'],new['frames']):
        assert a['frame']==b['frame']
        assert b['centre_x1']==[i+PAD_X1 for i in a['centre_x1']]
        assert b['logical_size_x1']==[i+2*PAD_X1 for i in a['logical_size_x1']]
        assert b['physical_size_x4']==[i+8*PAD_X1 for i in a['physical_size_x4']]
    siblings=sorted({r['resref'] for r in old_resources if r['resref']!=REF})
    protected={name:v.sha256_file(game/name) for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini')}
    are=game/'override'/(AREA+'.ARE');are_hash=v.sha256_file(are) if are.exists() else None
    specs=[str(PREVIOUS)+'::'+ref for ref in siblings]+[str(source)+'::'+REF]
    merge.merge(specs,AREA,PACKROOT,False);leaf=PACKROOT/AREA
    incoming=payload(leaf)
    for name,digest in before.items():
        if name!=v.REGISTRY_NAME and not name.startswith('AAX4-'+REF+'-'):
            assert incoming[name]==digest,'Sibling changed: '+name
    checked=installer.install_area_pack(leaf,game_root=game,verify_only=True);assert not checked.dropped
    WRAPPER.mkdir(parents=True,exist_ok=False)
    v.write_json(WRAPPER/'manifest.json',dict(schema='bg2-upscale-animation-visual-treatment-v1',status='completed',created_utc=v.utc_now(),
        resref=REF,resrefs=[REF],source_run=rel(OUT),source_run_manifest_sha256=v.sha256_file(OUT/'manifest.json'),
        source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
        output_split_root=rel(PACKROOT),output_manifest_sha256=v.sha256_file(PACKROOT/'manifest.json'),tested_areas=[AREA],
        recipe=dict(spatial='ReboutCX x4 fp16 on PLT_MAGE realized offline',temporal='Apollo8',target_fps=30,
            contour='soft2: edge-only Gaussian RGBA premultiplied sigma2 x4; core exact beyond8px; no second premultiply',
            canvas_padding_x1=PAD_X1,world_placement_preserved=True,cycle_phases=[48,36,20],cycle_durations_seconds=[1.6,1.2,20/30]),
        selection_reason='Utilisateur : ok installe celle du milieu ingame',qa_status='pending-ingame',release_status='not-selected'))
    result=installer.install_area_pack(leaf,game_root=game,backup_root=ROOT/'backups/animations/area-tests')
    assert result.status=='installed' and not result.dropped
    assert payload(live)==incoming
    assert all(v.sha256_file(game/name)==digest for name,digest in protected.items())
    assert (v.sha256_file(are) if are.exists() else None)==are_hash
    installer.record_lock(AREA,leaf,game)
    active=state.load_lock()['areas'][AREA]
    assert state.recipe_signatures(active)=={k:val['sig'] for k,val in active['resources'].items()}
    receipt=OUT/'installation.json'
    v.write_json(receipt,dict(schema='bg2-upscale-animation-installation-v1',status='installed',installed_utc=v.utc_now(),
        resref=REF,area_id=AREA,occurrences=5,variant='soft2',selected_run=rel(WRAPPER),
        source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),receipt=rel(result.receipt_path),
        previous_pack=rel(PREVIOUS),before_payload=before,installed_payload=incoming,siblings_preserved=siblings,
        incoming_files=result.incoming_files,incoming_bytes=result.incoming_bytes,world_placement_preserved=True,
        cycle_timelines_aliases_and_duration_preserved=True,runtime_unchanged=protected,native_are_unchanged=True,
        registry_geometry_updated_for_transparent_padding=True,qa_status='pending-ingame',release_status='not-selected'))
    with animation_authority_lock(ROOT):
        registry=ROOT/'animations/index/animation_upscale_registry.csv'
        rows=list(csv.DictReader(registry.open(encoding='utf-8-sig',newline='')))
        row=next(r for r in rows if r['resref']==REF)
        assert row['status']=='à-valider' and not row['qa_decision']
        row.update(selected_run=rel(WRAPPER),correction_id=ID,notes=
            'Lot5 AR3000 : fondu doux soft2 sélectionné et installé 2026-10-11 sur5occurrences. '
            'ReboutCX x4/PLT_MAGE puis Apollo8 30FPS, filtre RGBA prémultiplié au contour sigma2px x4, cœur exact au-delà8px. '
            '61frames/48-36-20phases, durées1,6/1,2/0,666667s conservées ; padding3px x1 compensé dans les centres, placement monde inchangé. '
            f'Frères byte-identiques ; reçu {rel(receipt)}. QA ingame en attente ; release non sélectionnée.')
        buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows);write_atomic(registry,buffer.getvalue())
    commands='\n'.join(['# AM3000E / fondu doux soft2 / AR3000 /5occurrences','','Coordonnées logiques x1 ; portrait0.','',
        '```lua','C:MoveToArea("AR3000")',"C:Eval('JumpToPoint([396.1169])',0)","C:Eval('JumpToPoint([640.1521])',0)",
        "C:Eval('JumpToPoint([899.1853])',0)","C:Eval('JumpToPoint([447.2006])',0)","C:Eval('JumpToPoint([194.1670])',0)",'```',''])
    (OUT/'CLUA.md').write_text(commands,encoding='utf-8')
    print('INSTALLED AM3000E soft2 on AR3000 /5 occurrences; preserved siblings:',','.join(siblings),flush=True)

if __name__=='__main__':main()
