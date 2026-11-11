import sys,json,subprocess
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path('pipeline/recipes/video-endings-locales-analysis-20261111-v1').resolve()))
from compare import read,save
result={}
for family in ['END15FPS','MELISSAN']:
 for locale in (['default','de_DE','it_IT','pl_PL'] if family=='END15FPS' else ['default','de_DE','pl_PL']):
  name=family+'-'+locale;d=read(name);src=d['meta']['source'];pts=d['pts'];frames=d['frames']
  audio=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','a:0','-show_packets','-show_entries','packet=pts_time,duration_time','-of','json',src]))['packets']
  result[name]=dict(audio_first_packet=audio[0],audio_last_packet=audio[-1],nonincreasing_video_pts=[dict(frame=int(i+1),pts=float(pts[i+1])) for i in np.where(np.diff(pts)<=0)[0]],tail=[dict(frame=i,pts=float(pts[i]),mean=round(float(frames[i].mean()),3),std=round(float(frames[i].std()),3),min=int(frames[i].min()),max=int(frames[i].max())) for i in range(max(0,len(frames)-45),len(frames))])
save('audio-tails-and-final-frames.json',result)
for name,d in result.items():
 print(name,'AUDIO',d['audio_first_packet'],d['audio_last_packet'],'non-increasing',d['nonincreasing_video_pts'])
 if name.startswith('MELISSAN'):print(json.dumps(d['tail']))
