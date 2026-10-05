"""Complete runtime identities after native verification; preserve its sealed bytes."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha
WORK=ROOT/'sprite/.work/q3m-large16-sdf-ingame-x2-20261004-v1';BUILD=WORK/'runtime-build/Release'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def ident(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
assert not (HERE/'runtime.json').exists() and not (HERE/'current-generation.json').exists()
verification=load(HERE/'verification.json');production=load(HERE/'production.json');sources=verification['source_provenance']
assert verification['passed'] and verification['cold_resolution']['cold_misses']==0
for item in [verification['dll'],verification['production'],verification['GPU'],*sources]:assert file_sha(ROOT/item['path'])==item['sha256']
# Same final runtime/generation construction as the verifier; no rerun of passed native tests.
code=(HERE/'verify.py').read_text(encoding='utf-8')
from palette_work_plan import write_json
exec(compile(code[code.index('parent=load('):],str(HERE/'verify.py'),'exec'))
print('Runtime and generation sealed; installed shader raw bytes pinned, archived GLSL identical after newline normalization.')
