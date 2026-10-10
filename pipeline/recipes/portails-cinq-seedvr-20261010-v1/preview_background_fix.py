"""Diagnostic only: preview frame 8 with corrected frame-2 source support.
Not a new runtime pack; Apollo RGB is retained solely to isolate the background.
"""
from pathlib import Path
import sys
import zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam
from workspace_paths import get_path
from run_animation_small_subject_xbr2 import run_xbr2x, nearest_x2
import run_animation_upscale_30fps_v2 as v2
OUT = ROOT / 'animations/batches/portails-deux-diagnostic-20261010-v1'
raw = (ROOT / 'animations/ressources/OHHPORT/source.bam').read_bytes()
frames, palette, _ = decode_bam(zlib.decompress(raw[12:]) if raw[:4] == b'BAMC' else raw)
idx, _, _, tr = frames[2]
rgb = palette[idx].copy()
# Exact zero RGB describes the anomalous frame's background; no colour threshold.
fixed = np.dstack((rgb, ((rgb.max(2) > 0) & (idx != tr)).astype(np.uint8)*255))
fixed[(fixed[:,:,3] == 0), :3] = 0
x4 = nearest_x2(run_xbr2x([fixed], get_path('mmpx_scalepix'), 'node', True)[0])
pack = ROOT / 'animations/packs-par-zone/portails-cinq-selection-20261010-v1-complete/AR0811'
resource = next(r for r in v2.load_json(pack / 'manifest.json')['resources'] if r['resref'] == 'OHHPORT')
entry = resource['frames'][8]
w,h = entry['physical_size_x4']
old = np.frombuffer((pack / entry['asset']).read_bytes(), np.uint8).reshape(h,w,4)
alpha = np.minimum(old[:,:,3], x4[:,:,3])
ratio = np.divide(alpha, old[:,:,3], out=np.zeros((h,w),dtype=float), where=old[:,:,3]>0)
new = old.copy()
new[:,:,:3] = np.rint(old[:,:,:3] * ratio[:,:,None]).astype(np.uint8)
new[:,:,3] = alpha
assert not new[new[:,:,3] == 0,:3].any()
yy,xx=np.indices((h,w))
bg=np.where(((xx//32+yy//32)%2)[:,:,None],np.array([39,43,48]),np.array([22,25,30])).astype(np.uint8)
board=Image.new('RGB',(1040,600),'#181b21')
d=ImageDraw.Draw(board)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
for x,label,a in [(0,'Installe : frame intermediaire 8',old),(528,'Masque corrige : simulation locale',new)]:
    d.text((x+8,10),label,font=font,fill='white')
    board.paste(Image.fromarray(np.minimum(bg.astype(np.uint16)+a[:,:,:3],255).astype(np.uint8)),(x,42))
d.text((8,566),'Fond corrige AVANT xBR ; RGB Apollo actuel conserve ici pour isoler la cause.',font=font,fill='white')
board.save(OUT/'OHHPORT-frame8-background-diagnosis.png')
v2.write_json(OUT/'OHHPORT-background-mask-check.json',{'native_frame':2,'bad_runtime_frame':8,'native_black_background_pixels':int((rgb.max(2)==0).sum()),
    'fixed_foreground_pixels':int((fixed[:,:,3]>0).sum()),'outside_corrected_alpha_rgb_zero':True,'installed_files_modified':False,'preview_kind':'mask-only-diagnostic-not-final-inference'})
