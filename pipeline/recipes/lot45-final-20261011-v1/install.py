from common import *
import io,csv,hashlib
sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
import area_animation_area_test as installer
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic
from bg2lib import load_key,resolve_resource
from extract_area_animations import parse_area

def commands(rows,title):
    result=[title,'','Coordonnées logiques x1 ; `,0` cible le premier portrait. Fermer la console et reprendre le jeu après le saut.',
            'Les activations mentionnées servent au test temporaire des effets nativement désactivés ; ARE et quêtes inchangés.','']
    for area in sorted({r['area_id'] for r in rows}):
        group=[r for r in rows if r['area_id']==area]
        result.extend([f'## {area} — '+', '.join(sorted({r['resource_resref'] for r in group})),'','```lua',f'C:MoveToArea("{area}")'])
        for row in group:
            result.append(f"-- {row['resource_resref']} / {row['instance_name']} / ({row['x']},{row['y']})")
            result.append(f"C:Eval('JumpToPoint([{row['x']}.{row['y']}])',0)")
            if not int(row['flags_hex'],16)&1:result.append(f"C:Eval('AmbientActivate(\"{row['instance_name']}\",1)')")
        result.extend(['```',''])
    return '\n'.join(result)

def main():
    installer.ensure_game_stopped(installer.running_game_processes)
    pack=PACKS/(TAG+'-complete');baseline=v.load_json(BATCH/'baseline.json')
    assert v.load_json(BATCH/'verification.json')['status']=='completed'
    receipt=BATCH/'installation.json'
    record=v.load_json(receipt) if receipt.exists() else dict(schema='bg2-upscale-animation-batch-installation-v1',status='installing',
        created_utc=v.utc_now(),complete_pack=rel(pack),areas=[],qa_status='pending-ingame',release_status='not-selected')
    completed={x['area_id'] for x in record['areas']}
    observations={n:v.sha256_file(GAME/n) for n in ['InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini']}
    previous_lot=ROOT/'animations/batches/lot3-decor-x4-20261011-v1/baseline.json'
    lot3=v.load_json(previous_lot)
    assert not set(lot3)&set(baseline)
    for a,x in lot3.items():assert payload(GAME/'iee-assets/areas'/a)==x['output_payload'],a+': lot3 changed before installation'
    for area,before in baseline.items():
        live=GAME/'iee-assets/areas'/area
        if area in completed:assert payload(live)==before['output_payload']
        else:
            assert live.exists()==before['present'] and payload(live)==before['payload'],area+': active payload changed'
            result=installer.install_area_pack(pack/area,game_root=GAME,verify_only=True);assert not result.dropped
    bifs,entries=load_key();lookup={n.upper():loc for n,t,loc in entries if t==0x3f2};occurrences=[];native={};overrides={}
    for area in sorted(baseline):
        override=GAME/'override'/(area+'.ARE')
        data=override.read_bytes() if override.exists() else resolve_resource(bifs,lookup[area])[0]
        digest=hashlib.sha256(data).hexdigest();native[area]=dict(are_sha256=digest,wed_resref=data[8:16].split(b'\0')[0].decode())
        if override.exists():overrides[area]=digest
        occurrences.extend(r for r in parse_area(area,data) if r['resource_resref'] in REFS)
    keys=lambda rows:sorted((r['area_id'],r['resource_resref'],int(r['x']),int(r['y']),int(r['sequence']),int(r['initial_frame']),r['flags_hex'],r['palette_mode'],r['palette_resref']) for r in rows)
    assert keys(occurrences)==keys(OCCURRENCES) and len(occurrences)==69
    record.update(occurrences=occurrences,native_areas=native)
    (BATCH/'CLUA.md').write_text(commands(occurrences,'# Lots4–5 — 21cartes /69occurrences'),encoding='utf-8')
    lot3_occ=v.load_json(ROOT/'animations/batches/lot3-decor-x4-20261011-v1/installation.json')['occurrences']
    combined=lot3_occ+occurrences;assert len(combined)==79 and len({r['area_id'] for r in combined})==31
    (BATCH/'CLUA-lots3-4-5.md').write_text(commands(combined,'# QA différée — lots3/4/5, 31cartes /79occurrences'),encoding='utf-8')
    for area in sorted(baseline):
        if area in completed:continue
        result=installer.install_area_pack(pack/area,game_root=GAME,backup_root=ROOT/'backups/animations/area-tests')
        assert payload(GAME/'iee-assets/areas'/area)==baseline[area]['output_payload']
        installer.record_lock(area,pack/area,GAME)
        record['areas'].append(dict(area_id=area,status=result.status,receipt=rel(result.receipt_path) if result.receipt_path else None,
            incoming_files=result.incoming_files,incoming_bytes=result.incoming_bytes,pack_manifest_sha256=v.sha256_file(pack/area/'manifest.json')))
        v.write_json(receipt,record);print('INSTALLED',area,result.status,flush=True)
    for n,digest in observations.items():assert v.sha256_file(GAME/n)==digest
    for area,digest in overrides.items():assert v.sha256_file(GAME/'override'/(area+'.ARE'))==digest
    for a,x in lot3.items():assert payload(GAME/'iee-assets/areas'/a)==x['output_payload'],a+': lot3 changed'
    record.update(status='installed',installed_utc=v.utc_now(),runtime_unchanged=observations,native_areas_unchanged=True,
        all_69_occurrences_installed=True,lot3_unchanged=True,siblings_preserved=True)
    v.write_json(receipt,record)
    with animation_authority_lock(ROOT):
        registry=ROOT/'animations/index/animation_upscale_registry.csv';rows=list(csv.DictReader(registry.open(encoding='utf-8-sig',newline='')))
        for row in rows:
            ref=row['resref']
            if ref not in REFS:continue
            assert row['status'] in ('non-traité','à-compléter','à-corriger','à-valider') and not row['qa_decision']
            notes='Masque fenêtre/halo produit; spatial SeedVR/Apollo8 historique conservé.' if ref=='AM0510A' else 'Palette PLT_MAGE réalisée avant ReboutCX/Apollo8; 3cycles et durées conservés.' if ref=='AM3000E' else 'ReboutCX/Apollo8; palette embarquée AR1008, PLT_PURP réalisée OH4210; variantes par carte.' if ref=='FLM2PUR' else 'Recette SeedVR/Apollo8 safe8x6-gauss3 reprise byte-identique sur17cartes; QA antérieures AR3011/AR3016/AR3017 conservées; liseré cyan AR3003 issu de la carte, raster inchangé.'
            row.update(status='à-valider',selected_run=f'{ref.lower()}-{TAG}',qa_decision='',qa_date='',correction_id=TAG,
                notes=f'Lots4–5 installés 2026-10-11. {notes} Aucun doublon source; durées natives préservées. Reçu animations/batches/{TAG}/installation.json; recette pipeline/recipes/{TAG}/README.md; QA utilisateur différée avec lot3; release non sélectionnée.')
        buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows);write_atomic(registry,buffer.getvalue())
    print('DONE: 21 maps / 69 occurrences; QA pending; combined CLUA for lots3/4/5 ready')

if __name__=='__main__':main()
