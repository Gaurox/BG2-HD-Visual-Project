"""Accept AM0510A; preserve lot5 bytes before purging the replaced portal outputs."""
from pathlib import Path
import sys, csv, io, shutil, copy
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/recipes/lot45-final-20261011-v1'))
from common import v, rel, pixels, payload, GAME, AREAS
import animation_workflow as workflow
import combine_area_pack_splits as combine
import area_pack_state as state
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic

RECIPE = Path(__file__).resolve().parent
OLD = ROOT/'animations/batches/lot45-final-20261011-v1'
TRIAL = ROOT/'animations/batches/am0510a-seedvr7b-retest-20261011-v1'
ACTIVE = ROOT/'animations/packs-par-zone/am0510a-seedvr7b-retest-30fps-mask-20261011-v1'
LOT5 = ROOT/'animations/packs-par-zone/lot5-current-20261011-v1'
FINAL = ROOT/'animations/ressources/AM0510A/runs/am0510a-seedvr7b-retest-accepted-20261011-v1'
REFS = ['AM3000E', 'FLM2PUR', 'AMWRPGT1']

def main():
    assert not (RECIPE/'acceptance.json').exists(), 'acceptance already sealed'
    areas = sorted({area for ref in REFS for area in AREAS[ref]})
    assert len(areas) == 20
    inputs = [ROOT/f'animations/packs-par-zone/lot45-final-20261011-v1-merged-{area}' for area in areas]
    combine.combine(inputs, LOT5, False)
    original = ROOT/'animations/packs-par-zone/lot45-final-20261011-v1-complete'
    lock = state.load_lock()
    for area in areas:
        assert payload(original/area) == payload(LOT5/area) == payload(GAME/'iee-assets/areas'/area), area
        assert state.zone_signatures(GAME/'iee-assets/areas'/area) == lock['areas'][area]['resources'], area
        lock['areas'][area]['build'] = {'leaf': rel(LOT5/area)}
    assert payload(ACTIVE/'AR0510') == payload(GAME/'iee-assets/areas/AR0510')
    lock['areas']['AR0510']['build'] = {'leaf': rel(ACTIVE/'AR0510')}
    state.save_lock(lock)

    # New pending wrappers bind the unchanged lot5 production to its independent index.
    replacements = {}
    for ref in REFS:
        source = ROOT/f'animations/ressources/{ref}/runs/{ref.lower()}-lot45-final-20261011-v1'
        destination = ROOT/f'animations/ressources/{ref}/runs/{ref.lower()}-lot5-current-20261011-v1'
        m = copy.deepcopy(v.load_json(source/'manifest.json'))
        leaf = LOT5/AREAS[ref][0]
        m.update(created_utc=v.utc_now(), source_pack=rel(leaf), source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
                 output_split_root=rel(LOT5), output_manifest_sha256=v.sha256_file(LOT5/'manifest.json'),
                 relocation_reason='Separate unchanged lot5 from explicitly discarded AM0510A version; no runtime or QA change')
        destination.mkdir(parents=True, exist_ok=False)
        v.write_json(destination/'manifest.json', m)
        replacements[ref] = rel(destination)
    with animation_authority_lock(ROOT):
        registry = ROOT/'animations/index/animation_upscale_registry.csv'
        rows = list(csv.DictReader(registry.open(encoding='utf-8-sig', newline='')))
        for row in rows:
            if row['resref'] in replacements:
                assert row['status'] == 'à-valider' and not row['qa_decision']
                row['selected_run'] = replacements[row['resref']]
                row['notes'] += ' Index lot5 autonome lot5-current-20261011-v1 : mêmes octets installés ; QA toujours en attente.'
        buffer = io.StringIO(newline='')
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
        write_atomic(registry, buffer.getvalue())

    FINAL.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(OLD/'mask-AM0510A/mask.png', FINAL/'mask.png')
    assert v.sha256_file(FINAL/'mask.png') == '39564e36dacc98902cfce1c2e5866bfb50d022f049b77a21ec5e663670ca1105'
    spatial = ROOT/'animations/ressources/AM0510A/runs/am0510a-seedvr7b-lab-x4-retest-20261011-v1'
    temporal = TRIAL/'temporal'
    recipe = 'SeedVR2 7B INT8 LAB x4 seed20261011 pad32; Apollo8 15→30FPS; masque arche/halo; 9poses distinctes→18phases, 0,6s'
    r = next(r for r in v.validate_v2_pack(ACTIVE/'AR0510')[1] if r['resref']=='AM0510A')
    assert r['frame_count'] == 18 and len(r['cycles'][0]['timeline_frame_indices']) == 18
    v.write_json(FINAL/'manifest.json', dict(schema='bg2-upscale-animation-final-selection-v1', status='completed', created_utc=v.utc_now(),
        resrefs=['AM0510A'], source_run=rel(spatial), source_run_manifest_sha256=v.sha256_file(spatial/'manifest.json'),
        source_temporal_run=rel(temporal), source_temporal_run_manifest_sha256=v.sha256_file(temporal/'manifest.json'),
        source_pack=rel(ACTIVE/'AR0510'), source_pack_manifest_sha256=v.sha256_file(ACTIVE/'AR0510/manifest.json'),
        output_split_root=rel(ACTIVE), output_manifest_sha256=v.sha256_file(ACTIVE/'manifest.json'),
        mask=rel(FINAL/'mask.png'), mask_sha256=v.sha256_file(FINAL/'mask.png'), tested_areas=['AR0510'], recipe=recipe,
        selection_reason='Utilisateur : ok je valide ta derniere version.', installation_receipt=rel(TRIAL/'installation.json'),
        qa_status='accepted-ingame', release_status='not-selected'))
    workflow.finalize(ROOT, 'AM0510A', FINAL, ACTIVE, ['AR0510'], 'accepted', '2026-10-11',
        'Utilisateur : ok je valide ta derniere version. AM0510A / AR0510 accepté ingame. '+recipe+'.',
        decision_id='2026-10-11-accepted-am0510a-lot4-final-v1', recipe_id=FINAL.name, correction_id=FINAL.name,
        notes='Lot4 terminé : dernière version SeedVR acceptée explicitement. '+recipe+'. Lot5 reste à-valider. Release non sélectionnée.', apply=True)
    check = workflow.check_workspace(ROOT, 'AM0510A'); assert check['ok'], check
    previews()
    discarded = [
        'animations/ressources/AM0510A/runs/am0510a-seedvr7b-lab-x4-20260919',
        'animations/ressources/AM0510A/runs/am0510a-apo8-x4-30fps-v2-20260919',
        'animations/ressources/AM0510A/runs/am0510a-lot45-final-20261011-v1',
        'animations/batches/lot45-final-20261011-v1/final-AM0510A',
        'animations/batches/lot45-final-20261011-v1/mask-AM0510A',
        'animations/packs-par-zone/lot45-final-20261011-v1-merged-AR0510',
        'animations/packs-par-zone/lot45-final-20261011-v1-complete',
        'animations/batches/lot45-final-20261011-v1/preview.png',
        'animations/batches/lot45-final-20261011-v1/preview-lot4.png',
        *[rel(TRIAL/name) for name in ('comparison.png', 'comparison-three-poses.png', 'comparison.gif')],
        # Preserve the immutable transaction receipt and all sibling frames; retire only its old portal payload.
        *[rel(p) for p in sorted((ROOT/'backups/animations/area-tests/AR0510-20261011T135200436072Z-afb89e4e/previous').glob('AAX4-AM0510A-frame*.rgba'))],
    ]
    cleanup = []
    for name in discarded:
        path = (ROOT/name).resolve(); assert path.is_relative_to(ROOT.resolve()) and path.exists()
        files = [p for p in path.rglob('*') if p.is_file()] if path.is_dir() else [path]
        cleanup.append(dict(path=name, files=len(files), bytes=sum(p.stat().st_size for p in files)))
    v.write_json(RECIPE/'acceptance.json', dict(schema='bg2-upscale-animation-batch-acceptance-v1', status='accepted-ingame',
        decision_date='2026-10-11', decision_origin='explicit-user-ingame-qa', resref='AM0510A', tested_areas=['AR0510'],
        final_run=rel(FINAL), qa_pack=rel(ACTIVE), qa_decision='animations/index/qa-decisions/AM0510A/2026-10-11-accepted-am0510a-lot4-final-v1.json',
        lot5_preserved=dict(pack=rel(LOT5), areas=areas, installed_bytes_identical=True, qa_status='pending-ingame', selected_runs=replacements),
        cleanup_status='prepared', cleanup_targets=cleanup, cleanup_bytes=sum(i['bytes'] for i in cleanup),
        retained='Native BAM/paint references, accepted mask, current SeedVR/temporal/final outputs, sibling assets; immutable historical metadata only',
        backup_rollback_retired='Old AM0510A frames removed from previous; historical receipt remains. This backup cannot restore the discarded portal.',
        game_payload_changed=False, release_status='not-selected'))
    print('ACCEPTED AM0510A / AR0510; lot5 preserved byte-identically: 20 areas /68 occurrences; cleanup prepared', flush=True)

