"""DLL-only final-flight-phase diagnostics; rendering, timing and images stay exact."""
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,json,shutil,struct,subprocess,sys,zlib
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import install_renderer_candidate as tx
GAME=tx.get_path('bg2ee_game_root',required=True)
OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-flight-phases-20261028-v9'
BUILD=ROOT/'build/iee-projectile-secondary-links-20261028-v1'
PRESERVE=['InfinityEngine-Enhancer.ini','BaldurReal.exe','override/SHAREA.bam',
 'override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl',
 'iee-assets/creature-sprites/CreatureSprites-XN.catalog',
 'iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry']
def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def snap(p):return asdict(tx.snapshot_file(p))
def save(p,d):
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);assert not(OUT/'before.json').exists()
 tests=(BUILD/'flight-phase-v9-tests.log').read_text();assert '100% tests passed, 0 tests failed out of 5' in tests
 old=js(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-sharea-palettes-20261028-v8/installation.json')
 assert snap(GAME/'InfinityEngine-Enhancer.dll')==old['dll']
 assert snap(GAME/'iee-assets/effects/manifest.json')==js(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-sharea-palettes-20261028-v8/before.json')['files']['iee-assets/effects/manifest.json']
 assert snap(GAME/'iee-assets/effects/EffectAnimations-X4.registry')==js(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-sharea-palettes-20261028-v8/before.json')['files']['iee-assets/effects/EffectAnimations-X4.registry']
 m=js(GAME/'iee-assets/effects/manifest.json');assert m['resource_count']==538
 r=next(r for r in m['resources'] if r['resref']=='SHAREA');assert r['rgb_encoding']=='premultiplied' and r['frame_count']==22
 native=(GAME/'override/SHAREA.bam').read_bytes();po=struct.unpack_from('<I',native,16)[0]
 source=zlib.decompress((ROOT/'effects/ressources/SHAREA/source.bam').read_bytes()[12:]);so=struct.unpack_from('<I',source,16)[0]
 assert native[po:po+1024]==source[so:so+1024]
 frames=[f for f in m['frames'] if f['resref']=='SHAREA'];assert len(frames)==22
 for f in frames:
  assert snap(GAME/'iee-assets/effects'/f['asset'])==dict(bytes=f['bytes'],sha256=f['sha256'])
 files={n:snap(GAME/n) for n in PRESERVE+['InfinityEngine-Enhancer.dll']}
 for n in ['SHAREA1','SHAREA2','SHAREA3','SHAREA4','SHAREA5','SHAREA6']:
  p=GAME/f'override/{n}.bmp'
  if p.exists():files[f'override/{n}.bmp']=snap(p)
 files.update({'iee-assets/effects/'+f['asset']:snap(GAME/'iee-assets/effects'/f['asset']) for f in frames})
 source_paths=[p for p in (ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee').rglob('*') if p.suffix in ('.h','.cpp')]
 save(OUT/'before.json',dict(files=files,PROs={p.name:snap(p) for p in (GAME/'override').glob('*.pro')},source_sha256={p.relative_to(ROOT).as_posix():tx.sha256_file(p) for p in source_paths},SHAREA_images=22,resource_count=538))
 candidate=OUT/'candidate';candidate.mkdir()
 for n in ['InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini']:
  shutil.copy2(BUILD/'Release'/n if n.endswith('.dll') else GAME/n,candidate/n)
 shutil.copy2(BUILD/'flight-phase-v9-tests.log',OUT/'tests.log')
 for p in ['effect_surface_owner_tests.cpp','effect_texture_cache_tests.cpp','effect_sharea_palette_fixtures.h']:
  assert (ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tests'/p).exists()
 print('Prepared DLL-only candidate;22existingSHAREA images verified;538resources unchanged')
def install():
 before=js(OUT/'before.json');assert not (OUT/'installation.json').exists()
 for n,old in before['files'].items():assert snap(GAME/n)==old,n
 for n,old in before['PROs'].items():assert snap(GAME/'override'/n)==old,n
 for n,h in before['source_sha256'].items():assert tx.sha256_file(ROOT/n)==h,n
 tx.ensure_game_stopped(tx.running_game_processes)
 result=tx.install_candidate(OUT/'candidate',game_root=GAME,backup_root=OUT/'backups')
 tx.verify_transaction(result.receipt_path,game_root=GAME)
 for n,old in before['files'].items():
  if n!='InfinityEngine-Enhancer.dll':assert snap(GAME/n)==old,n
 for n,old in before['PROs'].items():assert snap(GAME/'override'/n)==old,n
 assert snap(GAME/'InfinityEngine-Enhancer.dll')==snap(OUT/'candidate/InfinityEngine-Enhancer.dll')
 save(OUT/'installation.json',dict(status='installed-awaiting-one-flight-phase-test',utc=datetime.now(timezone.utc).isoformat(),receipt=str(result.receipt_path.relative_to(ROOT)),dll=snap(GAME/'InfinityEngine-Enhancer.dll'),previous_dll=before['files']['InfinityEngine-Enhancer.dll'],resources=538,SHAREA_images_preserved=22,image_files_changed=False,PROs_unchanged=True,metadata_unchanged=True,release_changed=False,inference_jobs=0,ingame_validated=False))
 print('Installed flight trace V9; no image/metadata/PRO/release changes')
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='install':install()
 else:raise SystemExit('prepare|install')
