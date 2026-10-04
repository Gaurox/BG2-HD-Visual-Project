"""Read cached planes only; build standalone FR/EN offline teaching proposals.
No inference, registry writes, installation, original-page edit or QA transfer.
Run: chaiNNer/python/python.exe -X utf8 -B build_visuals.py
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from palette_frac_encode import decode as decode_v6
import palette_partner_registry as v7
from run_creature_sprite_x2 import catalog_shard_filename

P1 = ROOT / 'sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p1-20260930-v1'
FAMILY = ROOT / 'docs/measurements/q3m-families-engine-x2-20261003-v2'
ANKHEG = ROOT / 'docs/measurements/q3m-monster-ankheg-full-x2-20261003-v1'
GOLD, TEAL, PAPER, MUTED = '#caa45b', '#8fbfc3', '#e9dfca', '#b9ae99'
INK, CARD, BORDER = '#090b0c', '#101314', '#35332b'
LAYER_ORDER = ['body', 'helmet', 'shield', 'weapon']
ORACLE_HASHES = {}
LABELS = {'fr': ['Corps', 'Casque', 'Bouclier', 'Arme'], 'en': ['Body', 'Helmet', 'Shield', 'Weapon']}
MANIFEST = {'schema': 'bg2-pedagogical-offline-visual-proposals-v1', 'integration': 'awaiting-user-validation',
            'ingame_capture': False, 'sources': {}, 'original_pages': {}, 'checks': {},
            'scope': 'four proposals for the three existing visual placeholders; no original page change'}


def read(path):
    path = Path(path)
    b = path.read_bytes()
    MANIFEST['sources'][path.relative_to(ROOT).as_posix()] = hashlib.sha256(b).hexdigest()
    return b


def load(path):
    return json.loads(read(path))


def png(array, filename):
    dest = OUT / 'assets' / filename
    Image.fromarray(array.astype(np.uint8), 'RGBA').save(dest)
    return 'assets/' + filename


def raw(array):
    return base64.b64encode(np.ascontiguousarray(array, dtype=np.uint8).tobytes()).decode()


def oracle(path):
    b = read(path)
    assert b[:8] == b'IEEQP7\0\0'
    pos = 12
    result = {}
    for _ in range(struct.unpack_from('<I', b, 8)[0]):
        aid, owner, ref, nf, nc = struct.unpack_from('<II8sII', b, pos)
        pos += 24
        palettes = np.frombuffer(b, np.uint8, 6*256*4, pos).reshape(6, 256, 4).copy()
        pos += 6*256*4 + 2052
        for __ in range(nc):
            slots = struct.unpack_from('<I', b, pos)[0]
            pos += 4 + slots*4
        name = ref.rstrip(b'\0').decode()
        for fi in range(nf):
            pos += 16
            ORACLE_HASHES[(aid,name,fi)] = [b[pos+i*32:pos+(i+1)*32].hex() for i in range(6)]
            pos += 6*32
        result[(aid, name)] = palettes
    assert pos == len(b)
    return result


def leaf(path):
    read(path)
    return v7.inspect(path, include_frames=True)['resources'][0]


def source_over(dst, src):
    """Float straight RGBA source-over; transparent RGB canonicalized."""
    a = src[..., 3:4]
    alpha = a + dst[..., 3:4]*(1-a)
    rgb = np.divide(src[..., :3]*a + dst[..., :3]*dst[..., 3:4]*(1-a), alpha,
                    out=np.zeros_like(src[..., :3]), where=alpha > 1e-8)
    return np.concatenate((rgb, alpha), axis=-1)


def composite(parts, scale=2):
    bounds = [min(-p['cx'] for p in parts), min(-p['cy'] for p in parts),
              max(p['w']-p['cx'] for p in parts), max(p['h']-p['cy'] for p in parts)]
    w, h = (bounds[2]-bounds[0])*scale, (bounds[3]-bounds[1])*scale
    canvas = np.zeros((h, w, 4), np.float64)
    for p in parts:
        a = p['rgba'].astype(float)/255
        x, y = (-p['cx']-bounds[0])*scale, (-p['cy']-bounds[1])*scale
        hh, ww = a.shape[:2]
        canvas[y:y+hh, x:x+ww] = source_over(canvas[y:y+hh, x:x+ww], a)
    return np.rint(np.clip(canvas, 0, 1)*255).astype(np.uint8), bounds


def premul(rgba, rounded=False):
    p = rgba.astype(float)/255
    p[..., :3] *= p[..., 3:4]
    return np.floor(p*255+.500000001)/255 if rounded else p


def straight(p):
    a = np.clip(p[..., 3:4], 0, 1)
    rgb = np.clip(p[..., :3], 0, a)
    rgb = np.divide(rgb, a, out=np.zeros_like(rgb), where=a > 1e-6)
    return np.concatenate((rgb, a), axis=-1)


def at(a, x, y):
    # Transparent border model, equivalent to CLAMP_TO_EDGE after transparent
    # padding for the selected sampling region. No neighbouring atlas data.
    valid = (x >= 0) & (y >= 0) & (x < a.shape[1]) & (y < a.shape[0])
    return a[np.clip(y, 0, a.shape[0]-1), np.clip(x, 0, a.shape[1]-1)] * valid[..., None]


def area_matrix(src, dst):
    lo = np.arange(dst)*src/dst
    hi = (np.arange(dst)+1)*src/dst
    return np.maximum(0, np.minimum(hi[:, None], np.arange(src)+1) -
                         np.maximum(lo[:, None], np.arange(src))) / (src/dst)


def mip_chain(rgba):
    # Representative CPU model of glGenerateMipmap: premultiplied RGBA8,
    # area-averaged NPOT floor-halves. Driver kernels are implementation-defined.
    chain = [premul(rgba, rounded=True)]
    while max(chain[-1].shape[:2]) > 1:
        a = chain[-1]
        h, w = a.shape[:2]
        hh, ww = max(1, h//2), max(1, w//2)
        b = np.einsum('ys,sxc,wx->ywc', area_matrix(h, hh), a, area_matrix(w, ww), optimize=True)
        chain.append(np.floor(b*255+.500000001)/255)
    return chain


def bilinear(a, x, y):
    bx, by = np.floor(x-.5).astype(int), np.floor(y-.5).astype(int)
    tx, ty = x-.5-bx, y-.5-by
    out = np.zeros(x.shape+(4,))
    for j in range(2):
        for i in range(2):
            out += at(a, bx+i, by+j) * ((tx if i else 1-tx)*(ty if j else 1-ty))[..., None]
    return out


def sample(rgba, x, y, footprint, method):
    if method == 'Nearest' or (method in ('BOX', 'Mipmaps') and footprint <= 1):
        return at(rgba.astype(float)/255, np.floor(x).astype(int), np.floor(y).astype(int))
    p = premul(rgba)
    if method == 'BOX':
        if footprint > 16:
            return sample(rgba, x, y, footprint, 'Nearest')
        lx, ly = x-footprint/2, y-footprint/2
        bx, by = np.floor(lx).astype(int), np.floor(ly).astype(int)
        out = np.zeros(x.shape+(4,))
        for j in range(math.ceil(footprint)+1):
            wy = np.maximum(0, np.minimum(ly+footprint, by+j+1)-np.maximum(ly, by+j))
            for i in range(math.ceil(footprint)+1):
                wx = np.maximum(0, np.minimum(lx+footprint, bx+i+1)-np.maximum(lx, bx+i))
                out += at(p, bx+i, by+j)*(wx*wy)[..., None]
        return straight(out / footprint**2)
    if method == 'Catmull-Rom':
        bx, by = np.floor(x-.5).astype(int), np.floor(y-.5).astype(int)
        tx, ty = x-.5-bx, y-.5-by
        def weights(t):
            return [-.5*t**3+t*t-.5*t, 1.5*t**3-2.5*t*t+1,
                    -1.5*t**3+2*t*t+.5*t, .5*t**3-.5*t*t]
        wx, wy = weights(tx), weights(ty)
        out = np.zeros(x.shape+(4,))
        for j in range(4):
            for i in range(4):
                out += at(p, bx+i-1, by+j-1)*(wx[i]*wy[j])[..., None]
        return straight(out)
    assert method == 'Mipmaps'
    chain = mip_chain(rgba)
    lod = min(math.log2(footprint), len(chain)-1)
    level = int(lod)
    a = chain[level]
    b = chain[min(level+1, len(chain)-1)]
    aa = bilinear(a, x*a.shape[1]/rgba.shape[1], y*a.shape[0]/rgba.shape[0])
    bb = bilinear(b, x*b.shape[1]/rgba.shape[1], y*b.shape[0]/rgba.shape[0])
    return straight(aa*(1-(lod-level)) + bb*(lod-level))


def filtered(parts, scale, zoom, method, phase=.25):
    bounds = [-40, -75, 40, 15]
    width, height = math.ceil(80*zoom), math.ceil(90*zoom)
    yy, xx = np.mgrid[:height, :width]
    world_x, world_y = bounds[0]+(xx+.5-phase)/zoom, bounds[1]+(yy+.5-phase)/zoom
    canvas = np.zeros((height, width, 4), float)
    for p in parts:
        layer = sample(p['rgba'], (world_x+p['cx'])*scale, (world_y+p['cy'])*scale, scale/zoom, method)
        canvas = source_over(canvas, layer)
    return np.rint(np.clip(canvas, 0, 1)*255).astype(np.uint8)


def background(width, height, kind='stone'):
    yy, xx = np.mgrid[:height, :width]
    if kind == 'parchment':
        base = np.array([184, 166, 132.])
        noise = 2*np.sin(xx*.079)*np.cos(yy*.057) + 1.2*np.sin(xx*.021+yy*.039)
    elif kind == 'grid':
        base = np.array([19, 25, 27.])
        noise = np.zeros((height, width))
        noise[(xx%24 == 0) | (yy%24 == 0)] = 8
        noise[(xx%120 == 0) | (yy%120 == 0)] = 13
    else:
        base = np.array([61, 64, 60.])
        noise = 2.5*np.sin(xx*.08+yy*.035)*np.cos(yy*.11) + 1.1*np.sin(xx*.43+yy*.21)
        row = yy//70
        seams = (yy%70 < 2) | ((xx+(row%2)*57)%114 < 2)
        noise[seams] -= 16
        noise[yy%70 == 3] += 5
    return Image.fromarray(np.clip(base+noise[..., None], 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def font(size, title=False, mono=False):
    name = 'consola.ttf' if mono else ('georgia.ttf' if title else 'calibri.ttf')
    return ImageFont.truetype(str(Path('C:/Windows/Fonts') / name), size)


def text(draw, xy, value, size=24, fill=PAPER, title=False, mono=False):
    draw.text(xy, value, font=font(size, title, mono), fill=fill)


def wrap(draw, value, width, size=22):
    lines, line = [], ''
    for word in value.split():
        test = line+' '+word if line else word
        if draw.textlength(test, font=font(size)) > width and line:
            lines.append(line)
            line = word
        else:
            line = test
    return lines+[line]


def paragraph(draw, xy, value, width, size=22, fill=MUTED):
    x, y = xy
    for line in wrap(draw, value, width, size):
        text(draw, (x, y), line, size, fill)
        y += size+6
    return y


def board(title, subtitle, height, lang):
    im = Image.new('RGBA', (1600, height), INK)
    d = ImageDraw.Draw(im)
    text(d, (45, 27), 'PROPOSITION · SIMULATION HORS JEU' if lang=='fr' else 'PROPOSAL · OFFLINE SIMULATION', 20, GOLD, mono=True)
    text(d, (45, 68), title, 36, title=True)
    text(d, (45, 118), subtitle, 23, MUTED)
    d.line((45, 155, 1555, 155), fill=BORDER, width=2)
    return im, d


def panel(im, box, kind):
    x, y, w, h = box
    im.alpha_composite(background(w, h, kind), (x, y))
    ImageDraw.Draw(im).rectangle((x, y, x+w-1, y+h-1), outline=BORDER, width=2)


def paste(im, rgba, x, y, factor=1):
    a = Image.fromarray(rgba, 'RGBA')
    if factor != 1:
        a = a.resize((int(a.width*factor), int(a.height*factor)), Image.Resampling.NEAREST)
    im.alpha_composite(a, (int(x), int(y)))


def anchor(d, x, y):
    d.ellipse((x-4, y-4, x+4, y+4), outline=GOLD, width=2)
    d.line((x-10, y, x+10, y), fill=GOLD, width=2)
    d.line((x, y-10, x, y+10), fill=GOLD, width=2)


def assembly_board(pose, lang):
    im, d = board('A · Quatre calques, un même point de référence' if lang=='fr' else 'A · Four layers, one shared reference point',
        'Q3m K6 x2 · pose synchronisée · coordonnées natives conservées' if lang=='fr' else 'Q3m K6 x2 · synchronized pose · native coordinates preserved', 690, lang)
    parts = pose['parts'][2]
    for i in range(5):
        x = 45+i*305
        panel(im, (x, 184, 285, 310), 'grid')
        ax, ay, zoom = x+143, 420, 3
        text(d, (x+14, 198), LABELS[lang][i] if i<4 else ('Assemblage' if lang=='fr' else 'Assembly'), 25, GOLD)
        selection = [parts[i]] if i<4 else parts
        for p in selection:
            paste(im, p['rgba'], ax-p['cx']*zoom, ay-p['cy']*zoom, zoom/2)
            if i<4:
                d.rectangle((ax-p['cx']*zoom, ay-p['cy']*zoom, ax+(p['w']-p['cx'])*zoom-1,
                             ay+(p['h']-p['cy'])*zoom-1), outline=TEAL, width=1)
        anchor(d, ax, ay)
        d.line((x+15, ay, x+270, ay), fill='#59604e', width=1)
        anchor(d, ax, ay)
        if i<4:
            p = parts[i]
            text(d, (x+14, 447), f"C = ({p['cx']}, {p['cy']})", 22, mono=True)
            text(d, (x+4, 507), p['key'], 19, TEAL, mono=True)
        else:
            text(d, (x+14, 447), 'A = référence' if lang=='fr' else 'A = reference', 22, mono=True)
            text(d, (x+4, 507), 'Même pose / même palette' if lang=='fr' else 'Same pose / same palette', 20, TEAL)
    text(d, (45, 554), 'Origine du calque = A − centre × zoom' if lang=='fr' else 'Layer origin = A − centre × zoom', 27, GOLD)
    paragraph(d, (45, 598), 'Le casque conserve le même repère que le corps, même si ce repère se trouve hors de son petit rectangle. Palette commune et ordre fixe pour cette démonstration ; agrandissement des pixels sans interpolation.' if lang=='fr' else 'The helmet uses the same reference as the body, even when it falls outside its small rectangle. Shared palette and fixed order for this demonstration; pixels enlarged without interpolation.', 1510)
    return im


def filter_board(pose, lang):
    im, d = board('B · Le filtre change la réduction, pas le contenu' if lang=='fr' else 'B · Filtering changes reduction, not the source content',
        'Même pose · texture x4 · zoom x1,35 · fonds et position identiques' if lang=='fr' else 'Same pose · x4 texture · x1.35 zoom · identical backgrounds and position', 810, lang)
    zoom, scale = 1.35, 4
    methods = ['Nearest', 'BOX', 'Mipmaps', 'Catmull-Rom']
    rendered = []
    for i, method in enumerate(methods):
        x = 45+i*383
        panel(im, (x, 184, 361, 260), 'stone')
        a = filtered(pose['parts'][scale], scale, zoom, method)
        rendered.append(a)
        paste(im, a, x+126, 266)
        text(d, (x+16, 198), method, 27, GOLD if method=='BOX' else PAPER)
        text(d, (x+16, 406), 'Choix retenu' if lang=='fr' else 'Selected option', 21, GOLD) if method=='BOX' else None
    text(d, (45, 465), 'Loupe du casque · mêmes pixels affichés, agrandis ×5 sans lissage' if lang=='fr' else 'Helmet close-up · same displayed pixels, enlarged ×5 without smoothing', 24, TEAL)
    for i, a in enumerate(rendered):
        x = 45+i*383
        panel(im, (x, 505, 361, 176), 'stone')
        crop = a[18:50, 35:73]
        paste(im, crop, x+85, 513, 5)
    paragraph(d, (45, 706), 'BOX moyenne la surface couverte par chaque pixel écran. Les mipmaps mélangent des niveaux déjà réduits ; ici, leur génération est simulée par des moyennes RGBA prémultipliées. Catmull-Rom reconstruit localement 4 × 4 texels. Aucun temps GPU ni résultat de QA n’est calculé par cette simulation.' if lang=='fr' else 'BOX averages the area covered by each screen pixel. Mipmaps blend pre-reduced levels; their generation is modeled here with premultiplied RGBA averages. Catmull-Rom reconstructs locally from 4 × 4 texels. This simulation computes no GPU timings or QA result.', 1510)
    return im


def gallery_board(gallery, lang):
    im, d = board('C · Plusieurs créatures, plusieurs profils de palette' if lang=='fr' else 'C · Different creatures, different palette profiles',
        'V7 x2 · exemples réels du pilote de 15 profils · palette K6 #0 neutre' if lang=='fr' else 'V7 x2 · real examples from the 15-profile pilot · neutral K6 palette #0', 905, lang)
    selected = [next(x for x in gallery if x['family']==f) for f in ['monster_large', 'monster', 'monster_quadrant', 'monster_ankheg']]
    for i, g in enumerate(selected):
        x = 45+i*383
        panel(im, (x, 184, 361, 365), 'stone')
        a = g['_rgba']
        factor = min(1, 325/a.shape[1], 265/a.shape[0])
        paste(im, a, x+(361-a.shape[1]*factor)/2, 250+(265-a.shape[0]*factor)/2, factor)
        text(d, (x+15, 198), g['name'][lang], 26, GOLD)
        text(d, (x+15, 518), 'Rampes recolorables' if lang=='fr' and g['kind']==1 else ('Recolourable ramps' if g['kind']==1 else ('Palette fixe' if lang=='fr' else 'Fixed palette')), 21, TEAL)
    g = selected[1]
    p = g['partners']
    text(d, (45, 578), 'Exemple réel · un indice I, quatre partenaires autorisés' if lang=='fr' else 'Real example · one index I, four permitted partners', 27, PAPER)
    text(d, (45, 620), f"I = {p['index']}   ·   code = (B << 3) | F   ·   F = 0…7", 21, TEAL, mono=True)
    for b in range(4):
        x = 45+b*383
        text(d, (x, 659), f"B={b} → J={p['indices'][b]}", 23, GOLD, mono=True)
        for f in range(8):
            c = tuple(((np.array(p['primary'][:3], int)*(8-f)+np.array(p['colours'][b][:3], int)*f+4)//8).tolist())
            d.rectangle((x+f*43, 704, x+f*43+38, 745), fill=c)
            text(d, (x+f*43+10, 752), str(f), 18, MUTED)
    paragraph(d, (45, 801), 'Dans une palette fixe, I + 1 n’est pas nécessairement une nuance voisine. La table choisit des partenaires compatibles avec la classe du pixel. La galerie interactive contient les 15 témoins ; elle ne déclare pas leurs animations complètes ni leur QA validées.' if lang=='fr' else 'In a fixed palette, I + 1 is not necessarily a neighbouring shade. The table selects partners compatible with the pixel class. The interactive gallery contains all 15 witnesses; it does not declare complete animations or accepted QA.', 1510)
    return im


def alpha_board(alpha, lang):
    im, d = board('D · Les couleurs restent identiques, le contour change' if lang=='fr' else 'D · Colours remain identical while the contour changes',
        'Ankheg · MAKHG1 / frame 11 · x2 · même géométrie · alpha séparé' if lang=='fr' else 'Ankheg · MAKHG1 / frame 11 · x2 · same geometry · separate alpha', 1120, lang)
    labels = ['Q3m V7 original', 'Spline Fit 1', 'Alpha léger' if lang=='fr' else 'Light alpha']
    statuses = ['Référence de production', 'Essai rejeté en jeu', 'Essai, QA en attente'] if lang=='fr' else ['Production reference', 'Trial rejected in game', 'Trial, QA pending']
    for i, a in enumerate(alpha['_rgba']):
        x = 45+i*511
        panel(im, (x, 184, 489, 370), 'parchment')
        text(d, (x+16, 198), labels[i], 27, '#29241b')
        paste(im, a, x+(489-a.shape[1])/2, 242)
        text(d, (x+16, 519), statuses[i], 21, '#29241b')
    text(d, (45, 575), 'Loupe synchronisée ×5 · détail du contour choisi parmi les pixels alpha modifiés' if lang=='fr' else 'Synchronized ×5 close-up · contour detail selected from modified alpha pixels', 23, TEAL)
    xx, yy, size = alpha['crop']
    for i, a in enumerate(alpha['_rgba']):
        x = 45+i*511
        panel(im, (x, 617, 489, 160), 'parchment')
        paste(im, a[yy:yy+size, xx:xx+size], x+174, 622, 5)
        panel(im, (x, 794, 489, 160), 'stone')
        paste(im, a[yy:yy+size, xx:xx+size], x+174, 799, 5)
    text(d, (45, 976), 'α final = α de la palette × A / 255' if lang=='fr' else 'Final α = palette α × A / 255', 27, GOLD)
    paragraph(d, (45, 1021), 'La loupe agrandit les pixels sans Catmull-Rom pour isoler l’effet du masque A. Le rejet du candidat spline concernait un essai en jeu combiné à Catmull-Rom ; cette planche ne prouve pas que le filtre seul en était la cause. L’alpha léger conserve le support positif du Q3m original.' if lang=='fr' else 'The close-up enlarges pixels without Catmull-Rom to isolate mask A. The spline rejection concerned an in-game trial combined with Catmull-Rom; this board does not establish the filter alone as the cause. Light alpha preserves the original Q3m positive support.', 1510)
    return im


def build():
    (OUT / 'assets').mkdir(exist_ok=True)
    for suffix in ('', '_EN'):
        p = OUT.parent / f'PRESENTATION_PEDAGOGIQUE_SPRITES_HD_0x6110{suffix}.html'
        MANIFEST['original_pages'][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    exp = load(P1 / 'experiment.json')
    golden = np.load(io.BytesIO(read(P1 / 'decoder-golden.npz')))
    palettes = golden['palettes_rgba']
    assert np.array_equal(decode_v6(golden['I'].reshape(1,-1), golden['F'].reshape(1,-1), palettes[0])[0], golden['expected_rgba'][0])
    poses = []
    selections = [('idle_s', 0, 'Attente', 'Idle'), ('attack_s', 4, 'Attaque', 'Attack'), ('walk_s', 5, 'Marche', 'Walk')]
    for sequence, slot, fr, en in selections:
        selected = {x['layer']: x for x in exp['occurrences'] if x['sequence']==sequence and x['slot']==slot}
        assert set(selected) == set(LAYER_ORDER)
        pose = {'name': {'fr': fr, 'en': en}, 'sequence': sequence, 'slot': slot, 'layers': [], 'parts': {2: [], 4: []}}
        for layer in LAYER_ORDER:
            key = selected[layer]['key']
            geo = exp['frames'][key]
            entry = {'layer': layer, 'key': key, 'w': geo['size'][0], 'h': geo['size'][1],
                     'cx': geo['center'][0], 'cy': geo['center'][1], 'planes': {}}
            for scale in (2, 4):
                z = np.load(io.BytesIO(read(P1/'encoded'/f'{key}-x{scale}.npz')))
                i, f = z['Q3m-k6_I'], z['Q3m-k6_F']
                assert i.shape == (geo['size'][1]*scale, geo['size'][0]*scale)
                entry['planes'][str(scale)] = {'I': raw(i), 'F': raw(f)}
                pose['parts'][scale].append(dict(entry, rgba=decode_v6(i, f, palettes[0])))
            pose['layers'].append(entry)
        poses.append(pose)

    generation = load(FAMILY/'current-generation.json')
    pack = load(FAMILY/'pack-summary.json')
    previews = load(FAMILY/'preview-frames.json')['frames']
    names = {x['family']: x for x in load(ROOT/'sprite/index/q3m-family-witnesses.json')['witnesses']}
    en_names = ['Human fighter', 'Drizzt', 'Spectator', 'Grey dog', 'Water spirit', 'Large wyvern', 'Black dragon',
                'Volo', 'Ankheg', 'Ogre', 'Carrion crawler', 'Rat', 'Horse', 'Sleeping woman', 'Indoor bird']
    pack_dir = ROOT/generation['pack_directory']
    pals = oracle(ROOT/generation['oracle']['path'])
    resources = {}
    for info in pack['leaves']:
        r = leaf(pack_dir/catalog_shard_filename(info['sha256']))
        resources[r['resref']] = r
    gallery = []
    for ix, entry in enumerate(previews):
        aid = int(entry['animation_id'], 16)
        parts = []
        for pose in entry['poses']:
            r = resources[pose['resref']]
            f = r['frames'][pose['frame']]
            w,h,cx,cy,_ = f['geometry']
            assert list((cx,cy)) == pose['center']
            p = pals[(aid,r['resref'])][0]
            # Sealed witness oracle stores fitting RGB plus alpha. Registry
            # profile.source stores BGRA; these are distinct representations.
            rgba = r['profile'].decode(f['I'], f['F'], p)
            assert hashlib.sha256(rgba.tobytes()).hexdigest() == ORACLE_HASHES[(aid,r['resref'],pose['frame'])][0]
            parts.append(dict(w=w,h=h,cx=cx,cy=cy,rgba=rgba))
        a, bounds = composite(parts)
        profile = resources[entry['poses'][0]['resref']]['profile']
        palette = pals[(aid,entry['poses'][0]['resref'])][0]
        example_frame = resources[entry['poses'][0]['resref']]['frames'][entry['poses'][0]['frame']]
        used = np.unique(example_frame['I'][(example_frame['F'] & 7)>0])
        candidates = [int(i) for i in used if profile.classes[i] >= (3 if profile.kind==0 else 4)]
        candidates = [int(i) for i in candidates if len(set(profile.table[i].tolist()))==4]
        # Select an informative actual row, not a made-up colour gradient.
        index = max(candidates, key=lambda i: float(np.linalg.norm(palette[profile.table[i],:3].astype(float)-palette[i,:3],axis=1).mean())) if candidates else int(np.where(profile.classes>=3)[0][0])
        g = {'family': entry['family'], 'name': {'fr': names[entry['family']]['name'], 'en': en_names[ix]},
             'animation': entry['animation_id'], 'kind': profile.kind, 'poses': entry['poses'], 'bounds': bounds,
             'image': png(a, f"gallery-{entry['family']}.png"), '_rgba': a,
             'partners': {'index': index, 'indices': profile.table[index].tolist(), 'primary': palette[index].tolist(),
                          'colours': palette[profile.table[index]].tolist(), 'resref': entry['poses'][0]['resref']}}
        gallery.append(g)

    orig = load(ANKHEG/'production.json')
    original_dir = ROOT/orig['pack_directory']
    ankheg_palettes = oracle(original_dir/'witnesses.oracle')
    alpha = {'labels': ['original', 'spline', 'light'], 'frames': [], '_rgba': []}
    trials = ['q3m-ankheg-spline-fit1-x2-20261003-v1', 'q3m-ankheg-alpha-light-x2-20261004-v1']
    trial_infos = []
    for name in trials:
        p = load(ROOT/'docs/measurements'/name/'production.json')
        detail = next(d for d in p['details'] if d['resref']=='MAKHG1')
        trial_infos.append((ROOT/Path(p['oracle']['path']).parent,detail))
    original_sha = trial_infos[0][1]['V7_sha256']
    variant_paths = [original_dir/catalog_shard_filename(original_sha)] + [path/catalog_shard_filename(d['V8_sha256']) for path,d in trial_infos]
    decoded = []
    pal = ankheg_palettes[(0x3000,'MAKHG1')][0]
    for ix, path in enumerate(variant_paths):
        r = leaf(path)
        f = r['frames'][11]
        rgba = r['profile'].decode(f['I'],f['F'],pal)
        assert hashlib.sha256(rgba.tobytes()).hexdigest() == ORACLE_HASHES[(0x3000,'MAKHG1',11)][0]
        coverage = f.get('A',np.full(f['I'].shape,255,np.uint8))
        rgba[:,:,3] = ((rgba[:,:,3].astype(np.uint16)*coverage.astype(np.uint16)+127)//255).astype(np.uint8)
        alpha['frames'].append({'image': png(rgba,f'alpha-{alpha["labels"][ix]}.png'), 'w':rgba.shape[1], 'h':rgba.shape[0],
                                'geometry':list(f['geometry']), 'I_sha256':hashlib.sha256(f['I'].tobytes()).hexdigest(),
                                'F_sha256':hashlib.sha256(f['F'].tobytes()).hexdigest()})
        alpha['_rgba'].append(rgba)
        decoded.append(f)
    assert all(np.array_equal(decoded[0][x],f[x]) for f in decoded[1:] for x in ('I','F'))
    assert all(decoded[0]['geometry']==f['geometry'] for f in decoded[1:])
    assert np.array_equal(alpha['_rgba'][0][:,:,3]>0,alpha['_rgba'][2][:,:,3]>0)
    assert all(np.array_equal(alpha['_rgba'][0][:,:,:3],a[:,:,:3]) for a in alpha['_rgba'][1:])
    # Automatically choose a genuinely affected visible contour crop, keeping
    # one identical region for all variants and both backgrounds.
    diff = np.abs(alpha['_rgba'][0][:,:,3].astype(int)-alpha['_rgba'][1][:,:,3]) + np.abs(alpha['_rgba'][0][:,:,3].astype(int)-alpha['_rgba'][2][:,:,3])
    size = 28
    best = max((int(diff[y:y+size,x:x+size].sum()),x,y) for y in range(0,diff.shape[0]-size,4) for x in range(0,diff.shape[1]-size,4))
    alpha['crop'] = [best[1],best[2],size]
    alpha['rgba'] = [raw(a) for a in alpha['_rgba']]

    # Meaningful numeric checks: alpha handling and the BOX magnification
    # contract; no tests of unrelated production code or game installation.
    xx,yy = np.meshgrid(np.arange(12)+.25,np.arange(12)+.75)
    opaque = np.full((24,24,4),255,np.uint8)
    assert np.max(np.abs(sample(opaque,xx+4,yy+4,3,'BOX')-1)) < 1e-10
    a = poses[0]['parts'][2][0]['rgba']
    assert np.array_equal(sample(a,xx,yy,.8,'BOX'),sample(a,xx,yy,.8,'Nearest'))
    assert np.all(straight(np.zeros((2,2,4)))==0)
    MANIFEST['checks'] = {'golden_V6_decode': True, 'character_dimensions_centres_preserved': True,
        'V8_I_F_RGB_and_geometry_equal_for_displayed_frame': True, 'light_alpha_positive_support_preserved_for_displayed_frame': True,
        'BOX_constant_colour_preserved': True, 'BOX_magnification_is_Nearest': True, 'transparent_RGB_canonicalized': True,
        'gallery_witness_count':len(gallery)}
    MANIFEST['checks']['every_displayed_V7_part_matches_sealed_oracle_RGBA_hash'] = True
    MANIFEST['simulation_assumptions'] = ['neutral palette, no effects/lighting/occlusion',
        'equipment: same native centres, fixed illustrative south-facing draw order and shared palette',
        'filters: per-layer premultiplied sampling; transparent texture border; screen phase 0.25 px',
        'mipmaps: CPU RGBA8 area-average pyramid, floor-halved NPOT levels; OpenGL driver kernel not reproduced',
        'alpha close-ups: nearest enlargement isolates mask effect, no Catmull-Rom applied',
        'gallery: K6 #0 from sealed oracle; selected frames/actions only, display normalization per card']
    for lang in ('fr','en'):
        for code, im in [('a',assembly_board(poses[0],lang)), ('b',filter_board(poses[0],lang)),
                         ('c',gallery_board(gallery,lang)), ('d',alpha_board(alpha,lang))]:
            im.convert('RGB').save(OUT/'assets'/f'proposal-{code}-{lang}.png')
        overview = Image.new('RGB',(1640,1105),INK)
        for index, code in enumerate('abcd'):
            im = Image.open(OUT/'assets'/f'proposal-{code}-{lang}.png').convert('RGB')
            im = im.resize((800,round(im.height/2)),Image.Resampling.LANCZOS)
            x,y = 10+(index%2)*820,10+(index//2)*505
            overview.paste(im,(x,y))
            ImageDraw.Draw(overview).rectangle((x,y,x+799,y+im.height-1),outline=BORDER)
        overview.save(OUT/'assets'/f'overview-{lang}.png')
    data = {'palettes':[{'name':exp['palettes'][i]['name'], 'rgba':raw(palettes[i])} for i in (0,1,2)],
        'poses':[{k:v for k,v in p.items() if k!='parts'} for p in poses],
        'gallery':[{k:v for k,v in g.items() if not k.startswith('_')} for g in gallery],
        'alpha':{k:v for k,v in alpha.items() if not k.startswith('_')}}
    (OUT/'data.js').write_text('window.VISUAL_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
    reference = {'w':math.ceil(80*1.35),'h':math.ceil(90*1.35),
        'methods':{method:raw(filtered(poses[0]['parts'][4],4,1.35,method))
                   for method in ['Nearest','BOX','Mipmaps','Catmull-Rom']}}
    (OUT/'filter-reference.json').write_text(json.dumps(reference,separators=(',',':'))+'\n',encoding='utf-8')
    for name, sha in MANIFEST['original_pages'].items():
        assert hashlib.sha256((OUT.parent/name).read_bytes()).hexdigest()==sha, 'Original page changed while rendering'
    (OUT/'sources-and-checks.json').write_text(json.dumps(MANIFEST,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'directory':str(OUT),'gallery':len(gallery),'poses':len(poses),'alpha_crop':alpha['crop'],
                      'checks':MANIFEST['checks'],'original_pages_unchanged':True},ensure_ascii=False))


if __name__ == '__main__':
    build()
