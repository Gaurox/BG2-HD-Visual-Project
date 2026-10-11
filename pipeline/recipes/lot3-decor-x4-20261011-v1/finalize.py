"""Seal explicit lot3 QA on installed bytes; identify AM0902L-only discarded outputs."""
from common import ROOT, v, rel, pixels
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont
import animation_workflow as workflow
import combine_area_pack_splits as combine
import area_pack_state as state
from workspace_paths import get_path

TAG='lot3-four-decors-accepted-20261011-v1'
PACK=ROOT/'animations/packs-par-zone'/TAG
REPORT=Path(__file__).resolve().parent/'acceptance.json'
JOBS={
    'AM0902L':(['AR0902'],'am0902l-seedvr7b-x4-30fps-context-20261011-v1',
        'SeedVR2 7B INT8 LAB x4 contextuel/Apollo8; silhouette inner2; redécoupe quatre tuiles; 16phases/cycle, 0,533333s'),
    'AM1001A':(['AR0905','AR1001','AR1006','AR1007','AR1009'],'am1001a-lot3-decor-x4-20261011-v1',
        'SeedVR2 7B INT8 LAB x4/Apollo8; Potrace angles préservés, inner4; 14phases, 0,466667s'),
    'AM1512PA':(['AR1512'],'am1512pa-lot3-decor-x4-20261011-v1',
        'SeedVR2 7B INT8 LAB x4/Apollo8; holds ×2 retirés avant interpolation 7,5→30FPS; Potrace angles, inner4; 20phases, 0,666667s'),
    'AM2008A':(['AR1010','AR2008','OH5120'],'am2008a-lot3-decor-x4-20261011-v1',
        'ReboutCX x4/Apollo8; centres variables conservés, inner16, prémultiplication unique; 30phases, 1s'),
}

def payload(path):
    return {p.name:v.sha256_file(p) for p in path.iterdir() if p.is_file() and p.name!='manifest.json'}

