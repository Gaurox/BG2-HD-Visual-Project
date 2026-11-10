"""Independent native mixing oracle and consumer fields for all palette renditions."""
from pathlib import Path
import io
import struct
import numpy as np
from PIL import Image
from prepare import ROOT,BATCH,digest,save
from bg2lib import load_key,resolve_resource
from bam_export import decode_bam
from export_bam_frames import read_bam
from palette_oracle import NativeMix
from workspace_paths import get_path
import json


def main():
    batch=json.loads((BATCH/'batch.json').read_text(encoding='utf-8'))
    bifs,entries=load_key();index={(n.upper(),t):loc for n,t,loc in entries}
    def resource(n,t):return resolve_resource(bifs,index[n.upper(),t])[0]
    ramps=np.asarray(Image.open(io.BytesIO(resource('MPALETTE',1))).convert('RGB'))
    reports=[]
    with NativeMix(get_path('bg2ee_game_root',required=True)/'BaldurReal.exe') as native:
        for a in batch['jobs']:
            ctx=json.loads((ROOT/a['palette_file']).read_text(encoding='utf-8'))
            actual=np.array(ctx['palette_rgb'],np.uint8)
            embedded=decode_bam(read_bam(ROOT/a['source']))[1]
            for owner in ctx['consumers']:
                if owner['relation']!='travel-animation':continue
                pro=resource(owner['consumer_key'].rsplit(':',1)[-1],1021)
                assert digest(pro)==owner['source_sha256'].upper()
                enabled=bool(struct.unpack_from('<I',pro,0x100)[0]&1)
                colors=list(pro[0x124:0x12b])
                palref=pro[0x11c:0x124].rstrip(b'\0').decode('ascii').upper()
                assert str(int(enabled))==owner['color_enabled']
                assert colors==[int(v) for v in owner['colors'].split(';')]
                assert palref==owner['palette'].upper()
                if enabled:
                    expected=native(ramps[colors])
                elif palref:
                    bmp=Image.open(io.BytesIO(resource(palref,1)))
                    expected=np.array(bmp.getpalette()[:768],np.uint8).reshape(256,3)
                else:expected=embedded
                assert np.array_equal(actual,expected),(a['job_id'],owner['consumer_key'])
            for src in ctx['sources']:
                assert digest(resource(src['resref'],1))==src['sha256']
            assert digest(actual.tobytes())==ctx['palette_rgb_sha256']
            reports.append({'job_id':a['job_id'],'resref':a['resref'],'kind':ctx['kind'],
                'consumers':len(ctx['consumers']),'palette_file':a['palette_file'],
                'palette_rgb_sha256':ctx['palette_rgb_sha256'],'passed':True})
        fragment=native.fragment_sha256
    save(BATCH/'palette-verification.json',{'status':'passed','contexts':len(reports),'assets':31,
        'native_mix_fragment_sha256':fragment,'native_rgb_exact':True,
        'note':'Offline source palettes; no in-game owner selection, runtime tint or routing inferred.', 'results':reports})
    print('Native palette verification PASS:',len(reports),'contexts')


if __name__=='__main__':main()
