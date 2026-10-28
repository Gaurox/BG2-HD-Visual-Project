"""Transactional DLL-only candidate; native projectiles and image bytes stay exact."""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import install_renderer_candidate as tx
OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-secondary-links-20261028-v1'
BUILD=ROOT/'build/iee-projectile-secondary-links-20261028-v1'
GAME=tx.get_path('bg2ee_game_root',required=True)
PRESERVE=['InfinityEngine-Enhancer.ini','BaldurReal.exe','override/fpDraw.glsl',
 'override/fpSprite.glsl','override/fpSELECT.glsl','iee-assets/creature-sprites/CreatureSprites-XN.catalog',
 'iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry']
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def snap(p):return dict(bytes=p.stat().st_size,sha256=tx.sha256_file(p))
def save(p,x):
 with p.open('x',encoding='utf-8') as f:f.write(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main(mode):
 global OUT
 test_log=BUILD/'final-tests.log'
 cloud_wave1=mode.endswith('-v6')
 if cloud_wave1:
  OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-clouds-wave1-20261028-v6'
  test_log=BUILD/'clouds-wave1-v6-tests.log'
  mode=mode[:-3]
 composite=mode.endswith('-v5')
 if composite:
  OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-native-underlay-20261028-v5'
  test_log=BUILD/'composite-v5-tests-final.log'
  mode=mode[:-3]
 cloud_alpha=mode.endswith('-v4')
 if cloud_alpha:
  OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-cloud-alpha-20261028-v4'
  test_log=BUILD/'cloud-alpha-v4-tests.log'
  mode=mode[:-3]
 flight_mask=mode.endswith('-v3')
 if flight_mask:
  OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-flight-mask-20261028-v3'
  test_log=BUILD/'flight-mask-v3-tests.log'
  mode=mode[:-3]
 if mode.endswith('-v2'):
  OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-secondary-links-padding-20261028-v2'
  mode=mode[:-3]
 OUT.mkdir(parents=True,exist_ok=True)
 if mode=='prepare':
  assert not (OUT/'before.json').exists()
  m=load(GAME/'iee-assets/effects/manifest.json');assert m['resource_count']==537
  expected='3477E7211680CF1CF7F067A471A003EBC0A2ECAA4C994136ED257A3AA59A872A'
  assert tx.sha256_file(GAME/'iee-assets/effects/manifest.json')==expected
  assert '100% tests passed' in test_log.read_text()
  if flight_mask:
   assert tx.sha256_file(GAME/'InfinityEngine-Enhancer.dll')=='2043B799AC90B32585AD09CFBFE89E32EF4ED744F8F94D25474AE86C959E81DB'
   assert 'iee_effect_occlusion_tests' in test_log.read_text()
  if cloud_alpha:
   assert tx.sha256_file(GAME/'InfinityEngine-Enhancer.dll')=='2370067272AC3CA909D86D05CF90656A24A5C0E84719049DF4817DC54DB67E7B'
   assert 'iee_effect_surface_owner_tests' in test_log.read_text()
   alpha=load(ROOT/'projectiles/analysis/six-tests-cloud-alpha-20261028-v1/evidence.json')['cloud_pair']
   assert alpha['pairs']==425 and alpha['RGB_identical'] and alpha['identical_cycles_timeline_geometry_encoding']
   assert any(r['resref']=='X58CLK' for r in m['resources'])
  if composite:
   assert tx.sha256_file(GAME/'InfinityEngine-Enhancer.dll')=='CEFBCB1986379DC23F526A2862E42DD75863D7FB96B55FACC0126DC46AB99C20'
   for name in ('iee_effect_surface_owner_tests','iee_effect_occlusion_tests',
                'iee_effect_texture_cache_tests','iee_tests'):
    assert name in test_log.read_text()
  if cloud_wave1:
   assert tx.sha256_file(GAME/'InfinityEngine-Enhancer.dll')=='36541C5F212077AD247658DC60CBC6998D4594414D9E4028CDCA4F8DACE80CF5'
   pairs=load(ROOT/'projectiles/analysis/validation-vague1-clouds-20261028-v1/evidence.json')['cloud_pairs']
   valid={p['native']:p for p in pairs if p.get('eligible')}
   assert set(valid)=={'SPCLOUDS','SPDFOGA'}
   assert all(p['all_SHA_RGB_geometry_cycles_timeline_encoding_carriers_ok'] for p in valid.values())
   assert 'iee_effect_surface_owner_tests' in test_log.read_text()
  assert (BUILD/'Release/InfinityEngine-Enhancer.dll').exists()
  header='generated/iee/water_route2_registry.generated.h'
  assert tx.sha256_file(BUILD/header)==tx.sha256_file(ROOT/'build/iee-effects-gl-flush-state-20261017-v1'/header)
  native_pros=load(ROOT/'projectiles/analysis/audit-complet-243-20261028-v1/summary.json')
  overrides=sorted((GAME/'override').glob('*.pro'))
  save(OUT/'before.json',dict(utc=datetime.now(timezone.utc).isoformat(),
   files={n:snap(GAME/n) for n in ['InfinityEngine-Enhancer.dll']+PRESERVE},
   pro_files={p.name:snap(p) for p in overrides},
   source_sha256={p.relative_to(ROOT).as_posix():tx.sha256_file(p) for p in
    (ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee').rglob('*') if p.suffix in ('.cpp','.h')},
   test_log=str(test_log.relative_to(ROOT)),test_log_sha256=tx.sha256_file(test_log)))
  c=OUT/'candidate';c.mkdir();shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll',c/'InfinityEngine-Enhancer.dll')
  shutil.copy2(GAME/'InfinityEngine-Enhancer.ini',c/'InfinityEngine-Enhancer.ini')
  print(OUT);return
 if mode!='install':raise SystemExit('prepare|install')
 assert not (OUT/'installation.json').exists()
 before=load(OUT/'before.json')
 for n,old in before['files'].items():assert snap(GAME/n)==old,n
 for n,old in before['pro_files'].items():assert snap(GAME/'override'/n)==old,n
 for n,h in before['source_sha256'].items():assert tx.sha256_file(ROOT/n)==h,n
 if flight_mask or cloud_alpha or composite or cloud_wave1:assert tx.sha256_file(ROOT/before['test_log'])==before['test_log_sha256']
 tx.ensure_game_stopped(tx.running_game_processes)
 result=tx.install_candidate(OUT/'candidate',game_root=GAME,backup_root=OUT/'backups')
 tx.verify_transaction(result.receipt_path,game_root=GAME)
 for n in PRESERVE:assert snap(GAME/n)==before['files'][n],n
 for n,old in before['pro_files'].items():assert snap(GAME/'override'/n)==old,n
 assert snap(GAME/'InfinityEngine-Enhancer.dll')==snap(OUT/'candidate/InfinityEngine-Enhancer.dll')
 save(OUT/'installation.json',dict(status='installed-awaiting-runtime-evidence',
  utc=datetime.now(timezone.utc).isoformat(),receipt=str(result.receipt_path.relative_to(ROOT)),
  dll=snap(GAME/'InfinityEngine-Enhancer.dll'),previous_dll=before['files']['InfinityEngine-Enhancer.dll'],
  resources=537,image_files_changed=False,pro_files_changed=False,inference_jobs=0,
  correction='SPCLOUDS-SPDFOGA-to-existing-native-palette-alpha-aliases' if cloud_wave1 else
    'last-HD-layer-with-exact-native-prefix' if composite else
    'SPCLOUDK-to-existing-X58CLK-native-palette-alpha' if cloud_alpha else
    'per-FX-surface-mask-isolation' if flight_mask else 'secondary-links',
  tests=before.get('test_log'),
  preserved={n:snap(GAME/n) for n in PRESERVE},ingame_validated=False,release_changed=False))
 print('DLL installed; 537 resources and all native PRO bytes preserved')
if __name__=='__main__':main(sys.argv[1])
