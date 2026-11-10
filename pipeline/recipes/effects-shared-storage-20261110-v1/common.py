import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
RELEASE=ROOT/'releases/BG2-HD-Upscale'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()
def rel(p):return p.resolve().relative_to(ROOT).as_posix()
def evidence(p):return dict(path=rel(p),bytes=p.stat().st_size,sha256=sha(p))
