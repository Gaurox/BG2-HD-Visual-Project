"""Decoded identity + temporal visual alignment; caches only, no movie production."""
import csv, json, re
from pathlib import Path
from fractions import Fraction
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'video/research/endings-locales-analysis-20261111-v1'


def save(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def hashes(path):
    lines=path.read_text().splitlines()
    tb=Fraction(next(x.split(':',1)[1].strip() for x in lines if x.startswith('#tb ')))
    records=[[x.strip() for x in line.split(',')] for line in lines if line and not line.startswith('#')]
    return np.array([float(int(r[2])*tb) for r in records]),[r[5] for r in records]


def read(name):
    meta=json.loads((OUT/f'{name}.metadata.json').read_text(encoding='utf-8'))
    times,decoded=hashes(OUT/f'{name}.decoded.sha256')
    _,packets=hashes(OUT/f'{name}.packets.sha256')
    pts=np.array([float(f['best_effort_timestamp_time']) for f in json.loads((OUT/f'{name}.native-frame-times.json').read_text())['frames']])
    assert len(times)==len(pts)==meta['frames']
    frames=np.memmap(OUT/f'{name}.gray',dtype=np.uint8,mode='r',shape=(len(times),90,160))
    return dict(meta=meta,pts=pts,decoded=decoded,packets=packets,frames=frames)


def dtw(cost):
    n,m=cost.shape
    dp=np.full((n+1,m+1),np.inf,np.float32);dp[0,0]=0
    steps=np.zeros((n,m),np.uint8)
    for i in range(n):
        center=i*(m-1)/max(1,n-1)
        for j in range(max(0,int(center)-240),min(m,int(center)+241)):
            a=dp[i,j];b=dp[i,j+1]+1.0;c=dp[i+1,j]+1.0
            if a<=b and a<=c: value=a;steps[i,j]=0
            elif b<=c: value=b;steps[i,j]=1
            else: value=c;steps[i,j]=2
            dp[i+1,j+1]=cost[i,j]+value
    i=n-1;j=m-1;path=[]
    while i>=0 and j>=0:
        path.append((i,j));step=steps[i,j]
        if step==0: i-=1;j-=1
        elif step==1:i-=1
        else:j-=1
    return path


def features(frames):
    return frames.reshape(len(frames),18,5,32,5).mean(axis=(2,4)).reshape(len(frames),-1).astype(np.float32)


def overview(family,items):
    width=320; height=202;cols=10
    sheet=Image.new('RGB',(width*cols,height*len(items)),(24,24,24));draw=ImageDraw.Draw(sheet)
    for row,(name,data) in enumerate(items):
        for col,i in enumerate(np.linspace(0,len(data['frames'])-1,cols).astype(int)):
            im=Image.fromarray(np.asarray(data['frames'][i])).convert('RGB').resize((320,180))
            sheet.paste(im,(col*width,row*height+22))
            draw.text((col*width+4,row*height+4),f'{name} #{i} {data["pts"][i]:.3f}s',fill='white')
    sheet.save(OUT/f'{family}-overview.jpg',quality=92)


def compare(base_name,other_name,base,other):
    a=features(base['frames']);b=features(other['frames'])
    cost=np.maximum((a*a).mean(1)[:,None]+(b*b).mean(1)[None,:]-2*(a@b.T)/a.shape[1],0)
    path=dtw(cost)
    matches=[[] for _ in b]
    for i,j in path:matches[j].append(i)
    mapping=np.array([min(v,key=lambda i:cost[i,j]) for j,v in enumerate(matches)],np.int32)
    with (OUT/f'{other_name}-to-default.csv').open('w',encoding='utf-8',newline='') as stream:
        w=csv.writer(stream);w.writerow(['locale_frame','locale_pts_s','default_frame','default_pts_s','luma_mae_160x90','luma_p99_error','pixels_error_gt12_percent','exact_yuv_sha256'])
        errors=[]
        for j,i in enumerate(mapping):
            delta=np.abs(other['frames'][j].astype(np.int16)-base['frames'][i].astype(np.int16))
            mae=float(delta.mean());p99=float(np.percentile(delta,99));pct=float((delta>12).mean()*100)
            w.writerow([j,other['pts'][j],int(i),base['pts'][i],round(mae,5),p99,round(pct,5),other['decoded'][j]==base['decoded'][i]])
            errors.append((mae,p99,pct))
    errors=np.array(errors)
    decoded=set(base['decoded']);packets=set(base['packets'])
    result=dict(base=base_name,other=other_name,base_frames=len(a),other_frames=len(b),
        exact_decoded_matches_anywhere=sum(h in decoded for h in other['decoded']),
        exact_encoded_packet_matches_anywhere=sum(h in packets for h in other['packets']),
        identical_decoded_sequence=base['decoded']==other['decoded'],
        identical_encoded_sequence=base['packets']==other['packets'],
        identical_audio_pcm=base['meta']['audio_pcm_hash']==other['meta']['audio_pcm_hash'],
        mae_percentiles=dict(zip(['p0','p50','p90','p95','p99','p100'],np.percentile(errors[:,0],[0,50,90,95,99,100]).tolist())),
        frames_mae_gt3=int((errors[:,0]>3).sum()),frames_mae_gt6=int((errors[:,0]>6).sum()))
    save(f'{other_name}-comparison.json',result)
    print(json.dumps(result),flush=True)
    return result


def main():
    sources=json.loads((OUT/'sources.json').read_text(encoding='utf-8'))['sources']
    data={s['name']:read(s['name']) for s in sources}
    results=[]
    for family in ['END15FPS','MELISSAN']:
        items=[(name,d) for name,d in data.items() if name.startswith(family+'-')]
        overview(family,items)
        base_name=family+'-default';base=data[base_name]
        for name,other in items:
            if name!=base_name:results.append(compare(base_name,name,base,other))
    save('comparisons.json',results)


if __name__=='__main__':main()
