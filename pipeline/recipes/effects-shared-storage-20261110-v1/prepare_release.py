"""Register a new local release; do not touch the installed game or historical packs."""
import copy,csv,shutil,sys
from pathlib import Path
from common import ROOT,OUT,RELEASE,load,save,sha,rel,evidence

def main():
 assert not (OUT/'prepare-receipt.json').exists()
 names=['release.json','renderer-bundle.json','runtime-compatibility.json','effect-release-candidates.json','sprite-release-candidates.json']
 before={name:load(RELEASE/'manifests'/name) for name in names};save(OUT/'manifests-before.json',before)
 bundle=RELEASE/'release-inputs/renderer/iee-0.1.0-alpha.11';snapshot=RELEASE/'release-inputs/renderer/iee-0.1.0-alpha.11-source'
 assert not bundle.exists() and not snapshot.exists()
 old=before['renderer-bundle.json'];old_snapshot=ROOT/old['source_tree']
 shutil.copytree(old_snapshot,snapshot)
 source=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
 for name in ['src/iee/effect_animation_x4_registry.cpp','src/iee/core/effect_storage_index.h','tests/effect_animation_x4_registry_tests.cpp']:
  dest=snapshot/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,dest)
 files=[]
 for f in old['files']:
  origin=RELEASE/'bg2hd/renderer'/f['path'];assert sha(origin)==f['sha256']
  src=ROOT/'build/iee-projectile-secondary-links-20261028-v1/Release/InfinityEngine-Enhancer.dll' if f['path']=='InfinityEngine-Enhancer.dll' else origin
  dest=bundle/f['path'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
  files.append(dict(path=f['path'],bytes=dest.stat().st_size,sha256=sha(dest)))
 dll=next(f for f in files if f['path']=='InfinityEngine-Enhancer.dll');assert dll['sha256']!=next(f for f in old['files'] if f['path']==dll['path'])['sha256']
 renderer=dict(old,bundle_id='iee-0.1.0-alpha.11',source_tree=rel(snapshot),files=files)
 renderer['build_environment']['command']='cmake --build build/iee-projectile-secondary-links-20261028-v1 --config Release --target InfinityEngine-Enhancer iee_effect_animation_x4_registry_tests iee_effect_texture_cache_tests'
 renderer['validation_required'] += ['Exact-byte shared storage: representative ingame streaming/masking smoke pending; no new image QA inferred']
 save(OUT/'renderer-source-inventory.json',dict(source=rel(snapshot),files={p.relative_to(snapshot).as_posix():sha(p) for p in snapshot.rglob('*') if p.is_file()},dll=dll))
 compat=copy.deepcopy(before['runtime-compatibility.json'])
 compat['renderer']['publication_rule']='Alpha.11 adds exact-byte shared effect storage; representative storage smoke, combined clean-game, future-save and full-uninstall lifecycle tests remain pending.'
 # Preserve active_development_install: the live game still uses alpha.10.
 compat['renderer']['reproducible_source_build'].update(source=rel(snapshot),output_sha256=dll['sha256'],output_bytes=dll['bytes'],build_status='Built and CPU/GPU regression tested; shared storage smoke and clean-game lifecycle pending.')
 compat['renderer']['effect_animation_runtime']['storage_index']='EffectStorage-X4.index: exact registry binding, independent logical cache identities'
 old_binding=compat['renderer']['map_water_runtime'];proof=load(ROOT/old_binding['evidence']['path'])
 for f in proof['identical_source_files']:assert sha(snapshot/f['path'])==f['sha256']
 assert sha(snapshot/'src/iee/water_route2_registry.cpp')==sha(old_snapshot/'src/iee/water_route2_registry.cpp')
 proof=dict(proof,dll_sha256=dll['sha256'],storage_only_successor_of=old_binding['dll_sha256'],parent_evidence=old_binding['evidence'],new_ingame_QA=False)
 save(OUT/'map-runtime-continuity.json',proof)
 compat['renderer']['map_water_runtime']=dict(old_binding,dll_sha256=dll['sha256'],evidence=evidence(OUT/'map-runtime-continuity.json'))
 register=copy.deepcopy(before['effect-release-candidates.json']);c=register['candidates'][0]
 packroot=RELEASE/'release-inputs/effects/accepted-shared-20261110-v1';pack=load(packroot/'manifest.json')
 c['candidate_id']='effects-accepted-shared-storage-20261110-v1'
 c['runtime_pack'].update(path=rel(packroot),manifest_sha256=sha(packroot/'manifest.json'),storage=pack['storage'])
 c['renderer_contract'].update(bundle_id=renderer['bundle_id'],dll_sha256=dll['sha256'])
 c['payload_projection']['reason']='Exact-byte shared storage; 71971 logical images, 65849 physical images. Native routes and acquired image QA unchanged.'
 sprites=copy.deepcopy(before['sprite-release-candidates.json'])
 for s in sprites['candidates']:s['runtime_contract'].update(bundle_id=renderer['bundle_id'],dll_sha256=dll['sha256'])
 release=copy.deepcopy(before['release.json']);release['version']='0.1.0-alpha.9'
 release['content_scope']['effects'] += ' Exact-byte shared storage: 71971 logical /65849 physical RGBA, 6122 duplicate files removed; image QA unchanged.'
 release['blocking_conditions']=[v.replace('renderer-alpha.10-effects-projectiles-combined','renderer-alpha.11-shared-storage-combined') for v in release['blocking_conditions']]
 release['blocking_conditions'].append('shared-effect-storage-representative-ingame-smoke-pending')
 for f in files:shutil.copy2(bundle/f['path'],RELEASE/'bg2hd/renderer'/f['path'])
 for name,data in [('renderer-bundle.json',renderer),('runtime-compatibility.json',compat),('effect-release-candidates.json',register),('sprite-release-candidates.json',sprites),('release.json',release)]:save(RELEASE/'manifests'/name,data)
 p=ROOT/'effects/index/processing.csv';rows=list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')));save(OUT/'processing-before.json',rows)
 for r in rows:
  if r['release_state']=='approved':r['release_candidate']=c['candidate_id']
 with p.open('w',encoding='utf-8',newline='') as stream:
  w=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 save(OUT/'prepare-receipt.json',dict(version=release['version'],renderer=renderer['bundle_id'],dll=dll,pack=evidence(packroot/'manifest.json'),game_modified=False,new_visual_QA=False))
 print('Prepared local alpha.9 / renderer alpha.11; game unchanged.',flush=True)

if __name__=='__main__':main()
