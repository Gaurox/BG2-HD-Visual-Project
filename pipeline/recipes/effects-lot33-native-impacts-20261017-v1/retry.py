"""Retry only failed interpolation assets in new runs, with transient Apollo padding."""
import argparse
import copy
from temporal_padded import ROOT,BATCH,load,save,produce


def main():
    p=argparse.ArgumentParser();p.add_argument('--resref',action='append',required=True);args=p.parse_args()
    path=BATCH/'batch.json';batch=load(path)
    if not (BATCH/'initial-plan.json').exists():save(BATCH/'initial-plan.json',batch)
    for name in args.resref:
        a=next(a for a in batch['assets'] if a['resref']==name)
        assert not (BATCH/'checks'/f'{name}.json').exists()
        old=a['interpolation_run'];a['interpolation_run']=f'{name.lower()}-apollo30-native-padded-20261017-v2'
        a['pack']=f'effects/ressources/{name}/packs/{name.lower()}-7b-x4-apollo30-native-padded-20261017-v2'
        a['failed_interpolation_run_preserved']=old
        assert not (ROOT/'effects/ressources'/name/'runs'/a['interpolation_run']).exists()
        save(path,batch)
        print('Retry padded',name,flush=True);produce(a)


if __name__=='__main__':main()
