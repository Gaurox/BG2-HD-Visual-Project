"""Correct soft2 native fallback: native frame rectangles, centres and timelines stay exact."""
from pathlib import Path
import sys,copy
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/recipes/lot45-final-20261011-v1'))
from common import v,pixels,write_pack,rel
from build_alpha_feather import canvas_edge_ramp
REF='AM3000E'
ID='am3000e-contour-native-20261011-v2'
OUT=ROOT/'animations/batches'/ID
NATIVE=ROOT/'animations/batches/lot45-final-20261011-v1/final-AM3000E-PLT_MAGE'
SOFT=ROOT/'animations/batches/am3000e-contour-soft-20261011-v1/soft2'

def main():
    assert not OUT.exists(),'versioned output exists'
    OUT.mkdir(parents=True)
    r=copy.deepcopy(v.validate_v2_pack(NATIVE)[1][0]);soft=v.validate_v2_pack(SOFT)[1][0]
    arrays={};metrics=[]
    for f in r['frames']:
        p=pixels(SOFT,soft['frames'][f['frame']])[12:-12,12:-12].copy()
        w,h=f['physical_size_x4'];assert p.shape==(h,w,4)
        # Limit only the cropped canvas cut; two physical pixels, no dilation/padding in runtime geometry.
        ramp=canvas_edge_ramp(w,h,2,('top','right','bottom','left'))
        p=np.rint(p.astype(float)*ramp[...,None]).clip(0,255).astype(np.uint8)
        assert not p[0].any() and not p[-1].any() and not p[:,0].any() and not p[:,-1].any()
        base=pixels(NATIVE,f);lum=np.array([.2126,.7152,.0722])
        metrics.append(dict(frame=f['frame'],additive_energy_change_pct=100*((p[...,:3]@lum).sum()/max((base[...,:3]@lum).sum(),1)-1)))
        arrays[(REF,f['frame'])]=p
    pack=write_pack(OUT/'final-assets',[r],arrays)
    current=v.validate_v2_pack(pack)[1][0]
    assert current['cycles']==r['cycles'] and current['frame_count']==61
    assert all(all(a[k]==b[k] for k in ('frame','logical_size_x1','physical_size_x4','centre_x1')) for a,b in zip(r['frames'],current['frames']))
    evidence=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.cpp'
    v.write_json(OUT/'manifest.json',dict(schema='bg2-upscale-animation-visual-treatment-v1',status='completed',created_utc=v.utc_now(),resrefs=[REF],
        source_pack=rel(NATIVE),source_pack_manifest_sha256=v.sha256_file(NATIVE/'manifest.json'),
        soft_input=rel(SOFT),soft_input_manifest_sha256=v.sha256_file(SOFT/'manifest.json'),
        final_pack=rel(pack),final_pack_manifest_sha256=v.sha256_file(pack/'manifest.json'),
        diagnosis='soft2 v1 padding violates resolve_timeline_subframe strict native logical dimensions; loaded pack silently falls back to BAM',
        runtime_contract_source=rel(evidence),runtime_contract_source_sha256=v.sha256_file(evidence),
        correction='crop12px x4 of padding; restore every native frame rectangle/centre; canvas2px premultiplied RGBA fade only at cropped frame edge',
        native_geometry_byte_identical=True,cycles_and_phase_slots_preserved=True,phase_counts=[48,36,20],durations_seconds=[1.6,1.2,20/30],
        metrics=metrics,max_absolute_additive_energy_change_pct=max(abs(m['additive_energy_change_pct']) for m in metrics),
        qa_status='pending-ingame',installation_status='not-installed',release_status='not-selected'))
    print('BUILT corrected soft2: 61frames, exact native rectangles/centres, 48/36/20 phases',flush=True)

if __name__=='__main__':main()
