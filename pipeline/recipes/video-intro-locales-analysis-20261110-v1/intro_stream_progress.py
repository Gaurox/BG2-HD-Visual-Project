"""Compact read-only progress of the INTRO streaming run."""
import json,re
from pathlib import Path
from datetime import datetime,timezone

r=Path(__file__).resolve().parents[3]/'video/experiments/intro-common-seedvr3b-stream-1080-20261111-v1'
d=json.loads((r/'run.json').read_text())
log=(r/d.get('log','seedvr-stream.log')).read_text(encoding='utf-8',errors='replace')
chunks=list(re.finditer(r'Chunk (\d+)/(\d+): (\d+) new',log))
portion=int(chunks[-1][1]) if chunks else 0
tail=log[chunks[-1].start():] if chunks else log
phases=list(re.finditer(r'(Encoding|Upscaling|Decoding|Post-processing) batch (\d+)/(\d+)',tail))
stage=phases[-1] if phases else None
saved=list(re.finditer(r'BG2_PORTION_SAVED (\d+) (\d+) ',log))
print(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),status=d['status'],portion=portion,
    portions=d['expected_chunks'],completed_portions=len(saved),saved_frames=sum(int(m[2]) for m in saved),
    phase=stage[1] if stage else None,batch=int(stage[2]) if stage else None,
    batches=int(stage[3]) if stage else None,
    last_log_line=log.strip().splitlines()[-1] if d['status']=='failed' else None)))
