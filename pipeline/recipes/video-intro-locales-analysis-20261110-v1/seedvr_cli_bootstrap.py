"""Launch installed SeedVR CLI with an SDPA-compatible optional-package fallback.

Portable Transformers can discover a flash_attn module without distribution metadata.
Report optional Flash Attention unavailable for this SDPA-only process. Process-local only.
"""
import runpy
import sys
import subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

cli=Path(sys.argv[1]).resolve()
sys.argv=sys.argv[1:]
sys.path.insert(0,str(cli.parent))
import transformers.utils.import_utils as imports
import transformers.utils as public_utils
def unavailable(*args,**kwargs):return False
for name in ('is_flash_attn_2_available','is_flash_attn_3_available','is_flash_attn_4_available',
             'is_flash_attn_greater_or_equal'):
    setattr(imports,name,unavailable)
    setattr(public_utils,name,unavailable)
namespace=runpy.run_path(str(cli),run_name='seedvr_stream_cli')
original=namespace['save_frames_to_video']
globals_=original.__globals__
parts=[]

class PartsState:
    def release(self):pass

def save_bounded_parts(frames_tensor,output_path,fps=30.0,writer=None,video_backend='ffmpeg',use_10bit=False):
    """Bound conversion memory and finalize each portion for immediate review."""
    folder=Path(output_path).parent/'portions'
    folder.mkdir(exist_ok=True)
    target=folder/f'INTRO-common-part-{len(parts)+1:02d}.mp4'
    if target.exists():raise FileExistsError(target)
    local=None
    for start in range(0,len(frames_tensor),8):
        local=original(frames_tensor[start:start+8],str(target),fps,writer=local,
                       video_backend=video_backend,use_10bit=use_10bit)
    local.release()
    parts.append(target)
    print(f'BG2_PORTION_SAVED {len(parts)} {len(frames_tensor)} {target}',flush=True)
    return writer or PartsState()

globals_['save_frames_to_video']=save_bounded_parts
namespace['main']()
if parts:
    output=Path(sys.argv[sys.argv.index('--output')+1])
    listing=output.parent/'portions-concat.txt'
    listing.write_text(''.join(f"file '{p.as_posix()}'\n" for p in parts),encoding='utf-8')
    subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-f','concat','-safe','0','-i',str(listing),
                    '-map','0:v:0','-an','-c:v','copy','-movflags','+faststart',str(output)],check=True)
