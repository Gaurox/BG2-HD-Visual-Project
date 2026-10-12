"""One-use freeze of existing QA; original assets and installed game remain unchanged."""
import csv, hashlib, json, shutil, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
RELEASE=ROOT/'releases/BG2-HD-Upscale'
SCRATCH=ROOT/'.tmp/maps-release-finalization-20261012-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()
def rel(p):return p.relative_to(ROOT).as_posix()
def write(p,d):
    assert not p.exists(),str(p)
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')

def main():
    assert not (HERE/'selection-manifest.json').exists(),'Immutable selection already exists'
    plan=read(SCRATCH/'complete-plan.json');assert not plan['missing']
    for directory in ('manifests','schemas','tools','tests','docs'):
        target=SCRATCH/'before'/directory
        assert not target.exists(),str(target)
        shutil.copytree(RELEASE/directory,target)
    baseline=read(RELEASE/'manifests/content.json')
    write(HERE/'baseline-authorities.json',{'files':[{'path':rel(p),'sha256':sha(p)} for p in [ROOT/'areas.csv',ROOT/'pipeline/water/ingame-map-tracking-v1.json',ROOT/'pipeline/water/route2-registry-current.json',RELEASE/'manifests/animation-release-candidates.json',RELEASE/'manifests/sprite-release-candidates.json',RELEASE/'manifests/effect-release-candidates.json',RELEASE/'manifests/overlay-sources.json',RELEASE/'manifests/renderer-bundle.json',RELEASE/'bg2hd/renderer/InfinityEngine-Enhancer.dll']]})
    rows={r['area_id']:r for r in csv.DictReader((ROOT/'areas.csv').open(encoding='utf-8-sig',newline=''))}
    evidence={e['id']:e for e in read(ROOT/'pipeline/water/release-tracking-v1.json')['evidence']}
    variants=[];candidates=[];copied=0;copied_bytes=0
    for v in plan['variants']:
        area=v['area'];base=area.removesuffix('N');row=rows[base];night=area.endswith('N')
        original_tis=next(e for e in baseline['entries'] if e['kind']=='map' and e['area']==area and Path(e['source']).name.upper()==area+'.TIS')
        frozen=bool(v['changed'])
        source_path=f'maps/{base}/runs/release-maps-20261012-v1/{area}/05_build' if frozen else v['catalog_source_path']
        target=ROOT/source_path
        if frozen:
            assert not target.exists(),str(target)
            target.mkdir(parents=True)
        files=[]
        for f in v['files']:
            original=ROOT/f['source'];assert sha(original)==f['sha256'] and original.stat().st_size==f['bytes']
            if frozen:
                destination=target/f['name'];shutil.copyfile(original,destination)
                assert sha(destination)==f['sha256']
                copied+=1;copied_bytes+=f['bytes']
            else:destination=original
            files.append({**f,'original_source':f['source'],'source':rel(destination)})
        qa=[]
        for id in v['qa_evidence_ids']:
            e=evidence[id];p=ROOT/e['path'];assert p.is_file(),str(p)
            qa.append({'id':id,'path':e['path'],'sha256':sha(p)})
        for path in (['maps/qa-retour-ingame-20261011-v1.json'] if area in ['AR3003','AR5200','AR2101','AR0604','AR0011','AR0046','AR0046N','AR0204','AR0300'] else []):
            qa.append({'id':Path(path).stem,'path':path,'sha256':sha(ROOT/path)})
        include_wed=any(f['name'].upper().endswith('.WED') and Path(f['source']).parent.as_posix()==source_path for f in files)
        model='SeedVR2-7B-final-water-30fps' if v['water'] else original_tis['model']
        variant={'area':area,'component_id':v['component_id'],'source_path':source_path,'catalog_source_path':v['catalog_source_path'],'include_wed':include_wed,'model':model,'qa_state':'acquired','new_ingame_qa':False,'byte_identity_with_installed_witness':True,'water':v['water'],'frozen_assembly':frozen,'catalog':{'area_id':base,'variant':'night' if night else 'day-or-unique','status':row['status_nuit'] if night else row['status'],'runs':row['runs_nuit'] if night else row['runs'],'qa_notes':row['notes']},'qa_evidence':qa,'files':files,'changes_from_alpha6_animations':v['changed']}
        variants.append(variant)
        candidates.append({'area':area,'component_id':v['component_id'],'source_path':source_path,'include_wed':str(include_wed).lower(),'model':model,'catalog_source_path':v['catalog_source_path']})
    manifest={'schema_version':1,'generated_by':rel(Path(__file__)),'state':'approved-for-local-release','qa_origin':'Existing acquired map QA; exact retained-source bytes matched to installed witness; no new ingame decision inferred.','game_mutation':False,'new_ingame_qa':False,'runtime':plan['runtime'],'catalog':{'path':'areas.csv','sha256_at_selection':sha(ROOT/'areas.csv'),'validated_variants':400,'packaged_variants':399,'shared_tilesets':{'OH6460':'OH8100'}},'variants':variants}
    write(HERE/'selection-manifest.json',manifest)
    shutil.copyfile(HERE/'selection-manifest.json',RELEASE/'manifests/map-release-assemblies.json')
    with (RELEASE/'manifests/map-release-candidates.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(candidates[0]));w.writeheader();w.writerows(sorted(candidates,key=lambda r:(r['component_id'],r['area'])))
    runtime=read(RELEASE/'manifests/runtime-compatibility.json')
    runtime['owned_ini_keys']['core-steam']['Shaders'].update(plan['runtime']['owned_ini_keys'])
    (RELEASE/'manifests/runtime-compatibility.json').write_text(json.dumps(runtime,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    release=read(RELEASE/'manifests/release.json')
    if 'manifests/map-release-assemblies.json' not in release['manifest_files']:release['manifest_files'].append('manifests/map-release-assemblies.json')
    release['content_scope']['maps']='399 variantes x4 : selections explicites dans map-release-candidates.csv, inventaires et QA acquises dans map-release-assemblies.json ; 63 assemblages eau/contours/WED/overlays jour-pluie finaux et AR3003 actualises a octets constants. OH6460 utilise le tileset partage du composant OH8100 sans duplication.'
    release['content_scope']['overlays']='overlay-sources.json gouverne les overlays partages historiques ; les 188 identites liquides locales du registre runtime courant sont groupees avec leur map (TIS/PVRZ jour-pluie + WED), inventoriees dans map-release-assemblies.json.'
    (RELEASE/'manifests/release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write(HERE/'freeze-receipt.json',{'variants':399,'frozen_variants':sum(v['frozen_assembly'] for v in variants),'frozen_files':copied,'frozen_bytes':copied_bytes,'selection_manifest_sha256':sha(HERE/'selection-manifest.json'),'ar3003_historical_binding':'backups/maps/AR3003-20260906T213541736829Z-783bd7c5/install-backup.json','animation_owned_wed_preserved':'AR0516.WED','game_mutation':False,'new_ingame_qa':False})
    print(json.dumps(read(HERE/'freeze-receipt.json'),indent=2))

if __name__=='__main__':main()
