"""Install seven technically verified endings WBM files + language-independent console aliases."""
import argparse
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
RECEIPT=ROOT/'video/installations/endings-shared-apollo30-20261111-v1'
RP=RECEIPT/'installation.json'
ALIASES={('END15FPS','default'):'HDENEN',('END15FPS','de_DE'):'HDENDE',('END15FPS','it_IT'):'HDENIT',('END15FPS','pl_PL'):'HDENPL',('MELISSAN','default'):'HDMLEN',('MELISSAN','de_DE'):'HDMLDE',('MELISSAN','pl_PL'):'HDMLPL'}

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def stopped():
    p=subprocess.run(['powershell','-NoProfile','-Command',
        "$p=Get-Process | Where-Object {$_.ProcessName -match '^(Baldur.*|BGMain|BG2.*|InfinityLoader.*)$'}; if($p){$p | Select-Object Id,ProcessName | ConvertTo-Json -Compress}"],capture_output=True,text=True,check=True)
    assert not p.stdout.strip(),'Close game/InfinityLoader before installation: '+p.stdout

def target(game,rel):
    path=(game/rel).resolve()
    assert path.is_relative_to(game) and path.suffix.lower()=='.wbm'
    return path

def prepare():
    stopped();game=get_path('bg2ee_game_root',required=True).resolve()
    manifest=json.loads((ROOT/'video/index/endings-finals30-20261111-v1.json').read_text())
    assert manifest['state']=='runtime-ready'
    variants=manifest['variants']
    assert {(v['film'],v['locale']) for v in variants}==set(ALIASES)
    entries=[]
    # Resolve all fourteen destinations before saving or replacing anything.
    for v in variants:
        assert v['fps']=='30/1' and v['native_audio_pcm_identical'] and v['ssim_sampled_all']>.99
        f=v['files']['game_ready'];source=ROOT/f['path'];assert sha(source)==f['sha256']
        prefix='config://bg2ee_game_root/';assert v['target'].startswith(prefix)
        for role,rel in [('localized-movie',v['target'][len(prefix):]),('console-test-alias','movies/'+ALIASES[(v['film'],v['locale'])]+'.wbm')]:
            p=target(game,rel);existed=p.is_file()
            assert existed if role=='localized-movie' else not p.exists(),(role,p)
            if role=='console-test-alias':
                assert not (game/'override'/p.name).exists()
                assert not list((game/'lang').glob('*/movies/'+p.name))
            entries.append(dict(film=v['film'],locale=v['locale'],role=role,alias=ALIASES[(v['film'],v['locale'])],target=prefix+rel,
                resolved_target=str(p),existed_before=existed,before_sha256=sha(p) if existed else None,
                backup=('video/installations/endings-shared-apollo30-20261111-v1/before/'+rel) if existed else None,
                source=f['path'],after_sha256=f['sha256'],state='planned'))
    RECEIPT.mkdir(parents=True,exist_ok=False)
    for e in entries:
        if e['existed_before']:
            backup=ROOT/e['backup'];backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(e['resolved_target'],backup);assert sha(backup)==e['before_sha256']
        e['state']='backed-up' if e['existed_before'] else 'new-alias'
    save(RP,dict(schema='bg2-endings-local-install-v1',state='prepared',
        prepared_utc=datetime.now(timezone.utc).isoformat(),entries=entries,
        qa_ingame='pending-user',release_integration=False))
    print('PREPARED: 7 original backups, 14 destinations checked',flush=True)

def install():
    stopped();data=json.loads(RP.read_text());assert data['state']=='prepared'
    game=get_path('bg2ee_game_root',required=True).resolve()
    for e in data['entries']:
        rel=e['target'].removeprefix('config://bg2ee_game_root/');p=target(game,rel)
        assert str(p)==e['resolved_target'];source=ROOT/e['source'];assert sha(source)==e['after_sha256']
        if e['existed_before']:
            assert sha(ROOT/e['backup'])==e['before_sha256'] and sha(p)==e['before_sha256']
        else:assert not p.exists()
    for e in data['entries']:
        stopped();p=Path(e['resolved_target']);source=ROOT/e['source']
        assert sha(p)==e['before_sha256'] if e['existed_before'] else not p.exists()
        temp=p.with_name(p.name+'.bg2hd-endings-20261111-v1.tmp');assert not temp.exists()
        shutil.copy2(source,temp);assert sha(temp)==e['after_sha256']
        stopped();os.replace(temp,p);assert sha(p)==e['after_sha256']
        e['state']='installed';save(RP,data);print('INSTALLED',e['locale'],e['role'],flush=True)
    for e in data['entries']:assert sha(e['resolved_target'])==e['after_sha256']
    data.update(state='installed',installed_utc=datetime.now(timezone.utc).isoformat());save(RP,data)
    save(ROOT/'video/index/endings-ingame-test-20261111-v1.json',data)
    save(Path(__file__).parent/'metadata/installation.json',data)
    print('ALL_SEVEN_ENDINGS_AND_ALIASES_INSTALLED',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','install']);args=parser.parse_args()
    {'prepare':prepare,'install':install}[args.action]()