def previews():
    out = ROOT/'animations/batches/lot5-current-20261011-v1'
    out.mkdir(parents=True, exist_ok=False)
    jobs = [
        ('AM3000E / PLT_MAGE - AR3000 (cycle 1)', OLD/'final-AM3000E-PLT_MAGE', 1, False),
        ('FLM2PUR / palette embarquee - AR1008', OLD/'final-FLM2PUR-embedded', 0, False),
        ('FLM2PUR / PLT_PURP - OH4210', OLD/'final-FLM2PUR-PLT_PURP', 0, False),
        ('AMWRPGT1 / portails - 17 cartes', ROOT/'animations/ressources/AMWRPGT1/runs/amwrpgt1-timeline30-apo8-safe8x6-gauss3-20260906/03_runtime_pack', 0, True),
    ]
    sheet = Image.new('RGB', (1200, 1280), (32,32,32)); draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 24)
    small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
    for row, (label, pack, cycle, straight) in enumerate(jobs):
        r = v.validate_v2_pack(pack)[1][0]; timeline = r['cycles'][cycle]['timeline_frame_indices']
        draw.text((16,row*320+10),label,font=font,fill='white')
        for col, phase in enumerate((0,len(timeline)//3,2*len(timeline)//3)):
            p = pixels(pack,r['frames'][timeline[phase]])
            if straight:
                image = Image.alpha_composite(Image.new('RGBA',(p.shape[1],p.shape[0]),(32,32,32,255)),Image.fromarray(p)).convert('RGB')
            else:
                image = Image.fromarray(np.minimum(p[...,:3].astype(np.uint16)+32,255).astype(np.uint8))
            image.thumbnail((380,235),Image.Resampling.LANCZOS)
            sheet.paste(image,(col*400+(400-image.width)//2,row*320+68+(235-image.height)//2))
            draw.text((col*400+14,row*320+42),f'Phase {phase}/{len(timeline)}',font=small,fill=(180,180,180))
    sheet.save(out/'preview-lot5.png')
    text = (OLD/'CLUA.md').read_text(encoding='utf-8')
    body = text[text.index('## AR1008'):]
    assert body.count('C:MoveToArea(')==20 and body.count('JumpToPoint(')==68
    (out/'CLUA.md').write_text('# Lot5 — 3 assets /4 variantes /20 cartes /68 occurrences\n\nCoordonnées logiques x1, portrait0. Fermer la console et reprendre le jeu après chaque saut. AR3017 ExitPortal : activation temporaire incluse.\n\n'+body,encoding='utf-8')
    v.write_json(out/'manifest.json',dict(schema='bg2-upscale-animation-batch-review-v1',status='completed',created_utc=v.utc_now(),
        resrefs=REFS,area_count=20,occurrence_count=68,source_pack=rel(LOT5),source_pack_manifest_sha256=v.sha256_file(LOT5/'manifest.json'),
        preview=rel(out/'preview-lot5.png'),commands=rel(out/'CLUA.md'),qa_status='pending-ingame'))

if __name__ == '__main__': main()
