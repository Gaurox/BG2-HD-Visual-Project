"""Plan remaining tests for existing productions only; never writes the game."""
from pathlib import Path
from datetime import datetime,timezone
import collections,csv,hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from bg2lib import load_key,resolve_resource
from projectile_tracking import validate_tracking
GAME=get_path('bg2ee_game_root',required=True)
BASE=ROOT/'projectiles/analysis/audit-complet-243-20261028-v1'
def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def save(n,data):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
def savecsv(n,data):
 with (OUT/n).open('x',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
if (OUT/'summary.json').exists():raise SystemExit('Existing plan: create a new version')
pros=rows(BASE/'projectiles-243.csv');components=rows(BASE/'components.csv')
usage=rows(ROOT/'projectiles/analysis/20261028-v2/usage.csv')
bifs,entries=load_key();key={(n.upper(),t):loc for n,t,loc in entries}
def read(n,t,ext):
 p=GAME/'override'/f'{n}.{ext}'
 return p.read_bytes() if p.exists() else resolve_resource(bifs,key[n,t])[0]
manifest=js(GAME/'iee-assets/effects/manifest.json');catalog={r['resref'] for r in manifest['resources']}
baseline=js(BASE/'summary.json')
assert hashlib.sha256((GAME/'iee-assets/effects/manifest.json').read_bytes()).hexdigest().upper()==baseline['manifest_sha256']
owner_rows=[]
for r in pros:
 family=set(r['closure'].split(';'))
 leaves=[c for c in components if c['pro'] in family and c['activity'] not in ('disabled','metadata')]
 produced={c['resource'] for c in leaves if c['production']=='produced' and c['resource'] in catalog}
 missing={c['resource'] for c in leaves if c['state'] in ('not-produced','missing-resource')}
 if r['verdict']=='hd-linked-static':state='technical-static-validated-no-new-systematic-test'
 elif produced:state='continue-existing-produced-components-only'
 elif r['verdict']=='native-only-no-image-job':state='native-no-HD-job-no-test-requested'
 else:state='native-dispatch-to-identify-no-new-production'
 owner_rows.append(dict(pro=r['pro'],state=state,produced_components=';'.join(sorted(produced)),
  excluded_missing_components=';'.join(sorted(missing)),baseline_verdict=r['verdict']))
waves=[
 (1,'SPWI213','CLOUD','Nuage puant','SPCLOUDS : fond, opacite, dispersion et disparition'),
 (1,'SPWI614','1PDEATHF','Brume mortelle','SPDFOGA : transparence, contour et disparition'),
 (1,'SPWI810','1PINCIND','Nuage incendiaire','SPINCINA : feu, fumee et zones persistantes'),
 (1,'SPWI812','PWILT','Fletrissure','SPHORWIL/SPHORWIA : impact, dispersion et transparence'),
 (2,'SPPR250','WRITHING','Brouillard putride','WRITHING : vol, dispersion et couleur'),
 (2,'SPPR450','BDSPFIRE','Feu spirituel','BDSFIRET/H/A : vol, impact et dispersion'),
 (2,'SPPR609','FDAWN','Aube illusoire','FDAWNX/A : explosion et dispersion'),
 (2,'SPWI925','COMET','Comete','SPCOMTRV/EXP : vol et explosion'),
 (3,'SPWI312','SPARBLNP','Ralentissement','Anneau natif SHAREA enfant197, vol deja produit'),
 (3,'SPWI116','SLEEP','Sommeil','Anneau natif SHAREA/BMP SHAREA3 enfant198'),
 (3,'SPWI302','SPARGRNP','Delivrance de la magie','Anneau natif SHAREA/BMP SHAREA4 enfant199'),
 (3,'SPPR416','SPARMANP','Manteau de terreur','Anneau natif SHAREA/BMP SHAREA5 enfant200'),
 (3,'SPPR101','SPARPUPA','Benediction','Anneau natif SHAREA/BMP SHAREA6 enfant201'),
 (4,'SPWI953','FIREBLIC','Malediction de Selune','FIREBICX/R : variante coloree d explosion'),
 (4,'SPCL239','SPCL239','Faisceau de la Conscience Solaire','SPCL239R : anneau et dispersion'),
 (4,'SPDD03','DDBREAT','Souffle','HDFBRER : cone/anneau natif'),
]
matrix=[]
bypro={r['pro']:r for r in pros}
for wave,spell,pro,label,watch in waves:
 raw=read(spell,1006,'spl');refs=[u for u in usage if u['resource']==spell and u['format']=='SPL']
 digest=hashlib.sha256(raw).hexdigest().upper()
 assert refs and all(u['source_sha256']==digest and u['projectile']==pro and
  struct.unpack_from('<H',raw,int(u['offset'],16))[0]==int(u['raw_missile_id']) for u in refs),(spell,pro)
 family=set(bypro[pro]['closure'].split(';'))
 covered=[c for c in components if c['pro'] in family and c['production']=='produced']
 assert covered
 matrix.append(dict(wave=wave,spell=spell,pro=pro,label=label,watch=watch,
  assets=';'.join(sorted({c['resource'] for c in covered})),spell_sha256=digest,
  command=f'C:Eval(\'ForceSpellRES("{spell}",Player2)\',0)',
  state='ready-to-test' if wave==1 else 'queued-not-yet-requested',
  limit='observe native palette dispatch; not proof of HD secondary rings' if wave==3 else 'runtime and visual acceptance pending'))
savecsv('owners-243.csv',owner_rows);savecsv('tests.csv',matrix);save('tests.json',matrix)
decision=dict(schema='bg2-projectile-technical-decision-v1',recorded_utc=datetime.now(timezone.utc).isoformat(),
 scope='100 complete static HD chains accepted technically without systematic individual ingame retest, per user agreement',
 projectiles=[r['pro'] for r in owner_rows if r['state']=='technical-static-validated-no-new-systematic-test'],
 evidence=['projectiles/analysis/audit-complet-243-20261028-v1/summary.json',
  'projectiles/analysis/audit-complet-243-20261028-v1/physical-checks.json',
  'projectiles/analysis/verifications-ciblees-20261028-v1/summary.json'],
 limits=['No visual ingame acceptance invented','Other QA/install/release states remain independent'])
assert len(decision['projectiles'])==100
save('technical-100.json',decision)
tracking_path=ROOT/'projectiles/index/work-tracking.json';tracking=js(tracking_path)
evidence='projectiles/analysis/validation-produits-suite-20261028-v1/technical-100.json'
for name in decision['projectiles']:
 item=tracking['projectiles'].setdefault(name,{})
 if 'integration' not in item:item['integration']=dict(state='verified-static',evidence=[evidence])
validate_tracking(tracking,{r['pro'] for r in pros})
tracking_path.write_text(json.dumps(tracking,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
summary=dict(owner_states=dict(collections.Counter(r['state'] for r in owner_rows)),
 no_inference=True,no_game_writes=True,planned_tests=len(matrix),current_wave=1,
 missing_outputs_excluded=['BGLRYU','SPCL236U','SPGLYPHI'],missing_resource_excluded=['MAGMIS'],
 scope='Only existing produced components. Mixed chains may be tested for their produced parts, not closed over missing parts.',
 preserve_previous_tests=['PFIRE2/FIREBAT','CLOUDKIL/X58CLK','TRAPSKUL/SKLT/SKLH','CHROMORB/SPCHRORB','INSEC2','ICESTORM','LIGHTCHA sequence2'],
 remaining_nonstandard=['TSKULLNP has no direct SPL reference; use static reuse or a later verified driver, not an invented spell command',
  'SHAREA child202 has no verified direct SPL in inventory','LIGHTCHA declared cycle9 requires native semantics review; previous cycle2 test preserved',
  'Item-only projectiles and native FIREBALL enum paths require additional targeted drivers/observations'])
save('summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
