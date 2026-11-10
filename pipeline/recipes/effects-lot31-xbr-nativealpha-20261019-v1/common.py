"""Second scoped trial: xBR/native masks on01..06, black-neutral22/27."""
from pathlib import Path
import sys,json,hashlib,os,threading,time
ROOT=Path(__file__).resolve().parents[3]
PREVIOUS=ROOT/'effects/batches/lot31-corrections-preview-20261018-v1'
OUT=ROOT/'effects/batches/lot31-xbr-nativealpha-black-20261019-v1'
WEB=PREVIOUS/'review'
REVISION='revisions/xbr-nativealpha-20261019-v1'
EXPOSED=WEB/REVISION
PREFIX='/'+REVISION
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.insert(0,str(ROOT/'pipeline/recipes/effects-lot31-corrections-20261018-v1'))
import correct as previous
import effect_workflow as workflow
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
evidence=lambda p:workflow.file_evidence(ROOT,p)
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    q=p.with_name('.'+p.name+f'.{os.getpid()}.{threading.get_ident()}.partial');q.write_bytes(workflow.json_bytes(value))
    for attempt in range(100):
        try:q.replace(p);return
        except PermissionError:
            if attempt==99:raise
            time.sleep(.05)
def old_image(path):return '/'+path.lstrip('/')
def image(array):
    from PIL import Image
    key=sha(array.tobytes()+str(array.shape).encode());p=OUT/'review/images'/(key+'.png');p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():Image.fromarray(array).save(p,compress_level=2)
    return PREFIX+'/images/'+p.name
def raw(array):
    b=array.tobytes();p=OUT/'rgba'/(sha(b)+'.rgba');p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():p.write_bytes(b)
    return {'path':p.relative_to(ROOT).as_posix(),'sha256':sha(b),'bytes':len(b)}
def media(path):
    if path.startswith(PREFIX+'/'):return OUT/'review'/path.removeprefix(PREFIX+'/')
    return WEB/path.lstrip('/')
def jobs():return [a for a in load(PREVIOUS/'plan.json')['jobs'] if a['ordinal'] in {1,2,3,4,5,6,22,27}]
