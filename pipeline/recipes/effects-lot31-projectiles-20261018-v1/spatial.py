"""SeedVR7B per realized native palette; exact RGB inputs share an inference cache."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_effect_spatial as spatial
import upscale_animation_frames as upscaler
import export_bam_frames as exporter
import effect_workflow as workflow
import numpy as np

BATCH = ROOT/'effects/batches/lot31-projectiles-7b-apollo30-20261018-v1'
WF = ROOT/'pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json'
CACHE = BATCH/'inference-cache'
CURRENT = None
BASE_EXPORT = exporter.decode_bam
BASE_RECIPE = spatial.recipe_snapshot
BASE_CLIENT = upscaler.ComfyClient


def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return workflow.sha256_file(path)
def save(path, value): workflow.atomic_write(path,workflow.json_bytes(value))


class CachedClient(BASE_CLIENT):
    def upload(self, source, subfolder):
        # Cache includes every model setting through the exact approved workflow.
        self.key = hashlib.sha256((sha(source)+sha(WF)+'scale4-pad16-lab').encode()).hexdigest()
        self.cache = CACHE/(self.key+'.png'); self.meta = CACHE/(self.key+'.json')
        self.hit = self.cache.exists() and self.meta.exists()
        if self.hit:
            assert sha(self.cache) == load(self.meta)['output_sha256']
            return 'cached/'+self.key
        return super().upload(source,subfolder)

    def queue(self,prompt):
        self.save_id = next(k for k,v in prompt.items() if v.get('class_type')=='SaveImage')
        if self.hit: return 'cached:'+self.key
        self.prompt_id = super().queue(prompt)
        return self.prompt_id

    def wait_history(self,prompt_id):
        if self.hit: return {'outputs':{self.save_id:{'images':[{'local_cached':str(self.cache)}]}}}
        return super().wait_history(prompt_id)

    def download(self,info,destination):
        if self.hit:
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(self.cache,destination)
        else:
            super().download(info,destination)
            CACHE.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(destination,self.cache)
            save(self.meta,{'input_signature':self.key,'output_sha256':sha(self.cache),
                'workflow_sha256':sha(WF),'original_prompt_id':self.prompt_id,'model':'seedvr2_7b_int8_convrot.safetensors'})


def export(plan,source,resume):
    if plan.frame_root.exists(): return spatial.validate_frame_stage(ROOT,plan.frame_root,source)
    palette = np.array(load(ROOT/CURRENT['palette_file'])['palette_rgb'],np.uint8)
    def decode(data):
        frames,_,tr = BASE_EXPORT(data)
        return frames,palette,tr
    exporter.decode_bam = decode
    before = sys.argv
    try:
        sys.argv = ['export_bam_frames',str(plan.source),str(plan.frame_root)]
        exporter.main()
    finally:
        exporter.decode_bam = BASE_EXPORT; sys.argv = before
    m=load(plan.frame_root/'manifest.json')
    m['palette_context']={'path':CURRENT['palette_file'],'sha256':sha(ROOT/CURRENT['palette_file'])}
    save(plan.frame_root/'manifest.json',m)
    spatial.normalize_manifest_paths(ROOT,plan.frame_root/'manifest.json')
    return spatial.validate_frame_stage(ROOT,plan.frame_root,source)


def upscale(plan,frames,resume):
    args=[str(plan.frame_root/'rgb'),str(plan.frame_root/'alpha'),str(plan.spatial_root),
        '--frame-manifest',str(plan.frame_root/'manifest.json'),'--scale','4','--workflow',str(WF),
        '--server',plan.server,'--pad',str(plan.pad),'--poll-seconds','0.2','--timeout-seconds','1800',
        '--upload-folder',plan.upload_folder,'--color-correction-method','lab']
    if plan.spatial_root.exists(): args.append('--resume')
    upscaler.main(args)
    spatial.normalize_manifest_paths(ROOT,plan.spatial_root/'manifest.json')
    return spatial.validate_spatial_stage(ROOT,plan.spatial_root,frames)


def recipe(plan):
    r=BASE_RECIPE(plan)
    snapshot=plan.run_root/'palette-producer-source.py'
    snapshot.parent.mkdir(parents=True,exist_ok=True)
    if not snapshot.exists(): snapshot.write_bytes(Path(__file__).read_bytes())
    r['tools'].append(spatial.file_evidence(ROOT,'palette-spatial-producer',snapshot))
    r['palette_context']=spatial.file_evidence(ROOT,'native-realized-palette',ROOT/CURRENT['palette_file'])
    r['native_source_policy']='Original indexed source untouched; model input uses explicit consumer RGB palette, alpha separate.'
    r['duplicate_policy']='Byte-identical padded RGB inference reused through workflow-bound SHA256 cache.'
    return r


def main():
    global CURRENT
    p=argparse.ArgumentParser();p.add_argument('--job',action='append');args=p.parse_args()
    spatial.export_frames=export;spatial.upscale_frames=upscale;spatial.recipe_snapshot=recipe
    upscaler.ComfyClient=CachedClient
    jobs=[a for a in load(BATCH/'batch.json')['jobs'] if not args.job or a['job_id'] in args.job]
    progress=BATCH/'spatial-progress.json';state=load(progress) if progress.exists() else {};failed=[]
    for i,a in enumerate(jobs,1):
        CURRENT=a;key=a['job_id'];print(f'Spatial {i}/{len(jobs)} {key}',flush=True)
        state[key]={'state':'running'};save(progress,state)
        try:
            plan=spatial.build_plan(ROOT,a['resref'],a['spatial_run'],'seedvr7b-x4-native-palette-lab',WF,
                server='http://127.0.0.1:8188',pad=16,poll_seconds=0.2,timeout_seconds=1800,upload_folder='effects-lot31')
            if not (plan.descriptor_path.exists() and load(plan.descriptor_path).get('result',{}).get('sealed')):
                spatial.execute(plan,resume=plan.run_root.exists())
            v=workflow.verify_run_descriptor(ROOT,plan.run_root.parent.parent,a['resref'],a['spatial_run'],stage='spatial')
            assert v['ok'],v
            if a['primary']: workflow.register_run(ROOT,a['resref'],'spatial',a['spatial_run'],write=True)
            else: workflow.reservation_path(plan.run_root.parent.parent,a['spatial_run']).unlink(missing_ok=True)
            state[key]['state']='completed'
        except Exception as exc:
            traceback.print_exc();failed.append(key);state[key].update(state='failed',error=repr(exc))
        save(progress,state)
    print('Spatial failures:',failed,flush=True)
    return bool(failed)


if __name__=='__main__':raise SystemExit(main())
