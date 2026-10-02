"""Scoped 0x6110 inventory: four bodies + 77 linked equipment appearances."""
from pathlib import Path
import csv
import hashlib
import json
import re
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import numpy as np
from PIL import Image, ImageDraw
import palette_frac_encode as encoder
import palette_registry as registry
from palette_complete import PixelProcessor, independent_lut, source_frames
from palette_oracle import read_bam_p8
from palette_p2 import golden
from reboutcx_multipal import inference_context, save_npz, sha256_file
from run_creature_sprite_x2 import KeyIndex, BAM_TYPE, canonical_bam
from workspace_paths import get_path

OUT = Path(__file__).resolve().parent
BASE = ROOT / 'sprite/Etudes_Sprite_codex_claude/CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29'
EXCLUDED = {'WPNH3INV', 'WPNH4INV', 'WPNH6INV', 'WPNWMOIN'}

def main():
    started = time.monotonic()
    if (OUT / 'production.json').exists():
        raise ValueError('Completed run; use a fresh version')
    rows = [r for r in csv.DictReader((BASE / 'assets_inventory.csv').open(encoding='utf-8-sig'))
            if r['role'].startswith('paperdoll') and r['resref'] not in EXCLUDED]
    assert len(rows) == 81
    palettes = golden()[0]
    fitting = palettes[:6, :, :3].copy(); fitting[:, 0] = (0, 255, 0)
    lut = independent_lut(palettes)
    context = inference_context()
    processor = PixelProcessor(OUT, fitting, context, workers=4, scale=2)
    index = KeyIndex(get_path('bg2ee_game_root', required=True))
    entries = index.resource_map(BAM_TYPE)
    sources, frames_by_ref, all_new = {}, {}, []
    for row in rows:
        ref = row['resref']
        raw, bif = index.resolve(entries[ref]); canonical, _ = canonical_bam(raw)
        source = BASE / 'vanilla_inventory' / (ref + '.BAM')
        if canonical != source.read_bytes() or hashlib.sha256(canonical).hexdigest() != row['sha256_source']:
            raise ValueError('Native source diverged: ' + ref)
        bam = read_bam_p8(canonical)
        if [c['frame_indices'] for c in bam['cycles']] != [[0, 0, 1, 1]]:
            raise ValueError('Unsupported native cycle: ' + ref)
        sources[ref] = bam
        frames_by_ref[ref] = source_frames(ref, bam)
        if ref not in ('CHFF1INV', 'CHFF2INV'):
            all_new.extend(frames_by_ref[ref])
    print(f'{len(rows)} resources / {sum(map(len, frames_by_ref.values()))} native frames; '
          f'{len(all_new)} new frames; validated body planes reused', flush=True)
    processor.process(all_new)
    processor.pool.shutdown(wait=True)
    packs = OUT / 'work/packs'; packs.mkdir(parents=True, exist_ok=True)
    oracles = OUT / 'work/oracles'; oracles.mkdir(exist_ok=True)
    planes = OUT / 'planes'; planes.mkdir(exist_ok=True)
    previews = OUT / 'work/previews'; previews.mkdir(exist_ok=True)
    reports, scope = [], []
    for number, row in enumerate(rows):
        ref = row['resref']; bam = sources[ref]; records, checks, images = [], [], []
        for frame in frames_by_ref[ref]:
            inherited = ref in ('CHFF1INV', 'CHFF2INV')
            if inherited:
                source = OUT.parent / f'palette-q3m-p7-{ref.lower()}-20261002-v1' / f'part-{frame.index}-q3m-x2.npz'
                report = json.loads((source.parent / 'result.json').read_text(encoding='utf-8'))
                if sha256_file(source) != report['frames'][frame.index]['sha256']:
                    raise ValueError('Accepted body planes changed')
            else:
                source = processor.path(frame)
            with np.load(source, allow_pickle=False) as data:
                guide, i, f = (data[k].copy() for k in ('guide', 'I', 'F'))
                dep = data['dep_mask' if inherited else 'dep'].copy()
            check = encoder.check_contract(guide, i, f, dep)
            for pi, palette in enumerate(palettes):
                if not np.array_equal(encoder.decode(i, f, palette), lut[pi, i, f]):
                    raise ValueError('Independent byte decoder differs')
            reps = np.full(256, 65535, np.uint16)
            values, offsets = np.unique(frame.indices.ravel(), return_index=True); reps[values] = offsets
            geometry = [frame.width, frame.height, frame.center_x, frame.center_y, 0]
            record = dict(geometry=geometry, representatives=reps, guide=guide, I=i, F=f, dep=dep)
            records.append(record)
            target = planes / f'{ref}-{frame.index}.npz'
            save_npz(target, guide=guide, I=i, F=f, dep_mask=dep, native_geometry=np.asarray(geometry, np.int32))
            checks.append(dict(frame=frame.index, geometry=geometry, **check,
                independent_decode_palettes=len(palettes), reused_accepted_planes=inherited,
                plane_path=target.relative_to(ROOT).as_posix(), plane_sha256=sha256_file(target)))
            images.append(Image.fromarray(lut[1, i, f]))
        pack = packs / (ref + '-Q3m-X2.registry')
        registry.write(pack, 2, [dict(resref=ref, source_sha256=row['sha256_source'], frames=records,
                                     cycles=[[0, 0, 1, 1]])], compress=False, retain_zero_f=True)
        # Pack inspection verifies complete tables, including unreferenced CHFF4 frame2.
        checked = registry.inspect(pack, include_frames=True)
        assert checked['frame_count'] == len(records)
        oracle = oracles / (ref + '.oracle')
        with oracle.open('wb') as stream:
            stream.write(struct.pack('<8sI', b'P7ORCL01', len(palettes)))
            for pi, palette in enumerate(palettes):
                bgra = palette[:, [2, 1, 0, 3]].copy(); bgra[0] = 0
                stream.write(bgra.tobytes())
                for record in records:
                    rgba = lut[pi, record['I'], record['F']].copy(); rgba[record['I'] == 0] = 0
                    stream.write(rgba[:, :, [2, 1, 0, 3]].tobytes())
        canvas = Image.new('RGBA', (256, 320))
        for n in range(2):
            frame = frames_by_ref[ref][n]
            canvas.alpha_composite(images[n], (-frame.center_x * 2, (-frame.center_y + 80 * n) * 2))
        canvas.save(previews / (ref + '.png'))
        reports.append(dict(resref=ref, role=row['role'], appearance=row['appearance_code'],
            linked_items=int(row['linked_itm_count']), eligible_items=int(row['base_mask_eligible_itm_count']),
            source_sha256=row['sha256_source'], source_bif=bif, key_locator=entries[ref][2],
            frames=checks, cycles=[[0, 0, 1, 1]],
            pack=dict(path=pack.relative_to(ROOT).as_posix(), sha256=sha256_file(pack), bytes=pack.stat().st_size),
            oracle=dict(path=oracle.relative_to(ROOT).as_posix(), sha256=sha256_file(oracle), palettes=len(palettes))))
        scope.append(dict(resref=ref, source_sha256=row['sha256_source'], geometries=[r['geometry'][:4] for r in records]))
        print(f'packed {number+1}/81 {ref}; {len(records)} full native frames', flush=True)
    # A compiled allowlist anchors source SHA and all native geometry; no wildcard takeover.
    header = ['#pragma once', '#include <array>', '#include <cstdint>',
              'namespace iee::paperdoll_q3m {', 'struct NativeGeometry { int width, height, centerX, centerY; };',
              'struct ScopeSpec { std::array<char,8> resref; std::array<std::uint8_t,32> source; '
              'std::size_t frameCount; std::array<NativeGeometry,3> geometry; };',
              'inline constexpr std::array<ScopeSpec,81> kScope{{']
    for item in scope:
        ref = '{' + ','.join(repr(c) for c in item['resref']) + '}'
        sha = '{' + ','.join(f'0x{b:02x}' for b in bytes.fromhex(item['source_sha256'])) + '}'
        gs = item['geometries'] + [[0,0,0,0]]*(3-len(item['geometries']))
        geom = '{{' + ','.join('{' + ','.join(map(str,g)) + '}' for g in gs) + '}}'
        header.append('  {' + f'{ref},{sha},{len(item["geometries"])},{geom}' + '},')
    header += ['}};', '} // namespace iee::paperdoll_q3m']
    (OUT / 'paperdoll_q3m_scope.h').write_text('\n'.join(header)+'\n', encoding='utf-8')
    sheet = Image.new('RGB', (7*170, 12*190), (26,29,34)); draw = ImageDraw.Draw(sheet)
    for n, row in enumerate(rows):
        image = Image.open(previews / (row['resref']+'.png')).resize((128,160), Image.Resampling.NEAREST)
        x,y=(n%7)*170,(n//7)*190
        sheet.paste(image,(x+15,y+22),image);draw.text((x+12,y+5),row['resref'],fill='white')
    sheet.save(OUT / 'contact-sheet.png')
    report = dict(schema='bg2-paperdoll-production-v1',state='working',animation_id='0x6110',
        scale=2,method='Q3m K6',ui_sampler='Nearest',dithering=False,boundary_mixing=False,
        resources=reports,excluded=sorted(EXCLUDED),resource_count=len(reports),
        frame_count=sum(len(r['frames']) for r in reports),processor_stats=dict(processor.stats),
        inference=context,total_seconds=time.monotonic()-started,ingame_qa=False,release_modified=False,
        scope_header_sha256=sha256_file(OUT/'paperdoll_q3m_scope.h'))
    (OUT/'production.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f'COMPLETE {len(reports)} resources, {report["frame_count"]} frames, {report["total_seconds"]:.1f}s',flush=True)

if __name__ == '__main__': main()
