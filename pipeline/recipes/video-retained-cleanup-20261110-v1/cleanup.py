"""Plan/apply the user-requested video-only cleanup with a hashed keep set."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
VIDEO = (ROOT / 'video').resolve()
HERE = Path(__file__).resolve().parent
PLAN = HERE / 'plan.json'
MEMORY = HERE / 'settings-memory'
NNDIR = VIDEO / 'daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1'
OLD = VIDEO / 'daynite/runs/daynite-h3-01604-seedvr-apollo30-20261110-v1'
TEXT = {'.json', '.md', '.py', '.log', '.txt', '.csv'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''):
            h.update(b)
    return h.hexdigest()


def rel(path):
    return path.relative_to(ROOT).as_posix()


def record(path, reason):
    return dict(path=rel(path), bytes=path.stat().st_size, sha256=sha(path), reason=reason)


def safe(path):
    resolved = path.resolve(strict=True)
    assert resolved.is_relative_to(VIDEO) and resolved != VIDEO, path
    assert path.absolute() == resolved, f'Link/redirect not allowed: {path}'
    for parent in (path, *path.parents):
        if parent == VIDEO.parent:
            break
        s = parent.lstat()
        assert not stat.S_ISLNK(s.st_mode), parent
        assert not (getattr(s, 'st_file_attributes', 0) & 0x400), f'Reparse point: {parent}'
    assert path.is_file(), path


def video_hash(path):
    return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path),
        '-map', '0:v:0', '-c:v', 'copy', '-f', 'hash', '-hash', 'sha256', '-'], text=True).strip()


def prepare():
    assert not PLAN.exists(), 'Plan is immutable; use a new cleanup version.'
    # Relocate the retained nearest pipeline inputs out of the rejected SeedVR branch.
    copied_input = NNDIR / 'DAYNITE-H3-01604-corrected-16x9-input-v1.mkv'
    if not copied_input.exists():
        shutil.copy2(OLD / copied_input.name, copied_input)
    assert sha(copied_input) == sha(OLD / copied_input.name)
    audio = NNDIR / 'DAYNITE-original-audio-aac.m4a'
    if not audio.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-i',
            str(OLD / 'DAYNITE-H3-01604-fondus-corriges-16x9-son-original-24fps-v2.mp4'),
            '-map', '0:a:0', '-c:a', 'copy', str(audio)], check=True)
    def audio_hash(p):
        return subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(p),
            '-map', '0:a:0', '-c:a', 'copy', '-f', 'hash', '-hash', 'sha256', '-'], text=True).strip()
    assert audio_hash(audio) == audio_hash(NNDIR / 'DAYNITE-H3-01604-NEAREST-Apollo8-1080p30-son-original-v1.mp4')

    duplicates = []
    duplicate_dirs = set()
    for asset, prefix in [('rest', 'REST'), ('restinn', 'RESTINN')]:
        run = VIDEO / f'{asset}/runs/{asset}-seedvr-apollo-20261109-v1'
        raw = list((run / 'comfy-output').glob('*.mp4'))
        assert len(raw) == 1, raw
        output = run / f'{prefix}-SeedVR2-3B-FP16-LAB-1080p15.mp4'
        a, b = video_hash(raw[0]), video_hash(output)
        assert a == b, f'Raw video not redundant: {raw[0]}'
        duplicates.append(dict(raw=rel(raw[0]), kept=rel(output), video_packet_hash=a))
        duplicate_dirs.add(rel(run / 'comfy-output'))

    discard_runs = {
        'daynite-seedvr-direction-20261109-v1',
        'daynite-h3-01604-seedvr-apollo30-20261110-v1',
        'daynite-keyframes-imagegen-20261110-v1',
        'daynite-keyframes-T3-day-geometry-night-style-20261110-v1',
        'daynite-minimax-h3-01600-analysis-20261110-v1',
        'flythr03-method-prototype-20260831',
        'flythr03-interpolation-apollo8-30fps-v1',
        'flythr03-interpolation-apollo8-30fps-v2',
        'flythr03-interpolation-comparison-20260831',
    }
    selected_all = {'deathand-upscale-seedvr2-lab-1080p-v1',
                    'deathand-interpolation-apollo8-30fps-v1',
                    'flythr03-upscale-seedvr2-lab-prototype-v1',
                    'flythr03-lab-interpolation-apollo8-30fps-v1',
                    'restdung-seedvr-reference-20261109-v1',
                    'restdung-seedvr-apollo30-20261109-v1',
                    'restdung-seedvr-ingame-20261109-v1',
                    'daynite-comfyui-experiment-20260814',
                    'daynite-keyframes-T4-night-geometry-day-style-20261110-v1'}
    # Selected runs remain immutable, including explicitly hashed QA evidence/logs.
    selected_partial = {'rest-seedvr-apollo-20261109-v1', 'restinn-seedvr-apollo-20261109-v1',
                        'daynite-seedvr-apollo-20261109-v1',
                        'daynite-h3-01604-nearest-apollo30-20261110-v1',
                        'daynite-h3-nearest-ingame-20261110-v1',
                        'daynite-keyframes-seedvr-imagegen-20261110-v1',
                        'daynite-minimax-h3-01604-fades-20261110-v1'}
    keep, remove = [], []
    for path in sorted(VIDEO.rglob('*')):
        if not path.is_file():
            continue
        safe(path)
        parts = path.relative_to(VIDEO).parts
        reason = None
        if 'runs' not in parts:
            if parts[0] == 'tools' and path.suffix in {'.png', '.jpg'}:
                reason = 'obsolete comparator UI capture'
        else:
            idx = parts.index('runs'); run = parts[idx + 1]
            if run == 'legacy-webm-conversion-20260814':
                native = VIDEO / parts[0] / f'{path.stem}.wbm'
                assert native.is_file(), path
                reason = 'unselected legacy WebM derivative; canonical WBM retained'
            elif run in discard_runs:
                reason = 'unselected/replaced experiment; settings archived'
            elif run == 'pocketzz-comfyui-experiments-20260814':
                if path.name != 'ComfyUI_00002_.mp4':
                    reason = 'POCKETZZ unselected trial; user keeps only SeedVR FullHD candidate'
            elif run in selected_all:
                pass
            elif run in selected_partial:
                if any(rel(path).startswith(d + '/') for d in duplicate_dirs):
                    reason = 'redundant Comfy input/output; same retained video stream'
                elif run == 'daynite-seedvr-apollo-20261109-v1':
                    if path.name not in {'DAYNITE-SeedVR2-3B-FP16-LAB-1080p15.mp4', 'production.json'}:
                        reason = 'DAYNITE old interpolation/review not used by retained H3 chain'
                elif run == 'daynite-h3-nearest-ingame-20261110-v1':
                    if path.suffix == '.nul':
                        reason = 'temporary commit path list'
                elif run == 'daynite-keyframes-seedvr-imagegen-20261110-v1':
                    if path.name in {'DAYNITE-timing-and-assembly.txt', 'MINIMAX-H3-prompt-8s.txt'}:
                        reason = 'superseded eight-second generation plan; settings archived'
                elif path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.js'}:
                    reason = 'temporary inspection capture or syntax-check copy'
                elif path.suffix.lower() == '.log':
                    reason = 'execution log retained in settings memory'
            else:
                raise RuntimeError(f'Unclassified run, refusing cleanup: {path}')
        if reason:
            assert 'installations' not in parts and parts[0] not in {'index'}, path
            entry = record(path, reason)
            if path.suffix.lower() in TEXT and path.name != 'commit-paths.txt':
                archive = MEMORY / path.relative_to(ROOT)
                archive.parent.mkdir(parents=True, exist_ok=True)
                if not archive.exists():
                    shutil.copy2(path, archive)
                assert sha(archive) == entry['sha256']
                entry['settings_archive'] = rel(archive)
            remove.append(entry)
        else:
            keep.append(record(path, 'canonical source, retained production chain, QA, installation backup or active tool'))

    # Verify inventory sources and accepted comparison media are all in the keep set.
    kept = {x['path'].casefold() for x in keep}
    with (VIDEO / 'index/resources.csv').open(encoding='utf-8-sig', newline='') as f:
        resources = list(csv.DictReader(f))
    assert len(resources) == 50
    for row in resources:
        p = ROOT / row['extracted_path']
        assert rel(p).casefold() in kept and sha(p).lower() == row['source_sha256'].lower(), p
    for path in (VIDEO / 'index/qa-decisions').rglob('*.json'):
        data = json.loads(path.read_text())
        for field in data.get('files', {}).values():
            p = ROOT / field
            if p.is_file():
                assert rel(p).casefold() in kept, f'QA-referenced media deletion: {p}'
    installations = []
    for receipt in (VIDEO / 'installations').glob('*/installation.json'):
        d = json.loads(receipt.read_text())
        target = Path(d['resolved_target']); backup = ROOT / d['backup']
        assert sha(target) == d['after_sha256'] and sha(backup) == d['before_sha256']
        assert rel(backup).casefold() in kept
        installations.append(dict(receipt=rel(receipt), installed_path=str(target),
            installed_sha256=sha(target), backup=rel(backup), backup_sha256=sha(backup)))
    plan = dict(schema='video-retained-cleanup-plan-v1', scope='workspace video/ only; no Desktop, ComfyUI, game or release writes',
        user_request='update video tracking; remove unselected attempts for all videos; keep final-result inputs; commit',
        pocketzz_user_choice='keep only SeedVR FullHD candidate; not a QA acceptance',
        relocated_dependencies=[dict(previous=rel(OLD / copied_input.name), retained=rel(copied_input), sha256=sha(copied_input)),
            dict(previous=rel(OLD / 'DAYNITE-H3-01604-fondus-corriges-16x9-son-original-24fps-v2.mp4'),
                 retained=rel(audio), audio_packet_hash=audio_hash(audio), operation='AAC packet extraction, no reencoding')],
        verified_duplicates=duplicates, protected_installations=installations,
        retained=keep, remove=remove,
        summary=dict(retained_files=len(keep), retained_bytes=sum(x['bytes'] for x in keep),
                     remove_files=len(remove), remove_bytes=sum(x['bytes'] for x in remove),
                     canonical_sources=len(resources), settings_files=sum('settings_archive' in x for x in remove)))
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(plan['summary']), flush=True)
    print(json.dumps(Counter(x['path'].split('/')[1] for x in remove)), flush=True)


def apply():
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    receipt = HERE / 'cleanup.json'
    assert not receipt.exists(), 'Cleanup receipt already exists.'
    for item in plan['retained']:
        p = ROOT / item['path']; safe(p)
        assert sha(p) == item['sha256'], f'Retained file changed since planning: {p}'
    for item in plan['remove']:
        p = ROOT / item['path']; safe(p)
        assert sha(p) == item['sha256'], f'Deletion target changed since planning: {p}'
        if item.get('settings_archive'):
            assert sha(ROOT / item['settings_archive']) == item['sha256']
    removed, failed = [], []
    for item in plan['remove']:
        p = ROOT / item['path']
        try:
            p.unlink(); removed.append(item['path'])
        except OSError as exc:
            failed.append(dict(path=item['path'], error=str(exc)))
    # Only prune already empty directories under runs; never recursive-delete computed roots.
    empty_dirs = []
    for p in sorted(VIDEO.glob('*/runs/**/'), key=lambda p: len(p.parts), reverse=True):
        if p.is_dir() and p.resolve().is_relative_to(VIDEO) and not p.is_symlink():
            try:
                p.rmdir(); empty_dirs.append(rel(p))
            except OSError:
                pass
    for item in plan['retained']:
        p = ROOT / item['path']; assert p.is_file() and sha(p) == item['sha256'], p
    for d in plan['protected_installations']:
        assert sha(Path(d['installed_path'])) == d['installed_sha256']
        assert sha(ROOT / d['backup']) == d['backup_sha256']
    result = dict(schema='video-retained-cleanup-receipt-v1', state='complete' if not failed else 'partial',
        plan_sha256=sha(PLAN), removed_files=len(removed),
        removed_bytes=sum(x['bytes'] for x in plan['remove'] if x['path'] in set(removed)),
        removed_paths=removed, failed=failed, pruned_empty_directories=empty_dirs,
        retained_files_verified=len(plan['retained']), canonical_sources_preserved=50,
        settings_archives_verified=True, installed_files_and_backups_unchanged=True)
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in {'removed_paths', 'pruned_empty_directories'}}))
    assert not failed, failed


if __name__ == '__main__':
    assert len(sys.argv) == 2 and sys.argv[1] in {'plan', 'apply'}
    {'plan': prepare, 'apply': apply}[sys.argv[1]]()
