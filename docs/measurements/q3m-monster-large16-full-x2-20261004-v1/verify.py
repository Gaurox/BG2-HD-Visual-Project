"""Seal the completed local/native checks; no installation or QA inference."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
import palette_partner_registry as leaves
import run_creature_sprite_x2 as registry
from q3m_family_witnesses import bmp_palette
from workspace_paths import get_path

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
def result(p):return next(json.loads(x) for x in reversed(p.read_text().splitlines()) if x.startswith('{'))
assert not (HERE/'verification.json').exists(),'new verification required'
production=load(HERE/'production.json');generation=load(HERE/'current-generation.json')
isolated=ROOT/production['pack_directory'];cat=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
idx=registry.KeyIndex(get_path('bg2ee_game_root',required=True));raw,_=idx.resolve(idx.resource_map(1)['MWYV_WS'])
assert file_sha(ROOT/generation['dll']['path'])==generation['dll']['sha256']
white=bmp_palette(raw);white_checked=0;plain_checked=0
for row in cat['directory']:
    shard=cat['shards'][row['shard_index']];path=isolated/Path(shard['registry']).name
    info=leaves.inspect(path,include_frames=True)
    assert info['version']==7 and info['class_profile_id']==8 and info['decode_rule_id']==3
    resource=info['resources'][row['resource_ordinal']]
    assert all('A' not in f and 'S' not in f and 'M' not in f for f in resource['frames'])
    if row['animation_id']=='0xA200':
        assert np.array_equal(resource['profile'].source,white);white_checked+=1
    else:
        if row['animation_id']=='0xA000':assert not np.array_equal(resource['profile'].source[:,:3],white[:,:3])
        plain_checked+=1
assert white_checked==7 and plain_checked==13
native=[result(HERE/name) for name in ('native-isolated.log','native-combined.log')]
assert all(x['passed'] and x['resources']==20 and x['frames']==1692 and x['palette_encodings']==3 for x in native)
assert production['resume']==dict(encoded_cache_hits=production['plan']['unique_encoded_work'])
assert production['resume_torch_import_blocked']
host=(HERE/'host-tests.log').read_text();assert 'Ran 10 tests' in host and '\nOK' in host
fixture=load(HERE/'creatures.json')['fixture'];test=(ROOT/fixture['path']).read_bytes()
assert file_sha(ROOT/fixture['path'])==fixture['sha256'] and test[0x28:0x2A]==b'\0\xa2'
proof=dict(schema='bg2-Large16-local-verification-v1',passed=True,host_tests=10,
    native_isolated=native[0],native_combined=native[1],white_palette_resource='MWYV_WS',
    white_source_palette_verified_leaves=white_checked,ordinary_source_palette_verified_leaves=plain_checked,
    registry_version=7,SDF=False,source_absent_ids=['0xA201','0xA202'],
    duplicate_work_rule='unique compatible colour/source keys; exact acquired hits unchanged; no Torch on resume',
    unique_original_BAM_source_work=production['plan']['unique_original_BAM_source_work'],
    unique_colour_source_work=production['plan']['unique_source_work'],unique_encoded_work=production['plan']['unique_encoded_work'],
    runtime= generation['runtime'],dll=generation['dll'],production=identity(HERE/'production.json'),
    catalog_proof=identity(HERE/'catalog-proof.json'),native_scope=identity(HERE/'native-scope.json'),
    logs=[identity(HERE/name) for name in ('host-tests.log','native-isolated.log','native-combined.log')],
    producer_sources=[identity(ROOT/'pipeline/scripts'/name) for name in ('q3m_family_witnesses.py','palette_q3m_partners.py','palette_partner_registry.py')],
    fixture=fixture,ingame_QA=False,release=False)
write_json(HERE/'verification.json',proof)
print(json.dumps(dict(passed=True,white_leaves=7,native_resources=20,native_frames=1692,encoded_work=production['plan']['unique_encoded_work'],SDF=False)))
