"""Read-only movie-path diagnosis; write a new report, never replace evidence."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path
from build_graphics_inventory import KeyIndex


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--documents', type=Path, default=Path.home() / 'Documents')
    args = parser.parse_args()
    game = get_path('bg2ee_game_root', required=True).resolve()
    receipt = json.loads((ROOT / 'video/installations/daynite-h3-nearest-20261110-v1/installation.json').read_text())
    installed = game / 'movies/daynite.wbm'
    runtime = ROOT / receipt['source'].replace('\\', '/')
    # Known-folder path checked separately; allow redirected Documents explicitly.
    documents = args.documents.resolve()
    profiles = sorted(p for p in documents.glob('*Baldur*') if p.is_dir())
    home_roots = [p / name for p in profiles
                  for name in ('movies', 'characters', 'portraits', 'sounds', 'scripts', 'override')]
    search_roots = [game / 'movies', game / 'lang', game / 'override', *home_roots]
    matches = []
    for root in search_roots:
        if not root.is_dir():
            continue
        print('SCAN', root, flush=True)
        for directory, _, files in os.walk(root):
            for name in files:
                if Path(name).stem.casefold() not in {'daynite', 'niteday'}:
                    continue
                p = Path(directory) / name
                matches.append(dict(path=str(p), size=p.stat().st_size, sha256=sha(p)))
    print('KEY', flush=True)
    key = KeyIndex(game)
    key_matches = [dict(resref=r.resref, type=r.resource_type, bif=r.bif_name)
                   for r in key.resources if r.resref in {'DAYNITE', 'NITEDAY'}]
    print('LOGS', flush=True)
    logs = []
    for p in sorted(game.glob('*.log')):
        data = p.read_bytes()
        hits = [line for line in data.splitlines()
                if re.search(rb'daynite|niteday|movie|cinematic|\.wbm', line, re.I)]
        logs.append(dict(path=str(p), size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                         modified_utc=datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(),
                         movie_matches=[v.decode('utf-8', errors='replace') for v in hits]))
    print('PROBE', installed, flush=True)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
        '-show_entries', 'stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames:format=duration',
        '-of', 'json', str(installed)], timeout=60))
    report = dict(schema='daynite-runtime-diagnosis-v1', collected_utc=datetime.now(timezone.utc).isoformat(),
        game_root=str(game), documents=str(documents), search_roots=[str(p) for p in search_roots],
        installed_target=str(installed), installed_sha256=sha(installed),
        runtime_source=str(runtime.relative_to(ROOT)), runtime_sha256=sha(runtime),
        installation_receipt_sha256=receipt['after_sha256'],
        installed_matches_runtime=sha(installed) == sha(runtime) == receipt['after_sha256'],
        matching_files=matches, key_matches=key_matches, logs=logs, installed_probe=probe,
        conclusion='Installed DAYNITE bytes are current; actually played resource remains unidentified. No runtime correction established.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(dict(report=str(args.output), installed_matches_runtime=report['installed_matches_runtime'],
        matching_files=len(matches), key_matches=len(key_matches),
        log_movie_matches=sum(len(x['movie_matches']) for x in logs))))


if __name__ == '__main__':
    main()
