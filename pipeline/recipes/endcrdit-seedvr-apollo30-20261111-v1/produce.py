"""Finish the complete ENDCRDIT while its first SeedVR portion is reviewed."""
import importlib.util
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[3]
RECIPE=Path(__file__).resolve().parent
RUN=ROOT/'video/endcrdit/runs/endcrdit-seedvr-apollo30-20261111-v1'
FINAL=ROOT/'video/final/endcrdit-seedvr-apollo30-20261111-v1'
BASE=ROOT/'pipeline/recipes/endings-shared-30fps-20261111-v1/produce.py'
spec=importlib.util.spec_from_file_location('endings_producer',BASE)
pipeline=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipeline)
pipeline.AUDIT=ROOT/'video/research/endcrdit-native-20261111-v1'
pipeline.FINAL=FINAL
pipeline.run_dir=lambda film:RUN

def main():
    assert not (FINAL/'manifest.json').exists(),'Final manifest immutable; use a new version'
    deadline=time.monotonic()+7200
    while True:
        checkpoint=RUN/'pause-checkpoint.json'
        if checkpoint.exists() and json.loads(checkpoint.read_text(encoding='utf-8'))['state'] in ('pause-requested','paused'):
            print('ENDCRDIT_PAUSED: retained prefix and resume boundary in pause-checkpoint.json',flush=True)
            return
        assert time.monotonic()<deadline,'SeedVR timed out'
        try:state=json.loads((RUN/'run.json').read_text(encoding='utf-8'))['status']
        except (FileNotFoundError,json.JSONDecodeError):state='starting'
        if state=='inference-completed':break
        assert state in ('starting','running'),state
        time.sleep(5)
    master=pipeline.interpolate('ENDCRDIT')
    result=pipeline.build('ENDCRDIT','default',master)
    report=dict(schema='endcrdit-finals30-v1',state='runtime-ready',masters=[master],variants=[result],
        text_readability_qa='pending-user',first_portion_review='video/previews/endcrdit-text-20261111-v1',
        installed=False,release_integration=False)
    pipeline.save(FINAL/'manifest.json',report)
    pipeline.save(RECIPE/'metadata/manifest.json',report)
    pipeline.save(ROOT/'video/index/endcrdit-finals30-20261111-v1.json',report)
    print('ENDCRDIT_FULL_RUNTIME_READY',flush=True)

if __name__=='__main__':main()
