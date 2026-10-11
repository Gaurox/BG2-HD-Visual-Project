"""Install the requested AM0510A retest on AR0510; preserve all acquired siblings."""
from build import ROOT,OUT,RUN,REF,v,rel
from pathlib import Path
import sys,csv,io
sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
import area_animation_area_test as installer
import merge_area_pack_resources as merge
import area_pack_state as state
from workspace_paths import get_path
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic

AREA='AR0510'
ID='am0510a-seedvr7b-retest-30fps-mask-20261011-v1'
PACKROOT=ROOT/'animations/packs-par-zone'/ID
WRAPPER=ROOT/'animations/ressources/AM0510A/runs'/ID
PREVIOUS=ROOT/'animations/packs-par-zone/lot45-final-20261011-v1-complete/AR0510'

def payload(path):
    return {p.name:v.sha256_file(p) for p in sorted(path.iterdir()) if p.is_file() and p.name!='manifest.json'}

def main():
    installer.ensure_game_stopped(installer.running_game_processes)
    trial=v.load_json(OUT/'manifest.json');assert trial['status']=='completed'
    source=ROOT/trial['final_pack'];assert v.sha256_file(source/'manifest.json')==trial['final_pack_manifest_sha256']
    game=get_path('bg2ee_game_root');live=game/'iee-assets/areas'/AREA
    before=payload(live);assert before==payload(PREVIOUS),'Active AR0510 changed since the compared version'
    lock=state.load_lock();assert state.zone_signatures(live)==lock['areas'][AREA]['resources']
    _,old_resources=v.validate_v2_pack(PREVIOUS)
    old=next(r for r in old_resources if r['resref']==REF)
    new=v.validate_v2_pack(source)[1][0]
    assert old['cycles']==new['cycles'] and new['frame_count']==18
    assert all(old[k]==new[k] for k in ('native_fps','target_fps','geometry_mode'))
    for a,b in zip(old['frames'],new['frames']):
        assert all(a[k]==b[k] for k in ('frame','logical_size_x1','physical_size_x4','centre_x1'))
    siblings=sorted({r['resref'] for r in old_resources if r['resref']!=REF})
    assert siblings==['FLAME2M','FLAME2S','FLMS']
    protected={name:v.sha256_file(game/name) for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini')}
    override=game/'override'/(AREA+'.ARE');are_hash=v.sha256_file(override) if override.exists() else None
    specs=[str(PREVIOUS)+'::'+ref for ref in siblings]+[str(source)+'::'+REF]
    merge.merge(specs,AREA,PACKROOT,False);leaf=PACKROOT/AREA
    incoming=payload(leaf)
    for name,digest in before.items():
        if name!=v.REGISTRY_NAME and not name.startswith('AAX4-'+REF+'-'):assert incoming[name]==digest
    assert incoming[v.REGISTRY_NAME]==before[v.REGISTRY_NAME],'Registry contract must remain byte-identical'
    installer.install_area_pack(leaf,game_root=game,verify_only=True)
    WRAPPER.mkdir(parents=True,exist_ok=False)
    v.write_json(WRAPPER/'manifest.json',dict(schema='bg2-upscale-animation-visual-treatment-v1',status='completed',created_utc=v.utc_now(),
        resref=REF,resrefs=[REF],source_run=rel(OUT),source_run_manifest_sha256=v.sha256_file(OUT/'manifest.json'),
        source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
        output_split_root=rel(PACKROOT),output_manifest_sha256=v.sha256_file(PACKROOT/'manifest.json'),
        recipe=dict(spatial='SeedVR2 7B INT8 LAB x4, seed20261011, pad32',temporal='Apollo8',target_fps=30,
            contour='same authored arch and motion-weighted floor halo mask',native_duration_seconds=.6),
        qa_status='pending-ingame',release_status='not-selected'))
    result=installer.install_area_pack(leaf,game_root=game,backup_root=ROOT/'backups/animations/area-tests')
    assert result.status=='installed' and not result.dropped
    assert payload(live)==incoming
    assert all(v.sha256_file(game/name)==digest for name,digest in protected.items())
    assert (v.sha256_file(override) if override.exists() else None)==are_hash
    installer.record_lock(AREA,leaf,game)
    active=state.load_lock()['areas'][AREA]
    assert state.recipe_signatures(active)=={k:val['sig'] for k,val in active['resources'].items()}
    receipt=OUT/'installation.json'
    v.write_json(receipt,dict(schema='bg2-upscale-animation-installation-v1',status='installed',installed_utc=v.utc_now(),
        resref=REF,area_id=AREA,selected_run=rel(WRAPPER),source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
        receipt=rel(result.receipt_path),previous_pack=rel(PREVIOUS),before_payload=before,installed_payload=incoming,
        incoming_files=result.incoming_files,incoming_bytes=result.incoming_bytes,siblings_preserved=siblings,
        registry_byte_identical=True,native_geometry_lookup_and_timing_preserved=True,
        runtime_unchanged=protected,native_are_unchanged=True,qa_status='pending-ingame',release_status='not-selected'))
    with animation_authority_lock(ROOT):
        registry=ROOT/'animations/index/animation_upscale_registry.csv'
        rows=list(csv.DictReader(registry.open(encoding='utf-8-sig',newline='')))
        row=next(r for r in rows if r['resref']==REF)
        assert row['status']=='à-valider' and not row['qa_decision']
        row.update(selected_run=rel(WRAPPER),correction_id=ID,notes=
            'Lot4 AR0510 : nouvelle inférence SeedVR2 7B INT8 LAB x4 seed20261011 installée le 2026-10-11, Apollo8 30FPS. '
            '18phases/0,6s; masque arche/halo, alpha, géométrie et registre runtime conservés. FLAME2S/FLAME2M/FLMS byte-identiques. '
            f'Reçu {rel(receipt)}. Activation QA AmbientActivate("AM0510A",1); QA ingame en attente; release non sélectionnée.')
        buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows);write_atomic(registry,buffer.getvalue())
    (OUT/'CLUA.md').write_text('# AM0510A nouveau SeedVR7B x4 — AR0510\n\n```lua\nC:MoveToArea("AR0510")\nC:Eval(\'JumpToPoint([839.397])\',0)\nC:Eval(\'AmbientActivate("AM0510A",1)\')\n```\n\nLaisser le script de zone initialiser la carte avant activation; fermer la console et reprendre le jeu.\n',encoding='utf-8')
    print('INSTALLED AM0510A / AR0510: 18 new frames; 3 sibling resources preserved; timing, alpha and runtime unchanged',flush=True)

if __name__=='__main__':main()
