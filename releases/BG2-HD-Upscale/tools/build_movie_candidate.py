"""Add the 37 WBM to the verified compressed alpha.12 installer."""
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from build_optimized_candidate import ROOT, MOD, json_bytes
from compress_optimized_candidate import FINAL as BASE
from encode_release_movies import DIST, TARGET

VERSION = '0.1.0-alpha.13'
OUT = DIST / f'BG2HD-{VERSION}-windows-local-alpha-deflate.zip'
MOVIES = 'bg2hd/manifests/movie-release-candidate.json'
TP2 = 'bg2hd/bg2hd.tp2'
ID = 4300
LABEL = 'cinematics-hd-vp8'
BUILD = 'BUILD-MANIFEST.json'
CHECKS = 'checksums.sha256'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def mutation(base, movies):
    content = json.loads(base.read(MOD+'content.json'))
    components = json.loads(base.read(MOD+'components.json'))
    release = json.loads(base.read(MOD+'release.json'))
    tp2 = base.read(TP2).decode()
    if release['version'] != '0.1.0-alpha.12' or any(r['id']==ID for r in components['components']):
        raise ValueError('Baseline or component identity differs')
    if (len(movies['movies']) != 37 or len({r['destination'] for r in movies['movies']}) != 37 or
            movies['target_video_bps'] != TARGET or sum(r['bytes'] for r in movies['movies']) != movies['total_bytes']):
        raise ValueError('Unexpected video selection')
    assets = {}
    groups = set()
    directories = set()
    copies = []
    for row in movies['movies']:
        dest = row['destination']
        if not re.fullmatch(r'(?:lang/[a-z]{2}_[A-Z]{2}/)?movies/[A-Za-z0-9_]+\.wbm',dest):
            raise ValueError(f'Invalid native movie destination: {dest}')
        d = Path(dest)
        locale = d.parts[1].lower().replace('_','-') if d.parts[0]=='lang' else 'default'
        group = f'movies-{locale}'
        source = f'bg2hd/payload/{group}/{d.name}'
        path = ROOT / row['source']
        if source in assets or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise ValueError(f'Duplicate or divergent film source: {source}')
        assets[source] = (path,row['sha256'])
        groups.add(group)
        directories.update(str(parent.as_posix()) for parent in d.parents if parent!=Path('.'))
        copies.append(f'  COPY_LARGE ~{source}~ ~{dest}~')
        content['entries'].append(dict(component_id=ID, component_label=LABEL, payload_group=group,
            kind='movie', area='MOVIES', source=row['source'], source_run=DIST.relative_to(ROOT).as_posix(),
            destination=dest, bytes=row['bytes'], sha256=row['sha256'],
            qa_status='pending-ingame', scale=1, model='FullHD-VP8-8Mbit', install_order=ID,
            replaces_component_output=False))
    components['components'].append(dict(id=ID,label=LABEL,name='HD cinematics (37 films and language variants)',
        status='blocked',depends_on=[0],payload_groups=sorted(groups),
        reason='WBM 8 Mbit/s encoded and verified offline; final in-game validation pending.'))
    components['components'].sort(key=lambda row:row['id'])
    content['generated_by']='tools/build_movie_candidate.py'
    release['version']=VERSION
    release['blocking_conditions'].append('cinematics-vp8-8mbit-ingame-validation-pending')
    release['manifest_files'].append('manifests/movie-release-candidate.json')
    release['content_scope']['movies']=(
        '37 native destinations including localized variants, Full HD VP8 at 8 Mbit/s video target, '
        'Vorbis audio copied, final in-game validation pending.')
    release['content_scope']['excluded']=[e for e in release['content_scope']['excluded']
                                         if not e.startswith('movies without finalized')]
    release['content_scope']['excluded'].append('13 tutorial movies and console test aliases')
    tp2,count=re.subn(r'(?m)^VERSION ~[^~]+~\r?$',f'VERSION ~{VERSION}~',tp2)
    if count!=1:
        raise ValueError('Missing WeiDU version declaration')
    lines=[f'BEGIN ~HD cinematics (37 films and language variants)~',f'  DESIGNATED {ID}',f'  LABEL ~{LABEL}~',
           '  REQUIRE_PREDICATE GAME_IS ~bg2ee~ @11',
           '  REQUIRE_COMPONENT ~bg2hd/bg2hd.tp2~ ~0~ @14']
    lines.extend(f'  MKDIR ~{d}~' for d in sorted(directories,key=lambda d:(d.count('/'),d)))
    tp2=tp2.rstrip()+'\n\n'+'\n'.join([*lines,*copies])+'\n'
    build=json.loads(base.read(BUILD))
    build.update(version=VERSION,content_entries=len(content['entries']),movies=37,video_bytes=movies['total_bytes'],
        base_compressed_archive_sha256=BASE.with_suffix('.zip.sha256').read_text(encoding='ascii').split()[0])
    block={MOD+'content.json':json_bytes(content),MOD+'components.json':json_bytes(components),
        MOD+'release.json':json_bytes(release),MOVIES:json_bytes(movies),TP2:tp2.encode(),
        'BUILD-STATUS.txt':f'BG2 HD Visual Project {VERSION}\nLOCAL CANDIDATE. Final ingame validation pending.\n'.encode()}
    build['content_manifest_sha256']=hashlib.sha256(block[MOD+'content.json']).hexdigest().upper()
    block[BUILD]=json_bytes(build)
    return assets,block,len(content['entries'])


