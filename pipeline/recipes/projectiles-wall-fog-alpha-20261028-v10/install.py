"""Route normal BDWOFOGA draws to the already-installed native-alpha alias; DLL only."""
from pathlib import Path
from dataclasses import asdict
import sys,json,shutil
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import install_renderer_candidate as tx
GAME=tx.get_path('bg2ee_game_root',required=True)
OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-wall-fog-alpha-20261028-v10'
BUILD=ROOT/'build/iee-projectile-secondary-links-20261028-v1'
PROOF=ROOT/'projectiles/analysis/mur-brouillard-alpha-20261028-v1'
PRESERVE=['InfinityEngine-Enhancer.ini','BaldurReal.exe','override/BDWOFOGA.bam','override/X58WFOG.bam',
 'override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl',
 'iee-assets/creature-sprites/CreatureSprites-XN.catalog',
 'iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry']
def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def snap(p):return asdict(tx.snapshot_file(p))
def save(p,d):
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);assert not(OUT/'before.json').exists()
 assert '100% tests passed, 0 tests failed out of 3' in (BUILD/'wall-fog-v10-tests.log').read_text()
 old=js(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-flight-phases-20261028-v9/installation.json');assert snap(GAME/'InfinityEngine-Enhancer.dll')==old['dll']
 proof=js(PROOF/'alias-correspondence.json');assert proof['geometry_centres_equal'] and proof['visible_and_hidden_RGB_identical'] and proof['profile_rates_durations_equal'] and proof['loader_contracts']==2720
 assert 'checked: 2720' in (PROOF/'native-contracts.log').read_text()
 m=js(GAME/'iee-assets/effects/manifest.json');assert m['resource_count']==538 and m['frame_count']==62500
 before=dict(files={n:snap(GAME/n) for n in PRESERVE+['InfinityEngine-Enhancer.dll']},PROs={p.name:snap(p) for p in (GAME/'override').glob('*.pro')},source_sha256={p.relative_to(ROOT).as_posix():tx.sha256_file(p) for p in (ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee').rglob('*') if p.suffix in ('.h','.cpp')},proof_sha256=tx.sha256_file(PROOF/'alias-correspondence.json'))
 save(OUT/'before.json',before);candidate=OUT/'candidate';candidate.mkdir()
 shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll',candidate/'InfinityEngine-Enhancer.dll');shutil.copy2(GAME/'InfinityEngine-Enhancer.ini',candidate/'InfinityEngine-Enhancer.ini')
 shutil.copy2(BUILD/'wall-fog-v10-tests.log',OUT/'tests.log');print('Prepared DLL-only normal-alpha alias correction')
def install():
 assert not (OUT/'installation.json').exists();b=js(OUT/'before.json')
 tx.ensure_game_stopped(tx.running_game_processes)
 for n,old in b['files'].items():assert snap(GAME/n)==old,n
 for n,old in b['PROs'].items():assert snap(GAME/'override'/n)==old,n
 for n,h in b['source_sha256'].items():assert tx.sha256_file(ROOT/n)==h,n
 assert tx.sha256_file(PROOF/'alias-correspondence.json')==b['proof_sha256']
 result=tx.install_candidate(OUT/'candidate',game_root=GAME,backup_root=OUT/'backups');tx.verify_transaction(result.receipt_path,game_root=GAME)
 for n,old in b['files'].items():
  if n!='InfinityEngine-Enhancer.dll':assert snap(GAME/n)==old,n
 for n,old in b['PROs'].items():assert snap(GAME/'override'/n)==old,n
 save(OUT/'installation.json',dict(status='installed-awaiting-wall-fog-alpha-retest',utc=tx.utc_now(),receipt=str(result.receipt_path.relative_to(ROOT)),dll=snap(GAME/'InfinityEngine-Enhancer.dll'),previous_dll=b['files']['InfinityEngine-Enhancer.dll'],resources=538,frames=62500,normal_alias='BDWOFOGA->X58WFOG',Blended_profile_unchanged=True,manifest=snap(GAME/'iee-assets/effects/manifest.json'),registry=snap(GAME/'iee-assets/effects/EffectAnimations-X4.registry'),images_changed=False,PROs_unchanged=True,gameplay_or_motion_changed=False,inference_jobs=0,release_changed=False,ingame_validated=False))
 print('Installed V10; normal BDWOFOGA uses existing X58WFOG; no image/PRO/metadata changes')
if __name__=='__main__':{'prepare':prepare,'install':install}[sys.argv[1]]()
