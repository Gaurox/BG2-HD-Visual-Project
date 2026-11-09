"""Qualify the four installed packs against native FX cells; never change pixels."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from bam_export import decode_bam
from export_bam_frames import cycle_metadata
from workspace_paths import get_path

NAMES = ['HLYMITE', 'SHAIR', 'SHEARTH', 'SPSCORIC']
OUT = ROOT / 'projectiles/analysis/final-four-links-20261109-v1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest().upper()


def save(p, data):
    assert not p.exists()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    assert not (OUT / 'qualification.json').exists(), 'Use a new completed version'
    OUT.mkdir(parents=True, exist_ok=True)
    game = get_path('bg2ee_game_root', required=True)
    assets = game / 'iee-assets/effects'
    manifest = json.loads((assets / 'manifest.json').read_text(encoding='utf-8'))
    registry = (assets / 'EffectAnimations-X4.registry').read_bytes()
    assert digest(registry) == manifest['registry_sha256']
    magic, version, scale, count, reserved = struct.unpack_from('<8sIIII', registry)
    assert (magic, version, scale, count, reserved) == (b'IEEEFX4\0', 3, 4, 743, 0)
    pos = 24

    def values(count=1):
        nonlocal pos
        v = list(struct.unpack_from('<' + 'I' * count, registry, pos))
        pos += count * 4
        return v

    decoded = {}
    for _ in range(count):
        name = registry[pos:pos + 8].rstrip(b'\0').decode('ascii')
        pos += 8
        nf, nc = values(2)
        dims = [values(2) for _ in range(nf)]
        cycles = [values(values()[0]) for _ in range(nc)]
        fps_n, fps_d, target_n, target_d, phases = values(5)
        timeline = [values(phases) for _ in range(nc)]
        once = {}
        for _ in range(values()[0]):
            cycle, size = values(2)
            once[cycle] = values(size)
        if name in NAMES:
            assert (fps_n, fps_d, target_n, target_d) == (15, 1, 30, 1)
            decoded[name] = dict(dims=dims, cycles=cycles, timeline=timeline, once=once)
    assert pos == len(registry) and set(decoded) == set(NAMES)
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}
    proofs, contracts = [], []
    for name in NAMES:
        raw, _ = resolve_resource(bifs, key[name, 1000])
        override = game / 'override' / (name + '.bam')
        if override.exists():
            raw = override.read_bytes()
        bam_hash = digest(raw)
        raw = zlib.decompress(raw[12:]) if raw[:4] == b'BAMC' else raw
        native, _, _ = decode_bam(raw)
        native_cycles = cycle_metadata(raw, len(native))
        resource = next(r for r in manifest['resources'] if r['resref'] == name)
        data = decoded[name]
        frames = sorted((f for f in manifest['frames'] if f['resref'] == name), key=lambda f: f['resource_frame'])
        assert len(frames) == resource['frame_count'] == len(data['dims'])
        assert [c['frame_indices'] for c in native_cycles] == [c['frame_indices'] for c in resource['cycles']]
        assert len(native_cycles) == len(data['cycles'])
        checks = []
        for f in frames:
            target = assets / f['asset']
            assert target.stat().st_size == f['bytes'] and sha(target) == f['sha256'], target
            assert f['logical_size_x1'] == data['dims'][f['resource_frame']]
        for cycle, source_cycle in enumerate(native_cycles):
            slots = source_cycle['frame_indices']
            assert len(data['cycles'][cycle]) == len(slots)
            for is_once in (0, 1):
                phases = data['once'].get(cycle, data['timeline'][cycle]) if is_once else data['timeline'][cycle]
                assert len(phases) >= len(slots) * 2
                for phase in range(len(slots) * 2):
                    slot = phase // 2
                    image, cx, cy, _ = native[slots[slot]]
                    size = [image.shape[1], image.shape[0]]
                    expected_native = phases[slot * 2] if is_once and cycle in data['once'] else data['cycles'][cycle][slot]
                    expected_target = phases[phase]
                    for ix in (expected_native, expected_target):
                        frame = frames[ix]
                        assert frame['logical_size_x1'] == size, (name, cycle, phase, ix, size, frame['logical_size_x1'])
                        assert frame['source_centre_x1'] == [cx, cy], (name, cycle, phase, ix, 'centre')
                    for ref in (name, name.lower()):
                        contracts.append(f'{ref}\t{slot}\t{size[0]}\t{size[1]}\t{phase}\t{cycle}\t{expected_native}\t{expected_target}\t{is_once}')
                checks.append(dict(cycle=cycle, once=is_once, native_slots=len(slots), phases=len(slots) * 2,
                                   sizes_centres_exact=True))
        proofs.append(dict(resref=name, installed_BAM_sha256=bam_hash, native_override=override.exists(),
            native_frames=len(native), native_cycles=len(native_cycles), registry_frames=len(frames),
            installed_backing_hashes_verified=len(frames), backing_bytes=sum(f['bytes'] for f in frames),
            resource_metadata=resource, profiles=checks,
            selection=dict(path=f'effects/index/selections/{name}.json', sha256=sha(ROOT / f'effects/index/selections/{name}.json'))))
        print(name, len(frames), 'installed backings exact; native cycle/slot/phase geometry+centres PASS', flush=True)
    (OUT / 'runtime-contracts.tsv').write_text('\n'.join(contracts) + '\n', encoding='ascii')
    save(OUT / 'qualification.json', dict(schema='bg2-projectiles-native-six-qualification-v1',
        resources=NAMES, installed_resources=count, installed_backings=manifest['frame_count'],
        manifest_sha256=sha(assets / 'manifest.json'), registry_sha256=digest(registry),
        installed_dll_sha256=sha(game / 'InfinityEngine-Enhancer.dll'), contracts=len(contracts),
        verified_backings=sum(p['registry_frames'] for p in proofs), proofs=proofs,
        new_inference=0, image_changes=0, native_geometry_changes=0,
        scope='Actual native-cell lookup for all four: current cycles, source centres/sizes, base+once profiles. Blend/palette/occlusion keep existing safe native fallback; live HD draw requires test.'))
    print(len(contracts), 'native lookup contracts prepared; zero image writes.')


if __name__ == '__main__':
    main()
