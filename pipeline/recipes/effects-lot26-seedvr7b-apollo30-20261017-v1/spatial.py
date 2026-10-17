"""Resumable lot26 using the established SeedVR7B spatial producer."""
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/lot26-seedvr7b-apollo30-20261017-v1'
spec = importlib.util.spec_from_file_location('lot33_spatial_producer', ROOT / 'pipeline/recipes/effects-lot33-seedvr7b-apollo30-20261014-v1/produce.py')
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
producer.BATCH = BATCH
original_command = producer.command


def command(stage, asset, args):
    if stage == 'spatial':
        args = [*args, '--server', 'http://127.0.0.1:8188', '--poll-seconds', '0.2']
    return original_command(stage, asset, args)


producer.command = command

if __name__ == '__main__':
    sys.argv = [sys.argv[0], 'spatial', *sys.argv[1:]]
    raise SystemExit(producer.main())
