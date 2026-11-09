"""Scoped COW188 sprite-to-projectile bridge, preserving the accepted sprite assets."""
from pathlib import Path
from dataclasses import asdict
import copy,importlib.util,json,shutil,struct,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
spec=importlib.util.spec_from_file_location('cow_delta_transaction',ROOT/'pipeline/recipes/projectiles3-production-20261109-v1/install_ingame.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
tx,w,authority=base.tx,base.w,base.authority
load,save,rel,digest,sha=base.load,base.save,base.rel,base.digest,base.sha
GAME=base.GAME;OUT=ROOT/'effects/installations/cow-sprite-bridge-20261109-v1';CANDIDATE=OUT/'candidate'
REUSE=ROOT/'projectiles/analysis/cow-sprite-reuse-20261109-v1'
base.OUT=OUT;base.CANDIDATE=CANDIDATE

def prepare():
 assert not (OUT/'plan.json').exists(),'Prepared candidate immutable; use install or a new version'
 OUT.mkdir(parents=True,exist_ok=True);CANDIDATE.mkdir(exist_ok=True)
 result=load(REUSE/'reuse.json');assert result['neural_inference']==result['temporal_interpolation']==0
 unit=base.validate_pack(ROOT/result['pack']);assert unit.manifest_sha256==result['pack_manifest_sha256']
 assert load(REUSE/'native-route.json')['same_existing_CProjectileBAM_hook']
 old=load(GAME/'iee-assets/effects/manifest.json');registry=(GAME/'iee-assets/effects/EffectAnimations-X4.registry').read_bytes();assert digest(registry)==old['registry_sha256']
 assert not any(r['resref']=='ACOWG1' for r in old['resources'])
 assert not (GAME/'override/ACOWG1.bam').exists(),'Native source already overridden; inspect before adapting'
 protected=['InfinityEngine-Enhancer.ini','BaldurReal.exe','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl','iee-assets/creature-sprites/CreatureSprites-XN.catalog']
 leaf='iee-assets/creature-sprites/CreatureSprites-XN-'+result['source_shard_sha256']+'.registry';protected.append(leaf)
 assert sha(GAME/leaf)==result['source_shard_sha256']
 before=dict(manifest_sha256=sha(GAME/'iee-assets/effects/manifest.json'),registry_sha256=digest(registry),dll=base.snap(GAME/'InfinityEngine-Enhancer.dll'),preserved={n:base.snap(GAME/n) for n in protected},owner_overrides={},projectile188_before=copy.deepcopy(load(ROOT/'projectiles/index/work-tracking.json')['engine_projectiles'].get('188')))
 save(OUT/'before.json',before);m=copy.deepcopy(old);files=[]
 def add(name,raw=None,source=None):
  assert not (GAME/name).exists() or name in base.REPLACED,name
  p=tx.managed_path(CANDIDATE,name,create_parents=True)
  if source is not None:
   if p.exists():assert base.snap(p)==base.snap(source)
   else:shutil.copy2(source,p)
  elif p.exists():assert p.read_bytes()==raw
  else:p.write_bytes(raw)
  files.append(dict(name=name,**base.snap(p)))
 resource=copy.deepcopy(unit.resources[0]);resource.update(reuse_evidence=rel(REUSE/'reuse.json'),source_pack=rel(unit.root),source_pack_sha256=unit.manifest_sha256)
 m['resources'].append(resource)
 for frame in unit.frames:
  f=copy.deepcopy(frame);f['frame']=len(m['frames']);m['frames'].append(f);add('iee-assets/effects/'+f['asset'],source=unit.root/f['asset'])
 reg=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(m['resources']),0)+registry[24:]+unit.registry_records
 assert reg[24:len(registry)]==registry[24:]
 assert m['resources'][:old['resource_count']]==old['resources'] and m['frames'][:old['frame_count']]==old['frames']
 code='ZCOWV';vvc=bytearray(base.builder.make_vvc('ACOWG1',0,True,15,len(resource['cycles'][0]['frame_indices']),False));struct.pack_into('<I',vvc,0x5c,180)
 add('override/'+code+'.vvc',bytes(vvc));m.setdefault('runtime_vvc_controllers',[]).append(dict(asset='override/'+code+'.vvc',bam='ACOWG1',bytes=len(vvc),sha256=digest(vvc),purpose='COW sprite reused: isolated native-cycle0 display, no damage'))
 m.update(resource_count=len(m['resources']),frame_count=len(m['frames']),registry_bytes=len(reg),registry_sha256=digest(reg));m.setdefault('source_packs',[]).append(dict(resref='ACOWG1',domain='sprite',source_sprite_scale=2,adapter=rel(REUSE/'reuse.json'),inference=0,interpolation=0))
 add('iee-assets/effects/EffectAnimations-X4.registry',reg);add('iee-assets/effects/manifest.json',w.json_bytes(m));add('InfinityEngine-Enhancer.dll',source=base.BUILD/'Release/InfinityEngine-Enhancer.dll')
 shutil.copy2(REUSE/'runtime-contracts.tsv',OUT/'runtime-contracts.tsv');test=ROOT/'.tmp/projectiles3-20261109-v1/cow-tests.log';assert '100% tests passed, 0 tests failed out of 5' in test.read_text();shutil.copy2(test,OUT/'engine-tests.log')
 base.probe(CANDIDATE/'iee-assets/effects','candidate-native-loader.log')
 sources=['src/iee/hooks.cpp','src/iee/core/effect_secondary_scope.h','src/iee/core/effect_texture_alias.h','tests/effect_surface_owner_tests.cpp']
 save(OUT/'plan.json',dict(files=files,new_resources=1,new_backings=22,old_resources=old['resource_count'],old_backings=old['frame_count'],resources=m['resource_count'],backings=m['frame_count'],manifest_sha256=sha(CANDIDATE/'iee-assets/effects/manifest.json'),new_dll=base.snap(CANDIDATE/'InfinityEngine-Enhancer.dll'),native_contracts=result['contracts'],source_sha256={n:sha(base.SOURCE/n) for n in sources},reuse=result,source_sprite_untouched=True,carrier_override=False,ingame_qa=False))
 (OUT/'CLUA.md').write_text('# COW188 — réemploi du sprite accepté\n\nRelancer via InfinityLoader. Utiliser une partie de test non sauvegardée, deux personnages espacés.\n\n## Image isolée sans dégâts —12secondes\n\n```lua\nC:Eval(\'CreateVisualEffectObject("ZCOWV",Player1)\',0)\n```\n\n## Vrai projectile COW\n\nLe sort stock SPWI299 lance PROJECTL188 / missile189 ; cible vivante éloignée, sort offensif.\n\n```lua\nC:Eval(\'ForceSpellRES("SPWI299",Player2)\',0)\n```\n\nSource : ACOWG1 Q3m V7 x2 déjà accepté côté sprites.22frames/40cycles natifs ; support effet x4 par duplication2× exacte, aucune inférence ni interpolation ajoutée. Le déplacement reste natif. La QA du sprite n’est pas une QA du projectile COW.\n',encoding='utf-8')
 print('READY COW: 1 resource /22 backings,',result['contracts'],'native contracts, accepted sprite and native BAM untouched.')

