"""Install the selected right-hand soft2 flame on OH4210; preserve AR1008 and all siblings."""
from build import ROOT,OUT,REF,v,rel,SOURCE
import sys,csv,io
sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
import area_animation_area_test as installer
import merge_area_pack_resources as merge
import combine_area_pack_splits as combine
import area_pack_state as state
from workspace_paths import get_path
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic
from bam_export import decode_bam
from export_bam_frames import read_bam

AREA='OH4210'
ID='flm2pur-oh4210-soft2-20261011-v1'
PREVIOUS=ROOT/'animations/packs-par-zone/lot5-current-20261011-v1'/AREA
MERGED=ROOT/'animations/packs-par-zone'/ID
SELECTION_ID='flm2pur-palette-selection-soft2-20261011-v1'
PACKROOT=ROOT/'animations/packs-par-zone'/SELECTION_ID
WRAPPER=ROOT/f'animations/ressources/{REF}/runs'/SELECTION_ID

def payload(path):
    return {p.name:v.sha256_file(p) for p in sorted(path.iterdir()) if p.is_file() and p.name!='manifest.json'}

def main():
    installer.ensure_game_stopped(installer.running_game_processes)
    trial=v.load_json(OUT/'manifest.json');assert trial['status']=='completed' and trial['area_scope']==[AREA]
    source=ROOT/trial['variants']['soft2']['pack']
    assert v.sha256_file(source/'manifest.json')==trial['variants']['soft2']['pack_manifest_sha256']
    game=get_path('bg2ee_game_root');live=game/'iee-assets/areas'/AREA
    before=payload(live);assert before==payload(PREVIOUS),'OH4210 changed since comparison'
    assert state.zone_signatures(live)==state.load_lock()['areas'][AREA]['resources']
    ar1008=game/'iee-assets/areas/AR1008';ar1008_before=payload(ar1008)
    embedded_root=ROOT/'animations/packs-par-zone/lot45-final-20261011-v1-merged-AR1008'
    assert payload(embedded_root/'AR1008')==ar1008_before
    old_resources=v.validate_v2_pack(PREVIOUS)[1]
    old=next(r for r in old_resources if r['resref']==REF)
    new=v.validate_v2_pack(source)[1][0]
    assert old['cycles']==new['cycles'] and new['frame_count']==32
    assert all(old[k]==new[k] for k in ('native_fps','target_fps','geometry_mode'))
    for a,b in zip(old['frames'],new['frames']):
        assert all(a[k]==b[k] for k in ('frame','centre_x1','logical_size_x1','physical_size_x4'))
    native=decode_bam(read_bam(ROOT/f'animations/ressources/{REF}/source.bam'))[0]
    for i,(idx,cx,cy,tr) in enumerate(native):
        assert new['frames'][i]['logical_size_x1']==[idx.shape[1],idx.shape[0]] and new['frames'][i]['centre_x1']==[cx,cy]
    siblings=sorted({r['resref'] for r in old_resources if r['resref']!=REF})
    protected={name:v.sha256_file(game/name) for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini')}
    are=game/'override'/(AREA+'.ARE');are_hash=v.sha256_file(are) if are.exists() else None
    specs=[str(PREVIOUS)+'::'+ref for ref in siblings]+[str(source)+'::'+REF]
    merge.merge(specs,AREA,MERGED,False)
    # Family selection contains the exact retained embedded leaf; only OH4210 is installed.
    combine.combine([embedded_root,MERGED],PACKROOT,False)
    leaf=PACKROOT/AREA;incoming=payload(leaf)
    for name,digest in before.items():
        if name!=v.REGISTRY_NAME and not name.startswith('AAX4-'+REF+'-'):
            assert incoming[name]==digest,'Sibling changed: '+name
    assert incoming[v.REGISTRY_NAME]==before[v.REGISTRY_NAME],'native registry must remain byte-identical'
    checked=installer.install_area_pack(leaf,game_root=game,verify_only=True);assert not checked.dropped
    WRAPPER.mkdir(parents=True,exist_ok=False)
    v.write_json(WRAPPER/'manifest.json',dict(schema='bg2-upscale-animation-visual-treatment-v1',status='completed',created_utc=v.utc_now(),
        resref=REF,resrefs=[REF],source_run=rel(OUT),source_run_manifest_sha256=v.sha256_file(OUT/'manifest.json'),
        source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
        output_split_root=rel(PACKROOT),output_manifest_sha256=v.sha256_file(PACKROOT/'manifest.json'),
        area_sources={AREA:dict(source_pack=rel(source),source_pack_manifest_sha256=v.sha256_file(source/'manifest.json'),palette='PLT_PURP',contour='soft2'),
            'AR1008':dict(source_pack=rel(PACKROOT/'AR1008'),source_pack_manifest_sha256=v.sha256_file(PACKROOT/'AR1008/manifest.json'),palette='embedded',existing_bytes_preserved=True)},
        recipe=dict(spatial='ReboutCX x4 on PLT_PURP realized offline',temporal='Apollo8',target_fps=30,
            contour='OH4210 only: Gaussian premultiplied RGBA edge sigma2 x4, spark sigma0.8 with capped flux preservation, canvas1px; AR1008 unchanged',
            canvas_padding_x1=0,native_geometry_preserved=True,phase_count=32,duration_seconds=32/30),
        selection_reason='Utilisateur : ok installe celui de droite ingame',qa_status='pending-ingame',release_status='not-selected'))
    result=installer.install_area_pack(leaf,game_root=game,backup_root=ROOT/'backups/animations/area-tests')
    assert result.status=='installed' and not result.dropped
    assert payload(live)==incoming and payload(ar1008)==ar1008_before
    assert all(v.sha256_file(game/name)==digest for name,digest in protected.items())
    assert (v.sha256_file(are) if are.exists() else None)==are_hash
    installer.record_lock(AREA,leaf,game)
    active=state.load_lock()['areas'][AREA]
    assert state.recipe_signatures(active)=={k:val['sig'] for k,val in active['resources'].items()}
    receipt=OUT/'installation.json'
    v.write_json(receipt,dict(schema='bg2-upscale-animation-installation-v1',status='installed',installed_utc=v.utc_now(),
        resref=REF,area_id=AREA,occurrences=1,variant='soft2',selected_run=rel(WRAPPER),
        source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),receipt=rel(result.receipt_path),
        previous_pack=rel(PREVIOUS),before_payload=before,installed_payload=incoming,siblings_preserved=siblings,
        incoming_files=result.incoming_files,incoming_bytes=result.incoming_bytes,native_geometry_and_registry_byte_identical=True,
        cycle_timelines_aliases_and_duration_preserved=True,runtime_unchanged=protected,native_are_unchanged=True,
        AR1008_payload_unchanged=ar1008_before,qa_status='pending-ingame',release_status='not-selected'))
    with animation_authority_lock(ROOT):
        registry=ROOT/'animations/index/animation_upscale_registry.csv'
        rows=list(csv.DictReader(registry.open(encoding='utf-8-sig',newline='')))
        row=next(r for r in rows if r['resref']==REF)
        assert row['status']=='à-valider' and not row['qa_decision']
        row.update(selected_run=rel(WRAPPER),correction_id=ID,notes=
            'Lot5 FLM2PUR : OH4210 PLT_PURP fondu soft2 choisi à droite, installé 2026-10-11 ; ReboutCX x4/Apollo8 30FPS, '
            'sigma2px x4 au contour, étincelles sigma0,8/flux protégé, canvas1px ;32phases/1,066667s, dimensions/centres/registre natifs exacts. '
            f'AR1008 embarqué et frères OH4210 byte-identiques. Reçu {rel(receipt)}. QA ingame en attente ; release non sélectionnée.')
        buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows);write_atomic(registry,buffer.getvalue())
    (OUT/'CLUA.md').write_text('# FLM2PUR PLT_PURP /OH4210 /fondu soft2\n\n```lua\nC:MoveToArea("OH4210")\nC:Eval(\'JumpToPoint([1522.962])\',0)\n```\n\nCoordonnées logiques x1, portrait0. Fermer la console et reprendre le jeu.\n',encoding='utf-8')
    print('INSTALLED FLM2PUR soft2 /OH4210; native registry identical; AR1008 unchanged; siblings:',','.join(siblings),flush=True)

if __name__=='__main__':main()
