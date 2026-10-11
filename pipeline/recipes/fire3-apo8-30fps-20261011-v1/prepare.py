"""Prepare AR0202-only FIRE_3 30fps trial; preserve anchors and siblings."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
RECIPE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
from area_pack_state import game_areas_dir

RUN = ROOT / 'animations/ressources/FIRE_3/runs/fire3-native-anchors-apo8-30fps-20261011-v1'
BASE = ROOT / 'animations/packs-par-zone/soa-ar0202-lot4-accepted-reserve-fire3-animation-20260916/AR0202'
SPLIT = ROOT / 'animations/packs-par-zone/fire3-apo8-30fps-ar0202-raw-20261011-v1'
FINAL = ROOT / 'animations/packs-par-zone/fire3-apo8-30fps-ar0202-zero-20261011-v1'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def payload(path):
    return {p.name: sha(p) for p in path.iterdir() if p.is_file()
            and (p.suffix == '.rgba' or p.name == v.REGISTRY_NAME)}

def write(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')

def main():
    assert not FINAL.exists() and not SPLIT.exists(), 'Immutable output exists'
    live = game_areas_dir() / 'AR0202'
    before = payload(live)
    assert before == payload(BASE), 'Unexpected installed AR0202 version'
    with (ROOT / 'animations/index/occurrences.csv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = [r for r in reader if r['area_id'] == 'AR0202']
    subset = RECIPE / 'occurrences-ar0202.csv'
    with subset.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    subprocess.run([sys.executable, str(ROOT/'pipeline/scripts/split_animation_pack_by_area.py'),
                    '--pack', str(RUN/'03_runtime_pack'), '--output', str(SPLIT),
                    '--occurrences', str(subset)], check=True)
    # The accepted RGB is already premultiplied. Zero only the new hidden RGB;
    # multiplying by alpha again would darken the accepted soft edges.
    subprocess.run([sys.executable, str(ROOT/'pipeline/scripts/build_blended_rgb_neutral_pack.py'),
                    '--split-root', str(SPLIT), '--output', str(FINAL),
                    '--resref', 'FIRE_3', '--mode', 'zero'], check=True)
    _, old_resources = v.validate_v2_pack(BASE)
    _, new_resources = v.validate_v2_pack(FINAL/'AR0202')
    old = next(r for r in old_resources if r['resref']=='FIRE_3')
    target = next(r for r in new_resources if r['resref']=='FIRE_3')
    assert target['frames'][:14] == old['frames'], 'Native anchor bytes/geometry changed'
    assert target['playback_mode'] == 'TimedTimeline'
    assert target['native_fps'] == {'numerator':15, 'denominator':1}
    assert target['target_fps'] == {'numerator':30, 'denominator':1}
    cycle = target['cycles'][0]
    timeline = cycle['timeline_frame_indices']
    assert len(timeline)==28 and len(set(timeline))==28
    assert cycle['native_frame_indices']==list(range(14))
    assert timeline[::2]==list(range(14))
    assert [r for r in old_resources if r['resref']!='FIRE_3']==[r for r in new_resources if r['resref']!='FIRE_3']
    after = payload(FINAL/'AR0202')
    for name,digest in before.items():
        if name!=v.REGISTRY_NAME:
            assert after[name]==digest, 'Existing payload changed: '+name
    frames=target['frames']
    left=min(-f['centre_x1'][0]*4 for f in frames)
    top=min(-f['centre_x1'][1]*4 for f in frames)
    right=max((f['logical_size_x1'][0]-f['centre_x1'][0])*4 for f in frames)
    bottom=max((f['logical_size_x1'][1]-f['centre_x1'][1])*4 for f in frames)
    aligned=[]
    for f in frames:
        w,h=f['physical_size_x4']
        a=np.frombuffer((FINAL/'AR0202'/f['asset']).read_bytes(),dtype=np.uint8).reshape(h,w,4)
        assert not np.any(a[:,:,:3][a[:,:,3]==0]), 'Hidden RGB remains'
        canvas=np.zeros((bottom-top,right-left,4),dtype=np.uint8)
        x=-f['centre_x1'][0]*4-left; y=-f['centre_x1'][1]*4-top
        canvas[y:y+h,x:x+w]=a
        aligned.append(canvas)
    hashes=[hashlib.sha256(a.tobytes()).hexdigest() for a in aligned]
    assert len(set(hashes))==28, 'Aligned visual duplicate detected'
    steps=[]
    for phase,index in enumerate(timeline):
        other=timeline[(phase+1)%28]
        a,b=aligned[index],aligned[other]
        delta=np.abs(a[:,:,:3].astype(np.int16)-b[:,:,:3].astype(np.int16))
        support=(a[:,:,3]>0)|(b[:,:,3]>0)
        steps.append(dict(phase=phase,frame=index,next_frame=other,
                          changed_visible_pixels=int(np.count_nonzero(np.any(delta>0,axis=2)&support)),
                          mean_rgb_delta=float(delta[support].mean())))
        assert steps[-1]['changed_visible_pixels']>0
    review=RECIPE/'review-frames'
    review.mkdir()
    # Blended RGB is added to the scene; do not multiply alpha a second time.
    sheet=Image.new('RGB',(14*(right-left),2*(bottom-top+20)),(25,25,25))
    draw=ImageDraw.Draw(sheet)
    for phase,index in enumerate(timeline):
        a=aligned[index]
        shown=np.minimum(a[:,:,:3].astype(np.uint16)+25,255).astype(np.uint8)
        img=Image.fromarray(shown)
        img.save(review/f'frame_{phase:04d}.png')
        x=(phase//2)*(right-left); y=(phase%2)*(bottom-top+20)
        sheet.paste(img,(x,y+20)); draw.text((x+2,y+2),f'{phase:02d}: frame{index:02d}',fill='white')
    sheet.save(RECIPE/'contact-sheet.png')
    write(RECIPE/'checks.json',dict(passed=True,area='AR0202',resref='FIRE_3',
        temporal_run=str(RUN.relative_to(ROOT)),installed_trial_pack=str(FINAL.relative_to(ROOT)),
        fps=30,phases=28,distinct_raw_frames=28,distinct_aligned_visible_frames=28,
        native_anchors_byte_identical=14,native_geometry_and_alpha_preserved=True,
        duration_seconds=14/15,loop_closed=True,sibling_payload_and_contract_unchanged=True,
        transparent_rgb_zero=True,steps=steps,qa_status='pending-explicit-user-ingame-approval'))
    write(RECIPE/'baseline.json',dict(area='AR0202',before=before,after=after))
    print('PASS: 28 distinct aligned frames; 14 exact anchors; 30fps; 14/15s; siblings unchanged')

if __name__=='__main__':
    main()
