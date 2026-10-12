import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC=importlib.util.spec_from_file_location('maps_verifier',Path(__file__).resolve().parents[1]/'scripts/verify_map_release_candidates.py')
verifier=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(verifier)

class MapReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.release=self.root/'releases/BG2-HD-Upscale';self.pack='maps/AR0001/runs/final/05_build'
        def write(path,data):
            p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(data if isinstance(data,bytes) else (json.dumps(data)+'\n').encode())
            return p
        self.write=write
        self.files=[]
        for name in ('AR0001.TIS','AR0001.WED','YTEST.TIS','YTEST00.PVRZ','YTESTR.TIS','YTESTR00.PVRZ'):
            p=write(self.pack+'/'+name,name.encode());self.files.append({'name':name,'source':self.pack+'/'+name,'bytes':p.stat().st_size,'sha256':verifier.digest(p)})
        fs={f['name']:f for f in self.files};qa=write('pipeline/water/manifests/test-qa.json',{'result':'validated'})
        self.variant={'area':'AR0001','component_id':1000,'source_path':self.pack,'catalog_source_path':self.pack,'model':'test','include_wed':True,'qa_state':'acquired','new_ingame_qa':False,'water':True,'qa_evidence':[{'id':'test-qa','path':'pipeline/water/manifests/test-qa.json','sha256':verifier.digest(qa)}],'files':self.files}
        registry={'entries':[{'wed':{'resref':'AR0001','sha256':fs['AR0001.WED']['sha256']},'base_tis':{'resref':'AR0001','sha256':fs['AR0001.TIS']['sha256']},'overlay':{'tis_resref':alias,'tis_sha256':fs[alias+'.TIS']['sha256'],'pages':[{'resref':alias+'00','sha256':fs[alias+'00.PVRZ']['sha256']}]}} for alias in ('YTEST','YTESTR')]}
        reg=write('pipeline/water/requests/test/registry.json',registry)
        dll=write('releases/BG2-HD-Upscale/bg2hd/renderer/InfinityEngine-Enhancer.dll',b'DLL')
        keys={'EnableWaterOverlayRoute2':'true','WaterOverlayStrength':'1.00'}
        write('releases/BG2-HD-Upscale/manifests/runtime-compatibility.json',{'owned_ini_keys':{'core-steam':{'Shaders':keys}}})
        write('releases/BG2-HD-Upscale/manifests/animation-release-candidates.json',{'candidates':[]})
        write('pipeline/water/ingame-map-tracking-v1.json',{'maps':[{'wed':'AR0001','qa_state':'validated-ingame','qa_evidence_ids':['test-qa']}]})
        self.manifest={'schema_version':1,'state':'approved-for-local-release','catalog':{'shared_tilesets':{}},'variants':[self.variant],'runtime':{'registry':'pipeline/water/requests/test/registry.json','registry_sha256':verifier.digest(reg),'dll_sha256':verifier.digest(dll),'entries':2,'owned_ini_keys':keys}}
        self.candidates=self.release/'manifests/map-release-candidates.csv'
        with self.candidates.open('w',newline='') as f:
            row={'area':'AR0001','component_id':1000,'source_path':self.pack,'catalog_source_path':self.pack,'model':'test','include_wed':'true'};w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
        with (self.root/'areas.csv').open('w',newline='') as f:
            row={'area_id':'AR0001','status':'validated-installed','status_nuit':'','runs':'final','runs_nuit':''};w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
        self.assemblies=self.release/'manifests/map-release-assemblies.json'

    def tearDown(self):self.temp.cleanup()
    def verify(self):
        self.assemblies.write_text(json.dumps(self.manifest))
        return verifier.verify(self.root,self.candidates,self.assemblies)
    def test_complete_acquired_stack_is_valid(self):self.assertTrue(self.verify()['valid'])
    def test_missing_rain_overlay_is_rejected(self):
        self.variant['files']=[f for f in self.files if f['name']!='YTESTR.TIS']
        (self.root/self.pack/'YTESTR.TIS').unlink()
        with self.assertRaisesRegex(ValueError,'Runtime guard/overlay'):self.verify()
    def test_changed_payload_is_rejected(self):
        (self.root/self.pack/'YTEST.TIS').write_bytes(b'changedxx')
        with self.assertRaisesRegex(ValueError,'differs'):self.verify()
    def test_unaccepted_extra_map_is_rejected(self):
        self.manifest['variants'].append(dict(self.variant,area='AR0002'))
        with self.assertRaisesRegex(ValueError,'coverage differs'):self.verify()
    def test_missing_owned_runtime_setting_is_rejected(self):
        self.write('releases/BG2-HD-Upscale/manifests/runtime-compatibility.json',{'owned_ini_keys':{'core-steam':{'Shaders':{}}}})
        with self.assertRaisesRegex(ValueError,'activation/strength'):self.verify()
    def test_path_escape_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Outside workspace'):verifier.safe_path(self.root,'../outside')
    def test_changed_qa_is_rejected(self):
        self.write('pipeline/water/manifests/test-qa.json',{'result':'rejected'})
        with self.assertRaisesRegex(ValueError,'QA evidence differs'):self.verify()
    def test_explicit_git_lf_and_local_crlf_proof_hashes_are_supported(self):
        p=self.root/'pipeline/water/manifests/test-qa.json'
        original=p.read_bytes();crlf=original.replace(b'\n',b'\r\n')
        evidence=self.variant['qa_evidence'][0]
        evidence['sha256']=hashlib.sha256(crlf).hexdigest().upper()
        evidence['git_blob_sha256']=hashlib.sha256(original).hexdigest().upper()
        self.assertTrue(self.verify()['valid'])
        p.write_bytes(crlf)
        self.assertTrue(self.verify()['valid'])

if __name__=='__main__':unittest.main()
