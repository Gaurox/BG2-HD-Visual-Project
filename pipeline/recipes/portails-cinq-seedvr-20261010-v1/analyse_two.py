"""Read-only runtime/source/WED diagnosis after user's two ingame screenshots."""
from pathlib import Path
import json
import struct
import sys
import zlib
import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam
from bg2lib import load_key, resolve_resource
from workspace_paths import get_path
import run_animation_upscale_30fps_v2 as v2

OUT = ROOT / 'animations/batches/portails-deux-diagnostic-20261010-v1'
OUT.mkdir(exist_ok=True)
GAME = get_path('bg2ee_game_root')
PACK = ROOT / 'animations/packs-par-zone/portails-cinq-selection-20261010-v1-complete'
FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)

def native(ref):
    raw = (ROOT / f'animations/ressources/{ref}/source.bam').read_bytes()
    if raw[:4] == b'BAMC':
        raw = zlib.decompress(raw[12:])
    return decode_bam(raw)

def runtime(ref, area):
    _, resources = v2.validate_v2_pack(PACK / area)
    resource = next(r for r in resources if r['resref'] == ref)
    values = []
    for f in resource['frames']:
        blob = (GAME / 'iee-assets/areas' / area / f['asset']).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == next(a['sha256'] for a in resource['assets'] if a['name'] == f['asset'])
        w, h = f['physical_size_x4']
        values.append(np.frombuffer(blob, np.uint8).reshape(h, w, 4))
    return resource, values

def ohh():
    frames, palette, cycles = native('OHHPORT')
    resource, values = runtime('OHHPORT', 'AR0811')
    x1 = json.loads((ROOT / 'animations/ressources/OHHPORT/runs/ohhport-xbr-spatial-20261010-v1/resources/OHHPORT/01_frames_x1/manifest.json').read_text())
    print('OHHPORT native cycles', cycles)
    report = []
    board = Image.new('RGB', (512*3, (512+40)*6), '#181b21')
    draw = ImageDraw.Draw(board)
    for i, (idx, cx, cy, tr) in enumerate(frames):
        rgb = palette[idx].copy()
        colors, counts = np.unique(rgb.reshape(-1, 3), axis=0, return_counts=True)
        common = sorted(zip(counts.tolist(), colors.tolist()), reverse=True)[:4]
        raw = np.dstack((rgb, (idx != tr).astype(np.uint8)*255))
        raw[idx == tr, :3] = 0
        source = raw.repeat(4, 0).repeat(4, 1)
        final = values[i]
        corners = np.concatenate([final[:40,:40].reshape(-1,4),final[-40:,-40:].reshape(-1,4)])
        item = {'frame': i, 'size': list(idx.shape[::-1]), 'centre': [cx,cy], 'transparent_index': tr,
                'native_alpha_nonzero_pct': round(100*float((idx != tr).mean()),4), 'native_dominant_rgb': common,
                'final_corner_mean_rgba': corners.mean(0).tolist(), 'final_corner_max_rgb': corners[:,:3].max(0).tolist()}
        report.append(item)
        print(json.dumps(item), flush=True)
        for j, arr in enumerate([source[:,:,:3],final[:,:,:3],np.repeat(final[:,:,3,None],3,2)]):
            image = Image.fromarray(arr)
            board.paste(image,(j*512,i*552+40))
        draw.text((8,i*552+8),f'Native frame {i}',font=FONT,fill='white')
        draw.text((520,i*552+8),'Installed xBR / Apollo',font=FONT,fill='white')
        draw.text((1032,i*552+8),'Installed alpha',font=FONT,fill='white')
    board.save(OUT/'OHHPORT-six-native-frames.png')
    report2=[]
    for phase, index in enumerate(resource['cycles'][0]['timeline_frame_indices']):
        a=values[index]
        corners=np.concatenate([a[:40,:40].reshape(-1,4),a[-40:,-40:].reshape(-1,4)])
        row={'phase':phase,'runtime_frame':index,'native_left':resource['cycles'][0]['native_frame_indices'][phase//2],
             'corner_mean_rgba':corners.mean(0).tolist(),'corner_nonzero_rgb_pct':round(100*float((corners[:,:3].max(1)>0).mean()),3)}
        report2.append(row)
        print('PHASE',json.dumps(row),flush=True)
    return {'native_frames':report,'timeline':report2}

def bdf():
    frames, palette, cycles = native('BDFORCEW')
    resource, values = runtime('BDFORCEW','OH8100')
    bifs, entries = load_key()
    override = GAME / 'override/OH8100.WED'
    if override.exists():
        data=override.read_bytes(); provenance=str(override)
    else:
        entry=next(e for e in entries if e[0].upper()=='OH8100' and e[1]==0x3e9)
        data,provenance=resolve_resource(bifs,entry[2])
    sec=struct.unpack_from('<I',data,0x14)[0]
    count,po,vo=struct.unpack_from('<III',data,sec)
    polygons=[]
    for i in range(count):
        start,n,flags,height,*bbox=struct.unpack_from('<IIBBHHHH',data,po+i*18)
        pts=[struct.unpack_from('<HH',data,vo+(start+k)*4) for k in range(n)]
        if pts:
            polygons.append({'index':i,'flags':hex(flags),'height':height,'vertices':pts,
                             'bounds':[min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)]})
    reports=[]
    for occurrence,(x,y) in enumerate([(2286,820),(2350,866)],1):
        fidx=resource['cycles'][2]['native_frame_indices'][10]
        idx,cx,cy,tr=frames[fidx]
        h,w=idx.shape
        bounds=(x-cx,y-cy,x-cx+w,y-cy+h)
        nearby=[p for p in polygons if p['bounds'][0]<bounds[2] and p['bounds'][2]>bounds[0] and p['bounds'][1]<bounds[3] and p['bounds'][3]>bounds[1]]
        actual=values[fidx]
        canvas=Image.new('RGB',(w*4*2+16,h*4+65),'#181b21')
        canvas.paste(Image.fromarray(actual[:,:,:3]),(0,65))
        canvas.paste(Image.fromarray(np.repeat(actual[:,:,3,None],3,2)),(w*4+16,65))
        d=ImageDraw.Draw(canvas)
        d.text((8,8),f'BDFORCEW instance {occurrence} / cycle 2 / native frame {fidx}',font=FONT,fill='white')
        d.text((8,34),'WED cover cyan / other polygons orange',font=FONT,fill='white')
        for p in nearby:
            color='cyan' if int(p['flags'],16)&8 else 'orange'
            pts=[((px-bounds[0])*4,(py-bounds[1])*4+65) for px,py in p['vertices']]
            d.line(pts+[pts[0]],fill=color,width=2)
            vx,vy=pts[0]
            d.text((vx,vy),str(p['index']),font=FONT,fill=color)
        canvas.save(OUT/f'BDFORCEW-instance-{occurrence}-WED-alpha.png')
        record={'occurrence':occurrence,'position':[x,y],'frame':fidx,'world_frame_bounds':bounds,'nearby_polygons':nearby}
        reports.append(record)
        print('BDF',json.dumps(record),flush=True)
    return {'wed_source':provenance,'wed_sha256':hashlib.sha256(data).hexdigest(),'instances':reports}

v2.write_json(OUT/'diagnostic.json',{'OHHPORT':ohh(),'BDFORCEW':bdf(),'installed_files_modified':False})
