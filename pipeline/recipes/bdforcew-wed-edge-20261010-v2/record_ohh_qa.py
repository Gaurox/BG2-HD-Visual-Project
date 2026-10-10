"""Record the user's explicit OHHPORT ingame approval without rewriting history."""
from pathlib import Path
import copy, sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
def artifact(path):
    p=ROOT/path;m=v2.load_json(p/'manifest.json')
    return dict(path=path,manifest_path=path+'/manifest.json',manifest_sha256=v2.sha256_file(p/'manifest.json').upper(),schema=m['schema'],status=m['status'])
final='animations/batches/portails-deux-correctif-20261010-v1/artifacts/OHHPORT-final-split'
pack=artifact(final);a=v2.load_json(ROOT/final/'AR0811/manifest.json')
pack['areas']=[dict(area='AR0811',path=final+'/AR0811',manifest_path=final+'/AR0811/manifest.json',manifest_sha256=v2.sha256_file(ROOT/final/'AR0811/manifest.json').upper(),registry_sha256=a['registry_sha256'].upper(),resource_entries=1)]
decision_id='2026-10-10-accepted-ohhport-xbr-apo8-backgroundfix-v1'
record={'$schema':'../../../schemas/animation-qa-decision.schema.json','schema_version':1,'decision_id':decision_id,'asset_id':'animations:bam:OHHPORT','resref':'OHHPORT','status':'accepted','result_kind':'x4','decision_origin':'explicit-user-ingame-qa','decision_date':'2026-10-10','recorded_at_utc':v2.utc_now(),'decision':'Utilisateur : « ok pour ohhpot » après installation AR0811 ; fond parasite frame8 corrigé. Validation limitée à OHHPORT/AR0811. Aucun changement release.','tested_areas':['AR0811'],'recipe_id':'xbr2-blend-nearest2-apo8-backgroundfix-premul','correction_id':'native-frame2-opaque-black-background-transparent','final_run':artifact(final),'source_pack':pack,'lineage':{'source_runs':[artifact('animations/ressources/OHHPORT/runs/ohhport-xbr-backgroundfix-20261010-v1'),artifact('animations/ressources/OHHPORT/runs/ohhport-apo8-backgroundfix-20261010-v1')],'source_packs':[]}}
schema=v2.load_json(ROOT/'animations/schemas/animation-qa-decision.schema.json')
assert set(schema['required'])<=set(record)<=set(schema['properties'])
out=ROOT/'animations/index/qa-decisions/OHHPORT'/(decision_id+'.json')
out.parent.mkdir(parents=True,exist_ok=True)
assert not out.exists();v2.write_json(out,record)
print('OHHPORT ingame approval recorded',flush=True)
