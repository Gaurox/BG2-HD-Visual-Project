"""Check newly produced Monster resources with the phase-4 host reader; reuse byte-identical pilot proofs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from palette_monster_work_plan import require


def verify(pack,executable,output):
    require(not output.exists(),'new native verification directory required');output.mkdir(parents=True)
    manifest=json.loads((pack/'pack.json').read_text());pilot=json.loads((ROOT/'docs/measurements/q3m-monster-pilot-x2-20261003-v1/verification.json').read_text())
    require(file_sha(executable)==pilot['host_test']['sha256'],'native host reader changed')
    records=[]
    for resource in manifest['resources']:
        ref=resource['resref'];oracle=ROOT/resource['oracle']['path']
        require(file_sha(oracle)==resource['oracle']['sha256'],'native oracle changed')
        if ref in manifest['pilot_leaf_oracle_byte_reuse']:
            record=next(r.copy() for r in pilot['native_tests'] if r['resref']==ref)
            record['proof_reused']=True;record['reuse_basis']='same leaf, oracle and host reader bytes; no repeated pilot verification'
        else:
            result=subprocess.run([str(executable),'--pack',str(pack/'iee-assets/creature-sprites'),str(oracle)],
                                  cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
            log=output/(ref+'.log');log.write_text(result.stdout+result.stderr,encoding='utf-8')
            require(result.returncode==0,f'native verification failed: {ref}; {log}')
            record=json.loads(result.stdout.splitlines()[-1]);record['proof_reused']=False
            record['log']=log.relative_to(ROOT).as_posix();record['log_sha256']=file_sha(log)
        require(record['frames']==resource['native_frames'] and record['cycles']==resource['cycles'] and
                record['cycle_slots']==resource['cycle_slots'] and record['profile_id']==resource['profile_id'] and
                record['decoded_pixels']==resource['decoded_pixels']*27,'native coverage differs')
        record['native_unreferenced_frames']=resource['native_unreferenced_frames'];records.append(record)
        print(json.dumps(dict(native_verified=len(records),resources=len(manifest['resources']),resref=ref,
                              frames=record['frames'],proof_reused=record['proof_reused'])),flush=True)
    report=dict(schema='bg2-monster-q3m-complete-native-host-verification-v1',status='passed',records=records,
                host_executable_sha256=file_sha(executable),frames=sum(r['frames'] for r in records),
                decoded_pixels=sum(r['decoded_pixels'] for r in records),cycles=sum(r['cycles'] for r in records),
                cycle_slots=sum(r['cycle_slots'] for r in records),new_resources=sum(not r['proof_reused'] for r in records),
                reused_resources=sum(r['proof_reused'] for r in records),ingame_validated=False)
    write_json(output/'verification.json',report);print(json.dumps({k:v for k,v in report.items() if k!='records'}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pack',type=Path,required=True)
    p.add_argument('--executable',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();verify(a.pack.resolve(),a.executable.resolve(),a.output.resolve())
