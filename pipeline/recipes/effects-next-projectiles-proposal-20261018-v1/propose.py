"""Source-only cohort proposal; does not start production or mutate authorities."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import re
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam, native_palette_alpha
from export_bam_frames import read_bam, cycle_metadata
from workspace_paths import get_path

OUT = ROOT / 'effects/batches/lot31-projectiles-control-proposal-20261018-v1'
GROUPS = {
    'projectiles-physiques': 'ARARROW AXE BOLT DAGGER DART SPEAR TRDARTST'.split(),
    'projectiles-magiques': 'ACIDBLOB MAGICSTN SPFIREBL SPFLMARR SPRDRABU STNKCLDT TRAVEL WEBENTT BDETHREA'.split(),
    'impacts-manifestations': 'SPGREAAI SPGREAXI SPIMPPT SPNPOISI SPRMPARI SPSCHGI'.split(),
    'marques-sol-controle': 'GLPHWRDH GREASED GREASEH SKLH SPENTACI WEBENTD WEBENTH'.split(),
    'protections-cylindriques': 'SANCTRY SPSHIELD'.split(),
}


def stock_evidence():
    """Validate references as BCS visual actions / SPL effect resource fields."""
    from bg2lib import load_key, resolve_resource
    import struct
    bifs, entries = load_key()
    index = {(n.upper(), t): loc for n, t, loc in entries}
    owners = {
        'SPGREAAI': [('ohrcut40', 1007), ('ohrwheel', 1007), ('ohryxtra', 1007)],
        'SPGREAXI': [('ohrshad', 1006)],
        'SPIMPPT': [('CUT217C', 1007), ('CUT218B', 1007), ('SPPR728', 1006)],
        'SPNPOISI': [('TEARDOOR', 1007)],
        'SPRMPARI': [('BALTH08', 1006)],
        'SPSCHGI': [('ohrshad', 1006)],
    }
    evidence = {}
    for name, resources in owners.items():
        refs = []
        for owner, typ in resources:
            data, bif = resolve_resource(bifs, index[owner.upper(), typ])
            hits = []
            if typ == 1007:
                txt = data.decode('latin1')
                for hit in re.finditer('"' + name + '"', txt, re.IGNORECASE):
                    start = txt.rfind('\nAC\n', 0, hit.start())
                    aid = int(re.match(r'\nAC\n(\d+)', txt[start:])[1])
                    assert aid in (272, 273), (name, owner, aid)
                    hits.append({'resource_offset': hex(hit.start()+1), 'action_id': aid,
                        'action': 'CreateVisualEffect' if aid == 272 else 'CreateVisualEffectObject'})
            else:
                effect_offset = struct.unpack_from('<I', data, 0x6a)[0]
                for pos in range(effect_offset, len(data)-47, 48):
                    resref = data[pos+20:pos+28].rstrip(b'\0').decode('ascii', errors='replace').upper()
                    if resref == name:
                        opcode = struct.unpack_from('<H', data, pos)[0]
                        assert opcode == 215, (name, owner, opcode)
                        hits.append({'resource_offset': hex(pos+20), 'effect_offset': hex(pos), 'opcode': opcode})
            assert hits, (name, owner)
            refs.append({'owner': owner, 'resource_type': 'BCS' if typ == 1007 else 'SPL',
                'sha256': digest(data), 'bif': bif, 'references': hits})
        evidence[name] = refs
    return evidence



def rows(path):
    return list(csv.DictReader((ROOT / path).open(encoding='utf-8-sig', newline='')))


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, 'Do not overwrite previous proposal'
    else:
        path.write_bytes(raw)


def main():
    work = {r['resref']: r for r in rows('effects/index/work-items.csv')}
    source = {r['resref']: r for r in rows('effects/index/bam-assets.csv')}
    state = {r['asset_key'].rsplit(':', 1)[-1]: r for r in rows('effects/index/processing.csv')}
    consumers = rows('effects/index/consumers.csv')
    stock = stock_evidence()
    animations = {p.stem.upper() for p in (ROOT / 'animations/index/selections').glob('*.json')}
    used = {r['canonical_sha256'] for n, r in work.items() if state[n]['spatial_state'] != 'not-started' or state[n]['selected_run'] or n in animations}
    exe = (get_path('bg2ee_game_root', required=True) / 'BaldurReal.exe').read_bytes()
    exe_upper = exe.upper()
    # Exact NUL-terminated literals, bounded on both sides to avoid DUST in DSTDUST.
    def engine_offset(name):
        match = re.search(rb'(?<![A-Z0-9_])' + name.encode() + rb'\x00', exe_upper)
        return match.start() if match else None
    selected, audits, tiles = [], [], []
    aliases_all = {}
    for group, names in GROUPS.items():
        for name in names:
            w, src, s = work[name], source[name], state[name]
            assert w['source_state'] == 'available' and s['spatial_state'] == 'not-started' and not s['selected_run']
            assert w['canonical_sha256'] not in used and name not in animations
            aliases = [n for n, v in work.items() if n != name and v['canonical_sha256'] == w['canonical_sha256']]
            for alias in aliases:
                assert state[alias]['spatial_state'] == 'not-started' and not state[alias]['selected_run']
            aliases_all[name] = aliases
            data = (ROOT / src['extracted_path']).read_bytes()
            assert digest(data) == src['source_sha256'].upper()
            raw = read_bam(ROOT / src['extracted_path'])
            assert digest(raw) == w['canonical_sha256']
            frames, palette, tr = decode_bam(raw)
            alpha = native_palette_alpha(raw, tr)
            cycles = cycle_metadata(raw, len(frames))
            l = min(-cx for _, cx, _, _ in frames); t = min(-cy for _, _, cy, _ in frames)
            r = max(-cx + idx.shape[1] for idx, cx, _, _ in frames)
            b = max(-cy + idx.shape[0] for idx, _, cy, _ in frames)
            keys, scores, grayscale, covered = [], [], 0, 0
            for idx, cx, cy, _ in frames:
                canvas = np.zeros((b-t,r-l,4), np.uint8); x, y = -cx-l, -cy-t
                rgba = np.dstack((palette[idx], alpha[idx])); rgba[rgba[:,:,3] == 0] = 0
                canvas[y:y+idx.shape[0],x:x+idx.shape[1]] = rgba
                keys.append(digest(canvas.tobytes()))
                mask = idx != tr
                rgb = palette[idx][mask]
                covered += len(rgb)
                grayscale += int((rgb.max(1)-rgb.min(1) < 8).sum())
                scores.append(int(rgb.astype(np.int64).max(1).sum()))
            counts = []
            for c in cycles:
                values = [keys[i] for i in c['frame_indices']]
                counts.append({'cycle': c['cycle'], 'native_slots': len(values), 'distinct_anchored_rgba': len(set(values)),
                               'repeated_slots': len(values)-len(set(values)),
                               'constant_native_cycle': len(set(values)) <= 1,
                               'adjacent_duplicate_slots': [i for i in range(1,len(values)) if values[i] == values[i-1]]})
            assert max(scores) > 0, 'Black-only runtime mask is not an RGB effect production'
            literal = engine_offset(name)
            owners = [c for c in consumers if c['asset_key'].rsplit(':',1)[-1] in [name] + aliases]
            assert literal is not None or owners or name in stock, name
            selected.append({'ordinal': len(selected)+1, 'resref': name, 'asset_key': w['asset_key'], 'group': group,
                'source': src['extracted_path'], 'source_sha256': digest(data), 'canonical_sha256': digest(raw),
                'reuse_aliases': aliases, 'source_frames': len(frames), 'native_cycles': cycles,
                'native_fps': w['native_fps'], 'playback_hint': w['playback'],
                'raw_x4_bytes_at_native_records': int(w['raw_x4_bytes']),
                'engine_literal_file_offset': hex(literal) if literal is not None else None,
                'usage_index': w['usage'], 'usage_evidence': 'native-executable-literal' if literal is not None else 'controller-consumer' if owners else 'stock-visual-action-or-opcode215',
                'stock_visual_references': stock.get(name, []),
                'source_tags': w['tags'],
                'palette_contexts': sorted({(o['palette'], o['color_enabled'], o['colors']) for o in owners}),
                'consumers': owners, 'grayscale_covered_fraction': grayscale/max(1,covered),
                'normal_palette_alpha_levels': sorted(int(v) for v in np.unique(alpha)),
                'production': {k:s[k] for k in ('spatial_state','interpolation_state','qa_state','installation_state')},
                'runtime_contract_to_observe': 'native FPS/cycle/once-loop/blend/tint; literal existence is not runtime measurement'})
            audits.append({'resref': name, 'cycles': counts})
            tile = Image.new('RGB',(256,190),(24,27,34)); draw = ImageDraw.Draw(tile)
            draw.text((7,5),f'{len(selected):02d} {name}  {len(frames)}f/{len(cycles)}c',font=FONT,fill='white')
            draw.text((7,27),'engine literal' if literal is not None else 'PRO/VVC' if owners else 'BCS/SPL visual',font=SMALL,fill=(145,185,210))
            choices=[]
            for n in sorted(range(len(frames)),key=lambda n:scores[n],reverse=True):
                if all(abs(n-v)>max(1,len(frames)//5) for v in choices): choices.append(n)
                if len(choices)==3: break
            for j,n in enumerate(sorted(choices)):
                idx,_,_,_=frames[n]; im=Image.fromarray(np.dstack((palette[idx],alpha[idx])),'RGBA')
                im.thumbnail((78,125),Image.Resampling.NEAREST)
                if max(im.size)<60:
                    k=max(1,min(3,78//max(1,im.width),125//max(1,im.height)));im=im.resize((im.width*k,im.height*k),Image.Resampling.NEAREST)
                tile.paste(im,(j*84+(84-im.width)//2,53+(125-im.height)//2),im)
            tiles.append(tile)
    assert len(selected)==31 and len({a['canonical_sha256'] for a in selected})==31
    summary = {'distinct_productions':len(selected),'covered_resrefs':sum(1+len(a['reuse_aliases']) for a in selected),
        'source_frames':sum(a['source_frames'] for a in selected),'native_cycles':sum(len(a['native_cycles']) for a in selected),
        'native_slots_alternative_cycles_not_global_duration':sum(c['native_slots'] for a in audits for c in a['cycles']),
        'repeated_native_slots':sum(c['repeated_slots'] for a in audits for c in a['cycles']),
        'assets_with_repeats':sum(any(c['repeated_slots'] for c in a['cycles']) for a in audits),
        'constant_native_cycles':sum(c['constant_native_cycle'] for a in audits for c in a['cycles']),
        'raw_x4_bytes_at_native_records':sum(a['raw_x4_bytes_at_native_records'] for a in selected),
        'groups':{k:len(v) for k,v in GROUPS.items()},
        'palette_tagged_assets':sum('palette' in a['source_tags'] for a in selected),
        'usage_evidence':dict(Counter(a['usage_evidence'] for a in selected))}
    save(OUT/'batch.json',{'schema':'bg2-effects-batch-proposal-v1','date':'2026-10-18','status':'proposed-source-only',
        'family':'Projectiles, visual impacts, ground control and cylindrical protections','summary':summary,'subgroups':GROUPS,
        'aliases':{n:v for n,v in aliases_all.items() if v},'assets':selected,
        'engine':{'path':'config://bg2ee_game_root/BaldurReal.exe','sha256':digest(exe),'literal_match':'case-insensitive exact NUL-terminated, alphanumeric boundary'},
        'scope_notes':['Existing production hashes and accepted animations excluded; sources and distinct canonical BAMs checked.',
            'Usage evidence: PRO/VVC consumers, exact native literals or parsed BCS actions 272/273 and SPL opcode215 resource fields; local proposal evidence only.',
            'No claim that every engine literal is executed in the tested session. Native tint/FPS/blend/phase contracts need observing during integration.',
            'Projectile palette/color contexts must be preserved at runtime; one fixed RGB output must not flatten all native recolorings.',
            'Source native alpha must be preserved; bright-mode encoding and normal-mode encoding must remain separate.'],
        'proposed_recipe':{'rgb':'SeedVR7B x4, geometry and fine particles retained','time':'Apollo30 per cycle, duplicate native poses removed with exact native duration retained; constant cycles retained',
            'alpha':'native palette alpha and native blend; fine arrows/glyphs retain detail, diffuse edges treated separately; no universal black key/erosion/feather',
            'production_started':False}})
    save(OUT/'native-duplicate-audit.json',{'summary':summary,'assets':audits})
    sheet=Image.new('RGB',(1280,55+((len(tiles)+4)//5)*190),(14,16,21));draw=ImageDraw.Draw(sheet)
    draw.text((12,12),'Lot31 - projectiles, manifestations et controle / sources natives',font=TITLE,fill='white')
    for k,tile in enumerate(tiles): sheet.paste(tile,((k%5)*256,55+(k//5)*190))
    (OUT/'preview').mkdir(exist_ok=True);sheet.save(OUT/'preview/native.png')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


FONT=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
SMALL=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',12)
TITLE=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',20)
if __name__=='__main__':main()
