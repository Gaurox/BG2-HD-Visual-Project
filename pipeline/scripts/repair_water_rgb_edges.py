"""Rebuild every safe water/art tile edge from a continuous x4 master; RGB only.

No installation. All alpha bytes and RGB blocks outside the selected bands are immutable.
Native masks exclude banks/structures; physical aliases are refused for modified slots.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import zlib

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion

import bg2lib
from area_decode import decode_tis_tiles
from bc3_refined import encode_bc3
from build_liquid_base_x4_trial import block_mask, rgb_seam_difference
from build_water_route1_batch import parse_pvr, parse_standalone_tis, parse_wed
from mos_decode import decode_pvrz_page
from workspace_paths import get_path

ROOT = Path(__file__).resolve().parents[2]
Image.MAX_IMAGE_PIXELS = None


def water_art_edge_masks(parsed, slots, stock_tile, full_cells):
    """All directed full/full, full/pair, pair/full, pair/pair water interfaces.

    Returns independent masks per side; full cells use primary art, pairs secondary art.
    A one-native-pixel erosion and two-pixel-deep edge checks protect real geometry.
    """
    width, height = parsed['layers'][0]['width'], parsed['layers'][0]['height']
    bits = sum(1 << slot for slot in slots)
    cells = {}
    water = np.zeros((height*64, width*64), bool)
    for cell in parsed['cells']:
        if cell['count'] != 1 or not cell['flags'] & bits:
            continue
        xy = cell['x'], cell['y']
        primary, secondary = cell['primary'][0], cell['secondary']
        if xy in full_cells:
            tile, kind = primary, 'full'
            valid = np.ones((64,64), bool)
        elif secondary != 65535:
            tile, kind = secondary, 'pair'
            valid = ((np.asarray(stock_tile(primary))[:,:,3] == 0)
                     & (np.asarray(stock_tile(secondary))[:,:,3] == 255))
        else:
            continue
        cells[xy] = tile, kind
        x,y = xy
        water[y*64:(y+1)*64, x*64:(x+1)*64] = valid
    safe = binary_erosion(water, structure=np.ones((3,3), bool), border_value=0)
    interfaces = []
    for (x,y), (tile,kind) in sorted(cells.items()):
        own = safe[y*64:(y+1)*64, x*64:(x+1)*64]
        for side,dx,dy in [('left',-1,0),('right',1,0),('top',0,-1),('bottom',0,1)]:
            neighbor = cells.get((x+dx,y+dy))
            if neighbor is None:
                continue
            other = safe[(y+dy)*64:(y+dy+1)*64, (x+dx)*64:(x+dx+1)*64]
            if side == 'left': valid = own[:,:2].all(1) & other[:,-2:].all(1)
            elif side == 'right': valid = own[:,-2:].all(1) & other[:,:2].all(1)
            elif side == 'top': valid = own[:2].all(0) & other[-2:].all(0)
            else: valid = own[-2:].all(0) & other[:2].all(0)
            if not valid.any():
                continue
            mask = np.zeros((256,256), np.float32)
            along = np.repeat(valid,4)
            for d,weight in enumerate([1,1,1,1,.75,.5,.25]):
                if side == 'left': mask[:,d] = along*weight
                elif side == 'right': mask[:,255-d] = along*weight
                elif side == 'top': mask[d] = along*weight
                else: mask[255-d] = along*weight
            interfaces.append({'tile':tile,'cell':[x,y],'side':side,
                'neighbor':list(neighbor),'kind':kind+'-'+neighbor[1], 'mask':mask})
    return interfaces


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--vanilla', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Immutable output already exists'
    request = json.loads(args.request.read_text(encoding='utf-8'))
    area = request['area']
    live = get_path('bg2ee_game_root',required=True) / 'override'
    tis_bytes = (live / (area+'.TIS')).read_bytes()
    tis = parse_standalone_tis(tis_bytes)
    prefix = area[0]+area[2:]
    baseline = ROOT / request['baseline']
    prior = ROOT / request['prior']
    bg2lib.GAME_DIR = str(args.vanilla.resolve(strict=True))
    bg2lib.KEY_PATH = str(Path(bg2lib.GAME_DIR)/'chitin.key')
    bifs,resources = bg2lib.load_key()
    index = {(name,kind):loc for name,kind,loc in resources}
    pvr = {name:(name,kind,loc) for name,kind,loc in resources if kind == 0x404}
    wed_bytes,_ = bg2lib.resolve_resource(bifs,index[area,0x3E9])
    parsed = parse_wed(wed_bytes)
    assert parsed['layers'][0]['tis'] == area
    live_wed_bytes = (live / (area+'.WED')).read_bytes()
    live_wed = parse_wed(live_wed_bytes)
    assert live_wed['cells'] == parsed['cells'], 'Live WED cell geometry diverges from native'
    assert all(live_wed['layers'][0][key] == parsed['layers'][0][key]
               for key in ('width','height','tis')), 'Live WED base geometry diverges'
    stock_tile,_ = decode_tis_tiles(bifs,pvr,area,index[area,0x3EB])
    full = {}
    for c in parsed['cells']:
        if c['count'] == 1 and c['secondary'] == 65535 and c['flags'] & sum(1<<s for s in request['slots']):
            if np.all(np.asarray(stock_tile(c['primary'][0]))[:,:,3] == 255):
                full[c['x'],c['y']] = c['primary'][0]
    interfaces = water_art_edge_masks(parsed,request['slots'],stock_tile,full)
    physical = Counter(tis['entries'])
    logical = Counter(c['secondary'] if c['secondary']!=65535 else c['primary'][0]
                      for c in parsed['cells'] if c['count'] == 1)
    masks,coords = {},{}
    by_tile = defaultdict(list)
    for interface in interfaces:
        tile = interface['tile']
        assert physical[tis['entries'][tile]] == 1 and logical[tile] == 1, f'Art slot alias: {tile}'
        masks[tile] = np.maximum(masks.get(tile,np.zeros((256,256),np.float32)),interface['mask'])
        coords[tile] = interface['cell']
        by_tile[tile].append(interface)
    pages = defaultdict(list)
    for tile in masks:
        pages[tis['entries'][tile][0]].append(tile)
    results, page_reports, tile_reports, previews = {},[],[],[]
    donor_path = ROOT / request['donor']
    with Image.open(donor_path) as donor:
        assert donor.size == (parsed['layers'][0]['width']*256,parsed['layers'][0]['height']*256)
        for page,tiles in sorted(pages.items()):
            name = f'{prefix}{page:02d}.PVRZ'
            source = (live/name).read_bytes()
            expected = prior/name if (prior/name).exists() else baseline/name
            assert source == expected.read_bytes(), f'Unexpected live page: {name}'
            raw,fmt,width,height,offset = parse_pvr(source)
            assert fmt == 11
            original = np.frombuffer(bytes(raw),np.uint8,offset=offset).reshape(height//4,width//4,16)
            blocks = np.frombuffer(raw,np.uint8,offset=offset).reshape(original.shape)
            allowed = np.zeros(blocks.shape[:2],bool)
            before = decode_pvrz_page(source).convert('RGBA')
            local = []
            for tile in sorted(tiles):
                _,x,y = tis['entries'][tile]
                assert (x%264,y%264) == (4,4)
                assert 0<=x-4<x+260<=width and 0<=y-4<y+260<=height
                for other,(op,ox,oy) in enumerate(tis['entries']):
                    if op == page and other != tile:
                        assert max(x-4,ox-4)>=min(x+260,ox+260) or max(y-4,oy-4)>=min(y+260,oy+260)
                cx,cy = coords[tile]
                core = np.array(before.crop((x,y,x+256,y+256)))
                weight = masks[tile][:,:,None]
                assert np.all(core[:,:,3][masks[tile]>0] >= 160), f'Matte guard violation {tile}'
                replacement = np.array(donor.crop((cx*256,cy*256,(cx+1)*256,(cy+1)*256)).convert('RGB'))
                metrics = [{k:v for k,v in i.items() if k!='mask'} | {
                    'before':rgb_seam_difference(core,replacement,i['mask'])} for i in by_tile[tile]]
                core[:,:,:3] = np.rint(core[:,:,:3]*(1-weight)+replacement*weight).clip(0,255).astype(np.uint8)
                coded = np.frombuffer(encode_bc3(np.pad(core,((4,4),(4,4),(0,0)),mode='edge')),
                                      np.uint8).reshape(66,66,16)
                mask = block_mask(masks[tile]>0)
                bx,by = (x-4)//4,(y-4)//4
                view = blocks[by:by+66,bx:bx+66]
                view[mask,8:] = coded[mask,8:]
                allowed[by:by+66,bx:bx+66] |= mask
                local.append((tile,x,y,replacement,metrics))
            assert np.array_equal(original[:,:,:8],blocks[:,:,:8]), 'Alpha changed'
            assert np.array_equal(original[~allowed,8:],blocks[~allowed,8:]), 'RGB outside bands changed'
            result = struct.pack('<I',len(raw))+zlib.compress(raw,9)
            after = decode_pvrz_page(result).convert('RGBA')
            assert np.array_equal(np.asarray(before)[:,:,3],np.asarray(after)[:,:,3])
            pixels = allowed.repeat(4,0).repeat(4,1)
            assert np.array_equal(np.asarray(before)[~pixels],np.asarray(after)[~pixels])
            for tile,x,y,replacement,metrics in local:
                fixed = np.array(after.crop((x,y,x+256,y+256)))
                for metric,i in zip(metrics,by_tile[tile]):
                    metric['after'] = rgb_seam_difference(fixed,replacement,i['mask'])
                    assert metric['after'][i['side']] < 4, f'Edge compression error: {tile}/{i["side"]}'
                tile_reports.append({'tile':tile,'cell':coords[tile],'interfaces':metrics})
                if coords[tile] in ([30,10],[31,10],[30,9],[29,11],[29,12]):
                    preview = Image.new('RGB',(528,264))
                    preview.paste(before.crop((x-4,y-4,x+260,y+260)).convert('RGB'),(0,0))
                    preview.paste(after.crop((x-4,y-4,x+260,y+260)).convert('RGB'),(264,0))
                    previews.append((f'tile-{tile}-before-after.png',preview))
            changed = int(np.any(original[:,:,8:] != blocks[:,:,8:],axis=2).sum())
            page_reports.append({'name':name,'source_sha256':sha(source),'output_sha256':sha(result),
                                 'rgb_blocks_changed':changed,'alpha_blocks_changed':0})
            if changed:
                results[name] = result
    args.output.mkdir(parents=True,exist_ok=False)
    candidate = args.output/'override-candidate'
    candidate.mkdir()
    for name,data in results.items(): (candidate/name).write_bytes(data)
    for name,img in previews: img.save(args.output/name)
    write_json(candidate/'manifest.json',{'schema':'bg2-upscale-area-animation-override-assets-v1',
        'status':'completed','area':area,'scope':'all safe water art tile edges; RGB only',
        'files':{name:{'bytes':len(data),'sha256':sha(data)} for name,data in results.items()}})
    report = {'schema':'bg2-water-all-rgb-edges-v1','area':area,
        'request':args.request.resolve().relative_to(ROOT).as_posix(),
        'tis_sha256':sha(tis_bytes),'native_wed_sha256':sha(wed_bytes),'live_wed_sha256':sha(live_wed_bytes),
        'donor_sha256':sha(donor_path.read_bytes()),
        'interfaces':len(interfaces),'interface_kinds':dict(Counter(i['kind'] for i in interfaces)),
        'tiles':tile_reports,'pages':page_reports,'files_changed':len(results),
        'alpha_byte_exact':True,'outside_rgb_block_footprint_byte_exact':True,
        'qa':'pending-ingame','installation':'separate receipt'}
    write_json(args.output/'build.json',report)
    print(json.dumps({k:report[k] for k in ['area','interfaces','interface_kinds','files_changed','alpha_byte_exact']},indent=2))


if __name__ == '__main__': main()
