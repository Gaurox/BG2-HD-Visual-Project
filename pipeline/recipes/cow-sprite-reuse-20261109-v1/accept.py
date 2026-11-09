"""Pin explicit COW ingame approval; keep source sprite and installed receipts immutable."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as w
from workspace_paths import get_path
OUT=ROOT/'projectiles/analysis/cow-accepted-20261109-v1'
SOURCE=ROOT/'projectiles/analysis/cow-sprite-reuse-20261109-v1'
INSTALL=ROOT/'effects/installations/cow-sprite-bridge-20261109-v1'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def ev(p):return w.file_evidence(ROOT,p)
def save(p,d):assert not p.exists(),'Accepted evidence immutable';p.write_bytes(w.json_bytes(d))
def main():
 assert not (OUT/'acceptance.json').exists();OUT.mkdir(parents=True,exist_ok=True)
 reuse=load(SOURCE/'reuse.json');installed=load(INSTALL/'installation.json');plan=load(INSTALL/'plan.json')
 game=get_path('bg2ee_game_root',required=True);manifest=game/'iee-assets/effects/manifest.json';m=load(manifest)
 assert w.sha256_file(manifest)==plan['manifest_sha256']
 assert w.sha256_file(game/'InfinityEngine-Enhancer.dll')==installed['dll']['sha256']
 assert w.sha256_file(ROOT/reuse['sprite_QA'])==reuse['sprite_QA_sha256']
 resource=next(r for r in m['resources'] if r['resref']=='ACOWG1');backings=[f for f in m['frames'] if f['resref']=='ACOWG1']
 assert len(backings)==22 and len(resource['cycles'])==40 and resource['source_q3m_shard_sha256']==reuse['source_shard_sha256']
 for f in backings:assert w.sha256_file(game/'iee-assets/effects'/f['asset'])==f['sha256']
 before=load(INSTALL/'before.json')
 for name,snapshot in before['preserved'].items():assert w.sha256_file(game/name)==snapshot['sha256']
 save(OUT/'acceptance.json',dict(schema='bg2-projectile-scoped-acceptance-v1',status='accepted',decision_date='2026-11-09',user_decision='ok validé. maj le suivi et committe',projectile_id=188,missile_id=189,resource='ACOWG1',scope=['Observed COW188 projectile and reused ACOWG1 image ingame'],source_sprite_QA=ev(ROOT/reuse['sprite_QA']),reuse=ev(SOURCE/'reuse.json'),selected_pack=ev(ROOT/reuse['pack']/'manifest.json'),installation=ev(INSTALL/'installation.json'),installed_manifest_sha256=w.sha256_file(manifest),installed_dll_sha256=installed['dll']['sha256'],verified_backings=22,source_sprite_unchanged=True,new_inference=0,new_interpolation=0,limits=['Observed use only; not every cycle/palette/scene-lighting combination','Native displacement retained; no position interpolation or 30FPS native-motion measurement inferred','No release acceptance or modification']))
 p=ROOT/'projectiles/index/work-tracking.json';d=load(p);node=d['engine_projectiles']['188'];save(OUT/'tracking-before.json',node)
 node['qa']=dict(state='accepted-observed-components',evidence=['projectiles/analysis/cow-accepted-20261109-v1/acceptance.json'],scope=['COW188/ACOWG1 observed ingame'],reviewed_on='2026-11-09',limits='Observed projectile only; all cycles/palettes/scene lighting and displacement interpolation not inferred.')
 node['integration']=dict(state='accepted-observed-runtime-route',evidence=['projectiles/analysis/cow-accepted-20261109-v1/acceptance.json'],scope='Existing CProjectileBAM Render0x233f20; retained Q3m x2 pixels adapted exactly to effect backing; native source/centres/cycles preserved.')
 node['notes']='COW188/missile189 accepted ingame2026-11-09. ACOWG1 Q3m V7 x2 reused,22frames/40cycles; exact2x storage duplication,0inference/interpolation. Native sprite/catalogue/QA and movement preserved. Other cycles/palettes/lighting and release independent.'
 p.write_bytes(w.json_bytes(d))
 (OUT/'README.md').write_text('# COW188 accepté ingame —2026-11-09\n\n- Décision utilisateur : «ok validé. maj le suivi et committe».\n- `acceptance.json` : source Q3m V7 x2 ACOWG1 déjà acceptée,22backings installés exacts, DLL et catalogue liés au reçu ; source sprite/feuille/catalogue/QAs conservés.\n- Route native partagée Render233f20,22frames/40cycles ; adaptation stockage2× exacte seulement,0inférence/interpolation. QA acquise pour le COW observé, pas toutes variantes d’éclairage/cycles ni interpolation du déplacement.\n- Autorité : `projectiles/index/work-tracking.json:engine_projectiles.188.{integration,qa,installation}`. Installation/release et3images précédentes inchangées.\n',encoding='utf-8')
 print('COW188 accepted ingame; exact installed pixels/runtime pinned, source sprite and prior3 retained.')
if __name__=='__main__':main()
