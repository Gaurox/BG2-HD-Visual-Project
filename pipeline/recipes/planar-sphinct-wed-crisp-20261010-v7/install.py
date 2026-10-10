"""Install scoped renderer + four cells; preserve AR0516 frames and AR0517 reference."""
from pathlib import Path
import sys,csv,io,hashlib
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'));sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import run_animation_upscale_30fps_v2 as v2
import area_animation_area_test as installer
import install_renderer_candidate as renderer
from workspace_paths import get_path
from bg2lib import load_key,resolve_resource
TAG='planar-sphinct-wed-crisp-20261010-v7';OUT=ROOT/'animations/batches'/TAG;GAME=get_path('bg2ee_game_root')
plan=v2.load_json(OUT/'plan.json');tests=v2.load_json(OUT/'native-tests.json');gpu=v2.load_json(OUT/'gpu-tests.json')
audit=v2.load_json(ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v6/analysis-all-phases.json')
assert tests['passed'] and gpu['passed'] and gpu['existing_shader_modes_0_1_2_byte_identical']
assert v2.load_json(OUT/'checks.json')['passed'] and v2.load_json(OUT/'embedded-masks.json')['RLE_roundtrip_exact']
assert not (OUT/'installation.json').exists()
def payload(area):
 return {p.name:v2.sha256_file(p) for p in (GAME/'iee-assets/areas'/area).iterdir() if p.is_file() and (p.name==v2.REGISTRY_NAME or p.suffix=='.rgba')}
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')==plan['renderer_sha256']
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==plan['ini_sha256']==tests['ini_sha256']
for a in plan['areas']:assert payload(a['area'])==a['before_payload'],a['area']+' drift'
bifs,entries=load_key()
def effective_digest(name,typ,ext):
 p=GAME/'override'/f'{name}.{ext}'
 if p.exists():return v2.sha256_file(p)
 loc=next(loc for n,t,loc in entries if n.upper()==name and t==typ);data,_=resolve_resource(bifs,loc)
 return hashlib.sha256(data).hexdigest()
def geometry_digests():
 return {a:dict(ARE=effective_digest(a,1010,'ARE'),WED=effective_digest(info['wed_ref'],1001,'WED')) for a,info in audit['areas'].items()}
geometry=geometry_digests()
for a,info in audit['areas'].items():assert geometry[a]==dict(ARE=info['are_sha256'],WED=info['wed_sha256'])
protected=['AR0516','AR0517','AR0811','OH8100'];before={a:payload(a) for a in protected}
prepared=[a for a in plan['areas'] if a['status']=='prepared'];assert {a['area'] for a in prepared}=={'AR0518','AR0519','AR0520','AR0521'}
renderer.ensure_game_stopped(renderer.running_game_processes)
for a in prepared:
 dry=installer.install_area_pack(ROOT/a['pack'],verify_only=True);assert not dry.dropped
result=renderer.install_candidate(OUT/'candidate');renderer.verify_transaction(result.receipt_path)
progress=dict(status='installing',renderer_receipt=result.receipt_path.resolve().relative_to(ROOT).as_posix(),area_receipts={})
v2.write_json(OUT/'installation-progress.json',progress)
for a in prepared:
 area=a['area'];pack=ROOT/a['pack'];installed=installer.install_area_pack(pack);installer.record_lock(area,pack,GAME)
 expected={p.name:v2.sha256_file(p) for p in pack.iterdir() if p.is_file() and (p.name==v2.REGISTRY_NAME or p.suffix=='.rgba')}
 assert payload(area)==expected
 progress['area_receipts'][area]=installed.receipt_path.resolve().relative_to(ROOT).as_posix();v2.write_json(OUT/'installation-progress.json',progress)
assert {a:payload(a) for a in protected}==before
assert geometry_digests()==geometry and v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')==tests['dll_sha256']
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==plan['ini_sha256']
v2.write_json(OUT/'installation.json',dict(status='installed',created_utc=v2.utc_now(),renderer_receipt=progress['renderer_receipt'],area_receipts=progress['area_receipts'],
 dll_sha256=tests['dll_sha256'],run=plan['run'],areas=['AR0516','AR0517','AR0518','AR0519','AR0520','AR0521'],
 AR0516_mode='three exact-occurrence x4 world masks in renderer; original registry and194 frames unchanged',AR0516_positions=[[1520,1287],[1529,1447],[2948,1776]],
 AR0517='accepted v5 reference payload byte-identical',cells='SPHINCT49 frames per cell; own position-bound mask',
 protected_area_payloads=before,ARE_WED_digests_unchanged=geometry,ini_preserved=True,geometry_centres_cadence_preserved=True,
 memory_limit_preserved=True,additional_world_mask_CPU_bytes=3*640*480*4,QA='AR0517 accepted reference; changed AR0516/18/19/20/21 pending user ingame',release='not-selected'))
progress['status']='installed';v2.write_json(OUT/'installation-progress.json',progress)
registry=ROOT/'animations/index/animation_upscale_registry.csv';lines=registry.read_text(encoding='utf-8-sig').splitlines(keepends=True)
head=next(csv.reader([lines[0]]));ni=head.index('notes');found=0
for i,line in enumerate(lines):
 if line.startswith('SPHINCT,'):
  fields=next(csv.reader([line]));fields[ni]='x4 TimedTimeline30fps. AR0517 crisp v5 accepte utilisateur le2026-10-10 et conserve octet-identique. Extension installee AR0518-AR0521 : WED AR0517 commun, Fit1 monde x4 SS4/BOX retrait0/fondu0,49 frames/cellule, registre lie aux positions ARE exactes. AR0516 : WED propre analyse sur49 phases ; masques renderer aux positions1520,1287(P46),1529,1447(P48+49),2948,1776(P89) ; fallback original et autres ressources inchanges ; positions2263,1103 et SPHINCT2 sans intersection. Pas de duplication des frames AR0516 ni hausse limite512MiB. DLL scoped ; modes precedents GPU identiques. Run '+plan['run']+' ; recu '+OUT.relative_to(ROOT).as_posix()+'/installation.json. QA ouverte pour les occurrences modifiees AR0516 et AR0518-AR0521 ; aucune propagation de validation ni release.'
  buf=io.StringIO(newline='');csv.writer(buf,lineterminator='\n').writerow(fields);lines[i]=buf.getvalue();found+=1
assert found==1;registry.write_text(''.join(lines),encoding='utf-8')
corrections=ROOT/'animations/index/animation_alpha_corrections.csv';old=corrections.read_text(encoding='utf-8-sig');assert TAG not in old
rows=[['SPHINCT','AR0518;AR0519;AR0520;AR0521','orifice devant arche',TAG,'world-wed-spline-fit1;SS4-BOX;guard0;feather0;occurrence-binding','0','0','none','unchanged','installed-pending-ingame','',plan['run'],
 'Extension autorisee du rendu AR0517 ; masques monde recales aux positions501,451/500,451/501,451/499,451.49 frames par cellule ; RGB/centres/cycles exacts ; decor/ARE/WED inchanges ; QA propre aux quatre cellules requise.'],
 ['SPHINCT','AR0516','branches aux trois occurrences',TAG,'renderer-world-wed-spline-fit1;SS4-BOX;guard0;feather0;scope-three-occurrences','0','0','none','unchanged','installed-pending-ingame','',plan['run'],
 'Positions1520,1287/1529,1447/2948,1776 ; polygones46/48+49/89 du WED actif.3 masques x4 en renderer ; registry194 frames conservees ; pas de duplication ni hausse de limite memoire.147 draws GPU controles ; modes precedents byte-identiques. Retest ingame requis ; autres occurrences et SPHINCT2 inchanges.']]
buf=io.StringIO(newline='');writer=csv.writer(buf,lineterminator='\n');writer.writerows(rows)
with corrections.open('a',encoding='utf-8',newline='') as stream:
 if old and not old.endswith('\n'):stream.write('\n')
 stream.write(buf.getvalue())
print('Installed planar correction:4 cells +3 AR0516 occurrences; AR0517 reference and source geometry preserved; QA pending',flush=True)
