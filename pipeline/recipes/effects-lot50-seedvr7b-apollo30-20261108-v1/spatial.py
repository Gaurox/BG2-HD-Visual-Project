import importlib.util
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('spatial_batch',ROOT/'pipeline/recipes/effects-lot33-seedvr7b-apollo30-20261014-v1/produce.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
p.BATCH=ROOT/'effects/batches/lot50-seedvr7b-apollo30-20261108-v1'
original=p.command
def command(stage,a,args):
    args[0]=str(HERE/'spatial_one.py')
    return original(stage,a,[*args,'--server','http://127.0.0.1:8188','--poll-seconds','0.2'])
p.command=command
if __name__=='__main__':
    sys.argv=[sys.argv[0],'spatial',*sys.argv[1:]]
    raise SystemExit(p.main())
