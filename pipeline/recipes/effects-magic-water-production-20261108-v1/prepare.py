"""Prepare authorized production from recipe v2; reuse last lot's native-clock producer."""
import json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'effects/batches/lot50-magic-water-production-20261108-v1'
OLD=ROOT/'pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 proposal=json.loads((ROOT/'effects/batches/lot50-magic-water-proposal-20261108-v1/batch.json').read_text(encoding='utf-8'))
 recipes=json.loads((ROOT/'effects/batches/lot50-magic-water-recipes-20261108-v2/recipes.json').read_text(encoding='utf-8'))
 by={a['resref']:a for a in recipes['assets']};assets=[];native=[]
 for old in proposal['assets']:
  a=copy.deepcopy(old);n=a['resref'];r=by[n]
  if r['profile']=='N-MASK':native.append(a);continue
  a.update(native_fps=[],recipe_profile=r['profile'],profile='H' if 'Light-only' in r['black_policy'] else 'N',sigma_x4=r['recipe'].get('rgb_gauss_sigma_x4',0),inner_feather_x4=0,
   spatial_run=f'{n.lower()}-magic-x4-20261108-v1',interpolation_run=f'{n.lower()}-magic-apollo30-20261108-v1',pack=f'effects/ressources/{n}/packs/{n.lower()}-magic-apollo30-initial-20261108-v1',green_index=None,recipe_plan=r)
  if n=='WHIRLY':
   import sys,numpy as np
   sys.path.insert(0,str(ROOT/'pipeline/scripts'))
   from bam_export import decode_bam,native_palette_alpha
   from export_bam_frames import read_bam
   raw=read_bam(ROOT/a['source']);fs,pal,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr)
   ids=[i for i in r['green_derivation']['palette_indices'] if alpha[i]>0 and any((f[0]==i).any() for f in fs)]
   assert len(ids)==1,ids
   a['green_index']=ids[0]
  assets.append(a)
 batch=dict(schema='bg2-effects-production-batch-v1',date='2026-11-08',authorization='User requested complete pack treatment and animated comparison board, SeedVR priority per recipe v2.',assets=assets,native_masks=native,spatial_batch=OUT.relative_to(ROOT).as_posix())
 p=OUT/'batch.json'
 if not p.exists():p.write_text(json.dumps(batch,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 for name in ['support.py','temporal.py','runtime_profiles.py','verify.py','review.py','board.html']:
  p=HERE/name
  if p.exists():continue
  s=(OLD/name).read_text(encoding='utf-8').replace('effects/batches/lot50-seedvr7b-apollo30-20261108-v1',OUT.relative_to(ROOT).as_posix())
  if name=='runtime_profiles.py':s=s.replace("f'{name.lower()}-7b-x4-apollo30-native-profiles-20261108-v2'","f'{name.lower()}-magic-x4-apollo30-profiles-20261108-v1'")
  if name=='review.py':
   s=s.replace("effects/batches/lot50-native-animated-board-20261108-v1","effects/batches/lot50-magic-water-proposal-20261108-v1/review")
  if name=='verify.py':
   s=s.replace("assert s['parameters']['model']=='seedvr2_7b_int8_convrot.safetensors'","assert s['parameters']['model'] in {'seedvr2_7b_int8_convrot.safetensors','XBR/xbr4X','XBR/xbr2blend-nearest2','reuse-TRGOOY-spatial'}")
   s=s.replace("assert s['parameters']['color_correction_method']=='lab' and s['scale']==4","assert s['parameters']['color_correction_method'] in {'lab','native','reuse'} and s['scale']==4")
  p.write_text(s,encoding='utf-8')
 s=(OLD/'spatial_one.py').read_text(encoding='utf-8');start=s.index("GREEN={");end=s.index('\noriginal_export',start)
 s=s[:start]+"GREEN={'WHIRLY':"+str(next(a['green_index'] for a in assets if a['resref']=='WHIRLY'))+"}"+s[end:]
 if not (HERE/'spatial_one.py').exists():(HERE/'spatial_one.py').write_text(s,encoding='utf-8')
 print('Prepared',len(assets),'productions/adaptations and',len(native),'native masks')
if __name__=='__main__':main()
