"""Established SeedVR7B x4/LAB producer for the33 native impact assets."""
from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('spatial33',ROOT/'pipeline/recipes/effects-lot33-seedvr7b-apollo30-20261014-v1/produce.py')
producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
producer.BATCH=ROOT/'effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1'
original=producer.command


def command(stage,asset,args):
    return original(stage,asset,[*args,'--server','http://127.0.0.1:8188','--poll-seconds','0.2'])


producer.command=command
if __name__=='__main__':
    sys.argv=[sys.argv[0],'spatial',*sys.argv[1:]]
    raise SystemExit(producer.main())
