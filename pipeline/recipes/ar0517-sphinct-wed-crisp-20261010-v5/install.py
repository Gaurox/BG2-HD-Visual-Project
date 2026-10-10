"""Install selected crisp AR0517 pack with backup; record installed, QA pending."""
from pathlib import Path
import sys,csv,io
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'));sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
import run_animation_upscale_30fps_v2 as v2
import area_animation_area_test as installer
from workspace_paths import get_path
TAG='ar0517-sphinct-wed-crisp-20261010-v5';OUT=ROOT/'animations/batches'/TAG;GAME=get_path('bg2ee_game_root')
plan=v2.load_json(OUT/'plan.json');assert v2.load_json(OUT/'checks.json')['passed']
PACK=ROOT/plan['pack']/'AR0517'
def payload(path):
 return {p.name:v2.sha256_file(p) for p in path.iterdir() if p.is_file() and (p.name==v2.REGISTRY_NAME or p.suffix=='.rgba')}
assert not (OUT/'installation.json').exists()
assert payload(GAME/'iee-assets/areas/AR0517')==plan['before_payload']
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')==plan['renderer_sha256']
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==plan['ini_sha256']
others=['AR0516','AR0518','AR0519','AR0520','AR0521','AR0811','OH8100'];before={a:payload(GAME/'iee-assets/areas'/a) for a in others}
assert not installer.running_game_processes(),'game or loader running'
dry=installer.install_area_pack(PACK,verify_only=True);assert not dry.dropped and dry.area_id=='AR0517'
result=installer.install_area_pack(PACK);installer.record_lock('AR0517',PACK,GAME)
assert payload(GAME/'iee-assets/areas/AR0517')==payload(PACK)
assert before=={a:payload(GAME/'iee-assets/areas'/a) for a in others}
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')==plan['renderer_sha256']
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==plan['ini_sha256']
v2.write_json(OUT/'installation.json',dict(status=result.status,created_utc=v2.utc_now(),area='AR0517',resref='SPHINCT',occurrence=[497,452],frames=49,
 receipt=result.receipt_path.resolve().relative_to(ROOT).as_posix(),source_pack=plan['pack'],source_run=plan['run'],mask_sha256=plan['mask_sha256'],
 fit_error_x4=1,supersampling=4,guard_x4=0,feather_x4=0,renderer_unchanged=True,ini_unchanged=True,other_area_payloads_preserved=before,
 geometry_centres_cycles_preserved=True,RGB_preserved=True,preview_frame8_exact=True,native_double_feather_avoided=True,ingame_QA='pending-user-retest',release='not-selected'))
# Preserve unrelated CSV rows and historical correction entries verbatim.
registry=ROOT/'animations/index/animation_upscale_registry.csv';lines=registry.read_text(encoding='utf-8-sig').splitlines(keepends=True)
head=next(csv.reader([lines[0]]));note_index=head.index('notes');found=0
for i,line in enumerate(lines):
 if line.startswith('SPHINCT,'):
  fields=next(csv.reader([line]));prefix=fields[note_index].split('Retour AR0517',1)[0]
  fields[note_index]=prefix+"AR0517 2026-10-10 : fondu v3 rejete pour bord melange ; choix utilisateur = preview droite crisp-g0. Actif : SplineFit1 monde x4 SS4/BOX, retrait0/fondu0, masque fixe sur49 frames, registre lie497,452 ; pas de clamp x1 ni double fondu. RGB/centres/cycles/ARE/WED conserves ; AR0517 seulement. Run "+plan['run']+" ; recu "+OUT.relative_to(ROOT).as_posix()+"/installation.json. Installation autorisee ; QA ingame AR0517 ouverte ; AR0516 et autres occurrences inchanges ; aucune release."
  buf=io.StringIO(newline='');csv.writer(buf,lineterminator='\n').writerow(fields);lines[i]=buf.getvalue();found+=1
assert found==1;registry.write_text(''.join(lines),encoding='utf-8')
corrections=ROOT/'animations/index/animation_alpha_corrections.csv';text=corrections.read_text(encoding='utf-8-sig');assert TAG not in text
row=['SPHINCT','AR0517','orifice devant arche',TAG,'world-wed-spline-fit1;SS4-BOX;guard0;feather0;occurrence-binding','0','0','none','unchanged','installed-pending-ingame','',plan['run'],
 'Choix utilisateur = version droite crisp-g0 ; installation 2026-10-10. Preview frame8 reproduite exactement ; 49 frames RGB/centres/cycles conserves. Contour continu sans clamp x1 ; anticrenelage fin seulement ; pont natif contourne par registre lie497,452. Decor/WED/ARE/DLL inchanges. QA ingame ouverte ; aucune release.']
buf=io.StringIO(newline='');csv.writer(buf,lineterminator='\n').writerow(row)
with corrections.open('a',encoding='utf-8',newline='') as stream:
 if text and not text.endswith('\n'):stream.write('\n')
 stream.write(buf.getvalue())
print('Installed and verified AR0517 / SPHINCT / Fit1 SS4 / guard0 fade0; QA pending',flush=True)
