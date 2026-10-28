"""End temporary V11 diagnostics; preserve every other INI byte and current DLL."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
from workspace_paths import get_path
from install_renderer_candidate import ensure_game_stopped,running_game_processes

GAME=get_path('bg2ee_game_root',required=True)
OUT=ROOT/'projectiles/analysis/validations-manuelles-consolidees-20261028-v1'
sha=lambda b:hashlib.sha256(b).hexdigest().upper()


def save(p,d):
    with p.open('x',encoding='utf-8') as f:
        json.dump(d,f,ensure_ascii=False,indent=2)
        f.write('\n')


def main():
    assert (OUT/'runtime-session.log').is_file() and (OUT/'latest-feedback.json').is_file()
    assert not (OUT/'trace-disabled.json').exists()
    ensure_game_stopped(running_game_processes)
    ini=GAME/'InfinityEngine-Enhancer.ini'
    before=ini.read_bytes()
    assert before.count(b'EnableEffectStreamingTrace = true')==1
    after=before.replace(b'EnableEffectStreamingTrace = true',b'EnableEffectStreamingTrace = false')
    dll=sha((GAME/'InfinityEngine-Enhancer.dll').read_bytes())
    expected=json.loads((ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-lightning-trails-20261028-v11/installation.json').read_text(encoding='utf-8-sig'))['dll']['sha256']
    assert dll==expected
    (OUT/'before-trace-disable.ini').write_bytes(before)
    (OUT/'candidate-trace-disabled.ini').write_bytes(after)
    save(OUT/'trace-disable-plan.json',dict(target='config://bg2ee_game_root/InfinityEngine-Enhancer.ini',
        before_sha256=sha(before),after_sha256=sha(after),only_change='EnableEffectStreamingTrace=true -> false',
        dll_sha256=dll,backup='before-trace-disable.ini'))
    temp=ini.with_name('InfinityEngine-Enhancer.ini.projectiles-trace-disable-v1.tmp')
    assert temp.resolve().parent==GAME.resolve() and not temp.exists()
    with temp.open('xb') as f:
        f.write(after)
        f.flush()
        os.fsync(f.fileno())
    assert ini.read_bytes()==before
    os.replace(temp,ini)
    assert ini.read_bytes()==after and sha((GAME/'InfinityEngine-Enhancer.dll').read_bytes())==dll
    save(OUT/'trace-disabled.json',dict(status='disabled',utc=datetime.now(timezone.utc).isoformat(),
        changed_file='config://bg2ee_game_root/InfinityEngine-Enhancer.ini',
        before_sha256=sha(before),after_sha256=sha(after),DLL_unchanged=dll,
        other_INI_bytes_unchanged=True,game_and_loader_stopped=True,images_changed=False))
    print('Temporary trace disabled; V11 DLL and other INI bytes preserved')


if __name__=='__main__':
    main()
