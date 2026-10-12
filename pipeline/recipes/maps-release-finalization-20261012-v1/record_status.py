"""Record final package evidence and preserve every unrelated acquired authority."""
import hashlib,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
R=ROOT/'releases/BG2-HD-Upscale';OUT=ROOT/'.tmp/maps-release-finalization-20261012-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import verify_map_release_candidates as verifier
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()
def rel(p):return p.relative_to(ROOT).as_posix()
def write(p,d):
    assert not p.exists(),str(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    for e in read(HERE/'baseline-authorities.json')['files']:assert sha(ROOT/e['path'])==e['sha256'],e['path']
    before=read(OUT/'before/manifests/content.json')['entries'];after=read(R/'manifests/content.json')['entries']
    assert [e for e in before if e['kind']!='map']==[e for e in after if e['kind']!='map'],'Non-map projection changed'
    old_ids={e['area']:e['component_id'] for e in before if e['kind']=='map'}
    assert old_ids=={e['area']:e['component_id'] for e in after if e['kind']=='map'},'Map component IDs changed'
    assert (R/'manifests/map-release-assemblies.json').read_bytes()==(HERE/'selection-manifest-v3.json').read_bytes(),'Accepted selection snapshot changed'
    assert (R/'manifests/map-release-assemblies.json').read_bytes()==(R/'bg2hd/manifests/map-release-assemblies.json').read_bytes(),'Map selection package mirror differs'
    verification=verifier.verify(ROOT,R/'manifests/map-release-candidates.csv',R/'manifests/map-release-assemblies.json',R/'manifests/content.json',metadata_only=True)
    package=read(HERE/'package-finalization.json');archive=Path(package['archive'])
    assert archive.is_file() and archive.stat().st_size==package['archive_bytes'] and sha(archive)==package['archive_sha256']
    counts=Counter(e['kind'] for e in after);maps=[e for e in after if e['kind']=='map']
    variants=read(R/'manifests/map-release-assemblies.json')['variants']
    gates=[]
    for name in ('phase2','stage','phase4','build-uncompressed','phase6b','phase5a'):
        p=HERE/(name+'-receipt.json');d=read(p);assert d['state']=='passed'
        assert sha(HERE/(name+'.log'))==d['log_sha256']
        assert sha(Path(d['script']))==d['script_sha256']
        gates.append({'name':name,'receipt':rel(p),'sha256':sha(p),'state':'passed'})
    release=read(R/'manifests/release.json');assert release['release_status']=='blocked' and release['payload_status']=='buildable'
    result={'schema':'bg2-maps-release-status-v1','recorded_utc':datetime.now(timezone.utc).isoformat(),'version':release['version'],'local_release_status':'completed','public_release_status':'blocked','publication_blockers':release['blocking_conditions'],'new_ingame_qa':False,'game_mutation':False,'selection_manifest':rel(HERE/'selection-manifest-v3.json'),'selection_manifest_sha256':sha(HERE/'selection-manifest-v3.json'),'statistics':{'validated_catalog_variants':400,'packaged_map_variants':399,'shared_tileset_aliases':{'OH6460':'OH8100'},'final_liquid_weds':63,'updated_map_assemblies':sum(v['frozen_assembly'] for v in variants),'runtime_entries':188,'map_files':len(maps),'map_bytes':sum(e['bytes'] for e in maps),'all_payload_files':len(after),'content_kind_counts':dict(counts),'components':len(read(R/'manifests/components.json')['components']),'immutable_qa_proofs':verification['qa_evidence']},'validation':{'map_projection':verification,'unit_tests':{'passed':33,'log':rel(HERE/'unit-tests-final.log'),'log_sha256':sha(HERE/'unit-tests-final.log')},'gates':gates,'zip':read(HERE/'zip-verification.json')},'preservation':{'authorities':read(HERE/'baseline-authorities.json')['files'],'non_map_content_entries_exact':True,'map_component_ids_exact':True,'ar0516_animation_wed_exact':True,'previous_staging':read(HERE/'previous-staging.json')},'package':package,'limits':['Local alpha only; clean-game Steam/EEex/renderer/save/uninstall lifecycle and public provenance/contact remain pending.','No comparison of two independent final builds.','Git contains selection/proof metadata; frozen payloads, staging, retained renderer inputs and ZIP also require local physical conservation.','Other optional per-map weather/pause/day-night observations remain unattested; existing acquired treatment QA is preserved.']}
    write(ROOT/'docs/validation/maps-release-status-20261012-v1.json',result)
    write(HERE/'final-verification.json',{'status_document':'docs/validation/maps-release-status-20261012-v1.json','sha256':sha(ROOT/'docs/validation/maps-release-status-20261012-v1.json'),'all_original_authorities_preserved':True,'non_map_content_entries_exact':True})
    print(json.dumps({'status':'completed','statistics':result['statistics'],'archive':package['archive'],'archive_bytes':package['archive_bytes']},indent=2))

if __name__=='__main__':main()
