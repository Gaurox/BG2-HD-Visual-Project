"""Hash each selected physical source once, concurrently, for this compilation."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).parent))
from build import ROOT,OUT,RELEASE,load,save,sha


def main():
    entries=[e for e in load(RELEASE/'manifests/content.json')['entries'] if e['kind']!='effect']
    for c in load(RELEASE/'manifests/effect-release-candidates.json')['candidates']:
        root=ROOT/c['runtime_pack']['path'];pack=load(root/c['runtime_pack']['manifest'])
        entries += [dict(source=c['runtime_pack']['path']+'/'+c['runtime_pack']['manifest'],bytes=(root/c['runtime_pack']['manifest']).stat().st_size,sha256=c['runtime_pack']['manifest_sha256']),
                    dict(source=c['runtime_pack']['path']+'/'+pack['registry'],bytes=pack['registry_bytes'],sha256=pack['registry_sha256'])]
        entries += [dict(source=c['runtime_pack']['path']+'/'+f['asset'],bytes=f['bytes'],sha256=f['sha256']) for f in pack['frames']]
        entries += c['runtime_files']
    unique={e['source']:e for e in entries}
    def check(e):
        path=(ROOT/e['source']).resolve();assert path.is_relative_to(ROOT.resolve())
        before=path.stat();digest=sha(path);after=path.stat()
        assert before.st_size==after.st_size==e['bytes'] and before.st_mtime_ns==after.st_mtime_ns,path
        assert digest==e['sha256'],path
        return str(path),dict(bytes=after.st_size,mtime_ticks=621355968000000000+after.st_mtime_ns//100,sha256=digest)
    files={}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for i,(path,record) in enumerate(pool.map(check,unique.values())):
            files[path]=record
            if (i+1)%10000==0: print(f'Physical SHA256 {i+1}/{len(unique)}',flush=True)
    save(OUT/'physical-hash-index.json',dict(schema='bg2-release-task-physical-hash-index-v1',files=files))
    print(f'Physical SHA256 complete: {len(files)} files',flush=True)


if __name__=='__main__':main()
