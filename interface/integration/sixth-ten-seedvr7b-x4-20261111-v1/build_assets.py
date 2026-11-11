"""Package ten selected MOS compositions, preserving every other DXT5 block."""
import importlib.util,hashlib,io,json,struct,sys,zlib
from pathlib import Path
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
if (HERE/'assets.json').exists():raise SystemExit('Existing final assets: create a new run for replacement.')
spec=importlib.util.spec_from_file_location('original_builder',ROOT/'interface/integration/four-menus-seedvr7b-20261111-v1/build_assets.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
from bg2lib import load_key,resolve_resource
from mos_decode import pvr_to_dds_bytes,decode_pvrz_page
from workspace_paths import get_path
RUN=ROOT/'interface/experiments/sixth-ten-seedvr7b-x4-20261111-v1';results=json.loads((RUN/'results.json').read_text(encoding='utf-8'));bifs,entries=load_key();index={(n.upper(),k):loc for n,k,loc in entries};game=get_path('bg2ee_game_root');pages={}
sha=lambda data:hashlib.sha256(data).hexdigest()
for row in results['results']:
 n=row['resref'];path=RUN/row['output'];assert sha(path.read_bytes())==row['sha256'];im=Image.open(path).convert('RGBA');assert list(im.size)==row['size']
 for page,sx,sy,bw,bh,dx,dy in row['blocks']:pages.setdefault(page,[]).append((row['job'],im,sx,sy,bw,bh,dx,dy))
(HERE/'assets').mkdir();(HERE/'native-fixtures').mkdir();manifest=[]
for page,blocks in sorted(pages.items()):
 pvrz=resolve_resource(bifs,index[f'MOS{page:04}',1028])[0];pvr=zlib.decompress(pvrz[4:]);header=list(struct.unpack_from('<13I',pvr));h,w=header[6:8];raw=pvr[52+header[12]:];assert header[2]==11 and header[11]==1 and len(raw)==w*h;(HERE/'native-fixtures'/f'MOS{page:04}.dxt5').write_bytes(raw)
 stem='MAINMENU-MOS0181' if page==181 else 'HUD-MOS0140' if page==140 else 'MAINMENU-MOS0257' if page==257 else f'GAMEPLAY7B-MOS{page:04}'
 if page in (107,137,138,150,151,157,158,179):
  baseline=(game/'iee-assets'/f'{stem}-x4.dxt5').read_bytes();kind='installed active x4'
 else:
  baseline=bytes(old.expand_native(raw,w,h));kind='lossless native x4'
  hh=header[:];hh[6],hh[7],hh[12]=h*4,w*4,0;dds,_,_=pvr_to_dds_bytes(struct.pack('<13I',*hh)+baseline);assert Image.open(io.BytesIO(dds)).convert('RGBA').tobytes()==decode_pvrz_page(pvrz).resize((w*4,h*4),Image.Resampling.NEAREST).tobytes()
 assert len(baseline)==w*h*16;atlas=Image.new('RGBA',(w*4,h*4));mask=bytearray(w*h);rectangles=[]
 for n,im,sx,sy,bw,bh,dx,dy in blocks:
  atlas.paste(im.crop((dx*4,dy*4,(dx+bw)*4,(dy+bh)*4)),(sx*4,sy*4))
  for y in range(sy,sy+bh):
   assert not any(mask[y*w+sx:y*w+sx+bw]),'Overlapping new resource regions';mask[y*w+sx:y*w+sx+bw]=b'\1'*bw
  rectangles.append(dict(resref=n,rect=[sx,sy,bw,bh]))
 if page in (107,137,138,150,151,157,158,179):
  protected=[]
  for prior in ['four-menus-seedvr7b-20261111-v1','journal-paper-seedvr7b-20261111-v1','next-ten-seedvr7b-x4-20261111-v1','third-ten-seedvr7b-x4-20261111-v1','fourth-ten-seedvr7b-x4-20261111-v1','fifth-ten-seedvr7b-x4-20261111-v1']:
   old_manifest=json.loads((ROOT/'interface/integration'/prior/'assets.json').read_text())
   for a in old_manifest:
    if a['page']==page:protected.extend(a['rectangles'])
  for r in protected:
   sx,sy,bw,bh=r['rect'];assert not any(mask[y*w+x] for y in range(sy,sy+bh) for x in range(sx,sx+bw)), 'New asset overlaps accepted prior composition'
 buf=io.BytesIO();atlas.save(buf,format='DDS',pixel_format='DXT5');encoded=buf.getvalue()[128:];output=bytearray(baseline)
 for r in rectangles:
  sx,sy,bw,bh=r['rect']
  for y in range(sy,sy+bh):
   off=(y*w+sx)*16;output[off:off+bw*16]=encoded[off:off+bw*16]
 assert all(output[i*16:i*16+16]==baseline[i*16:i*16+16] for i,m in enumerate(mask) if not m)
 asset=HERE/'assets'/f'{stem}-x4.dxt5';asset.write_bytes(output);manifest.append(dict(page=page,stem=stem,asset=asset.name,width=w,height=h,fnv1a64=f'{old.fnv(raw):016X}',source_sha256=sha(raw),sha256=sha(output),baseline=kind,baseline_sha256=sha(baseline),rectangles=rectangles,untouched_blocks_exact=True));print(page,'prepared',flush=True)
(HERE/'assets.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print('Packaged',len(manifest),'pages')
