"""Accept explicit final50 QA, bound to exact installed primary tests; no game/release writes."""
import copy,sys,json,hashlib,struct
from pathlib import Path
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as w
from workspace_paths import get_path
BATCH=ROOT/'effects/batches/lot50-magic-water-production-20261108-v1'
OUT=ROOT/'effects/batches/magic-water50-accepted-20261109-v1'
DATE='2026-11-09';DECISION='06 et34 validés, tout est bon. Mets à jour le suivi et committe.'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def ev(p):return w.file_evidence(ROOT,p)
def save(p,d):
 assert not p.exists(),'Final evidence immutable'
 p.write_bytes(w.json_bytes(d))
def main():
 OUT.mkdir(parents=True,exist_ok=True);assert not (OUT/'acceptance.json').exists()
 if not (OUT/'processing-before.csv').exists():(OUT/'processing-before.csv').write_bytes((ROOT/'effects/index/processing.csv').read_bytes())
 before={r['asset_key']:r for r in w.read_csv(OUT/'processing-before.csv',w.PROCESSING_FIELDS)}
 current=load(BATCH/'current-production.json');prod=load(ROOT/current['path']);assert w.sha256_file(ROOT/current['path'])==current['sha256'];jobs=copy.deepcopy(prod['assets']);assert len(jobs)==44
 # The accepted main test20 was SeedVR (M3SPCS), not its retained xBR comparison.
 seed=load(BATCH/'alternatives/spcsprai-seedvr7b-test-20261108-v1/result.json')
 for i,a in enumerate(jobs):
  if a['resref']=='SPCSPRAI':jobs[i]={**a,**seed['asset'],**seed['result'], 'resref':'SPCSPRAI','method':'seedvr2_7b_int8_convrot.safetensors'}
 game=get_path('bg2ee_game_root',required=True);mp=game/'iee-assets/effects/manifest.json';installed=load(mp);installed_sha=w.sha256_file(mp);registry_sha=w.sha256_file(game/'iee-assets/effects/EffectAnimations-X4.registry');assert registry_sha==installed['registry_sha256']
 resources={r['resref']:r for r in installed['resources']};backings=defaultdict(list)
 for f in installed['frames']:backings[f['resref']].append(f)
 controls={r['asset']:r for r in installed['runtime_vvc_controllers']};bindings=[];primary=[]
 for a in jobs:
  n=a['resref'];assert w.sha256_file(ROOT/a['pack']/'manifest.json')==a['pack_manifest_sha256'];stage=ROOT/'effects/ressources'/n/'runs'/a['interpolation_run']/'02-interpolation';m=load(stage/'manifest.json')
  code=f"ZMWT{a['ordinal']:02d}";c=controls['override/'+code+'.vvc'];assert w.sha256_file(game/c['asset'])==c['sha256'];ref=c['bam'];resource=resources[ref];assert resource['production_bam']==n and resource['interpolation_run']==a['interpolation_run'],(n,resource['interpolation_run'],a['interpolation_run'])
  kind='straight_raw_rgba_x4' if resource['rgb_encoding']=='straight' else 'raw_rgba_x4';sources={str((stage/f[kind]).resolve()):f for f in m['frames']}
  for f in backings[ref]:
   sf=sources[str((ROOT/f['source']).resolve())];assert f['sha256']==sf[kind+'_sha256'] and f['physical_size_x4']==sf['physical_size_x4'] and f['source_centre_x1']==sf['centre_x1']
  runtime={f['resource_frame']:f for f in backings[ref]}
  for cnum,seq in enumerate(resource['timeline']['timeline_frame_indices_by_cycle']):
   if not seq:continue
   v=next(v for v in m['timing']['cycles'] if v['cycle']==cnum and v['loop_closed'])
   assert len(seq)==len(v['timeline_frame_indices'])
   for rid,mid in zip(seq,v['timeline_frame_indices']):assert runtime[rid]['sha256']==m['frames'][mid][kind+'_sha256']
  carrier=next(r for r in installed['runtime_bam_carriers'] if r['resref']==ref);assert carrier['sha256']==m['runtime_carrier']['sha256'] and w.sha256_file(game/carrier['asset'])==carrier['sha256']
  bindings.append(dict(resref=n,runtime_ref=ref,interpolation_run=a['interpolation_run'],pack=a['pack'],pack_manifest_sha256=a['pack_manifest_sha256'],backings=len(backings[ref]),controller=c,source_carrier=carrier,loop_phase_pixels_exact=True))
  primary.append(dict(ordinal=a['ordinal'],resref=n,vvc=code,runtime_ref=ref,mode='x4'))
 natives=copy.deepcopy(prod['native_masks']);assert len(natives)==6
 for a in natives:
  n=a['resref'];code=f"ZMWT{a['ordinal']:02d}";c=controls['override/'+code+'.vvc'];ref=c['bam'];carrier=next(r for r in installed['runtime_bam_carriers'] if r['resref']==ref)
  assert w.sha256_file(ROOT/a['source'])==a['source_sha256'];assert w.sha256_file(game/carrier['asset'])==a['source_sha256'];assert w.sha256_file(game/c['asset'])==c['sha256']
  raw=(game/c['asset']).read_bytes();cycle=struct.unpack_from('<I',raw,0x68)[0]-1
  if n=='SPSDRAE2':assert cycle==1
  bindings.append(dict(resref=n,runtime_ref=ref,mode='native',source_sha256=a['source_sha256'],controller=c,source_carrier=carrier,test_cycle=cycle,diagnostic_colors_or_scale_accepted=False))
  primary.append(dict(ordinal=a['ordinal'],resref=n,vvc=code,runtime_ref=ref,mode='native'))
 assert len(bindings)==50 and {r['ordinal'] for r in primary}==set(range(1,51))
 accepted=[];reused=[]
 for a in jobs+natives:
  n=a['resref'];native=n in {r['resref'] for r in natives};selection=ROOT/f'effects/index/selections/{n}.json'
  if selection.exists():
   s=load(selection);assert s['mode']==('native' if native else 'x4');assert native or s['selected_run']==a['interpolation_run'];assert w.sha256_file(ROOT/s['qa_evidence']['path'])==s['qa_evidence']['sha256'];reused.append(n)
  else:
   if not native:
    rows={r['asset_key'].rsplit(':',1)[-1]:r for r in w.read_csv(ROOT/'effects/index/processing.csv',w.PROCESSING_FIELDS)};r=rows[n]
    if r['spatial_run']!=a['spatial_run']:w.register_run(ROOT,n,'spatial',a['spatial_run'],write=True)
    rows={r['asset_key'].rsplit(':',1)[-1]:r for r in w.read_csv(ROOT/'effects/index/processing.csv',w.PROCESSING_FIELDS)}
    if rows[n]['interpolation_run']!=a['interpolation_run']:w.register_run(ROOT,n,'interpolation',a['interpolation_run'],write=True)
   why=DECISION+' Validation globale explicite du lot50 testé ; masques conservés natifs, aucun témoin rouge/agrandi retenu. Tous les profils/modes et les vrais propriétaires natifs ne sont pas déduits comme testés.'
   w.accept_asset(ROOT,n,native=native,pack_path=None if native else a['pack'],decision=why,decision_date=DATE,write=True)
  s=load(selection);accepted.append(dict(resref=n,mode=s['mode'],selected_run=s['selected_run'],selection=ev(selection),qa=ev(ROOT/s['qa_evidence']['path'])))
  print('accepted',n,'native' if native else a['interpolation_run'],flush=True)
 names={a['resref'] for a in jobs+natives};changed=[]
 for r in w.read_csv(ROOT/'effects/index/processing.csv',w.PROCESSING_FIELDS):
  n=r['asset_key'].rsplit(':',1)[-1];old=before[r['asset_key']]
  if n not in names:assert r==old;continue
  assert r['qa_state']==('native' if n in {a['resref'] for a in natives} else 'passed')
  assert all(r[k]==old[k] for k in ['installation_state','installation_receipt','release_state','release_candidate'])
  changed.append(n)
 assert w.sha256_file(mp)==installed_sha and w.sha256_file(game/'iee-assets/effects/EffectAnimations-X4.registry')==registry_sha
 result=dict(schema='bg2-effects-batch-user-acceptance-v1',status='accepted',decision_date=DATE,user_decision=DECISION,accepted_count=50,x4_count=44,native_count=6,methods=dict(Counter(a['method'] for a in jobs)),reused_prior_qa=reused,accepted=accepted,final_assets=jobs,native_assets=natives,runtime_bindings=bindings,primary_tests=sorted(primary,key=lambda r:r['ordinal']),source_production=ev(ROOT/current['path']),installed_manifest_sha256=installed_sha,installed_registry_sha256=registry_sha,limits=['SPCSPRAI accepted SeedVR is installed/tested under M3SPCS; canonical SPCSPRAI retains xBR comparison, separate future canonical routing required.','SP_DEMGT runtime alias exists but independent QA not inferred.','WTRBODY2 accepted earlier with native map unconfirmed.','No individual proof of every once/loop/profile or native consumer coverage inferred.'],game_files_changed=False,installation_release_unchanged=True,gpu_used=False)
 save(OUT/'acceptance.json',result);save(OUT/'verification.json',dict(passed=True,accepted_count=50,runtime_primary_bindings=50,other_rows_preserved=True,installation_release_unchanged=True,gpu_used=False))
 (OUT/'README.md').write_text('# Magie/eau50 — accepté le2026-11-09\n\n- Décision explicite : «06 et34 validés, tout est bon. Mets à jour le suivi et committe.»\n- 50acceptations :44x4/30FPS +6masques natifs ;36SeedVR7B,8xBR.06xBR4X/CPU-motion30 ;13vert corrigé CPU ;34natif cycle1 visible ;35natif.47nouvelles décisions,3QA antérieures conservées (13/35/45).\n- `acceptance.json` lie les packs sélectionnés aux octets des50tests installés ; `verification.json` : autres lignes, installation et release conservées.\n- SPCSPRAI : **SeedVR accepté via M3SPCS/ZMWT20** ; canoniqueSPCSPRAI conserve le comparatifxBR. Ne pas confondre présence des2versions et routage canonique.\n- AliasSP_DEMGT installé mais pas de QA indépendante inventée. WTRBODY2 validé sansmap native confirmée ; aucune couverture réelle desowners/profils déduite.\n- GPU en pause ; aucune installation/release modifiée pendant acceptation.\n',encoding='utf-8')
 for p in [ROOT/'effects/README.md',ROOT/'effects/REPRISE.md']:
  text=p.read_text(encoding='utf-8-sig');i=text.index('\n')+1;note='\n**Magie/eau50 accepté — 2026-11-09** : [décision et preuves](batches/magic-water50-accepted-20261109-v1/README.md).44x4/30FPS +6natifs,36SeedVR7B/8xBR ;06xBR/CPU30,13vert corrigé,34cycle1,35natif.50liaisons primaires installées exactes ;47QA nouvelles/3antérieures préservées. SPCSPRAI SeedVR accepté sousaliasM3SPCS/ZMWT20, canonique reste comparatifxBR ; aliasSP_DEMGT nonvalidé indépendamment. Installation/release et autres lignes conservées ; GPUenpause.\n\n';p.write_text(text[:i]+note+text[i:].lstrip('\n'),encoding='utf-8')
 print('ACCEPTED50:',len(reused),'prior QA reused; game/release unchanged; GPU paused.',flush=True)
if __name__=='__main__':main()