def main():
    game=get_path('bg2ee_game_root');old=ROOT/'animations/packs-par-zone/lot3-decor-x4-20261011-v1-complete'
    seed=ROOT/'animations/packs-par-zone/am0902l-seedvr7b-x4-30fps-context-20261011-v1'
    # Copy only the exact four selected treatments; AR0902 replaces the historical Rebout leaf.
    combine.combine([old,seed],PACK,False,{'AR0902'})
    lock=state.load_lock();checks=[]
    for ref,(areas,source_id,recipe) in JOBS.items():
        areas=sorted(areas)
        for area in areas:
            live=game/'iee-assets/areas'/area;leaf=PACK/area
            assert payload(live)==payload(leaf),area+': QA bytes differ from installation'
            assert state.zone_signatures(live)==lock['areas'][area]['resources']
            resource=next(r for r in v.validate_v2_pack(leaf)[1] if r['resref']==ref)
            assert resource['target_fps']==dict(numerator=30,denominator=1)
            for c in resource['cycles']:
                assert len(c['native_frame_indices'])/15==len(c['timeline_frame_indices'])/30
        source=ROOT/f'animations/ressources/{ref}/runs/{source_id}'
        final=ROOT/f'animations/ressources/{ref}/runs/{ref.lower()}-{TAG}'
        final.mkdir(parents=True,exist_ok=False)
        leaf=PACK/areas[0]
        receipt='animations/batches/am0902l-seedvr7b-x4-trial-20261011-v1/installation.json' if ref=='AM0902L' else 'animations/batches/lot3-decor-x4-20261011-v1/installation.json'
        v.write_json(final/'manifest.json',dict(schema='bg2-upscale-animation-final-selection-v1',status='completed',created_utc=v.utc_now(),
            resrefs=[ref],source_run=rel(source),source_run_manifest_sha256=v.sha256_file(source/'manifest.json'),
            source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
            output_split_root=rel(PACK),output_manifest_sha256=v.sha256_file(PACK/'manifest.json'),
            selection_reason='Utilisateur : on valide SeedVR. tu peux valider tout le lot 3.',tested_areas=areas,
            recipe=recipe,installation_receipt=receipt,qa_status='accepted-ingame',release_status='not-selected'))
        decision_id=f'2026-10-11-accepted-{ref.lower()}-lot3-final-v1'
        workflow.finalize(ROOT,ref,final,PACK,areas,'accepted','2026-10-11',
            'Utilisateur : on valide SeedVR. tu peux valider tout le lot 3. '+ref+' validé sur '+','.join(areas)+'. '+recipe+'.',
            decision_id=decision_id,recipe_id=TAG,correction_id=TAG,
            notes='Lot3 validé explicitement le 2026-10-11 sur '+','.join(areas)+'. '+recipe+'. Reçu '+receipt+'. Release non sélectionnée.',apply=True)
        check=workflow.check_workspace(ROOT,ref);assert check['ok'],check
        checks.append(dict(resref=ref,areas=areas,recipe=recipe,final_run=rel(final),installed_payload_matches=True,
            qa_decision=f'animations/index/qa-decisions/{ref}/{decision_id}.json'))
        print('ACCEPTED',ref,','.join(areas),flush=True)
    # These stand-alone outputs belong only to the discarded AM0902L treatment.
    # Shared batch/split archives remain immutable: AM2008A and other selected assets reference their hashes.
    discarded=[
        'animations/ressources/AM0902L/runs/am0902l-lot3-decor-x4-20261011-v1',
        'animations/packs-par-zone/lot3-decor-x4-20261011-v1-merged-AR0902',
        *['animations/batches/lot3-decor-x4-20261011-v1/'+name for name in
          ('context-spatial','context-base','temporal-AM0902L','recut-AM0902L')],
    ]
    cleanup=[]
    for name in discarded:
        path=(ROOT/name).resolve();assert path.is_relative_to(ROOT.resolve())
        assert path.is_dir()
        files=[p for p in path.rglob('*') if p.is_file()]
        cleanup.append(dict(path=name,files=len(files),bytes=sum(p.stat().st_size for p in files),
            manifest_sha256=v.sha256_file(path/'manifest.json') if (path/'manifest.json').exists() else None))
    v.write_json(REPORT,dict(schema='bg2-upscale-animation-batch-acceptance-v1',status='accepted-ingame',decision_date='2026-10-11',
        decision_origin='explicit-user-ingame-qa',decision='on valide SeedVR. tu peux valider tout le lot 3.',
        asset_count=4,area_count=10,occurrences=10,qa_pack=rel(PACK),qa_pack_manifest_sha256=v.sha256_file(PACK/'manifest.json'),
        resources=checks,discarded_AM0902L_cleanup_targets=cleanup,
        retained_shared_archives='mixed manifests needed by AM2008A/AM1001A/AM1512PA and immutable comparison/installation history',
        game_payload_changed=False,release_status='not-selected'))
    lot4_preview()
    print('LOT3 ACCEPTED: 4 assets / 10 areas; cleanup plan recorded; lot4 preview ready',flush=True)

def lot4_preview():
    base=ROOT/'animations/batches/lot45-final-20261011-v1'
    pack=base/'final-AM0510A';r=v.validate_v2_pack(pack)[1][0]
    timeline=r['cycles'][0]['timeline_frame_indices']
    bg=Image.open(ROOT/'animations/ressources/AM0510A/paint-ready-am0510a/background-x4-512.png').convert('RGBA')
    sheet=Image.new('RGB',(1536,600),(32,32,32));draw=ImageDraw.Draw(sheet)
    try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
    except OSError:font=ImageFont.load_default()
    draw.text((16,10),'Lot 4 - AM0510A - arche lumineuse / AR0510 - SeedVR x4 / 30 FPS',font=font,fill='white')
    for col,phase in enumerate((0,6,12)):
        p=pixels(pack,r['frames'][timeline[phase]])
        image=Image.alpha_composite(bg,Image.fromarray(p)).convert('RGB')
        sheet.paste(image,(col*512,75));draw.text((col*512+16,44),f'Phase {phase}/18',font=font,fill='white')
    sheet.save(base/'preview-lot4.png')
    (base/'CLUA-lot4.md').write_text('# Lot4 — AM0510A / AR0510\n\n```lua\nC:MoveToArea("AR0510")\nC:Eval(\'JumpToPoint([839.397])\',0)\n```\n\nContrôler l’arche lumineuse, le halo au sol et la disparition du rectangle sur la carte. Coordonnées logiques x1.\n',encoding='utf-8')

if __name__=='__main__':main()
