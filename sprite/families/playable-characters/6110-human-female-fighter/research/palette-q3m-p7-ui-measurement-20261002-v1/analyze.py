"""Archive latest P7 UI session; compare native Character ramp semantics."""
from pathlib import Path
import hashlib
import json
import re
import sys
import zlib

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
import numpy as np
import palette_frac_encode as encoder
from palette_oracle import scalar_palette
from workspace_paths import get_path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def colors(value):
    if not re.fullmatch(r'[0-9A-Fa-f]{2048}', value):
        raise ValueError('Incomplete 256-entry native palette')
    return np.asarray([int(value[n:n+8],16) for n in range(0,2048,8)],dtype='<u4')


def main():
    out = Path(__file__).resolve().parent
    if (out/'result.json').exists() or (out/'session.log').exists():
        raise ValueError('Use a fresh measurement directory')
    log = get_path('bg2ee_game_root',required=True)/'InfinityEngine-Enhancer.log'
    raw = log.read_bytes()
    lines = raw.decode('utf-8',errors='replace').splitlines()
    starts = [n for n,line in enumerate(lines) if 'P7_UI_PROBE ready:' in line]
    if not starts:
        raise ValueError('No ready P7 probe session')
    session = lines[starts[-1]:]
    evidence = [line for line in session if 'P7_UI_' in line]
    (out/'session.log').write_text('\n'.join(evidence)+'\n',encoding='utf-8',newline='\n')
    palettes,draws=[],[]
    for line in evidence:
        record = dict(re.findall(r'(\w+)=([^\s]+)',line))
        if record.get('resref') != 'CHFF1INV':
            continue
        record['timestamp']=line[1:24]
        if 'P7_UI_PALETTE ' in line:
            p=colors(record['colors'])
            if zlib.crc32(p.tobytes())&0xffffffff != int(record['crc32'],16):
                raise ValueError('Realized palette CRC differs')
            source=colors(record['sourceColors'])
            sb=source.view(np.uint8).reshape(256,4)
            pb=p.view(np.uint8).reshape(256,4)
            src_rgb=sb[:,[2,1,0]]
            realized_rgb=pb[:,[2,1,0]]
            src_expected=scalar_palette(src_rgb[4:88].reshape(7,12,3))
            real_expected=scalar_palette(realized_rgb[4:88].reshape(7,12,3))
            record.update(source_mixed_differences=int(np.count_nonzero(np.any(src_expected[88:]!=src_rgb[88:],axis=1))),
                realized_mixed_differences=int(np.count_nonzero(np.any(real_expected[88:]!=realized_rgb[88:],axis=1))),
                specials_rgba=pb[:4,[2,1,0,3]].tolist(), alpha_histogram={str(v):int(np.count_nonzero(pb[:,3]==v)) for v in np.unique(pb[:,3])})
            palettes.append(record)
        elif 'P7_UI_DRAW ' in line:
            p=colors(record['drawColors'])
            if zlib.crc32(p.tobytes())&0xffffffff != int(record['drawPaletteCrc32'],16):
                raise ValueError('Draw palette CRC differs')
            draws.append(record)
    if not palettes or not draws:
        raise ValueError('Incomplete palette/draw observation')
    # Decode the already produced I/F planes against every actual observed
    # native palette, with an independent scalar byte interpolation.
    pilot=out.parent/'palette-q3m-p7-chff1inv-20261002-v1'
    decoded, decode_differences=0,0
    decoded_crcs=[]
    for index in range(2):
        with np.load(pilot/f'part-{index}-q3m-x2.npz',allow_pickle=False) as data:
            i,f=data['I'].copy(),data['F'].copy()
            encoder.check_contract(data['guide'],i,f,data['dep_mask'])
        successors=np.arange(256,dtype=np.uint16)
        for first,last in [(n,n+11) for n in range(4,88,12)]+[(n,n+7) for n in range(88,256,8)]:
            successors[first:last]=np.arange(first+1,last+1)
        for record in palettes:
            p=colors(record['colors']).view(np.uint8).reshape(256,4).copy()
            p[0]=0 # Existing Q3m decoder's native transparency convention.
            rgba=p[:,[2,1,0,3]]
            actual=encoder.decode(i,f,rgba)
            expected=np.dstack((((rgba[i,:3].astype(np.uint16)*(8-f[...,None])+rgba[successors[i],:3].astype(np.uint16)*f[...,None]+4)//8).astype(np.uint8),rgba[i,3]))
            decode_differences+=int(np.count_nonzero(actual!=expected))
            decoded+=1
            decoded_crcs.append(dict(frame=index, native_crc=record['crc32'], q3m_rgba_crc=f'{zlib.crc32(actual.tobytes())&0xffffffff:08X}'))
    geometry=[]
    for record in draws:
        slot=int(record['slot']); frame=0 if slot in (0,1) else 1 if slot in (2,3) else -1
        x,y=int(record['x']),int(record['y'])
        rect=[int(v) for v in record['render'].split(',')]
        left,top=rect[:2]
        geometry.append(dict(slot=slot, frame=frame, logical=record['logical'],source=record['source'],
            canvas=[rect[2]-left,rect[3]-top], part_offset=[x-left,y-top], flags=record['flags'],native_tone=record['nativeTone']))
    unique_geometry={json.dumps(row,sort_keys=True):row for row in geometry}
    for record in palettes:
        del record['colors'];del record['sourceColors']
    for record in draws:
        del record['drawColors']
    result=dict(schema='bg2-p7-native-ui-measurement-v1', status='measured-native-ui-only',
        session_start=evidence[0][1:24], first_capture=palettes[0]['timestamp'],last_capture=draws[-1]['timestamp'],
        palette_records=len(palettes),draw_records=len(draws),unique_palette_crcs=len({p['crc32'] for p in palettes}),
        unique_range_sets=sorted({p['ranges'] for p in palettes}),
        limits_reached=[line.split('] ',2)[-1] for line in evidence if 'limit=' in line],
        capture_is_bounded_not_exhaustive=True, native_kinds=sorted({p['kind'] for p in palettes}),
        encodings=sorted({(p['format'],p['type']) for p in palettes}),
        source_mixed_differences=sorted({p['source_mixed_differences'] for p in palettes}),
        realized_mixed_differences=sorted({p['realized_mixed_differences'] for p in palettes}),
        alpha_histograms=[json.loads(value) for value in sorted({json.dumps(p['alpha_histogram'],sort_keys=True) for p in palettes})],
        geometry=list(unique_geometry.values()),decoded_observed_palettes=decoded,decode_byte_differences=decode_differences,
        palette_to_draw_crc_missing=sum(d['drawPaletteCrc32'] not in {p['crc32'] for p in palettes} for d in draws),
        palettes=palettes,draws=draws,decoded_crcs=decoded_crcs,
        provenance=dict(game_log=str(log),game_log_sha256=sha(raw),session_sha256=sha((out/'session.log').read_bytes()),
            analyzer_sha256=sha(Path(__file__).read_bytes())),
        hd_paperdoll_installed=False, ingame_hd_qa=False,controls_pc_input=False,installation_modified=False)
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('palettes','draws','decoded_crcs','provenance')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
