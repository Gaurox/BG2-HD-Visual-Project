"""Record explicit ingame approval of the three installed selected images."""
from pathlib import Path
import copy,json,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as w
import effect_authority as authority
import effect_tracking as tracking
from workspace_paths import get_path
BATCH=ROOT/'effects/batches/projectiles3-production-20261109-v1'
OUT=ROOT/'effects/batches/projectiles3-accepted-20261109-v1'
DECISION='les 3 sont bons, valide-les et passe au raccord de COW avec le sprite déjà produit'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def ev(p):return w.file_evidence(ROOT,p)
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists(),'Accepted evidence immutable';p.write_bytes(w.json_bytes(d))
def main():
 assert not (OUT/'acceptance.json').exists();OUT.mkdir(parents=True,exist_ok=True)
 production=load(BATCH/'production-current-v3.json');install=load(ROOT/'effects/installations/projectiles3-selected-20261109-v1/installation.json')
 game=get_path('bg2ee_game_root',required=True);manifest=game/'iee-assets/effects/manifest.json';m=load(manifest);catalog={r['resref']:r for r in m['resources']};sha=w.sha256_file(manifest)
 before=w.read_csv(ROOT/'effects/index/processing.csv');save(OUT/'processing-before.json',before);bindings=[]
 for a in production['assets']:
  n=a['resref'];resource=catalog[n];assert resource['selected_method']==a['selected_version'] and resource['interpolation_run']==a['interpolation_run']
  pack=load(ROOT/a['pack']/'manifest.json');assert w.sha256_file(ROOT/a['pack']/'manifest.json')==a['pack_manifest_sha256']
  # All installed canonical backings must be exact bytes declared by selected pack.
  installed=[f for f in m['frames'] if f['resref']==n]
  expected={(f['sha256'],tuple(f['physical_size_x4'])) for f in pack['frames']}
  assert {(f['sha256'],tuple(f['physical_size_x4'])) for f in installed}==expected
  for f in installed:assert w.sha256_file(game/'iee-assets/effects'/f['asset'])==f['sha256']
  why=DECISION+'. Validation ingame des trois images sélectionnées, tests visuels ZP3T01/02/03. Portée image/composant observé ; aucune QA de tous les propriétaires PRO, profils, palettes, déplacements ou compagnons alpha non observés déduite.'
  w.accept_asset(ROOT,n,pack_path=a['pack'],decision=why,decision_date='2026-11-09',write=True)
  s=load(ROOT/f'effects/index/selections/{n}.json')
  bindings.append(dict(resref=n,version=a['selected_version'],selected_pack=ev(ROOT/a['pack']/'manifest.json'),selection=ev(ROOT/f'effects/index/selections/{n}.json'),qa=ev(ROOT/s['qa_evidence']['path']),installed_canonical_backings=len(installed)))
 after=w.read_csv(ROOT/'effects/index/processing.csv');old={r['asset_key']:r for r in before};names={a['resref'] for a in production['assets']}
 for r in after:
  previous=old[r['asset_key']]
  if r['asset_key'].rsplit(':',1)[-1] not in names:assert r==previous
  else:assert all(r[k]==previous[k] for k in ['installation_state','installation_receipt','release_state','release_candidate'])
 assert w.sha256_file(manifest)==sha
 save(OUT/'acceptance.json',dict(schema='bg2-effects-batch-user-acceptance-v1',status='accepted',decision_date='2026-11-09',user_decision=DECISION,assets=bindings,source_production=ev(BATCH/'production-current-v3.json'),installation='effects/installations/projectiles3-selected-20261109-v1/installation.json',installed_manifest_sha256=sha,scope='Three observed image components; not full PRO/owner/profile/alpha/movement coverage',game_files_changed=False,release_changed=False))
 p=ROOT/'projectiles/index/work-tracking.json';d=load(p)
 for owner,n in [('BGLRY','BGLRYU'),('SPCL236','SPCL236U'),('TRAPGLPN','SPGLYPHI'),('TRAPGLYP','SPGLYPHI')]:
  node=d['projectiles'].setdefault(owner,{})
  node.setdefault('component_visual_qa',{})['projectiles3-20261109-v1']=dict(state='accepted-assets-only',assets=[n],evidence=['effects/batches/projectiles3-accepted-20261109-v1/acceptance.json'],reviewed_on='2026-11-09',limits='Image tested via isolated VVC; native PRO owner, all profiles/palettes/alpha companions and displacement not inferred.')
 p.write_bytes(w.json_bytes(d))
 q=tracking.queue(ROOT,limit=3);completion=load(ROOT/'effects/index/completion.json');completion.update(q['completion'],status='complete',accepted_x4=424,accepted_native=6,processing_sha256=w.sha256_file(ROOT/'effects/index/processing.csv'),extension_acceptance='effects/batches/projectiles3-accepted-20261109-v1/acceptance.json',scope='497 entries closed: initial494 plus3 user-accepted projectile image components. No global PRO/installation/release acceptance inferred.')
 assert completion['remaining']==0 and completion['total']==497
 with authority.guard(ROOT,True):authority.commit(ROOT,{'effects/index/completion.json':w.json_bytes(completion)})
 (OUT/'README.md').write_text('# Projectiles3 acceptés —2026-11-09\n\n- BGLRYU/SPCL236U SeedVR7B ; SPGLYPHI xBR4X. Décision utilisateur explicite après installation et test des3images.\n- Sélections effets liées aux packs exacts ; backings canoniques installés vérifiés. QA composants seule ; aucun retest demandé ni QA globale des4PRO/profils/palettes/compagnons/déplacement déduite.\n- `acceptance.json` ; autres494lignes, installation/release et fichiers du jeu conservés.0inférence.\n',encoding='utf-8')
 print('Accepted3: SeedVR BGLRYU/SPCL236U, xBR SPGLYPHI. Effects497/497 closed; owner QA distinct.')
if __name__=='__main__':main()
