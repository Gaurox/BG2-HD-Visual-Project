"""One-time migration from the reviewed UI scope; refuses to overwrite the tracker."""
import csv,json,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
DEST=ROOT/'interface/index/work-tracking.json'
if DEST.exists():raise SystemExit('Tracker already exists; edit per-resource states, do not reinitialize.')
def rel(p):return p.relative_to(ROOT).as_posix()
def state(s,e=(),**kw):return dict(state=s,evidence=list(e),**kw)
analysis='interface/analysis/large-surfaces-20261110-v1'
inventory=json.loads((ROOT/analysis/'inventory.json').read_text(encoding='utf-8'))
active=[r for r in inventory['resources'] if r['status'].startswith('keep')]
base=ROOT/'interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50'
selector=base/'selection-des-trois-jeux'
qa='interface/menus-options-bg2ee/integration/selector-startup-20261110-v1/accepted-20261110-v1.json'
receipt='interface/menus-options-bg2ee/integration/selector-startup-20261110-v1/README.md'
outputs={
 'LOGOSOA':[base/'upscale-topaz-recovery-v2-d50'/f'LOGOSOA-frame-{i:02}-x4.png' for i in range(2)],
 'LOGOTOB':[selector/'upscale-topaz-recovery-v2-d50'/f'LOGOTOB-frame-{i:02}-x4.png' for i in range(2)],
 'LOGOTBP':[selector/'upscale-topaz-recovery-v2-d50'/f'LOGOTBP-frame-{i:02}-x4.png' for i in range(2)],
 'TITLE':[base/'upscale-topaz-recovery-v2-d50'/f'TITLE-frame-{i:02}-x4.png' for i in range(4)],
 'START2EE':[base/'upscale-topaz-recovery-v2-d50/START2EE-background-x4.png'],
 'START3EE':[selector/'upscale-topaz-recovery-v2-d50/START3EE-background-x4.png'],
 'BIGLOGO':[base/'upscale-topaz-recovery-v2-d50/BIGLOGO-options-frame-0-x4.png']}
rows=[]
for r in sorted(active,key=lambda r:r['resref']):
 n=r['resref'];menus=r.get('menus',[])
 category='illustrations' if r['kind']=='BAM' else 'menu-panels'
 if n.startswith(('CH','GUIDRM','BPEND')) or n in ('TOSCEND','ULGOTHST','ARRIVE','LEAVE'):category='chapter-art'
 if n.startswith(('GUIW','GUWB','GMW','GMPW','GU10','GU20')):category='hud-decoration'
 if 'MAP' in n:category='map-art-or-frame'
 production=state('not-assessed',note='No inference of missing production from absence in these two current menu folders.')
 if n in outputs:
  evidence=[];sizes=[]
  for f in outputs[n]:
   assert f.is_file(),f
   with Image.open(f) as im:assert im.width%4==0 and im.height%4==0;sizes.append(list(im.size))
   evidence.append(rel(f))
  production=state('partial-existing-x4' if n=='BIGLOGO' else 'complete-existing-x4',evidence,output_sizes=sizes,recipe='Topaz Gigapixel 8.4.1 Recovery v2 Detail50 x4 preserve',coverage='frame 0 only; frames 1/2 remain to qualify/produce' if n=='BIGLOGO' else 'all native frames; reuse existing PNGs, not a new QA')
 observed=n in ('START3EE','LOGOSOA','LOGOTOB','LOGOTBP')
 rows.append(dict(resref=n,kind=r['kind'],category=category,selection_evidence=analysis+'/decisions.json',source=state('resolved',[analysis+'/inventory.json'],container=r.get('source'),dimensions=[r['width'],r['height']],frames=r['frames'],pages=r.get('pages',[])),usage=state('observed-selector-normal' if observed else 'static-reference' if menus else 'variant-to-qualify',menus=menus,ui_lines=r.get('ui_lines',[])),production=production,qa=state('accepted-observed-normal',[qa],limits='One startup, normal state only; hover states not separately accepted.') if observed else state('not-reconciled',note='Historical menu-group QA retained separately; not automatically mapped to resource/frame units.'),installation=state('recorded-selector-installation',[receipt],note='2026-11-10 receipt, not a fresh live filesystem audit.') if observed else state('not-reconciled'),release=state('not-reconciled',note='Existing release is unchanged. No resource count derived from two legacy menu groups.'),constraints=['preserve soft native alpha; RGB inference separate'] if n=='DONATE' else [],next_action='reuse-and-qualify-reduced-atlas' if n in outputs and n!='BIGLOGO' else 'complete-missing-large-medallion-variants' if n=='BIGLOGO' else 'qualify-usage-and-existing-production'))
old={}
for path in ['interface/index/resources.csv','interface/gameplay-hud-bg2ee/index/resources.csv','interface/fonts/index/resources.csv']:
 for r in csv.DictReader((ROOT/path).open(encoding='utf-8-sig')):old.setdefault(r['resref'],dict(resref=r['resref'],kind=r.get('format', r.get('formats', r.get('type', 'BAM'))),source_index=path,reason='outside-selected-visual-scope',historical_state='preserved'))
for r in inventory['resources']:
 if not r['status'].startswith('keep'):old[r['resref']]=dict(resref=r['resref'],kind=r['kind'],source_index=analysis+'/inventory.json',reason=r['status'],historical_state='preserved')
for n in ['STARTMBT','MAINEEAN','GUILS10','GUILS20']:
 old[n]=dict(resref=n,kind='BAM',source_index='interface/README.md',reason='buttons-or-text-controls-retired-from-active-production',historical_state='preserved')
for r in rows:old.pop(r['resref'],None)
with (HERE/'out-of-scope.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['resref','kind','source_index','reason','historical_state']);w.writeheader();w.writerows(sorted(old.values(),key=lambda r:r['resref']))
data=dict(schema='bg2-ui-work-tracking-v1',updated_on='2026-11-10',selection_inventory=analysis+'/inventory.json',selection_decisions=analysis+'/decisions.json',excluded_catalogue='interface/tracking/out-of-scope.csv',unit='One logical native MOS/BAM resref, all frames for complete production; never atlas pages or menu groups.',historical_groups=dict(state='preserved-not-converted',count=2,source='Website progress snapshot before scope migration: 2 produced/QA/payload menu groups over 1672 source resources; incompatible units.',evidence=['interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/README.md',qa]),limits=['Visual scope acceptance is not upscale QA.','204 selected resrefs include historical variants; current runtime use remains to qualify.','Unknown production/QA/release is not a negative verdict on historical accepted assets.','No release payload or installed asset modified by tracking migration.'],resources=rows)
DEST.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Active',len(rows),'outside',len(old))

