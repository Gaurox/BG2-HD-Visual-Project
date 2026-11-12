"""Interpolate the user-selected six-second POCKETZZ candidate; preserve its AAC audio."""
from pathlib import Path
import importlib.util
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
RECIPE = Path(__file__).resolve().parent
RUN = ROOT/'video/pocketzz/runs/pocketzz-apollo30-20261112-v1'
SOURCE = ROOT/'video/pocketzz/runs/pocketzz-comfyui-experiments-20260814/ComfyUI_00002_.mp4'
FINAL = ROOT/'video/final/pocketzz-apollo30-20261112-v1/POCKETZZ/default'
spec = importlib.util.spec_from_file_location('ending_tools', ROOT/'pipeline/recipes/endings-shared-30fps-20261111-v1/produce.py')
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)
tools.run_dir = lambda film: RUN

def main():
    assert not (FINAL/'verification.json').exists(), 'Completed run is immutable'
    RUN.mkdir(parents=True, exist_ok=True)
    FINAL.mkdir(parents=True, exist_ok=True)
    tools.save(RUN/'run.json', dict(status='inference-completed', output=str(SOURCE), frames=90,
        source_sha256=tools.sha(SOURCE), user_spatial_qa='accepted-user-20261112'))
    apollo = tools.interpolate('POCKETZZ')
    video = ROOT/apollo['output']
    output = FINAL/'POCKETZZ-default-1080p30-audio.mp4'
    command = [tools.FF, '-v', 'error', '-nostdin', '-n', '-i', video, '-i', SOURCE,
        '-map', '0:v:0', '-map', '1:a:0', '-c', 'copy', '-map_metadata', '-1',
        '-movflags', '+faststart', output]
    tools.save(RUN/'mux-command.json', [str(x) for x in command])
    tools.call(command)
    probe = tools.probe(output)
    v = next(s for s in probe['streams'] if s['codec_type']=='video')
    assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames'])) == (1920,1080,'30/1',180)
    stamps = tools.frames(output)
    assert np.max(np.abs(stamps-np.arange(180)/30)) < .000002
    before, after = tools.audio(SOURCE), tools.audio(output)
    assert before[:2] == after[:2]
    assert len(before[2]) == len(after[2]) and np.max(np.abs(before[2]-after[2])) < .000002
    gray = np.frombuffer(tools.call([tools.FF,'-v','error','-threads','2','-i',output,
        '-an','-vf','scale=160:90:flags=area,format=gray','-threads','1',
        '-fps_mode','passthrough','-f','rawvideo','-']), np.uint8).reshape(180,90,160).astype(np.float32)
    odd = gray[1:179:2]
    novel = int(((np.abs(odd-gray[:178:2]).mean((1,2))>.01) &
        (np.abs(odd-gray[2:180:2]).mean((1,2))>.01)).sum())
    assert novel > 0, 'No interpolated motion detected'
    report = dict(asset_key='movie:default:POCKETZZ', source=SOURCE.relative_to(ROOT).as_posix(),
        source_sha256=tools.sha(SOURCE), output=output.relative_to(ROOT).as_posix(),
        sha256=tools.sha(output), bytes=output.stat().st_size, dimensions=[1920,1080],
        fps='30/1', frames=180, duration_s=6, apollo=apollo, audio='candidate AAC copied unchanged',
        audio_pcm_identical=True, audio_encoded_identical=True, audio_pts_identical=True,
        novel_intermediate_frames=novel, tested_intermediate_frames=89,
        full_frame_decode=True, probe=probe, user_visual_qa='pending',
        installed=False, release_integration=False)
    tools.save(FINAL/'verification.json', report)
    tools.save(RECIPE/'metadata/verification.json', report)
    print('POCKETZZ_READY', output, 'novel intermediate frames', novel, flush=True)

if __name__ == '__main__':
    main()
