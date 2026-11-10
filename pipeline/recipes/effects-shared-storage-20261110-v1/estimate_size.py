"""Estimate a ZIP/DEFLATE installer from deterministic byte-weighted samples."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import statistics
import sys
import zlib

sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, OUT, RELEASE, load, rel, save


sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from effect_storage import physical_frames,NAME as STORAGE_NAME

def main():
    content=load(RELEASE/'manifests/content.json')['entries']
    candidate_mode='--candidate-effects' in sys.argv
    if candidate_mode:
        content=[e for e in content if e['kind']!='effect']
        for c in load(RELEASE/'manifests/effect-release-candidates.json')['candidates']:
            root=ROOT/c['runtime_pack']['path'];pack=load(root/c['runtime_pack']['manifest'])
            files=[dict(source=rel(root/c['runtime_pack']['manifest']),bytes=(root/c['runtime_pack']['manifest']).stat().st_size,sha256=c['runtime_pack']['manifest_sha256']),
                   dict(source=rel(root/pack['registry']),bytes=pack['registry_bytes'],sha256=pack['registry_sha256'])]
            files += [dict(source=rel(root/f['asset']),bytes=f['bytes'],sha256=f['sha256']) for f in physical_frames(root,pack)]
            files += c['runtime_files']
            content += [dict(f,kind='effect',payload_group=c['payload_group']) for f in files]
    groups=defaultdict(list)
    for e in content:groups[e['kind']].append(e)
    samples={}
    indices={}
    for kind,entries in groups.items():
        entries.sort(key=lambda e:e['source'])
        total=sum(e['bytes'] for e in entries)
        n=min(192,len(entries))
        picked=[]
        offset=0;j=0
        for i in range(n):
            pos=total*(i+0.5)/n
            while offset+entries[j]['bytes']<=pos:
                offset+=entries[j]['bytes'];j+=1
            e=entries[j];picked.append(e['source']);samples[e['source']]=e
        indices[kind]=picked
    cache_path=OUT/'compression-sample-cache.json'
    cache=load(cache_path) if cache_path.exists() else {}
    def compress(e):
        key=e['source']+'|'+e['sha256']
        if key in cache:return e['source'],cache[key]
        compressor=zlib.compressobj(6,zlib.DEFLATED,-15)
        size=0
        with (ROOT/e['source']).open('rb') as stream:
            while block:=stream.read(1024*1024):size+=len(compressor.compress(block))
        size+=len(compressor.flush())
        ratio=size/e['bytes'];cache[key]=ratio
        return e['source'],ratio
    with ThreadPoolExecutor(max_workers=8) as pool:ratios=dict(pool.map(compress,samples.values()))
    save(cache_path,cache)
    rows=[]
    for kind,entries in groups.items():
        raw=sum(e['bytes'] for e in entries)
        rr=[ratios[s] for s in indices[kind]]
        ratio=statistics.mean(rr)
        # Descriptive sample variability, not a formal confidence interval:
        # deterministic samples and within-family correlations remain possible.
        margin=max(0.05*ratio,2*statistics.stdev(rr)/math.sqrt(len(rr))) if len(rr)>1 else 0.1*ratio
        rows.append(dict(kind=kind,files=len(entries),bytes=raw,sampled_files=len(set(indices[kind])),
            compressed_estimate_bytes=round(raw*ratio),compression_ratio=ratio,
            compressed_low_bytes=round(raw*max(0,ratio-margin)),compressed_high_bytes=round(raw*min(1.01,ratio+margin))))
    # Package helpers, renderer, mirrored manifests, public docs and WeiDU source.
    extras=[]
    for parent,dirs,names in os.walk(RELEASE/'bg2hd'):
        dirs[:]=[d for d in dirs if not d.startswith('payload')]
        extras.extend(Path(parent)/name for name in names)
    for p in (RELEASE/'release-inputs/weidu').glob('*'):
        if p.is_file():extras.append(p)
    for p in [*RELEASE.glob('*.md'),*(RELEASE/'docs').glob('*.md')]:
        if p not in extras:extras.append(p)
    overhead=sum(p.stat().st_size for p in extras)
    zip_headers=sum(100+2*len(('bg2hd/payload/'+e['payload_group']+'/'+Path(e['source']).name).encode()) for e in content)
    checksums=sum(67+len(('bg2hd/payload/'+e['payload_group']+'/'+Path(e['source']).name).encode()) for e in content)
    bootstrap_budget=1024*1024
    package_overhead=overhead+zip_headers+checksums+bootstrap_budget
    raw=sum(r['bytes'] for r in rows)
    # Exact uncompressed source byte count; small packaging metadata is budgeted separately.
    estimate=dict(version=load(RELEASE/'manifests/release.json')['version'],method='ZIP DEFLATE level6; deterministic probability-proportional-to-bytes midpoint samples, 192 draws per content kind',
        payload_files=len(content),payload_bytes=raw,packaging_uncompressed_budget_bytes=package_overhead,
        uncompressed_package_estimate_bytes=raw+package_overhead,
        compressed_package_estimate_bytes=sum(r['compressed_estimate_bytes'] for r in rows)+package_overhead,
        compressed_low_bytes=sum(r['compressed_low_bytes'] for r in rows)+package_overhead,
        compressed_high_bytes=sum(r['compressed_high_bytes'] for r in rows)+package_overhead,
        compression_samples=len(samples),breakdown=rows,
        limits=['Compressed archive not built; range describes sample variability, not a formal confidence interval.',
                'NoCompression remains the local package default; Optimal compression is reserved for final distribution.',
                'Installation requires extracted package plus installed content and WeiDU backups, beyond archive size.',
                'Icons, movies, development caches and corresponding renderer source snapshots are excluded from installer payload.'])
    save(OUT/('size-estimate-candidate.json' if candidate_mode else 'size-estimate.json'),estimate)
    print(json.dumps(estimate,indent=2))


if __name__=='__main__':main()
