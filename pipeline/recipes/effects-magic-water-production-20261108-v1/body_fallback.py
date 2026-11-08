"""Observed SeedVR hallucination on32px body: retain seed run; add faithful xBR fallback."""
import copy,sys
from pathlib import Path
import local_spatial,temporal,verify,runtime_profiles,review
from temporal import ROOT,BATCH,load,save
def main():
 a=copy.deepcopy(next(a for a in load(BATCH/'batch.json')['assets'] if a['resref']=='WTRBODY2'))
 a.update(spatial_run='wtrbody2-magic-xbr2-nearest2-x4-20261108-v1',interpolation_run='wtrbody2-magic-xbr2-apollo30-20261108-v1',pack='effects/ressources/WTRBODY2/packs/wtrbody2-magic-xbr2-initial-20261108-v1',final_pack='effects/ressources/WTRBODY2/packs/wtrbody2-magic-xbr2-apollo30-profiles-20261108-v1',sigma_x4=0,profile='N',recipe_profile='X-BODY')
 alt=BATCH/'alternatives/wtrbody2-xbr2-20261108-v1';alt.mkdir(parents=True,exist_ok=True)
 local_spatial.produce(a)
 temporal.BATCH=verify.BATCH=runtime_profiles.BATCH=alt
 temporal.produce(a);verify.verify(a);result=runtime_profiles.build(a)
 old=review.OUT;review.OUT=old/'alternatives/wtrbody2-xbr2'
 for f in ['data','native','images']:(review.OUT/f).mkdir(parents=True,exist_ok=True)
 c=review.card(a);c.update(method='xBR2 → nearest2 x4 · Apollo30 · repli fidèle',nativeOnly=False,profile='X-BODY')
 prefix='alternatives/wtrbody2-xbr2/'
 c['native']['image']=prefix+c['native']['image']
 for f in c['frames']:
  for k in ['image','neutral']:
   if k in f:f[k]=prefix+f[k]
 seed=load(old/'data/WTRBODY2.json');save(alt/'seedvr-card.json',seed)
 save(BATCH/'body-fallback.json',dict(resref='WTRBODY2',reason='Observed SeedVR converts dark water/body pixels into decorative engraved patterns. Source32x32; preserve source appearance with proven WTRBODY1 xBR2/nearest2 method.',seedvr_preserved=True,asset=a,result=result,card=c,verification=str((alt/'verification/WTRBODY2.json').relative_to(ROOT)),runtime_verification=str((alt/'runtime-verification/WTRBODY2.json').relative_to(ROOT))))
 save(alt/'batch.json',dict(assets=[a]));print('WTRBODY2 faithful fallback produced; SeedVR retained.',flush=True)
if __name__=='__main__':main()
