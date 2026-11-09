"""Projectile source/dependency/work analysis. Never produces or installs graphics.

refresh writes a NEW snapshot and generated index projections; status/queue are
read-only. Effects/animations/sprites remain their own production authorities.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import zlib

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'bg2-projectiles-work-analysis-v1'
TRACKING = 'projectiles/index/work-tracking.json'
PRO_FIELDS = (
    ('source-animation', 0x20, (1020, 1019, 1000)),
    ('travel-animation', 0x104, (1000,)), ('shadow-animation', 0x10c, (1000,)),
    ('palette', 0x11c, (1,)),
    ('trailing-animation-1', 0x136, (1000,)),
    ('trailing-animation-2', 0x13e, (1000,)),
    ('trailing-animation-3', 0x146, (1000,)),
    ('explosion-animation', 0x21c, (1020, 1019, 1000)),
    ('spread-animation', 0x228, (1020, 1019, 1000)),
    ('ring-animation', 0x230, (1020, 1019, 1000)),
)
FORMATS = {1: 'BMP', 1000: 'BAM', 1019: 'VVC', 1020: 'VEF'}
REFERENCES = {
    'PRO': 'https://gibberlings3.github.io/iesdp/file_formats/ie_formats/pro_v1.htm',
    'PROJECTL': 'https://gibberlings3.github.io/iesdp/files/ids/bgee/projectl.htm',
    'SPL': 'https://gibberlings3.github.io/iesdp/file_formats/ie_formats/spl_v1.htm',
    'ITM': 'https://gibberlings3.github.io/iesdp/file_formats/ie_formats/itm_v1.htm',
}


def hardcoded_label(number):
    labels = {0: 'instant-none', 21: 'burning-hands', 24: 'cone-cold', 25: 'cone-fire',
        44: 'smoke-large', 65: 'holy-might', 66: 'flame-strike', 78: 'invisible-travel',
        96: 'color-spray', 109: 'travel-door', 188: 'cow', 190: 'scorcher-ice',
        194: 'red-holy-might', 207: 'finger-death-hit', 241: 'pillar-light', 254: 'holy-light-pillar'}
    if 67 <= number <= 77:
        return 'magic-missile-count-variant'
    if 80 <= number <= 90:
        return 'call-lightning-chain-variant'
    if 118 <= number <= 148:
        return 'opcode141-hit-visual'
    if 195 <= number <= 202:
        return 'school-hit-area'
    return labels.get(number, 'unmapped-or-missing-id')


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def csv_bytes(rows):
    if not rows:
        return b''
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ';'.join(map(str, v)) if isinstance(v, list) else v for k, v in row.items()})
    return b'\xef\xbb\xbf' + stream.getvalue().encode('utf-8')


def resref(raw, offset):
    return raw[offset:offset + 8].split(b'\0')[0].decode('ascii').upper()


def ids_entries(raw):
    entries = {}
    for line in raw.decode('latin1').splitlines():
        match = re.match(r'\s*(0x[0-9a-fA-F]+|[0-9]+)\s+([A-Za-z0-9_]+)', line)
        if match:
            number = int(match[1], 16 if match[1].lower().startswith('0x') else 10)
            if number in entries and entries[number] != match[2].upper():
                raise ValueError(f'conflicting IDS entry {number}')
            entries[number] = match[2].upper()
    return entries


def parse_pro(raw):
    if raw[:8] != b'PRO V1.0' or len(raw) not in (256, 512, 768):
        raise ValueError('Unsupported PRO header/size')
    word = lambda offset: struct.unpack_from('<H', raw, offset)[0]
    dword = lambda offset: struct.unpack_from('<I', raw, offset)[0]
    data = {'type': word(8), 'speed': word(10), 'sparking_flags': dword(12),
        'particle_color': word(0x28), 'extended_flags': dword(0x2c),
        'default_spell': resref(raw, 0x44), 'success_spell': resref(raw, 0x4c),
        'resources': [(role, offset, resref(raw, offset), formats)
                      for role, offset, formats in PRO_FIELDS
                      if offset + 8 <= len(raw) and resref(raw, offset)]}
    if len(raw) >= 512:
        data.update({'bam_flags': dword(0x100), 'travel_cycle': raw[0x114],
            'shadow_cycle': raw[0x115], 'palette': resref(raw, 0x11c),
            'colors': list(raw[0x124:0x12b]), 'smoke_delay': raw[0x12b],
            'smoke_colors': list(raw[0x12c:0x133]), 'orientations': raw[0x133],
            'smoke_animation_id': word(0x134),
            'trailing_periods': [word(p) for p in (0x14e, 0x150, 0x152)],
            'trail_flags': dword(0x154)})
    if len(raw) == 768:
        data.update({'area_flags': word(0x200), 'ray_count': word(0x202),
            'fragment_animation_id': word(0x212), 'secondary_raw': word(0x214),
            'repetitions': raw[0x216], 'explosion_effect': raw[0x217],
            'explosion_color': raw[0x218], 'explosion_projectile_raw': word(0x21a),
            'area_extended_flags': dword(0x240)})
    return data


def dependency_activity(pro, role):
    """Conservative conditions: retain uncertain paths instead of dropping them."""
    flags, ext = pro.get('bam_flags', 0), pro['extended_flags']
    if role == 'shadow-animation' and not flags & 32:
        return 'disabled', 'PRO BAM flag5 clear'
    if role == 'palette' and flags & 1:
        return 'metadata', 'seven ranges take precedence; embedded BMP must not be an upscale job'
    if role == 'palette':
        return 'metadata', 'palette data, no spatial/temporal inference'
    if role.startswith('trailing-animation'):
        if pro['trailing_periods'][int(role[-1]) - 1] == 0:
            return 'conditional', 'trailing period zero; runtime creation not proven'
    if role in ('spread-animation', 'ring-animation') and pro.get('explosion_effect') == 255:
        return 'disabled', 'explosion effect NONE=255'
    if role == 'explosion-animation' and pro.get('explosion_effect') == 255 and not pro.get('area_flags', 0) & 1024:
        return 'disabled', 'explosion NONE and draw-animation flag10 clear'
    if role == 'travel-animation':
        if ext & (1 << 12) and not ext & (1 << 13):
            return 'conditional', 'falling-path can suppress travel; retain until native route confirmed'
        if pro.get('area_flags', 0) & (1 << 11) and not pro.get('area_flags', 0) & 1:
            return 'conditional', 'cone suppresses flight; other paths/flags require observation'
    return 'potential', 'declared native visual dependency; static evidence, no draw observation'


def ability_projectiles(raw, fmt):
    if raw[:4] != (b'SPL ' if fmt == 'SPL' else b'ITM ') or len(raw) < 0x72:
        raise ValueError(f'invalid {fmt}')
    offset, count = struct.unpack_from('<IH', raw, 0x64)
    size, field = (40, 0x26) if fmt == 'SPL' else (56, 0x2a)
    if offset + count * size > len(raw):
        raise ValueError('ability table outside resource')
    return [(i, offset + i * size + field, struct.unpack_from('<H', raw, offset + i * size + field)[0])
            for i in range(count)]


def existing_action(black_only, candidates, begun=False):
    if black_only:
        return 'native-mask-no-ai'
    if candidates:
        return 'reuse-existing-output'
    if begun:
        return 'resume-existing-work'
    return 'new-context-required'


def validate_tracking(data, pro_names):
    if data.get('schema') != 'bg2-projectiles-work-tracking-v1':
        raise ValueError('Unknown projectile tracking schema')
    for namespace in ('projectiles', 'engine_projectiles'):
        for name, item in data.get(namespace, {}).items():
            if namespace == 'projectiles' and name not in pro_names:
                raise ValueError(f'Unknown PRO decision: {name}')
            if namespace == 'engine_projectiles' and (not name.isdecimal() or int(name) > 65535):
                raise ValueError(f'Invalid engine projectile ID: {name}')
            allowed = {'priority', 'notes', 'historical_evidence', 'integration', 'qa', 'installation', 'release', 'component_visual_qa'}
            if not isinstance(item, dict) or set(item) - allowed:
                raise ValueError(f'Invalid tracking decision fields: {name}')
            if 'priority' in item and (type(item['priority']) is not int or not 0 <= item['priority'] <= 999):
                raise ValueError(f'Invalid priority: {name}')
            # Image QA can be linked without granting native projectile QA.
            components = item.get('component_visual_qa', {})
            if not isinstance(components, dict):
                raise ValueError(f'Invalid component visual QA: {name}')
            for batch, component in components.items():
                if (not isinstance(component, dict)
                    or component.get('state') != 'accepted-assets-only'
                    or not component.get('evidence') or not component.get('assets')
                    or not isinstance(component['assets'], list)
                    or not all(isinstance(asset, str) and asset for asset in component['assets'])
                    or not component.get('limits') or not component.get('reviewed_on')):
                    raise ValueError(f'Invalid component visual QA: {name}/{batch}')
            for field in ('integration', 'qa', 'installation', 'release'):
                if field in item:
                    value = item[field]
                    if not isinstance(value, dict) or not isinstance(value.get('state'), str):
                        raise ValueError(f'Invalid independent state {name}/{field}')
                    if value['state'] in ('accepted', 'passed', 'installed', 'complete', 'released') and not value.get('evidence'):
                        raise ValueError(f'Explicit evidence required for acquired state {name}/{field}')


class Analysis:
    def __init__(self, root):
        self.root = root
        self.inputs = {}
        self.issues = []

    def read(self, relative):
        path = self.root / relative
        raw = path.read_bytes()
        self.inputs[relative.replace('\\', '/')] = digest(raw)
        return raw

    def js(self, relative):
        return json.loads(self.read(relative).decode('utf-8-sig'))

    def csv(self, relative):
        return list(csv.DictReader(io.StringIO(self.read(relative).decode('utf-8-sig'))))

    def optional(self, relative):
        return self.js(relative) if (self.root / relative).is_file() else None

    def run(self):
        from bam_export import decode_bam, native_palette_alpha
        from export_bam_frames import read_bam, cycle_metadata
        from bg2lib import load_key, resolve_resource
        from palette_oracle import scalar_palette
        from workspace_paths import get_path

        now = datetime.now(timezone.utc).isoformat()
        resources = self.csv('projectiles/index/resources.csv')
        previous_deps = self.csv('projectiles/index/dependencies.csv')
        sources = {r['resref']: r for r in self.csv('effects/index/bam-assets.csv')}
        work = {r['resref']: r for r in self.csv('effects/index/work-items.csv')}
        processing = {r['asset_key'].split(':')[-1]: r for r in self.csv('effects/index/processing.csv')}
        controller_rows = self.csv('effects/index/resources.csv')
        controllers = {(r['resref'], r['format']): r for r in controller_rows}
        tracking = self.js(TRACKING)
        sprite_rows = {int(r['animation_id'], 16): r for r in self.csv('sprite/index/sprite_animations.csv')}
        sprite_sources = {r['bam_resref']: r for r in self.csv('sprite/index/sprite_resources.csv')}
        sprite_work = {int(r['animation_id'], 16): r for r in self.csv('sprite/index/q3m-work-items.csv')}
        animations = {r['resref']: r for r in self.csv('animations/index/animation_upscale_registry.csv')}
        bifs, entries = load_key()
        key = {(n.upper(), t): loc for n, t, loc in entries}
        game = get_path('bg2ee_game_root', required=True)
        self.inputs['config://bg2ee_game_root/chitin.key'] = digest((game / 'chitin.key').read_bytes())

        @lru_cache(None)
        def stock(name, typ):
            raw, bif = resolve_resource(bifs, key[name.upper(), typ])
            self.inputs[f'KEY://{name.upper()}.{typ}'] = digest(raw)
            return raw

        projectl = ids_entries(stock('PROJECTL', 1008))
        animate = ids_entries(stock('ANIMATE', 1008))
        fireball = ids_entries(stock('FIREBALL', 1008))
        missile = ids_entries(stock('MISSILE', 1008))
        self.read('pipeline/scripts/projectile_tracking.py')
        for source_code in ('engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp',
                            'engine/InfinityEngine-Enhancer/source-patchee/src/iee/effect_animation_x4_registry.cpp'):
            self.read(source_code)
        pro_names = {r['resref'] for r in resources}
        validate_tracking(tracking, pro_names)
        assert {n for n, t in key if t == 1021} == pro_names, 'PRO inventory differs from KEY'
        ids_by_name = defaultdict(list)
        for number, name in projectl.items():
            ids_by_name[name].append(number)
        raw_pro, pros = {}, {}
        for row in resources:
            raw = self.read(row['extracted_path'])
            assert digest(raw) == row['source_sha256'].upper(), row['resref']
            assert stock(row['resref'], 1021) == raw, 'extracted PRO differs from KEY'
            raw_pro[row['resref']] = raw
            pros[row['resref']] = parse_pro(raw)

        # Sources are decoded once. Canonical equality means exact BAM bytes,
        # including palettes, indices, centres, cycles and lookup tables.
        decoded = {}

        def bam(name):
            if name not in decoded:
                source = sources.get(name)
                if source and source['source_state'] == 'available':
                    packed = self.read(source['extracted_path'])
                    source_path = source['extracted_path']
                    assert digest(packed) == source['source_sha256'].upper(), name
                else:
                    packed = stock(name, 1000)
                    source_path = f'KEY://{name}.1000'
                    if name in sprite_sources:
                        assert digest(packed) == sprite_sources[name]['source_sha256'].upper()
                raw = zlib.decompress(packed[12:]) if packed[:4] == b'BAMC' else packed
                frames, palette, tr = decode_bam(raw)
                decoded[name] = {'raw': raw, 'frames': frames, 'palette': palette,
                    'transparent': tr, 'canonical_sha256': digest(raw),
                    'cycles': cycle_metadata(raw, len(frames)),
                    'source': source_path}
            return decoded[name]

        @lru_cache(None)
        def bmp_palette(name):
            raw = stock(name, 1)
            image = Image.open(io.BytesIO(raw))
            table = image.getpalette()
            if not table or len(table) < 768:
                raise ValueError(f'indexed BMP palette missing: {name}')
            return np.array(table[:768], np.uint8).reshape(256, 3)

        ramps = np.asarray(Image.open(io.BytesIO(stock('MPALETTE', 1))).convert('RGB'))
        assert ramps.shape == (256, 12, 3)
        edges, links, engine, all_profiles = [], [], [], {}
        bom = defaultdict(list)

        def context(name, palette, palette_kind):
            d = bam(name)
            identifier = d['canonical_sha256'] + ':' + digest(palette.tobytes())
            record = all_profiles.setdefault(identifier, {'context_id': identifier,
                'bam_names': set(), 'canonical_sha256': d['canonical_sha256'],
                'palette_rgb_sha256': digest(palette.tobytes()), 'palette_kinds': set(),
                'uses': [], 'palette_rgb': palette.tolist()})
            record['bam_names'].add(name)
            record['palette_kinds'].add(palette_kind)
            return identifier

        def leaf(owner, role, name, path, activity, reason, inherited=None):
            inherited = inherited or {}
            d = bam(name)
            pro = pros[owner]
            palette, palette_kind = d['palette'], 'embedded'
            if role == 'travel-animation' and len(path) == 1:
                if pro['bam_flags'] & 1:
                    palette = scalar_palette(ramps[pro['colors']])
                    palette_kind = 'seven-native-ranges'
                elif pro['palette']:
                    palette = bmp_palette(pro['palette'])
                    palette_kind = 'external-bmp'
            elif inherited.get('palette'):
                # Preserve metadata; do not silently apply unproven VVC palette semantics.
                palette_kind = 'vvc-palette-needs-contract-review'
            cid = context(name, palette, palette_kind)
            use = {'projectile': owner, 'role': role, 'bam': name,
                'context_id': cid, 'activity': activity, 'reason': reason,
                'path': '>'.join(path), 'via': inherited.get('controller', ''),
                'native_fps': inherited.get('native_fps', ''),
                'blend': inherited.get('blend', ''),
                'cycles': inherited.get('cycles', []),
                'travel_cycle': pro.get('travel_cycle', '') if role == 'travel-animation' else '',
                'orientations': pro.get('orientations', '') if role == 'travel-animation' else '',
                'pro_flags': pro.get('bam_flags', 0), 'extended_flags': pro['extended_flags'],
                'area_extended_flags': pro.get('area_extended_flags', 0),
                'explosion_color': pro.get('explosion_color', ''),
                'owner_recolor_review': role in ('explosion-animation', 'spread-animation', 'ring-animation') and
                    bool(pro.get('area_extended_flags', 0) & (8 if role == 'explosion-animation' else 32 if role == 'spread-animation' else 1)),
                'runtime_state': 'not-proven-for-this-owner-role'}
            bom[owner].append(use)
            all_profiles[cid]['uses'].append(use)
            edges.append({'projectile': owner, 'role': role, 'dependency': name, 'format': 'BAM',
                'activity': activity, 'reason': reason, 'offset': '', 'path': use['path'], 'context_id': cid})

        def expand(owner, role, name, typ, path, activity, reason, seen=()):
            if (name, typ) in seen:
                self.issues.append({'kind': 'controller-cycle', 'projectile': owner, 'path': path})
                return
            if typ == 1000:
                leaf(owner, role, name, path, activity, reason)
                return
            row = controllers.get((name, FORMATS[typ]))
            raw = self.read(row['extracted_path']) if row else stock(name, typ)
            if row:
                assert digest(raw) == row['source_sha256'].upper(), name
            if typ == 1019:
                assert raw[:8] == b'VVC V1.0' and len(raw) >= 0x94
                fields = {'controller': name, 'native_fps': struct.unpack_from('<I', raw, 0x34)[0],
                    'blend': bool(struct.unpack_from('<H', raw, 0x18)[0] & 8),
                    'palette': resref(raw, 0x44),
                    'cycles': [struct.unpack_from('<I', raw, p)[0] for p in (0x68, 0x6c, 0x90)]}
                for offset, part in ((8, 'animation'), (0x88, 'alpha-animation')):
                    child = resref(raw, offset)
                    if child:
                        if (child, 1000) in key:
                            leaf(owner, role, child, path + [f'{name}:{part}:{child}'], activity, reason, fields)
                        else:
                            self.issues.append({'kind': 'missing-VVC-BAM', 'projectile': owner, 'resref': child})
            elif typ == 1020:
                assert raw[:4] == b'VEF '
                for off_at, count_at in ((8, 12), (16, 20)):
                    offset, count = struct.unpack_from('<I', raw, off_at)[0], struct.unpack_from('<I', raw, count_at)[0]
                    assert offset + count * 0xe0 <= len(raw)
                    for i in range(count):
                        pos = offset + i * 0xe0
                        kind = struct.unpack_from('<I', raw, pos + 12)[0]
                        child = resref(raw, pos + 16)
                        allowed = {1: (1019, 1000), 2: (1020, 1019, 1000)}.get(kind, ())
                        if not child or not allowed:
                            continue
                        child_type = next((t for t in allowed if (child, t) in key), None)
                        if child_type:
                            expand(owner, role, child, child_type, path + [f'{name}:{i}:{child}'],
                                activity, reason, seen + ((name, typ),))
                        else:
                            self.issues.append({'kind': 'missing-VEF-member', 'projectile': owner, 'resref': child})

        for name, pro in pros.items():
            for role, offset, dep, types in pro['resources']:
                # PRO's draw-animation flag selects VEF/VVC resolution for the
                # explosion field; without it the native path only accepts BAM.
                effective_types = (1000,) if role == 'explosion-animation' and not pro.get('area_flags', 0) & 1024 else types
                typ = next((t for t in effective_types if (dep, t) in key), None)
                active, reason = dependency_activity(pro, role)
                edges.append({'projectile': name, 'role': role, 'dependency': dep,
                    'format': FORMATS.get(typ, 'missing'), 'activity': active,
                    'reason': reason, 'offset': hex(offset), 'path': dep, 'context_id': ''})
                if typ == 1:
                    continue
                if typ is None:
                    self.issues.append({'kind': 'missing-resource', 'projectile': name, 'role': role, 'resref': dep})
                else:
                    expand(name, role, dep, typ, [dep], active, reason)
            if pro.get('bam_flags', 0) & 2:
                aid = pro['smoke_animation_id']
                sr, sw = sprite_rows.get(aid, {}), sprite_work.get(aid, {})
                engine.append({'projectile': name, 'role': 'smoke-animation', 'value': aid,
                    'symbol': animate.get(aid, ''), 'activity': 'conditional' if pro['extended_flags'] & 16384 else 'potential',
                    'resolution': 'sprite-effect' if sr.get('resref') else 'hardcoded-animation',
                    'resref': sr.get('resref', ''), 'sprite_work_state': sw.get('queue_state', ''),
                    'next_action': 'resolve-native-animation-route-before-any-new-inference'})
                if sr.get('resref') and (sr['resref'], 1000) in key:
                    expand(name, 'smoke-animation', sr['resref'], 1000, [f'ANIMATE:{aid:#06x}', sr['resref']],
                        'potential', 'sprite effect INI mapping; independent owner route needs checking')
            if 'area_flags' in pro:
                for role, field, enabled, adjustment in (
                    ('secondary-projectile', 'secondary_raw', bool(pro['area_flags'] & 16) and not pro['ray_count'], 1),
                    ('explosion-projectile', 'explosion_projectile_raw', True, 0)):
                    value = pro[field]
                    if value or enabled and role == 'secondary-projectile':
                        number = value + adjustment
                        child = projectl.get(number, '')
                        links.append({'projectile': name, 'relation': role, 'raw_value': value,
                            'projectl_id': number, 'target': child or f'engine-id:{number}',
                            'activity': 'potential' if enabled else 'disabled',
                            'resolution': 'PRO' if child in pros else 'engine-hardcoded-or-unmapped',
                            'offset': '0x214' if adjustment else '0x21a'})
                if pro['extended_flags'] & 1024:
                    pass  # Multiple flag edges are added below for both PRO types.
                if pro['area_flags'] & 32:
                    aid = pro['fragment_animation_id']
                    sr = sprite_rows.get(aid, {})
                    engine.append({'projectile': name, 'role': 'fragment-animation', 'value': aid,
                        'symbol': animate.get(aid, ''), 'activity': 'disabled' if pro['ray_count'] else 'potential',
                        'resolution': 'sprite-effect' if sr.get('resref') else 'hardcoded-animation',
                        'resref': sr.get('resref', ''), 'sprite_work_state': sprite_work.get(aid, {}).get('queue_state', ''),
                        'next_action': 'resolve-native-fragment-route; do-not-upscale-a-controller'})
                    if sr.get('resref') and (sr['resref'], 1000) in key:
                        expand(name, 'fragment-animation', sr['resref'], 1000, [f'ANIMATE:{aid:#06x}', sr['resref']],
                            'disabled' if pro['ray_count'] else 'potential', 'sprite effect INI mapping')
                effect = pro['explosion_effect']
                if effect not in (254, 255):
                    engine.append({'projectile': name, 'role': 'native-explosion-effect', 'value': effect,
                        'symbol': fireball.get(effect, ''), 'activity': 'potential',
                        'resolution': 'engine-effect-enum', 'resref': '', 'sprite_work_state': '',
                        'next_action': 'map-implicit-native-assets-before-new-inference; declared ring/spread already tracked'})
            if pro['extended_flags'] & 1024:
                for own_id in ids_by_name[name]:
                    prev = projectl.get(own_id - 1, '')
                    links.append({'projectile': name, 'relation': 'multiple-previous', 'raw_value': own_id - 1,
                        'projectl_id': own_id - 1, 'target': prev or f'engine-id:{own_id - 1}',
                        'activity': 'conditional', 'resolution': 'PRO' if prev in pros else 'engine-hardcoded-or-unmapped',
                        'offset': '0x2c:bit10'})
            if pro['sparking_flags'] & 1:
                engine.append({'projectile': name, 'role': 'sparks', 'value': pro['particle_color'],
                    'symbol': 'SPRKCLR', 'activity': 'potential', 'resolution': 'procedural-particles',
                    'resref': '', 'sprite_work_state': '', 'next_action': 'preserve-native-particles-no-raster-ai'})

        # Match source hashes against the complete effects authority, not just
        # same-name records. A source-only alias is NOT a second model job.
        groups = defaultdict(list)
        for name, row in work.items():
            groups[row['canonical_sha256'].upper()].append(name)
        candidates = defaultdict(list)
        selection_issues = []

        @lru_cache(None)
        def pack_files(relative):
            manifest = self.js(relative)
            parent = (self.root / relative).parent
            missing = []
            for frame in manifest.get('frames', []):
                path = parent / frame['asset']
                if not path.is_file() or path.stat().st_size != frame['bytes']:
                    missing.append(frame['asset'])
            return {'frames_checked': len(manifest.get('frames', [])), 'missing_or_wrong_size': missing,
                    'method': 'existence+size; immutable metadata hashes checked separately; payloads not rehashed'}

        for requested in list(decoded):
            d = bam(requested)
            for alias in groups[d['canonical_sha256']]:
                ps = processing[alias]
                sel = self.optional(f'effects/index/selections/{alias}.json')
                palette_sha = digest(bam(alias)['palette'].tobytes())
                if sel:
                    refs = [sel.get('source', {}), sel.get('qa_evidence', {}), sel.get('run_descriptor', {}),
                            sel.get('runtime_pack', {}).get('manifest', {}), sel.get('runtime_pack', {}).get('registry', {})]
                    checks = []
                    for ref in refs:
                        if ref.get('path') and ref.get('sha256'):
                            exists = (self.root / ref['path']).is_file()
                            checks.append(exists and digest(self.read(ref['path'])) == ref['sha256'].upper())
                    if not checks or not all(checks):
                        selection_issues.append(alias)
                    else:
                        pack_ref = sel.get('runtime_pack', {}).get('manifest', {}).get('path', '')
                        physical = pack_files(pack_ref)
                        accepted_palette_sha = palette_sha
                        accepted_spatial = sel.get('contract', {}).get('source', {}).get('spatial_run')
                        if accepted_spatial:
                            recipe = self.optional(f'effects/ressources/{alias}/runs/{accepted_spatial}/recipe.json') or {}
                            if recipe.get('palette_context', {}).get('path'):
                                realized = self.js(recipe['palette_context']['path'])
                                accepted_palette_sha = digest(np.array(realized['palette_rgb'], np.uint8).tobytes())
                        candidates[d['canonical_sha256'] + ':' + accepted_palette_sha].append({
                            'bam': alias, 'kind': 'accepted-selection', 'evidence': f'effects/index/selections/{alias}.json',
                            'pack': str(Path(pack_ref).parent).replace('\\', '/'),
                            'selected_run': sel['selected_run'], 'palette_basis': 'embedded-source-compatible-only',
                            'checks': 'source/QA/run/pack metadata hashes; payloads not rehashed',
                            'physical_pack': physical})
                elif ps['spatial_run']:
                    run = f'effects/ressources/{alias}/runs/{ps["spatial_run"]}'
                    manifest = self.optional(run + '/01-spatial-x4/manifest.json')
                    if manifest and manifest.get('status') in ('completed', 'verified'):
                        recipe = self.optional(run + '/recipe.json') or {}
                        palette_ref = recipe.get('palette_context', {})
                        if palette_ref.get('path'):
                            palette_ctx = self.js(palette_ref['path'])
                            palette_sha = digest(np.array(palette_ctx['palette_rgb'], np.uint8).tobytes())
                        candidates[d['canonical_sha256'] + ':' + palette_sha].append({'bam': alias,
                            'kind': 'spatial-output-existing', 'evidence': run + '/01-spatial-x4/manifest.json',
                            'pack': '', 'selected_run': '', 'palette_basis': 'check-explicit-palette-before-reuse'})
            # animation rows are only hints until their selection source is hash matched.
            for alias in groups[d['canonical_sha256']]:
                if alias in animations:
                    row = animations[alias]
                    evidence = f'animations/index/selections/{alias}.json'
                    sel = self.optional(evidence)
                    if sel:
                        source_ref = sel.get('source', {})
                        if source_ref.get('path') and (self.root / source_ref['path']).is_file():
                            raw = read_bam(self.root / source_ref['path'])
                            if digest(raw) == d['canonical_sha256']:
                                candidates[d['canonical_sha256'] + ':' + palette_sha].append({'bam': alias,
                                    'kind': 'animation-selection-review-contract', 'evidence': evidence,
                                    'pack': '', 'selected_run': row['selected_run'], 'palette_basis': 'embedded'})

        # Discover all palette batch jobs for relevant sources, including work in
        # progress. Never equate a batch declaration with a completed output.
        relevant_hashes = {d['canonical_sha256'] for d in decoded.values()}
        cross_domain = []
        for name, row in sprite_sources.items():
            if row['canonical_sha256'].upper() in relevant_hashes:
                cross_domain.append({'domain': 'sprite', 'bam': name, 'canonical_sha256': row['canonical_sha256'],
                    'runtime_relevant': row['runtime_relevant'], 'families': row['family_ids'],
                    'note': 'source inventory membership is not a Q3m production; effect family excluded from sprite campaign'})
        # Hash only native animation sources, never all generated map payloads.
        # This detects exact content aliases across domains without decoding pixels.
        animation_inventory = self.csv('animations/index/ressources.csv')
        for row in animation_inventory:
            path = self.root / 'animations' / row['relative_path'] / 'source.bam'
            if not path.is_file():
                continue
            packed = path.read_bytes()
            raw = zlib.decompress(packed[12:]) if packed[:4] == b'BAMC' else packed
            canonical = digest(raw)
            if canonical in relevant_hashes:
                self.read(path.relative_to(self.root).as_posix())
                source_name = row['bam_resref']
                ar = animations.get(source_name, {})
                cross_domain.append({'domain': 'animation', 'bam': source_name, 'canonical_sha256': canonical,
                    'status': ar.get('status', ''), 'selected_run': ar.get('selected_run', ''),
                    'note': 'exact native source match; runtime context/recipe remains separate'})
                if ar.get('selected_run'):
                    for requested, d in decoded.items():
                        if d['canonical_sha256'] == canonical:
                            cid = canonical + ':' + digest(d['palette'].tobytes())
                            candidates[cid].append({'bam': source_name, 'kind': 'animation-selection-review-contract',
                                'evidence': 'animations/index/animation_upscale_registry.csv', 'pack': '',
                                'selected_run': ar['selected_run'], 'palette_basis': 'exact-source; verify retained output'})
        palette_jobs = []
        for path in sorted((self.root / 'effects/batches').glob('*/batch.json')):
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            if data.get('schema') != 'bg2-effects-palette-production-batch-v1':
                continue
            self.read(path.relative_to(self.root).as_posix())
            for job in data['jobs']:
                if job['canonical_sha256'].upper() not in relevant_hashes:
                    continue
                palette = self.js(job['palette_file'])
                arr = np.array(palette['palette_rgb'], np.uint8)
                assert digest(arr.tobytes()) == palette['palette_rgb_sha256'].upper()
                cid = job['canonical_sha256'].upper() + ':' + digest(arr.tobytes())
                proof_path = path.parent.relative_to(self.root).as_posix() + '/verification/' + job['job_id'] + '.json'
                proof = self.optional(proof_path)
                pack = self.optional(job['pack'] + '/manifest.json')
                sm = f'effects/ressources/{job["resref"]}/runs/{job["spatial_run"]}/01-spatial-x4/manifest.json'
                spatial = self.optional(sm)
                verified = bool(proof and proof.get('passed') and pack and pack.get('status') == 'completed')
                candidate = {'bam': job['resref'], 'kind': 'verified-palette-output' if verified else
                    'palette-spatial-output' if spatial and spatial.get('status') == 'completed' else 'palette-job-reserved',
                    'evidence': proof_path if verified else sm if spatial else path.relative_to(self.root).as_posix(),
                    'pack': job['pack'] if pack else '', 'selected_run': '',
                    'job_id': job['job_id'], 'palette_basis': 'explicit-native-consumer-palette',
                    'palette_file': job['palette_file']}
                if pack:
                    candidate['physical_pack'] = pack_files(job['pack'] + '/manifest.json')
                candidates[cid].append(candidate)
                palette_jobs.append({'context_id': cid, **candidate})

        context_rows, asset_rows = [], []
        source_by_hash = defaultdict(list)
        for name, d in decoded.items():
            source_by_hash[d['canonical_sha256']].append(name)
        for cid, ctx in all_profiles.items():
            d = bam(sorted(ctx['bam_names'])[0])
            palette = np.array(ctx['palette_rgb'], np.uint8)
            used = {i for c in d['cycles'] for i in c['frame_indices']}
            nonblack = sum(int(np.any(palette[d['frames'][i][0]][d['frames'][i][0] != d['transparent']] > 0)) for i in used)
            black = nonblack == 0
            possible = [u for u in ctx['uses'] if u['activity'] != 'disabled']
            found = list({(c['kind'], c['evidence']): c for c in candidates.get(cid, [])}.values())
            usable = [c for c in found if c['kind'] != 'palette-job-reserved']
            reserved = [c for c in found if c['kind'] == 'palette-job-reserved']
            action = existing_action(black, usable, bool(reserved)) if possible else 'inactive-no-work'
            if 'vvc-palette-needs-contract-review' in ctx['palette_kinds']:
                action = 'palette-contract-review-before-inference'
            ctx.update({'black_only': black, 'candidates': found, 'action': action})
            ctx['owner_recolor_uses'] = [u['projectile'] for u in ctx['uses'] if u['owner_recolor_review']]
            kinds = {c['kind'] for c in usable}
            level = ('native-mask' if black else 'accepted-asset' if 'accepted-selection' in kinds else
                'verified-palette-pack' if 'verified-palette-output' in kinds else
                'spatial-output' if kinds & {'spatial-output-existing', 'palette-spatial-output'} else
                'animation-contract-review' if usable else 'reserved-job' if reserved else 'missing-output')
            ctx['coverage_level'] = level
            context_rows.append({'context_id': cid, 'bams': sorted(ctx['bam_names']),
                'palette_kinds': sorted(ctx['palette_kinds']), 'action': action,
                'coverage_level': level,
                'uses': len(ctx['uses']), 'potential_uses': len(possible),
                'projectiles': sorted({u['projectile'] for u in possible}),
                'candidate_kinds': sorted({c['kind'] for c in found}),
                'candidate_evidence': sorted({c['evidence'] for c in found}),
                'owner_recolor_projectiles': sorted(set(ctx['owner_recolor_uses'])),
                'qa_scope': 'asset-only; per-PRO-assembly not inferred',
                'runtime_tint_blend': 'owner-contract-required'})
        # Exact native pose overlap is recorded for the few new sources. A match
        # is a reuse lead, not permission to ignore model input context/geometry.
        needed = [ctx for ctx in all_profiles.values() if ctx['action'] == 'new-context-required']
        if needed:
            def pose_keys(ctx):
                d = bam(sorted(ctx['bam_names'])[0])
                pal = np.array(ctx['palette_rgb'], np.uint8)
                alpha = native_palette_alpha(d['raw'], d['transparent'])
                output = set()
                for fi in {i for c in d['cycles'] for i in c['frame_indices']}:
                    idx, cx, cy, _ = d['frames'][fi]
                    mask = alpha[idx]
                    yy, xx = np.where(mask > 0)
                    if not len(xx):
                        continue
                    box = (int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1)
                    x0, y0, x1, y1 = box
                    rgba = np.dstack((pal[idx], mask))[y0:y1, x0:x1].copy()
                    rgba[rgba[:, :, 3] == 0] = 0
                    output.add(digest(struct.pack('<iiii', x1-x0, y1-y0, cx-x0, cy-y0) + rgba.tobytes()))
                return output
            target_keys = {c['context_id']: pose_keys(c) for c in needed}
            target_union = set.union(*target_keys.values())
            existing_poses = defaultdict(set)
            for ctx in all_profiles.values():
                if ctx['action'] != 'reuse-existing-output':
                    continue
                for pose in pose_keys(ctx) & target_union:
                    existing_poses[pose].update(ctx['bam_names'])
            for ctx in needed:
                poses = target_keys[ctx['context_id']]
                ctx['exact_pose_overlap'] = {'unique_native_poses': len(poses),
                    'matching_existing_poses': len(poses & existing_poses.keys()),
                    'matched_bams': sorted(set().union(*(existing_poses[p] for p in poses))),
                    'meaning': 'RGBA+native anchor equality only; does not certify reuse across different inference canvases'}
        installed_path = game / 'iee-assets/effects/manifest.json'
        installed, installed_ok = {}, False
        installation_observation = {'manifest': 'config://bg2ee_game_root/iee-assets/effects/manifest.json'}
        if installed_path.is_file():
            raw = installed_path.read_bytes()
            self.inputs[installation_observation['manifest']] = digest(raw)
            installed_data = json.loads(raw.decode('utf-8-sig'))
            reg_path = installed_path.parent / installed_data['registry']
            reg_raw = reg_path.read_bytes()
            installed_ok = digest(reg_raw) == installed_data['registry_sha256'].upper()
            self.inputs['config://bg2ee_game_root/iee-assets/effects/EffectAnimations-X4.registry'] = digest(reg_raw)
            installed = {r['resref']: r for r in installed_data['resources']} if installed_ok else {}
            installation_observation.update({'registry_manifest_hash_matches': installed_ok,
                'resource_count': len(installed), 'meaning': 'catalog declaration only; no current draw, palette dispatch or full backing-byte audit'})
        for canonical, names in sorted(source_by_hash.items(), key=lambda pair: sorted(pair[1])[0]):
            aliases = sorted(groups[canonical])
            contexts = [c for c in context_rows if c['context_id'].split(':')[0] == canonical]
            refs = sorted({e for c in contexts for e in c['candidate_evidence']})
            all_names = sorted(set(names) | set(aliases))
            asset_rows.append({'canonical_bam': sorted(names)[0], 'projectile_bams': sorted(names),
                'exact_source_aliases': aliases, 'canonical_sha256': canonical,
                'source_frames': len(bam(names[0])['frames']), 'source_cycles': len(bam(names[0])['cycles']),
                'contexts': len(contexts), 'actions': sorted({c['action'] for c in contexts}),
                'effects_states': [n + ':' + processing[n]['spatial_state'] for n in aliases],
                'accepted_assets': [n for n in aliases if (self.root / f'effects/index/selections/{n}.json').is_file()],
                'catalog_names_present': [n for n in all_names if n in installed],
                'reusable_evidence': refs,
                'anti_duplicate': 'one work unit per exact source+realized palette; aliases are not jobs'})

        # All stock SPL/ITM ability references, retained with byte offset/hash.
        # No-reference is NOT proof of unused: BCS/opcodes/engine defaults exist.
        usage, effect_metadata = [], []
        scan_counts = Counter()
        for (name, typ), loc in sorted(key.items()):
            if typ not in (1005, 1006, 1016):
                continue
            raw, _ = resolve_resource(bifs, loc)
            if typ == 1016:
                scan_counts['EFF'] += 1
                if raw[:8] == b'EFF V2.0' and len(raw) >= 0xa4:
                    value = struct.unpack_from('<I', raw, 0xa0)[0]
                    if value:
                        effect_metadata.append({'resource': name, 'offset': '0xa0', 'raw_projectile': value,
                            'source_sha256': digest(raw),
                            'meaning': 'EFF provenance metadata; does not itself prove a launched projectile'})
                continue
            fmt = 'ITM' if typ == 1005 else 'SPL'
            scan_counts[fmt] += 1
            for ability, offset, raw_id in ability_projectiles(raw, fmt):
                if raw_id == 0:
                    continue
                number = raw_id - 1
                usage.append({'resource': name, 'format': fmt, 'ability': ability,
                    'offset': hex(offset), 'raw_missile_id': raw_id, 'projectl_id': number,
                    'projectile': projectl.get(number, f'engine-id:{number}'),
                    'source_sha256': digest(raw)})
        usages = defaultdict(list)
        for u in usage:
            usages[u['projectile']].append(u)
        out_links = defaultdict(list)
        for link in links:
            if link['activity'] != 'disabled':
                out_links[link['projectile']].append(link['target'])

        def closure(name, seen=()):
            if name in seen:
                return set()
            result = {name}
            for child in out_links[name]:
                if child in pros:
                    result |= closure(child, seen + (name,))
            return result

        # Reachability by abilities and projectile links. Unreachable remains
        # unresolved, never automatically excluded.
        reachable = set()
        for name in usages:
            if name in pros:
                reachable |= closure(name)
        projectiles = []
        for row in resources:
            name = row['resref']
            nodes = closure(name)
            uses = [u for child in nodes for u in bom[child] if u['activity'] != 'disabled']
            context_ids = sorted({u['context_id'] for u in uses})
            actions = Counter(all_profiles[cid]['action'] for cid in context_ids)
            levels = Counter(all_profiles[cid]['coverage_level'] for cid in context_ids)
            unresolved = [x for x in engine if x['projectile'] in nodes and x['activity'] != 'disabled'
                          and x['resolution'] != 'procedural-particles']
            missing = [x for x in self.issues if x.get('projectile') in nodes]
            overrides = tracking.get('projectiles', {}).get(name, {})
            qa = overrides.get('qa', {}).get('state', 'not-assessed')
            historical = tracking.get('projectiles', {}).get(name, {}).get('historical_evidence', [])
            if missing:
                next_action = 'resolve-missing-dependency'
            elif actions['new-context-required']:
                next_action = 'prepare-missing-visual-contexts'
            elif actions['resume-existing-work']:
                next_action = 'finish-existing-palette-jobs'
            elif unresolved:
                next_action = 'resolve-engine-visual-routes'
            elif actions['reuse-existing-output']:
                next_action = 'reuse-outputs-and-check-owner-contract'
            else:
                next_action = 'native-or-non-raster-route-review'
            projectiles.append({'asset_key': row['asset_key'], 'resref': name,
                'projectl_ids': ids_by_name[name], 'type': pros[name]['type'],
                'source_state': 'available-hash-checked', 'source_sha256': row['source_sha256'],
                'direct_ability_references': len(usages[name]),
                'reachability': 'ability-or-PRO-chain' if name in reachable else 'no-static-ability-reference-found',
                'projectile_closure': sorted(nodes), 'visual_bams': sorted({u['bam'] for u in uses}),
                'visual_contexts': len(context_ids), 'new_contexts': actions['new-context-required'],
                'existing_contexts': actions['reuse-existing-output'],
                'reserved_contexts': actions['resume-existing-work'],
                'accepted_asset_contexts': levels['accepted-asset'],
                'verified_pack_contexts': levels['verified-palette-pack'],
                'spatial_only_contexts': levels['spatial-output'],
                'native_masks': actions['native-mask-no-ai'],
                'implicit_routes_to_resolve': len(unresolved),
                'missing_dependencies': len(missing), 'next_action': next_action,
                'integration_state': overrides.get('integration', {}).get('state', 'not-assessed'),
                'qa_state': qa, 'historical_scoped_evidence': historical,
                'installation_state': overrides.get('installation', {}).get('state', 'not-assessed'),
                'release_state': overrides.get('release', {}).get('state', 'not-evaluated'),
                'asset_catalog_names_present': sorted({u['bam'] for u in uses if u['bam'] in installed}),
                'owner_contract_tasks': sorted(set(
                    ['check-native-geometry-timing-directions-alpha-blend'] +
                    (['palette-dispatch-by-owner-required'] if any(all_profiles[c]['palette_kinds'] & {'seven-native-ranges','external-bmp'} for c in context_ids) else []) +
                    (['secondary-smoke-fragment-owner-route-required'] if any(u['role'] in ('smoke-animation','fragment-animation','shadow-animation') for u in uses) else []) +
                    (['trail-owner-route-required'] if any(u['role'].startswith('trailing') for u in uses) else []) +
                    (['VVC-VEF-occurrence-timeline-required'] if any(u['via'] for u in uses) else []))),
                'notes': overrides.get('notes', '')})
            projectiles[-1]['priority'] = overrides.get('priority', 100)
        engine_ids = sorted({u['projectl_id'] for u in usage if u['projectile'].startswith('engine-id:')} |
                            {l['projectl_id'] for l in links if l['resolution'] != 'PRO' and l['activity'] != 'disabled'})
        documented_ids = {n for n in range(346) if hardcoded_label(n) != 'unmapped-or-missing-id'}
        engine_projectiles = []
        for number in sorted(documented_ids | set(engine_ids)):
            if number in projectl:
                continue
            label = hardcoded_label(number)
            declared = [u for u in usage if u['projectl_id'] == number]
            manual = tracking.get('engine_projectiles', {}).get(str(number), {})
            engine_projectiles.append({'projectl_id': number, 'missile_id': number + 1,
                'missile_symbol': missile.get(number + 1, ''), 'documented_family': label,
                'direct_ability_references': len(declared),
                'PRO_references': sum(l['projectl_id'] == number and l['activity'] != 'disabled' for l in links),
                'upscale_action': 'no-raster-upscale' if number in (0, 78) else
                    'reuse-SPMAGMIS-check-count-and-owner' if 67 <= number <= 77 else 'map-native-assets-before-any-new-inference',
                'integration_state': manual.get('integration', {}).get('state', 'not-assessed'),
                'qa_state': manual.get('qa', {}).get('state', 'not-assessed'),
                'installation_state': manual.get('installation', {}).get('state', 'not-assessed'),
                'release_state': manual.get('release', {}).get('state', 'not-evaluated'),
                'priority': manual.get('priority', 100), 'notes': manual.get('notes', ''),
                'reason': 'no PRO file; do not create a separate model job for an engine ID'})
        changing = [path for path, expected in self.inputs.items()
                    if not path.startswith(('KEY://', 'config://')) and digest((self.root / path).read_bytes()) != expected]
        result = {'schema': SCHEMA, 'created_utc': now, 'scope': 'stock KEY PROs + ability-used hardcoded IDs; no mod/override equivalence inferred',
            'source_projectiles': len(projectiles), 'source_type_counts': dict(Counter(p['type'] for p in projectiles)),
            'projectl_entries': len(projectl), 'source_BAM_names': len({u['bam'] for v in bom.values() for u in v}),
            'canonical_BAM_contents': len(asset_rows), 'visual_contexts': len(context_rows),
            'context_actions': dict(Counter(c['action'] for c in context_rows)),
            'coverage_levels': dict(Counter(c['coverage_level'] for c in context_rows)),
            'new_source_candidates': [{k: c[k] for k in ('context_id', 'exact_pose_overlap')}
                                      | {'bams': sorted(c['bam_names'])} for c in needed],
            'projectile_next_actions': dict(Counter(p['next_action'] for p in projectiles)),
            'ability_scan': dict(scan_counts), 'ability_references': len(usage),
            'hardcoded_ids_referenced': engine_ids,
            'hardcoded_ids_tracked': len(engine_projectiles),
            'cross_domain_matches': cross_domain, 'effect_projectile_metadata': effect_metadata,
            'owner_recolor_uses': sum(u['owner_recolor_review'] for v in bom.values() for u in v),
            'changing_inputs_during_analysis': changing,
            'implicit_engine_roles': dict(Counter(e['role'] for e in engine)),
            'missing_or_ambiguous': self.issues, 'selection_metadata_failures': sorted(set(selection_issues)),
            'installation_observation': installation_observation,
            'live_override_PROs': sorted(p.stem.upper() for p in (game / 'override').glob('*.pro')),
            'known_limits': [
                'Native engine default explosion/smoke/chunk resources not inferred from labels; enumerated as explicit route work.',
                'No full installed texture rehash, no current runtime observation, no new ingame QA.',
                'Accepted BAM/alias QA stays acquired for its exact bytes/contract; not promoted to every PRO palette/role.',
                'Use includes direct SPL/ITM abilities and PRO chains; no-reference never means unused (scripts, opcodes and hardcoded creation possible).',
                'VVC/VEF leaves retained; PRO flags can suppress fields. Conditional rows are retained, not automatically processed.',
                'Exact source+realized RGB palette dedups model inputs; alpha/blend/directions/timing remain per consumer.',
                'Controller PRO/VVC/VEF, palette BMP, sounds, geometry and procedural particles are not independent AI upscale jobs.'],
            'inputs': dict(sorted(self.inputs.items()))}
        result['references'] = REFERENCES
        result['native_contracts'] = pros
        result['engine_projectiles'] = engine_projectiles
        return result, projectiles, asset_rows, context_rows, edges, links, engine, usage, palette_jobs, all_profiles


def refresh(root, snapshot):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,90}', snapshot):
        raise ValueError('invalid snapshot identifier')
    destination = root / 'projectiles/analysis' / snapshot
    if destination.exists():
        raise ValueError('Snapshot already exists; choose a new version')
    result, projectiles, assets, contexts, edges, links, engine, usage, jobs, profiles = Analysis(root).run()
    # All outputs are computed before writes. Historical snapshot is never replaced.
    result['snapshot'] = f'projectiles/analysis/{snapshot}'
    outputs = {'analysis.json': json_bytes(result),
        'work-items.csv': csv_bytes(projectiles), 'visual-assets.csv': csv_bytes(assets),
        'visual-contexts.csv': csv_bytes(contexts), 'dependencies-resolved.csv': csv_bytes(edges),
        'projectile-links.csv': csv_bytes(links), 'engine-routes.csv': csv_bytes(engine),
        'usage.csv': csv_bytes(usage), 'palette-jobs.csv': csv_bytes(jobs),
        'engine-projectiles.csv': csv_bytes(result['engine_projectiles']),
        'contexts.json': json_bytes({k: {**v, 'bam_names': sorted(v['bam_names']), 'palette_kinds': sorted(v['palette_kinds'])}
                                     for k, v in profiles.items()})}
    current_report = report_markdown(result, projectiles, contexts, profiles)
    outputs['REPORT.md'] = current_report.replace(
        f'](analysis/{snapshot}/analysis.json)', '](analysis.json)').encode('utf-8')
    destination.mkdir(parents=True)
    for name, raw in outputs.items():
        (destination / name).write_bytes(raw)
    index = root / 'projectiles/index'
    projections = ('work-items.csv', 'visual-assets.csv', 'visual-contexts.csv', 'engine-routes.csv', 'engine-projectiles.csv')
    for name in projections:
        temporary = index / (name + '.tmp')
        temporary.write_bytes(outputs[name])
        temporary.replace(index / name)
    current = {'schema': SCHEMA, 'snapshot': result['snapshot'], 'created_utc': result['created_utc'],
               'analysis_sha256': digest(outputs['analysis.json']),
               'projections': {name: digest(outputs[name]) for name in projections}}
    (index / 'work-analysis-current.json').write_bytes(json_bytes(current))
    (root / 'projectiles/SUIVI.md').write_text(current_report, encoding='utf-8')
    render_new_sources(destination, profiles)
    print(json.dumps({k: v for k, v in result.items() if k not in ('inputs', 'known_limits', 'native_contracts',
        'engine_projectiles', 'cross_domain_matches', 'effect_projectile_metadata')}, ensure_ascii=False, indent=2))


def report_markdown(result, projectiles, contexts, profiles):
    snap = result['snapshot'].split('/')[-1]
    levels = result['coverage_levels']
    new = [c for c in profiles.values() if c['action'] == 'new-context-required']
    masks = sorted({name for c in profiles.values() if c['action'] == 'native-mask-no-ai' for name in c['bam_names']})
    lines = [
        '# Suivi projectiles — analyse des travaux', '',
        f'- Instantané UTC : `{result["created_utc"]}` ; [rapport figé](analysis/{snap}/analysis.json).',
        '- Projection générée ; décisions métier : `index/work-tracking.json`. Ne pas éditer les CSV générés.',
        '- Cette analyse conserve les autorités effets/animations/sprites ; aucune production, QA, installation ou release accordée.',
        '', '| Inventaire | Nombre |', '|---|---:|',
        f'| PRO stock vérifiés contre KEY/source/SHA | {result["source_projectiles"]} |',
        f'| Types 2 / 3 | {result["source_type_counts"][2]} / {result["source_type_counts"][3]} |',
        f'| Entrées PROJECTL (incluant plusieurs IDs par PRO) | {result["projectl_entries"]} |',
        f'| IDs moteur sans PRO suivis, dont IDs non résolus | {result["hardcoded_ids_tracked"]} |',
        f'| BAM visuels explicites + INI fumées/fragments | {result["source_BAM_names"]} |',
        f'| Contextes source canonique + palette RGB | {result["visual_contexts"]} |',
        f'| SPL / ITM / EFF parcourus | {result["ability_scan"]["SPL"]} / {result["ability_scan"]["ITM"]} / {result["ability_scan"]["EFF"]} |',
        f'| Références dans les capacités SPL/ITM | {result["ability_references"]} |', '',
        '## Travail sur les images — sans double inférence', '',
        '| État observé du contexte | Nombre | Action |', '|---|---:|---|',
        f'| Asset accepté, source et métadonnées liées vérifiées | {levels.get("accepted-asset",0)} | Réutiliser le résultat exact ; préserver la portée QA. |',
        f'| Pack de palette vérifié, pas de QA projectile déduite | {levels.get("verified-palette-pack",0)} | Réutiliser ; raccord propriétaire/palette et QA restent distincts. |',
        f'| Upscale spatial présent | {levels.get("spatial-output",0)} | Terminer/reprendre temporalité et pack ; ne pas relancer SeedVR. |',
        f'| Job réservé sans sortie spatiale complète | {levels.get("reserved-job",0)} | Reprendre le job existant ; aucun lot en doublon. |',
        f'| Masque noir natif | {levels.get("native-mask",0)} | Aucun upscale IA ; préserver indices/alpha/mélange natifs. |',
        f'| Source sans sortie correspondante trouvée | {levels.get("missing-output",0)} | Confirmer chemin moteur puis produire seulement ce manque. |',
        '', '### Sources nouvelles candidates', '',
        '| BAM | Appels PRO/rôle | Source | Poses natives uniques / correspondances exactes existantes |',
        '|---|---|---|---|']
    for c in new:
        name = sorted(c['bam_names'])[0]
        overlap = c['exact_pose_overlap']
        calls = ', '.join(sorted({u['projectile'] + '/' + u['role'] for u in c['uses']}))
        lines.append(f'| {name} | {calls} | sprite `effect`, inventorié, hors campagne Q3m | {overlap["unique_native_poses"]} / {overlap["matching_existing_poses"]} |')
    lines += ['', '- Ces trois BAM ne sont ni des équipements superposés ni des sprites multipart Q3m : animations moteur de classe `effect`. Le rendu de ces propriétaires reste à raccorder/confirmer.',
        '- Planche : `analysis/' + snap + '/new-source-candidates.png`.',
        '', '### Cas à préserver', '',
        '- Masques sans IA : `' + '`, `'.join(masks) + '`.',
        '- Alias exact `SPIPLARI` → production `SPIPLAAI` : preuve `effects/batches/lot26-accepted-20261017-v1/acceptance.json:source_alias`. Ne pas produire SPIPLARI une seconde fois.',
        '- Missile magique : preuve historique ciblée `effects/index/qa-decisions/SPMAGMIS/2026-09-07-accepted-spmagmis-final-fx-r8.json`. Elle ne valide pas chaque ID moteur/compte de missiles.',
        '- `PRO`, `VVC`, `VEF`, `BMP` de palette, IDs, sons, particules procédurales : pas de tâche IA autonome.',
        '', '## Travail sur les projectiles complets', '',
        '| Prochaine action statique dominante | PRO |', '|---|---:|']
    for action, count in sorted(result['projectile_next_actions'].items()):
        lines.append(f'| `{action}` | {count} |')
    lines += ['', '- Ces classes sont exclusives par priorité ; les tâches détaillées peuvent se cumuler dans `index/work-items.csv:owner_contract_tasks`.',
        '- Couverture images ≠ couverture projectile : consulter `accepted_asset_contexts`, `verified_pack_contexts`, `spatial_only_contexts`, puis les états indépendants intégration/QA/installation/release.',
        '- `LIGHTSTO` déclare `MAGMIS`, absent de KEY/BIF. Ne pas remplacer arbitrairement par SPMAGMIS ; vérifier usage et branche native.',
        f'- Appels implicites : {result["implicit_engine_roles"].get("smoke-animation",0)} fumées, {result["implicit_engine_roles"].get("fragment-animation",0)} fragments, {result["implicit_engine_roles"].get("native-explosion-effect",0)} effets d’explosion moteur ; liste exhaustive `index/engine-routes.csv`.',
        '- Les fumées 0x0300/0x0301, les fragments 0x0400 et les effets FIREBALL sont des chemins moteur : identifier leurs ressources effectives avant toute inférence supplémentaire. Un libellé IDS ne prouve pas un BAM.',
        '- Les IDs moteur sans PRO possèdent leurs propres lignes (`index/engine-projectiles.csv`) ; instantané/sans image et variants multi-missiles ne doivent pas devenir autant de jobs IA.',
        '', '## Contrat runtime observé statiquement', '',
        '- `hooks.cpp:detour_projectile_bam_render` : cellule projectile primaire via offset manifesté ; `g_effectOnceProfile=false` = table de base, pas preuve d’une boucle universelle.',
        '- `hooks.cpp:resolve_effect_animation_cell` : recherche par RESREF/séquence/slot/géométrie ; aucun choix de pack par palette PRO dans cette résolution.',
        '- Un RESREF partagé par plusieurs palettes/contextes ne peut pas être couvert par la simple présence d’une entrée du registre. Prévoir dispatch par propriétaire/palette ou représentation compatible ; conserver les sorties existantes.',
        '- Fumées/fragments, ombres/traînées et autres classes : ne pas déduire leur prise en charge du seul hook de la cellule primaire. Vérifier le chemin final et préserver le fallback natif.',
        f'- Catalogue installé : {result["installation_observation"].get("resource_count",0)} noms, SHA registre/manifeste concordants ; aucune observation de draw ni validation palette/propriétaire actuelle déduite.',
        '', '## Fichiers et commandes', '',
        '| Besoin | Fichier |', '|---|---|',
        '| Une ligne par PRO, travaux/états indépendants | `index/work-items.csv` |',
        '| IDs moteur sans PRO, décisions et travaux distincts | `index/engine-projectiles.csv` |',
        '| Déduplication des BAM + alias exacts | `index/visual-assets.csv` |',
        '| Une ligne par source canonique + palette réalisée | `index/visual-contexts.csv` |',
        '| Décisions explicites, notes/priorités humaines | `index/work-tracking.json` |',
        '| Dépendances développées, PRO secondaires, usages, contrats natifs | `analysis/' + snap + '/` |',
        '| Source/QA/run/pack/palette et SHA des entrées | `analysis/' + snap + '/analysis.json`, `contexts.json` |', '',
        '```powershell',
        'python -B pipeline/scripts/projectile_tracking.py status',
        'python -B pipeline/scripts/projectile_tracking.py queue --action new-context-required',
        '# Actualiser : choisir un NOUVEAU nom, les instantanés existants sont immuables.',
        'python -B pipeline/scripts/projectile_tracking.py refresh --snapshot AAAAMMJJ-vN',
        '```', '', '## Limites vérifiables', '',
        '- Analyse exhaustive des 243 PRO stock, références explicites développées, IDs/flags et autorités disponibles. Résolution des chemins hardcodés et validation en jeu restent des travaux explicitement listés, pas des images déclarées terminées.',
        '- Sources hachées ; sélections : SHA source/QA/run/manifest/registre ; backings : existence/taille. Pas de rehash global des payloads, ni de modification du jeu/release.',
        '- Les usages SPL/ITM sont statiques : absence de référence directe ne signifie pas inutilisé (scripts/opcodes/création moteur). Les 559 EFF ont leur champ de provenance inspecté, sans le confondre avec un lancement.',
        '- Snapshot d’une production pouvant évoluer : relancer `refresh` pour actualiser. Entrées changeantes pendant cette lecture : `' + str(result['changing_inputs_during_analysis']) + '`.',
        '- Références de format : [PRO](' + REFERENCES['PRO'] + '), [PROJECTL / IDs sans PRO](' + REFERENCES['PROJECTL'] + ').', '']
    return '\n'.join(lines)


def render_new_sources(destination, profiles):
    from bam_export import decode_bam, native_palette_alpha
    from bg2lib import load_key, resolve_resource
    from PIL import ImageDraw, ImageFont
    selected = [v for v in profiles.values() if v['action'] == 'new-context-required']
    if not selected:
        return
    bifs, entries = load_key()
    lookup = {(n.upper(), t): loc for n, t, loc in entries}
    width, cell = max(1080, 360 * len(selected)), 360
    sheet = Image.new('RGB', (width, 420), '#151b25')
    draw = ImageDraw.Draw(sheet)
    title = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 25)
    font = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 21)
    small = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 14)
    draw.text((16, 12), 'Sources sans production trouvee / chemins moteur a confirmer', font=title, fill='white')
    draw.text((16, 48), 'Frames natives, agrandissement sans IA. Ces candidats ne sont pas des projectiles deja integres.', font=small, fill='#bdccdd')
    for number, ctx in enumerate(selected):
        name = sorted(ctx['bam_names'])[0]
        packed, _ = resolve_resource(bifs, lookup[name, 1000])
        raw = zlib.decompress(packed[12:]) if packed[:4] == b'BAMC' else packed
        frames, palette, tr = decode_bam(raw)
        best = max(range(len(frames)), key=lambda i: int(palette[frames[i][0]][frames[i][0] != tr].astype(np.int64).sum()))
        idx = frames[best][0]
        im = Image.fromarray(np.dstack((palette[idx], native_palette_alpha(raw, tr)[idx])))
        im = im.crop(im.getbbox())
        scale = min(4, 320 // im.width, 220 // im.height)
        if scale >= 1:
            im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
        else:
            im.thumbnail((320, 220), Image.Resampling.NEAREST)
        x = number * cell
        draw.rounded_rectangle((x + 8, 82, x + cell - 8, 406), radius=8, fill='#263244')
        draw.text((x + 22, 94), f'{number+1:02d} {name}', font=font, fill='white')
        draw.rectangle((x + 20, 130, x + cell - 20, 356), fill='#373d46')
        sheet.paste(im, (x + (cell-im.width)//2, 134 + (220-im.height)//2), im)
        owners = ', '.join(sorted({u['projectile'] for u in ctx['uses']}))
        draw.text((x + 22, 365), owners, font=small, fill='#95c8f0')
        draw.text((x + 22, 386), f'frame {best}, {len(frames)} frames source', font=small, fill='#d0d6df')
    sheet.save(destination / 'new-source-candidates.png')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('refresh', 'status', 'queue'))
    parser.add_argument('--snapshot', help='NEW immutable snapshot, e.g. 20261018-v1')
    parser.add_argument('--action', help='queue action filter')
    args = parser.parse_args(argv)
    if args.command == 'refresh':
        if not args.snapshot:
            parser.error('--snapshot required for refresh')
        refresh(ROOT, args.snapshot)
        return
    pointer = json.loads((ROOT / 'projectiles/index/work-analysis-current.json').read_text(encoding='utf-8'))
    report = json.loads((ROOT / pointer['snapshot'] / 'analysis.json').read_text(encoding='utf-8'))
    if digest((ROOT / pointer['snapshot'] / 'analysis.json').read_bytes()) != pointer['analysis_sha256']:
        raise ValueError('Analysis snapshot digest differs from current pointer')
    changed = [p for p, expected in report['inputs'].items()
               if not p.startswith(('KEY://', 'config://')) and
               (not (ROOT / p).is_file() or digest((ROOT / p).read_bytes()) != expected)]
    if changed:
        print('Snapshot outdated; changed inputs: ' + '; '.join(changed[:8]), file=sys.stderr)
    for name, expected in pointer['projections'].items():
        if digest((ROOT / 'projectiles/index' / name).read_bytes()) != expected:
            raise ValueError(f'Generated projection modified: {name}; refresh instead of editing CSVs')
    if args.command == 'status':
        print(json.dumps({k: report[k] for k in ('created_utc', 'source_projectiles', 'source_BAM_names',
            'canonical_BAM_contents', 'visual_contexts', 'context_actions', 'coverage_levels', 'projectile_next_actions', 'hardcoded_ids_referenced')}, indent=2))
    else:
        for row in read_csv(ROOT / 'projectiles/index/visual-contexts.csv'):
            if args.action is None or row['action'] == args.action:
                print(f'{row["bams"]:20} {row["action"]:40} {row["palette_kinds"]} {row["context_id"][:16]}')


if __name__ == '__main__':
    main()
