import sys,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path('pipeline/recipes/video-endings-locales-analysis-20261111-v1').resolve()))
from compare import OUT,read,save
for family in ['END15FPS','MELISSAN']:
 a=read(family+'-default');b=read(family+'-pl_PL')
 for part,start in enumerate(range(0,int(b['pts'][-1])+1,40),1):
  times=list(range(start,min(start+40,int(b['pts'][-1])+1)))
  sheet=Image.new('RGB',(1600,202*((len(times)+4)//5)),(22,22,22));draw=ImageDraw.Draw(sheet)
  for n,t in enumerate(times):
   j=int(np.argmin(abs(b['pts']-t)));x=(n%5)*320;y=(n//5)*202
   sheet.paste(Image.fromarray(np.asarray(b['frames'][j])).convert('RGB').resize((320,180)),(x,y+22));draw.text((x+4,y+4),f'pl_PL {b["pts"][j]:.3f}s #{j}',fill='white')
  sheet.save(OUT/f'{family}-polish-every-second-{part}.jpg',quality=92)
 if family=='MELISSAN':
  errs=np.abs(np.asarray(b['frames'][:525]).astype(np.int16)-np.asarray(a['frames']).astype(np.int16)).mean(axis=(1,2))
  save('MELISSAN-polish-index-alignment.json',dict(first_525_same_frame_index_luma_mae_percentiles=np.percentile(errs,[0,50,90,99,100]).tolist(),note='DTW becomes ambiguous during final white fade; use index correspondence then hold final master frame for Polish tail. Gain/white-level difference is visible, not a translated insert.'))
