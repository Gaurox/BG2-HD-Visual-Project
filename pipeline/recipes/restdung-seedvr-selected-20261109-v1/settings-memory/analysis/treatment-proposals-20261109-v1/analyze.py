import cv2
import numpy as np
from PIL import Image, ImageDraw
from pathlib import Path
import hashlib
import json

OUT = Path(__file__).resolve().parent
ASSET = OUT.parents[1]
AB = ASSET / 'runs/restdung-topaz-ab-20261109-v1'
N = ASSET / 'runs/restdung-preclean-ab-20261110-v1'
FILES = {
    'Source': ASSET / 'restdung.wbm',
    'A': AB / 'A-proteus-doux-1080p15-master.mov',
    'B': AB / 'B-gaia-cg-1080p15-master.mov',
    'N1-seul': N / 'N1-proteus-nettoyage-720p15.mkv',
    'N1-A': N / 'N1-proteus-nettoyage-puis-A-1080p15-master.mov',
    'N2-seul': N / 'N2-nyx-nettoyage-720p15.mkv',
    'N2-A': N / 'N2-nyx-nettoyage-puis-A-1080p15-master.mov',
}
ROIS = {'pierre': (760,250,1060,700), 'bois': (1210,360,1630,780), 'sol': (360,740,1000,930), 'lumiere': (430,300,700,650)}
TIMES = [1.2, 2.8, 4.2]
snapshots = {}
report = {'method': 'Frame-index alignment at 15 fps. Masters; 720p inputs resized to 1080p Lanczos. Measures on frames 33..63 inclusive; temporal differences are NOT motion-compensated and do not measure perceptual quality.', 'files': {}}
for label, path in FILES.items():
    cap = cv2.VideoCapture(str(path))
    rows = []; prev = {}; count = 0; hashes = []; lumas = []; thumbs = []
    while True:
        ok, frame = cap.read()
        if not ok: break
        hashes.append(hashlib.md5(frame.tobytes()).hexdigest())
        if frame.shape[:2] != (1080,1920):
            frame = cv2.resize(frame,(1920,1080),interpolation=cv2.INTER_LANCZOS4)
        gray = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        lumas.append(round(float(gray[180:948].mean()),3))
        if count in [round(t*15) for t in TIMES]:
            snapshots[(label,count)] = Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
        if label == 'Source' and count % 7 == 0:
            thumbs.append((count,Image.fromarray(cv2.cvtColor(cv2.resize(frame,(320,180)),cv2.COLOR_BGR2RGB))))
        if 33 <= count <= 63:
            row = {}
            for name,(x0,y0,x1,y1) in ROIS.items():
                crop = gray[y0:y1,x0:x1]
                mean = float(crop.mean())
                hp = crop.astype(np.float32) - cv2.GaussianBlur(crop,(0,0),1.2).astype(np.float32)
                row[name] = {'luma': mean, 'laplacian_var': float(cv2.Laplacian(crop,cv2.CV_32F).var()), 'highpass_rms': float(np.sqrt(np.mean(hp**2)))}
                if name in prev:
                    # Remove global brightness change; residual still includes actual moving features.
                    a = crop.astype(np.float32)-mean; b = prev[name]
                    row[name]['temporal_mae_demeaned'] = float(np.abs(a-b).mean())
                prev[name] = crop.astype(np.float32)-mean
            rows.append(row)
        count += 1
    cap.release()
    summary = {}
    for name in ROIS:
        summary[name] = {key:round(float(np.mean([r[name][key] for r in rows if key in r[name]])),4) for key in rows[0][name]}
        summary[name]['temporal_mae_demeaned'] = round(float(np.mean([r[name]['temporal_mae_demeaned'] for r in rows if 'temporal_mae_demeaned' in r[name]])),4)
    report['files'][label] = {'path': str(path), 'frames': count, 'unique_frames': len(set(hashes)), 'adjacent_exact_duplicates': sum(a==b for a,b in zip(hashes,hashes[1:])), 'luma_by_frame': lumas, 'regions': summary}
    if label == 'Source':
        board = Image.new('RGB',(1280,4*205),(22,22,22)); draw=ImageDraw.Draw(board)
        for i,(idx,im) in enumerate(thumbs):
            x=(i%4)*320;y=(i//4)*205
            board.paste(im,(x,y+25));draw.text((x+5,y+5),f'{idx/15:.2f}s / frame {idx}',fill='white')
        board.save(OUT/'source-timeline.jpg')
    print(label, count, summary, flush=True)

for region,(x0,y0,x1,y1) in ROIS.items():
    width=x1-x0; height=y1-y0
    board=Image.new('RGB',(len(FILES)*width,len(TIMES)*(height+28)),(22,22,22));draw=ImageDraw.Draw(board)
    for col,label in enumerate(FILES):
        for row,t in enumerate(TIMES):
            im=snapshots[(label,round(t*15))].crop((x0,y0,x1,y1))
            x=col*width;y=row*(height+28)
            board.paste(im,(x,y+28));draw.text((x+5,y+6),f'{label} - {t}s',fill='white')
    board.save(OUT/(region+'.jpg'),quality=95)
(OUT/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
