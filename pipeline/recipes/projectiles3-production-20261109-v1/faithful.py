"""Faithful xBR4X alternative after visible SeedVR halo overinterpretation."""
from pathlib import Path
import importlib.util,sys,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as w
BASE=ROOT/'effects/batches/projectiles3-production-20261109-v1'
ALT=BASE/'alternatives/xbr4x-20261109-v1'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
 batch=load(BASE/'batch.json')
 for a in batch['assets']:
  n=a['resref'].lower();a.update(spatial_run=f'{n}-xbr4x-20261109-v1',interpolation_run=f'{n}-xbr-apollo30-20261109-v1',pack=f'effects/ressources/{a["resref"]}/packs/{n}-xbr-apollo30-initial-20261109-v1',final_pack=f'effects/ressources/{a["resref"]}/packs/{n}-xbr4x-apollo30-profiles-20261109-v1')
 save(ALT/'batch.json',batch)
 sp=module('projectiles3_faithful_spatial',ROOT/'pipeline/recipes/effects-magic-water-production-20261108-v1/local_spatial.py')
 for a in batch['assets']:sp.produce(a)
 import temporal
 temporal.BATCH=ALT
 import verify,runtime_profiles,review
 verify.BATCH=ALT;runtime_profiles.BATCH=ALT;review.BATCH=ALT;review.OUT=ALT/'review';review.NATIVE=BASE/'native-review'
 for a in batch['assets']:
  print('Faithful temporal',a['resref'],flush=True);temporal.produce(a);verify.verify(a);runtime_profiles.build(a)
 print('Faithful review',review.build(),flush=True)
 save(ALT/'production.json',dict(status='completed-production-pending-visual-QA',reason='SeedVR adds geometric motifs to tiny native halos; xBR4X offers faithful alternative. No SeedVR outputs removed.',assets=[dict(resref=a['resref'],**{k:v for k,v in load(ALT/'runtime-verification'/f'{a["resref"]}.json').items() if k!='resref'}) for a in batch['assets']]))
if __name__=='__main__':main()
