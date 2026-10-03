"""Seal trial runtime and installation entry points after native/GPU checks."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
old=HERE.parent/'q3m-ankheg-alpha-light-x2-20261004-v1'
p=load(HERE/'production.json');v=load(HERE/'verification.json');baseline=load(HERE/'baseline.json')
assert v['V9_SDF']['passed'] and load(ROOT/v['GPU']['path'])['passed']
log=(HERE/'native-composition.log').read_text();assert 'SDF composite golden cases passed: 48' in log
assert not (HERE/'current-generation.json').exists()
write_json(HERE/'composition-verification.json',dict(passed=True,cases=48,native_log=identity(HERE/'native-composition.log'),
    native_harness=identity(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tests/palette_partner_tests.cpp'),
    oracle=identity(ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1/isolated/sdf-composite.oracle'),ingame_QA=False))
runtime=load(old/'runtime.json');runtime.pop('reused_V8_runtime_compatibility_proof',None)
runtime['runtime_id']='iee-q3m-v9-ankheg-sdf-x2-20261004-v1';runtime['dll']=v['dll']
cap=runtime['capabilities']['creature_sprite_xn_catalog'];cap['shard_registry_versions'].append(9)
cap['frame_storage'].append('q3m-v9-padded-u8-signed-distance-and-u32-nearest-material')
cap['SDF']=dict(native_kind=0,scale=2,colour_profile=8,decode_rule=3,pad_x2=6,distance_step_x2=1/16,
    screen_coverage_samples=64,shader_contract='IEE_CREATURE_SDF_CONTRACT_V1',required_filter='CatmullRom',
    scope='monster_ankheg trial',extreme_minification='smoothstep when footprint exceeds two x2 texels')
for entry in runtime['shaders']:
    current=identity(ROOT/entry['path']);entry.update(sha256=current['sha256'],bytes=current['bytes'])
runtime['source_provenance']=[v[k] for k in ('source','shader_bridge','leaf_writer','SDF_encoder','reference_processor')]
runtime['verification']=identity(HERE/'verification.json');runtime['composition_verification']=identity(HERE/'composition-verification.json')
runtime['installation']['mask_recipe']=p['recipe']
write_json(HERE/'runtime.json',runtime)
generation=dict(schema='bg2-ankheg-Q3m-SDF-V9-current-v1',role='production-not-QA-installation-or-release',family='monster_ankheg',
    animation_ids=['0x3000'],resources=12,frames=516,scale=2,registry_version=9,colour='K6-four-partners-eight-levels-unchanged',
    mask_recipe=p['recipe'],generation_dir='sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1/combined',
    catalog=p['catalog'],production=identity(HERE/'production.json'),runtime=identity(HERE/'runtime.json'),dll=v['dll'],
    host_verification=identity(HERE/'verification.json'),composition_verification=identity(HERE/'composition-verification.json'),
    replaces_trial=identity(old/'current-generation.json'),reference_offline=identity(HERE.parent/'q3m-ankheg-sdf-offline-x2-20261004-v1/trial.json'),
    state='produced-host-verified-ready-to-install',ingame_QA=False,release=False)
write_json(HERE/'current-generation.json',generation)
s=(old/'install.ps1').read_text()
s=s.replace('q3m-ankheg-alpha-light-x2-20261004-v1','q3m-ankheg-sdf-ingame-x2-20261004-v1').replace('bg2-ankheg-alpha','bg2-ankheg-sdf')
s=s.replace('registry_version -ne 8','registry_version -ne 9').replace('registry_version=8','registry_version=9').replace('$shard.version -ne 8','$shard.version -ne 9')
s=s.replace('V8_alpha','V9_SDF').replace('native_alpha','native_SDF').replace('Unexpected alpha scope','Unexpected SDF scope')
s=s.replace("if (-not $verified.source_support_preserved -or $verified.physical_pixels_cleared -ne 0) { throw 'Alpha topology verification incomplete.' }", "if (-not (Read-JsonFile (Join-Path $PSScriptRoot 'composition-verification.json')).passed) { throw 'Native layering incomplete.' }")
s=s.replace('$verified.mask_processor','$verified.SDF_encoder').replace('$verified.source,$verified.SDF_encoder,$verified.leaf_writer', '$verified.source,$verified.SDF_encoder,$verified.leaf_writer,$generation.composition_verification,$verified.GPU')
s=s.replace('Assert-Identity $dllTarget $baseline.dll_sha256\nforeach', '''Assert-Identity $dllTarget $baseline.dll_sha256
$runtime=Read-JsonFile (Resolve-WorkspaceInput $generation.runtime.path -RequireExisting)
foreach ($shader in $baseline.replaced_shaders) { Assert-Identity (Resolve-ChildPath $game $shader.relative_path -RequireExisting) $shader.sha256 }
foreach ($shader in $runtime.shaders) { Assert-Identity (Resolve-WorkspaceInput $shader.path -RequireExisting) $shader.sha256 }
foreach''')
s=s.replace('$receipt=[ordered]@{', '''foreach ($shader in $baseline.replaced_shaders) {
    $target=Resolve-ChildPath $game $shader.relative_path -RequireExisting
    $backup=Resolve-ChildPath $backupRoot $shader.relative_path
    Copy-FileAtomic $target $backup
    Assert-Identity $backup $shader.sha256
}
$receipt=[ordered]@{''')
s=s.replace(' new_shards=@($pack.new_shards);', ' shaders=@($runtime.shaders); parent_shaders=@($baseline.replaced_shaders)\n new_shards=@($pack.new_shards);')
s=s.replace('    $published=$true', '''    foreach ($shader in $baseline.replaced_shaders) { Assert-Identity (Resolve-ChildPath $game $shader.relative_path -RequireExisting) $shader.sha256 }
    $published=$true''')
s=s.replace('    Copy-FileAtomic (Resolve-WorkspaceInput $generation.catalog.path', '''    foreach ($shader in $runtime.shaders) {
        Copy-FileAtomic (Resolve-WorkspaceInput $shader.path -RequireExisting) (Resolve-ChildPath $game $shader.target)
        Assert-Identity (Resolve-ChildPath $game $shader.target -RequireExisting) $shader.sha256
    }
    Copy-FileAtomic (Resolve-WorkspaceInput $generation.catalog.path''')
s=s.replace('        Copy-FileAtomic $dllBackup $dllTarget', '''        Copy-FileAtomic $dllBackup $dllTarget
        foreach ($shader in $baseline.replaced_shaders) {
            Copy-FileAtomic (Resolve-ChildPath $backupRoot $shader.relative_path -RequireExisting) (Resolve-ChildPath $game $shader.relative_path)
            Assert-Identity (Resolve-ChildPath $game $shader.relative_path -RequireExisting) $shader.sha256
        }''')
s=s.replace('Installed Ankheg light alpha:', 'Installed Ankheg adaptive SDF:')
(HERE/'install.ps1').write_text(s,encoding='utf-8',newline='\n')
print(json.dumps(dict(catalog=generation['catalog']['sha256'],dll=generation['dll']['sha256'],ready=True)))