def finish():
 receipt=load(OUT/'transaction.json');plan=load(OUT/'plan.json');assert receipt['status']=='installed';base.preserved(load(OUT/'before.json'))
 assert sha(GAME/'iee-assets/effects/manifest.json')==plan['manifest_sha256'];assert base.snap(GAME/'InfinityEngine-Enhancer.dll')==plan['new_dll']
 p=ROOT/'projectiles/index/work-tracking.json';d=load(p);node=d['engine_projectiles'].setdefault('188',{})
 node.update(integration=dict(state='installed-shared-BAM-render-awaiting-observation',evidence=[rel(OUT/'installation.json'),rel(REUSE/'native-route.json')],scope='ACOWG1 source sprite x2 reused through existing CProjectileBAM Render; 40 native cycles, no movement interpolation'),installation=dict(state='installed',evidence=[rel(OUT/'transaction.json')],resources=['ACOWG1']),notes='COW188/missile189: accepted Q3m x2 pixels reused. No new inference/interpolation. Native palette neutral, shadow alpha127, exact native centres/cycles. Sprite QA retained; projectile QA awaits user test.')
 p.write_bytes(w.json_bytes(d))
 save(OUT/'installation.json',dict(status='installed-awaiting-COW-ingame-review',transaction=rel(OUT/'transaction.json'),source_reuse=rel(REUSE/'reuse.json'),source_sprite_scale=2,effect_storage_scale=4,scale_adapter='exact nearest2 duplication of accepted x2 pixels',native_contracts_candidate_and_installed=plan['native_contracts']*2,resources=plan['resources'],backings=plan['backings'],old_resources_preserved=plan['old_resources'],old_backings_preserved=plan['old_backings'],dll=plan['new_dll'],engine_tests='5/5 passed',source_sprite_catalogue_leaf_and_QA_unchanged=True,native_BAM_untouched=True,new_inference=0,new_interpolation=0,movement_unchanged=True,game_launched=False,ingame_validated=False,release_changed=False))
 (OUT/'README.md').write_text('# COW188 raccordé pour test —2026-11-09\n\n- ACOWG1 :22frames/40cycles Q3m V7 x2 acceptés, palette native neutre/shadow127 ; copie2× exacte vers support effet x4, pas une nouvelle production modèle.\n- Même chemin natif CProjectileBAM Render0x233f20. Whitelist étendue ; source BAM, catalogue/feuille/QAs sprites et déplacement conservés.\n- `CLUA.md` : ZCOWV isolé sans dégâts ; SPWI299 surPlayer2 pour le vrai projectile. QA COW en attente ; trois images précédentes acceptées conservées.\n- Reçu réversible `transaction.json`, sauvegardes `before/`. Aucun GPU ni release.\n',encoding='utf-8')
 print('INSTALLED COW188 bridge. Test ZCOWV or native SPWI299. Source sprites and accepted3 preserved.')

def restore():
 tx.ensure_game_stopped(tx.running_game_processes);base.rollback(load(OUT/'transaction.json'))
 before=load(OUT/'before.json')['projectile188_before'];p=ROOT/'projectiles/index/work-tracking.json';d=load(p)
 if before is None:d['engine_projectiles'].pop('188',None)
 else:d['engine_projectiles']['188']=before
 p.write_bytes(w.json_bytes(d))

base.finish=finish
if __name__=='__main__':{'prepare':prepare,'install':base.install,'restore':restore}[sys.argv[1]]()
