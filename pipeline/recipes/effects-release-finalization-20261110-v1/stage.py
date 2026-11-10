"""Stage a new versioned payload; preserve the former canonical stage."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import shutil
import sys

sys.path.insert(0, str(Path(__file__).parent))
from build import ROOT, OUT, RELEASE, load, rel, save, sha


def main():
    content=load(RELEASE/'manifests/content.json')
    target=RELEASE/'bg2hd/payload-allvalidated'
    new=RELEASE/'.payload-alpha8-20261110-v1'
    previous=RELEASE/'archive/payload-alpha7-before-effects-20261110-v1'
    assert target.resolve().is_relative_to(RELEASE.resolve())
    assert previous.resolve().is_relative_to(RELEASE.resolve())
    assert not previous.exists(), 'Previous staging must remain immutable'
    assert not (OUT/'staging.json').exists()
    new.mkdir(exist_ok=True)
    destinations=set()
    directories=set()
    jobs=[]
    linked=set()
    for e in content['entries']:
        src=(ROOT/e['source']).resolve()
        assert src.is_relative_to(ROOT.resolve())
        assert e['qa_status']=='validated'
        dest=new/e['payload_group']/Path(e['source']).name
        assert dest not in destinations
        destinations.add(dest)
        jobs.append((src,dest,e))
        if dest.parent not in directories:
            dest.parent.mkdir(parents=True,exist_ok=True)
            directories.add(dest.parent)
    def copy(job):
        src,dest,e=job
        assert src.stat().st_size==e['bytes'],src
        if not dest.exists():
            if '--hardlink' in sys.argv:
                try:
                    os.link(src,dest)
                    linked.add(str(dest))
                except OSError:
                    shutil.copyfile(src,dest)
            else:
                shutil.copyfile(src,dest)
        assert dest.stat().st_size==e['bytes'] and sha(dest)==e['sha256'],dest
        return e['bytes']
    total=0
    with ThreadPoolExecutor(max_workers=12) as pool:
        for i,size in enumerate(pool.map(copy,jobs)):
            total+=size
            if (i+1)%10000==0: print(f'Staged and SHA-verified {i+1}/{len(jobs)} files',flush=True)
    actual={p for p in new.rglob('*') if p.is_file()}
    assert actual==destinations
    previous.parent.mkdir(exist_ok=True)
    if target.exists(): shutil.move(str(target),str(previous))
    shutil.move(str(new),str(target))
    save(OUT/'staging.json',dict(status='passed',payload_root=rel(target),files=len(jobs),bytes=total,
        sha256_verified=True,hardlinked_files=len(linked),previous_payload=rel(previous),game_modified=False))
    print(f'Staged {len(jobs)} files, {total} bytes',flush=True)


if __name__=='__main__':main()
