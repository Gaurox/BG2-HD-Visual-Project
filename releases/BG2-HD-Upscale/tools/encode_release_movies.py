"""Re-encode the selected BG2EE movies without changing the existing installations."""
import csv
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess

from build_optimized_candidate import ROOT, RELEASE

INDEX = ROOT / 'video/index'
DIST = RELEASE / 'dist-local/alpha13-movies-20261122-v1'
RUN = DIST / 'encode'
TARGET = 8_000_000
WORKERS = 6


def json_file(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def read_csv(name):
    with (INDEX / name).open(encoding='utf-8-sig', newline='') as stream:
        return {r['asset_key']: r for r in csv.DictReader(stream)}


def inventory():
    selection = read_csv('status.csv')
    resources = read_csv('resources.csv')
    finals = {}
    for path in sorted(INDEX.glob('*final*.json')):
        if path.name == 'niteday-finals30-20261112-v1.json':
            # The accepted H3 reverse has its own manifest for this asset key.
            continue
        data = json_file(path)
        for row in data.get('variants', [data]):
            key = row.get('asset_key') or f"movie:{row['locale']}:{row['film']}"
            if key in finals:
                raise ValueError(f'Duplicate final selection: {key}')
            finals[key] = row['files']
    if len(selection) != 37 or len(finals) != 31:
        raise ValueError(f'Unexpected movie inventory: {len(selection)}, {len(finals)}')
    for key, row in selection.items():
        src = resources[key]
        original = ROOT / src['extracted_path']
        if key in finals:
            files = finals[key]
            audio = ROOT / files['game_ready']['path']
            m = files.get('master') or files.get('native_audio_master') or files['preview']
            video = ROOT / m['path']
            for path, spec in ((audio, files['game_ready']), (video, m)):
                if sha(path) != spec['sha256'].upper():
                    raise ValueError(f'Selected asset differs: {path}')
        else:
            video = ROOT / row['retained_output']
            audio = original
            if key == 'movie:default:DAYNITE':
                receipt = json_file(ROOT/'video/installations/daynite-h3-nearest-20261110-v1/installation.json')
                audio = ROOT / receipt['source'].replace('\\', '/')
            elif key == 'movie:default:RESTDUNG':
                receipt = json_file(ROOT/'video/installations/restdung-seedvr-20261109-v1/installation.json')
                audio = ROOT / receipt['source'].replace('\\', '/')
                # Preserve the accepted installed 15 fps version.
                video = audio
            if audio == original and sha(audio) != src['source_sha256'].upper():
                raise ValueError(f'Original audio source differs: {key}')
        if not (video.is_file() and audio.is_file()):
            raise FileNotFoundError((key, video, audio))
        dst = Path(src['source_path'])
        if dst.is_absolute() or '..' in dst.parts or dst.parent.name != 'movies' or dst.suffix != '.wbm':
            raise ValueError(f'Invalid native movie path: {dst}')
        yield key, video, audio, dst


def probe(path, full=False):
    args = ['ffprobe','-v','error']
    if full:
        args += ['-count_frames']
    args += ['-show_entries','stream=codec_type,codec_name,width,height,nb_read_frames,avg_frame_rate,r_frame_rate,start_time:format=duration','-of','json',str(path)]
    return json.loads(subprocess.check_output(args))


def stream_hash(path):
    return subprocess.check_output(['ffmpeg','-hide_banner','-v','error','-i',str(path),
        '-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-'], text=True).strip()


def encode(item):
    key, video, audio, dst = item
    tag = key.replace(':','-')
    target = DIST/'assets'/dst
    target.parent.mkdir(parents=True, exist_ok=True)
    stats = RUN/(tag+'.json')
    if stats.is_file() and target.is_file():
        record = json_file(stats)
        if sha(target) != record['sha256']:
            raise ValueError(f'Resumed movie differs: {key}')
        return record
    stage = target.with_suffix('.partial.wbm')
    if stage.exists():
        stage.unlink()
    aud = probe(audio)
    has_audio = any(s['codec_type']=='audio' for s in aud['streams'])
    if any(s['codec_type']=='audio' and s['codec_name']!='vorbis' for s in aud['streams']):
        raise ValueError(f'Unexpected original audio codec: {key}')
    options = ['-c:v','libvpx','-b:v',str(TARGET),'-deadline','good','-cpu-used','3','-threads','4',
               '-auto-alt-ref','0','-drop-threshold','0','-pix_fmt','yuv420p','-fps_mode','passthrough',
               '-enc_time_base','1:1000','-passlogfile',str(RUN/tag)]
    base = ['ffmpeg','-hide_banner','-v','error','-nostdin','-n','-copyts','-threads','3','-i',str(video)]
    with (RUN/(tag+'.log')).open('wb') as log:
        subprocess.run([*base,'-map','0:v:0','-an',*options,'-pass','1','-f','null',os.devnull],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
        maps = ['-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:a','copy'] if has_audio else ['-map','0:v:0','-an']
        subprocess.run([*base,*maps,*options,'-pass','2','-avoid_negative_ts','disabled','-f','webm',str(stage)],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
    expected, verified = probe(video,True),probe(stage,True)
    old_v=next(s for s in expected['streams'] if s['codec_type']=='video')
    new_v=next(s for s in verified['streams'] if s['codec_type']=='video')
    if (new_v['codec_name'],new_v['width'],new_v['height'])!=('vp8',1920,1080) or any(
        old_v[k]!=new_v[k] for k in ('width','height','nb_read_frames')
    ):
        raise ValueError(f'Video dimensions or frame count differs: {key}')
    if abs(float(old_v['start_time'])-float(new_v['start_time']))>0.002:
        raise ValueError(f'Video start time differs: {key}')
    duration=float(verified['format']['duration'])
    expected_duration=max(float(x['format']['duration']) for x in (expected,aud))
    if abs(duration-expected_duration)>0.25:
        raise ValueError(f'Movie duration differs: {key} {duration} != {expected_duration}')
    audio_sha=stream_hash(audio) if has_audio else None
    if has_audio and stream_hash(stage)!=audio_sha:
        raise ValueError(f'Audio bytes differ: {key}')
    record=dict(asset_key=key,destination=dst.as_posix(),source=target.relative_to(ROOT).as_posix(),
                video_master=video.relative_to(ROOT).as_posix(),audio_source=audio.relative_to(ROOT).as_posix(),
                bytes=stage.stat().st_size,sha256=sha(stage),frames=int(new_v['nb_read_frames']),
                duration_s=duration,average_total_bps=round(stage.stat().st_size*8/duration),
                audio_unchanged=audio_sha,audio_present=has_audio)
    stage.rename(target)
    stats.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(f"{key} | {record['bytes']/1e6:.1f} Mo | {duration:.3f}s",flush=True)
    return record


if __name__=='__main__':
    RUN.mkdir(parents=True,exist_ok=True)
    items=list(inventory())
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        result=list(pool.map(encode,items))
    report={'target_video_bps':TARGET,'mode':'VP8 2-pass / native Vorbis copied','movies':result,
            'total_bytes':sum(r['bytes'] for r in result),'ingame_validation':'pending'}
    (DIST/'movies.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f"{len(result)} vidéos / {report['total_bytes']} octets vérifiés",flush=True)
