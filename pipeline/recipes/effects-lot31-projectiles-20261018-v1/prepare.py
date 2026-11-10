"""31 authorized BAMs, explicit native palette contexts; no source replacement."""
from pathlib import Path
import copy
import hashlib
import io
import json
import struct
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from bam_export import decode_bam, native_palette_alpha
from export_bam_frames import read_bam
from palette_oracle import scalar_palette

BATCH = ROOT/'effects/batches/lot31-projectiles-7b-apollo30-20261018-v1'
PROPOSAL = ROOT/'effects/batches/lot31-projectiles-control-proposal-20261018-v1'


def digest(data): return hashlib.sha256(data).hexdigest().upper()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode()
    if path.exists(): assert path.read_bytes() == raw, path
    else: path.write_bytes(raw)


def main():
    p = json.loads((PROPOSAL/'batch.json').read_text(encoding='utf-8'))
    bifs, entries = load_key()
    index = {(n.upper(), t): loc for n, t, loc in entries}
    def resource(name):
        data, bif = resolve_resource(bifs, index[name.upper(), 1])
        return data, {'resref':name, 'type':'BMP', 'sha256':digest(data), 'bif':bif}
    data, ramp_identity = resource('MPALETTE')
    ramps = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))
    assert ramps.shape == (256,12,3)
    assets, jobs = [], []
    for original in p['assets']:
        a = copy.deepcopy(original); name = a['resref']
        raw = read_bam(ROOT/a['source']); frames, embedded, tr = decode_bam(raw)
        assert digest(raw) == a['canonical_sha256']
        contexts = {}
        for c in a['consumers']:
            if c['relation'] != 'travel-animation': continue
            palette = embedded.copy(); kind = 'embedded'; evidence = []
            if c['color_enabled'] == '1':
                colors = [int(v) for v in c['colors'].split(';')]
                assert len(colors) == 7
                palette = scalar_palette(ramps[colors]); kind = 'seven-native-ranges'
                evidence = [ramp_identity]
            elif c['palette']:
                external, identity = resource(c['palette'])
                im = Image.open(io.BytesIO(external))
                table = im.getpalette()
                assert table is not None and len(table) >= 768, (name, c['palette'])
                palette = np.array(table[:768], np.uint8).reshape(256,3)
                kind = 'external-bmp'; evidence = [identity]
            key = digest(palette.tobytes())
            ctx = contexts.setdefault(key, {'kind':kind, 'palette_rgb':palette.tolist(),
                'palette_rgb_sha256':key, 'sources':evidence, 'consumers':[]})
            ctx['consumers'].append(c)
        if not contexts:
            contexts[digest(embedded.tobytes())] = {'kind':'embedded', 'palette_rgb':embedded.tolist(),
                'palette_rgb_sha256':digest(embedded.tobytes()), 'sources':[], 'consumers':a['consumers']}
        values = list(contexts.values())
        values.sort(key=lambda c: (not any(o['consumer_key'].rsplit(':',1)[-1] == name for o in c['consumers']), c['palette_rgb_sha256']))
        a['native_fps'] = [int(v) for v in str(a['native_fps']).split(';') if v]
        a['native_rate_basis'] = 'VVC source field' if a['native_fps'] else '15FPS compatibility default, runtime rate not measured'
        a['inner_feather_x4'] = 0
        a['playback'] = 'retain independent once and loop profiles per native cycle'
        a['static'] = False
        a['max_frame_x1'] = [max(f[0].shape[1] for f in frames), max(f[0].shape[0] for f in frames)]
        a['palette_contexts_produced'] = []
        for i, ctx in enumerate(values,1):
            job = copy.deepcopy(a); cid = f'p{i:02d}'; job['job_id'] = name+'-'+cid
            job['primary'] = i == 1; job['palette_kind'] = ctx['kind']
            job['consumers'] = ctx['consumers']
            path = BATCH/'palettes'/f'{name}-{cid}.json'
            save(path, {'resref':name, 'context_id':cid, **ctx,
                'native_alpha_levels':sorted(int(v) for v in np.unique(native_palette_alpha(raw,tr))),
                'source_indices_geometry_cycles':'unchanged original BAM; palette RGB override only'})
            job['palette_file'] = path.relative_to(ROOT).as_posix()
            job['spatial_run'] = f'{name.lower()}-{cid}-seedvr7b-x4-20261018-v1'
            job['interpolation_run'] = f'{name.lower()}-{cid}-apollo30-retimed-20261018-v1'
            job['pack'] = f'effects/ressources/{name}/packs/{name.lower()}-{cid}-7b-x4-apollo30-20261018-v1'
            a['palette_contexts_produced'].append({'job_id':job['job_id'], 'palette_file':job['palette_file'],
                'spatial_run':job['spatial_run'], 'interpolation_run':job['interpolation_run'], 'pack':job['pack']})
            if i == 1:
                for k in ('job_id','primary','palette_kind','palette_file','spatial_run','interpolation_run','pack'):a[k]=job[k]
            jobs.append(job)
        assets.append(a)
    # Complete one useful rendition of every source before secondary palette variants.
    jobs.sort(key=lambda j:(not j['primary'], j['palette_kind']!='embedded', j['ordinal'], j['job_id']))
    save(BATCH/'batch.json', {'schema':'bg2-effects-palette-production-batch-v1', 'date':'2026-10-18',
        'assets_count':31, 'jobs_count':len(jobs), 'assets':assets, 'jobs':jobs, 'alias_policy':{},
        'proposal':str(PROPOSAL.relative_to(ROOT)/'batch.json'),
        'spatial_batch':BATCH.relative_to(ROOT).as_posix(),
        'authorization':'User: complete31 SeedVR7B x4/Apollo30, remove duplicates, native duration, palettes and alpha preserved.',
        'palette_contract':'One explicit rendition per distinct full native RGB palette among known consumers; original BAM and all context metadata retained. No claim of dynamic runtime routing before integration.',
        'palette_reference_sources':['https://github.com/gemrb/gemrb/blob/master/gemrb/core/Projectile.cpp#L140-L150',
            'https://gibberlings3.github.io/iesdp/file_formats/ie_formats/pro_v1.htm'],
        'native_owner_policy':'Source VVC FPS where supplied; otherwise15FPS compatibility basis, both modes retained. Runtime rates not measured.'})
    save(BATCH/'native-duplicate-audit.json',json.loads((PROPOSAL/'native-duplicate-audit.json').read_text()))
    print(f'Prepared {len(assets)} BAMs, {len(jobs)} explicit palette contexts',flush=True)


if __name__ == '__main__': main()
