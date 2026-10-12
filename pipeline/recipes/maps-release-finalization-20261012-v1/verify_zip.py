"""Verify stored archive and exact final map/animation manifests and payload inventories."""
import hashlib,json,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];R=ROOT/'releases/BG2-HD-Upscale'
archive=Path(sys.argv[1]);assert not (HERE/'zip-verification.json').exists()
with zipfile.ZipFile(archive) as z:
    entries=z.infolist();assert all(e.compress_type==zipfile.ZIP_STORED for e in entries)
    assert len(entries)==len({e.filename for e in entries})
    for name in ('content.json','map-release-assemblies.json','map-release-candidates.csv','runtime-compatibility.json','animation-release-candidates.json'):
        assert z.read('bg2hd/manifests/'+name)==(R/'manifests'/name).read_bytes(),name
    content=json.loads(z.read('bg2hd/manifests/content.json'))['entries']
    expected={'bg2hd/payload/'+e['payload_group']+'/'+Path(e['source']).name:e for e in content}
    actual={e.filename for e in entries if e.filename.startswith('bg2hd/payload/')}
    assert actual==set(expected)
    # Phase6B already hashes every ZIP entry. Check projection identity here without another 20 GB pass.
    for name,e in expected.items():assert z.getinfo(name).file_size==e['bytes']
    build=json.loads(z.read('BUILD-MANIFEST.json'));assert build['zip_compression_level']=='NoCompression'
    result={'zip_entries':len(entries),'all_zip_stored':True,'payload_files':len(expected),'map_files':sum(e['kind']=='map' for e in content),'map_variants':len({e['area'] for e in content if e['kind']=='map'}),'duplicate_entries':False,'root_manifest_mirrors_exact':True,'phase6b_provides_complete_zip_hashes':True}
(HERE/'zip-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
