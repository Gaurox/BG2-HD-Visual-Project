"""Read-only verification of the installed Ogre delta; persist a new factual snapshot."""
import configparser,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path

def require(ok,message):
    if not ok:raise ValueError(message)
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def identity(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path),bytes=path.stat().st_size)
def native_result(path):
    return next(json.loads(line) for line in reversed(path.read_text(encoding='utf-8',errors='replace').splitlines()) if line.startswith('{'))

require(not (HERE/'installation-verification.json').exists(),'new verification version required')
game=get_path('bg2ee_game_root',required=True)
baseline=load(HERE/'baseline.json');generation=load(HERE/'current-generation.json')
receipt_path=HERE/'ingame-installation/active-test.json';receipt=load(receipt_path)
require(receipt['status']=='installed-pending-ingame-qa','installation incomplete')
for relative,expected in (('BaldurReal.exe',baseline['executable_sha256']),
                         ('InfinityEngine-Enhancer.dll',generation['dll']['sha256']),
                         ('InfinityEngine-Enhancer.ini',baseline['ini_sha256']),
                         (baseline['catalog_relative'],generation['catalog']['sha256'])):
    require(file_sha(game/relative)==expected.lower(),'installed identity differs: '+relative)
for item in baseline['preserved']:
    require(file_sha(game/item['relative_path'])==item['sha256'],'preserved asset differs')
for item in receipt['new_shards']:
    require(file_sha(game/item['registry'])==item['sha256'].lower(),'installed Ogre leaf differs')
for item in receipt['backups']:
    require(file_sha(HERE/'work/before'/item['file'])==item['sha256'].lower(),'backup identity differs')
config=configparser.ConfigParser(interpolation=None,strict=False);config.read(game/'InfinityEngine-Enhancer.ini')
require(all(config.get('Shaders',key)==value for key,value in baseline['box_configuration'].items()),'world filter differs')
parent=registry.read_sealed_catalog_index(HERE/'work/before/CreatureSprites-XN.catalog',baseline['parent_catalog_sha256'])
active=registry.read_sealed_catalog_index(game/baseline['catalog_relative'],generation['catalog']['sha256'])
require(active['components'][:len(parent['components'])]==parent['components'] and
        active['shards'][:len(parent['shards'])]==parent['shards'] and
        active['animations'][:81]==parent['animations'] and
        active['directory'][:len(parent['directory'])]==parent['directory'],'inherited native contract differs')
require(len(active['animations'])==82 and active['total_resources']==4556 and active['total_frames']==1585413,'installed totals differ')
work=ROOT/'sprite/.work/q3m-monster-large-full-x2-20261003-v1'
results={kind:native_result(work/('native-'+kind+'-tests.log')) for kind in ('isolated','combined')}
require(all(r['passed'] and r['resources']==7 and r['frames']==434 for r in results.values()),'native tests incomplete')
creatures=load(HERE/'creatures.json')['creatures']
require(len(creatures)==22 and (HERE/'CLUA.txt').read_text().splitlines()==[c['clua'] for c in creatures],'CLUA scope differs')
snapshot=dict(schema='bg2-monster-large-installed-verification-v1',
              role='installation-facts-not-ingame-QA-or-release',verified_at_utc=receipt['installed_at_utc'],
              installation_receipt=identity(receipt_path),generation=identity(HERE/'current-generation.json'),
              family='monster_large',animation_ids=['0x9000'],scale=2,resources=7,frames=434,
              native_tests=results,inherited_animations_unchanged=81,inherited_routes_unchanged=len(parent['directory']),
              active_animations=82,active_resources=4556,active_frames=1585413,new_leaf_sha256_verified=7,
              unchanged_assets_sha256_verified=len(baseline['preserved']),ini_byte_identical=True,
              backup_sha256_verified=True,clua_count=22,ingame_QA=False,release=False)
write_json(HERE/'installation-verification.json',snapshot)
print(json.dumps(snapshot))
