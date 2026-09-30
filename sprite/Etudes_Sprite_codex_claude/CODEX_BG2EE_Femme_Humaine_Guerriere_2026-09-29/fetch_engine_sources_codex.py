"""Fetch only named public primary source code (no audits)."""
from pathlib import Path
import urllib.request, json, hashlib
HERE=Path(__file__).resolve().parent
OUT=HERE/'source_reference'
OUT.mkdir(exist_ok=True)
repos={
    'NearInfinityBrowser/NearInfinity':[
        'src/org/infinity/resource/cre/decoder/util/SpriteUtils.java',
        'src/org/infinity/resource/cre/decoder/SpriteDecoder.java',
    ],
    'gemrb/gemrb':['gemrb/core/CharAnimations.cpp'],
    'Bubb13/EEex':[
        'EEex/copy/EEex_scripts/EEex_Assembly_x86-64.lua',
        'EEex/copy/EEex_scripts/EEex_Sprite.lua',
        'README.md',
    ],
}
records=[]
for repo,paths in repos.items():
    metadata=json.load(urllib.request.urlopen(f'https://api.github.com/repos/{repo}/commits/master'))
    sha=metadata['sha']
    for path in paths:
        url=f'https://raw.githubusercontent.com/{repo}/{sha}/{path}'
        raw=urllib.request.urlopen(url).read()
        target=OUT/(repo.replace('/','_')+'_'+Path(path).name)
        target.write_bytes(raw)
        records.append(dict(repo=repo,revision=sha,path=path,url=url,sha256=hashlib.sha256(raw).hexdigest(),downloaded='2026-09-29'))
(OUT/'references.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print(json.dumps(records,indent=2))
