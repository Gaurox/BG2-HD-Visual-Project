from pathlib import Path
import copy, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
TAG = 'lot3-decor-x4-20261011-v1'
BATCH = ROOT/'animations/batches'/TAG
SEED = ROOT/'animations/batches/lot3-seedvr7b-lab-x4-20261011-v1'
REB = ROOT/'animations/batches/lot3-reboutcx-x4-20261011-v1'
AREAS = {'AM0902L':['AR0902'], 'AM1001A':['AR0905','AR1001','AR1006','AR1007','AR1009'],
         'AM1512PA':['AR1512'], 'AM2008A':['AR1010','AR2008','OH5120']}

def rel(p): return Path(p).resolve().relative_to(ROOT).as_posix()
def pixels(pack, f):
    w,h = f['physical_size_x4']
    return np.frombuffer((pack/f['asset']).read_bytes(), np.uint8).reshape(h,w,4).copy()

def write_pack(path, resources, arrays):
    path.mkdir(parents=True, exist_ok=False)
    resources = copy.deepcopy(resources)
    for r in resources:
        r['assets'] = []
        for f in r['frames']:
            data = arrays[(r['resref'],f['frame'])].astype(np.uint8).tobytes()
            name = v.asset_name(r['resref'],f['frame'])
            (path/name).write_bytes(data)
            digest = v.sha256_file(path/name)
            f.update(asset=name, sha256=digest, bytes=len(data))
            r['assets'].append(dict(name=name,sha256=digest,bytes=len(data)))
    registry = path/v.REGISTRY_NAME
    registry.write_bytes(v.registry_v2_from_resources(resources,3))
    v.write_json(path/'manifest.json',dict(schema=v.PACK_SCHEMA,status='completed',created_utc=v.utc_now(),
        scale=4, registry_version=3,runtime_contract=dict(feature='TimedTimeline',clock='QPC-pause-aware',registry_version=3),
        registry=v.REGISTRY_NAME,registry_sha256=v.sha256_file(registry),registry_bytes=registry.stat().st_size,
        resource_count=len(resources),frame_count=sum(r['frame_count'] for r in resources),
        timed_resources=[r['resref'] for r in resources if r['playback_mode']=='TimedTimeline'],
        raw_bytes=sum(a['bytes'] for r in resources for a in r['assets']),runtime_budget_enforced=True,
        base_assets=[],new_assets=[],resources=resources))
    v.validate_v2_pack(path)
    return path

def temporal(base, ref, collapse=False):
    output=BATCH/('temporal-'+ref)
    plan=v.build_plan(None,base,[ref],model='apo-8',collapse_uniform_duplicate_holds=collapse,
                      transparent_rgb_mode='nearest-opaque-dilate')
    v.build_run(None,base,output,[ref],plan['plan_sha256'],v.DEFAULT_TVAI_FFMPEG,v.DEFAULT_TVAI_MODEL_DIR,
                'apo-8','-2','ffmpeg',False,collapse_uniform_duplicate_holds=collapse,
                transparent_rgb_mode='nearest-opaque-dilate')
    return output/'03_runtime_pack'
