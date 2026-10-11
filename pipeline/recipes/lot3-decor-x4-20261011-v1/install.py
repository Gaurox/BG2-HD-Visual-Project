"""Install lot3's ten area leaves, preserve siblings and native ARE activation."""
from common import *
import csv, io, hashlib
sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
import area_animation_area_test as installer
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic
from workspace_paths import get_path
from bg2lib import load_key,resolve_resource
from extract_area_animations import parse_area
from build import payload

def main():
    game=get_path('bg2ee_game_root')
    installer.ensure_game_stopped(installer.running_game_processes)
    pack=ROOT/'animations/packs-par-zone'/(TAG+'-complete')
    baseline=v.load_json(BATCH/'baseline.json')
    receipt=BATCH/'installation.json'
    record=v.load_json(receipt) if receipt.exists() else dict(schema='bg2-upscale-animation-batch-installation-v1',
        status='installing',created_utc=v.utc_now(),complete_pack=rel(pack),areas=[],qa_status='pending-ingame',release_status='not-selected')
    completed={r['area_id'] for r in record['areas']}
    observations={name:v.sha256_file(game/name) for name in ['InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini']}
    for area,before in baseline.items():
        live=game/'iee-assets/areas'/area
        if area in completed:assert payload(live)==before['output_payload']
        else:
            assert live.exists()==before['present'] and payload(live)==before['payload'],area+': active payload changed'
            result=installer.install_area_pack(pack/area,game_root=game,verify_only=True)
            assert not result.dropped,area+': dropped sibling'
    bifs,entries=load_key();lookup={n.upper():loc for n,t,loc in entries if t==0x3f2}
    occurrences=[];originals={};override_hashes={}
    for area in sorted(baseline):
        override=game/'override'/(area+'.ARE')
        data=override.read_bytes() if override.exists() else resolve_resource(bifs,lookup[area])[0]
        if override.exists():override_hashes[area]=hashlib.sha256(data).hexdigest()
        originals[area]=dict(are_sha256=hashlib.sha256(data).hexdigest(),wed_resref=data[8:16].split(b'\0')[0].decode())
        occurrences.extend(row for row in parse_area(area,data) if row['resource_resref'] in AREAS)
    expected=list(csv.DictReader((ROOT/'animations/index/occurrences.csv').open(encoding='utf-8-sig')))
    keys=lambda rows:sorted((r['area_id'],r['resource_resref'],int(r['x']),int(r['y']),int(r['sequence']),int(r['initial_frame']),r['flags_hex']) for r in rows)
    assert keys(occurrences)==keys([r for r in expected if r['resource_resref'] in AREAS])
    assert len(occurrences)==10
    assert [r['area_id'] for r in occurrences if not int(r['flags_hex'],16)&1]==['OH5120']
    record.update(occurrences=occurrences,native_areas=originals)
    commands=['# Lot3 — 10 occurrences / 10 cartes','',
        'Coordonnées logiques x1 ; `,0` cible le premier portrait. Fermer la console et reprendre le jeu après le saut.',
        'OH5120 : Fiery_Boil désactivée nativement ; activation console temporaire pour le test, sans modifier ARE/quête.','']
    for ref,areas in AREAS.items():
        for area in areas:
            row=next(r for r in occurrences if r['area_id']==area and r['resource_resref']==ref)
            commands.extend([f'## {ref} / {area}','','```lua',f'C:MoveToArea("{area}")',
                f"C:Eval('JumpToPoint([{row['x']}.{row['y']}])',0)"])
            if area=='OH5120':commands.append("C:Eval('AmbientActivate(\"Fiery_Boil\",1)')")
            commands.extend(['```',''])
    (BATCH/'CLUA.md').write_text('\n'.join(commands),encoding='utf-8')
    for area in sorted(baseline):
        if area in completed:continue
        result=installer.install_area_pack(pack/area,game_root=game,backup_root=ROOT/'backups/animations/area-tests')
        assert payload(game/'iee-assets/areas'/area)==baseline[area]['output_payload']
        installer.record_lock(area,pack/area,game)
        record['areas'].append(dict(area_id=area,status=result.status,receipt=rel(result.receipt_path) if result.receipt_path else None,
            incoming_files=result.incoming_files,incoming_bytes=result.incoming_bytes,pack_manifest_sha256=v.sha256_file(pack/area/'manifest.json')))
        v.write_json(receipt,record);print('INSTALLED',area,result.status,flush=True)
    for name,digest in observations.items():assert v.sha256_file(game/name)==digest
    for area,digest in override_hashes.items():assert v.sha256_file(game/'override'/(area+'.ARE'))==digest
    record.update(status='installed',installed_utc=v.utc_now(),runtime_unchanged=observations,
        native_areas_unchanged=True,all_10_occurrences_installed=True,siblings_preserved=True)
    v.write_json(receipt,record)
    with animation_authority_lock(ROOT):
        registry=ROOT/'animations/index/animation_upscale_registry.csv'
        rows=list(csv.DictReader(registry.open(encoding='utf-8-sig',newline='')))
        for row in rows:
            ref=row['resref']
            if ref not in AREAS:continue
            assert row['status'] in ('non-traité','à-valider') and not row['qa_decision']
            row.update(status='à-valider',selected_run=f'{ref.lower()}-{TAG}',qa_decision='',qa_date='',correction_id=TAG,
                notes=f'Lot3 x4/30fps installé 2026-10-11 sur {"/".join(AREAS[ref])}; doublons poses contrôlés, holds AM1512PA retirés avant interpolation à durée constante; recette pipeline/recipes/{TAG}/build.py; reçu animations/batches/{TAG}/installation.json; QA ingame en attente; release non sélectionnée.')
        buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows);write_atomic(registry,buffer.getvalue())
    print('DONE: 4 assets / 10 maps / QA pending; CLUA:',rel(BATCH/'CLUA.md'))

if __name__=='__main__':main()