def put(archive, name, data):
    item=ZipInfo(name,date_time=(1980,1,1,0,0,0))
    archive.writestr(item,data,compress_type=ZIP_DEFLATED,compresslevel=4)


def build():
    if OUT.exists():
        raise FileExistsError(OUT)
    stage=OUT.with_suffix('.partial')
    movies=json.loads((DIST/'movies.json').read_bytes())
    with ZipFile(BASE) as old:
        original={i.filename:i for i in old.infolist()}
        if len(original)!=len(old.infolist()):
            raise ValueError('Baseline ZIP contains duplicate names')
        assets,block,content_count=mutation(old,movies)
        checks={n:s for s,n in (ln.split('  ',1) for ln in old.read(CHECKS).decode().splitlines())}
    digest=hashlib.sha256()
    with BASE.open('rb') as src, stage.open('xb') as dst:
        for data in iter(lambda:src.read(16<<20),b''):
            digest.update(data)
            dst.write(data)
    if digest.hexdigest().upper()!=BASE.with_suffix('.zip.sha256').read_text(encoding='ascii').split()[0]:
        raise ValueError('Compressed baseline hash differs')
    changed=set(block)|{CHECKS}
    with ZipFile(stage,'a') as archive:
        # Retain exact compressed local records and replace only their directory
        # entries for metadata updated by this candidate.
        archive.filelist[:]=[i for i in archive.filelist if i.filename not in changed]
        for name in changed:
            archive.NameToInfo.pop(name,None)
        for name,data in block.items():
            put(archive,name,data)
            checks[name]=hashlib.sha256(data).hexdigest().upper()
        for name,(path,expected) in assets.items():
            archive.write(path,name,compress_type=ZIP_STORED)
            checks[name]=expected
        put(archive,CHECKS,''.join(f'{s}  {n}\n' for n,s in sorted(checks.items())).encode())
    with ZipFile(stage) as archive:
        if len(archive.infolist())!=len(checks)+1 or set(archive.namelist())!=set(checks)|{CHECKS}:
            raise ValueError('Final installer inventory differs')
        for name in set(original)-changed:
            a,b=original[name],archive.getinfo(name)
            attrs=('header_offset','CRC','file_size','compress_size','compress_type')
            if any(getattr(a,k)!=getattr(b,k) for k in attrs):
                raise ValueError(f'Existing compressed record differs: {name}')
        for name in [*block,*assets]:
            with archive.open(name) as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest().upper()!=checks[name]:
                    raise ValueError(f'New package file differs: {name}')
    result=dict(version=VERSION,bytes=stage.stat().st_size,sha256=sha(stage),
        movies=37,movie_bytes=movies['total_bytes'],content_entries=content_count,
        archive_members=len(checks)+1,unchanged_archive_members=len(set(original)-changed),
        ingame_validation='pending')
    stage.rename(OUT)
    OUT.with_suffix('.zip.sha256').write_text(f"{result['sha256']}  {OUT.name}\n",encoding='ascii')
    (DIST/'verification.json').write_bytes(json_bytes(result))
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    build()
