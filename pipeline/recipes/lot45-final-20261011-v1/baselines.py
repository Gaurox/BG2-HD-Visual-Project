from common import *
import merge_area_pack_resources as merge

def main():
    BATCH.mkdir(parents=True,exist_ok=True)
    lock=v.load_json(ROOT/'animations/index/area-pack-lock.json');records={}
    chosen=v.validate_v2_pack(AMWRP)[1][0]
    for area in sorted({a for areas in AREAS.values() for a in areas}):
        live=GAME/'iee-assets/areas'/area;before=payload(live)
        record=dict(present=live.exists(),payload=before,preserved_pack=None)
        if live.exists():
            build=lock['areas'][area]['build'];inputs=build.get('merged_from') or [build['leaf']]
            out=PACKS/(TAG+'-baseline-'+area)
            merge.merge([str(ROOT/p) for p in inputs],area,out,False)
            preserved=out/area
            assert payload(preserved)==before,area+': active pack differs from lock source'
            record['preserved_pack']=rel(preserved)
            rs=v.validate_v2_pack(preserved)[1]
            old=[r for r in rs if r['resref']=='AMWRPGT1']
            if old:
                identical= len(old)==1 and v.resource_binary_v2(old[0],3)==v.resource_binary_v2(chosen,3) and [f['sha256'] for f in old[0]['frames']]==[f['sha256'] for f in chosen['frames']]
                record['AMWRPGT1_same_as_selected']=identical
                print(area,'AMWRPGT1 candidate identical:',identical,flush=True)
        records[area]=record
        print('BASELINE',area,flush=True)
    v.write_json(BATCH/'baselines-source.json',records)

if __name__=='__main__':main()
