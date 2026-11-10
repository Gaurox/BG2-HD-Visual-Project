"""Create an immutable exact-byte shared-image pack; native/runtime identities unchanged."""
import argparse,copy,hashlib,json,shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from effect_storage import NAME,encode,read_map,validate_layout

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()
def build(source,output,receipt):
 assert not output.exists() and not receipt.exists(),'Use a new output version'
 m=json.loads((source/'manifest.json').read_text(encoding='utf-8-sig'));assert not m.get('storage')
 frames=m['frames'];ids=[];first={}
 validate_layout((source/m['registry']).read_bytes(),frames)
 for i,f in enumerate(frames):
  assert f['frame']==i
  key=(f['sha256'],f['bytes'],tuple(f['physical_size_x4']),tuple(f['logical_size_x1']))
  ids.append(first.setdefault(key,i))
 assert all(ids[j]==j for j in ids)
 output.mkdir(parents=True)
 def process(i):
  f=frames[i];src=source/f['asset'];assert src.stat().st_size==f['bytes']
  if ids[i]==i:
   shutil.copyfile(src,output/f['asset']);assert sha(output/f['asset'])==f['sha256']
  assert sha(src)==f['sha256']
 with ThreadPoolExecutor(max_workers=12) as pool:
  for i,_ in enumerate(pool.map(process,range(len(frames)))):
   if (i+1)%10000==0:print(f'Logical images verified {i+1}/{len(frames)}',flush=True)
 shutil.copyfile(source/m['registry'],output/m['registry']);assert sha(output/m['registry'])==m['registry_sha256']
 raw=encode((output/m['registry']).read_bytes(),ids);(output/NAME).write_bytes(raw)
 result=copy.deepcopy(m);result['storage']=dict(index=NAME,version=1,bytes=len(raw),sha256=sha(output/NAME),physical_frame_count=len(set(ids)))
 result['storage_parent']=dict(manifest_sha256=sha(source/'manifest.json'),registry_sha256=m['registry_sha256'])
 (output/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 assert read_map(output,result)==ids
 assert {p.name for p in output.iterdir()}=={'manifest.json',NAME,m['registry']}|{f['asset'] for i,f in enumerate(frames) if ids[i]==i}
 saved=sum(f['bytes'] for i,f in enumerate(frames) if ids[i]!=i)
 report=dict(status='verified',logical_frames=len(frames),physical_frames=len(set(ids)),removed_files=len(frames)-len(set(ids)),
    saved_rgba_bytes=saved,index_bytes=len(raw),net_frame_storage_saved_bytes=saved-len(raw),registry_unchanged=True,
    logical_frame_metadata_unchanged=result['frames']==m['frames'],resources_unchanged=result['resources']==m['resources'],
    all_logical_sha256_verified=True,manifest_sha256=sha(output/'manifest.json'),storage=result['storage'])
 receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args();build(a.source,a.output,a.receipt)
