import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import effect_storage as storage
import compose_effect_runtime_packs as composer
from build_shared_effect_storage import build

class StorageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.source=self.root/'source';self.source.mkdir()
  reg=struct.pack('<8sIIII',b'IEEEFX4\0',1,4,1,0)+b'FXTEST\0\0'+struct.pack('<II',3,1)+struct.pack('<IIIIII',1,1,1,1,1,1)+struct.pack('<IIII',3,0,1,2)
  (self.source/'EffectAnimations-X4.registry').write_bytes(reg)
  frames=[]
  for i,data in enumerate([b'A'*64,b'A'*64,b'B'*64]):
   name=f'EFX4-FXTEST-frame{i:03d}.rgba';(self.source/name).write_bytes(data)
   frames.append(dict(frame=i,asset=name,resref='FXTEST',resource_frame=i,bytes=64,sha256=hashlib.sha256(data).hexdigest().upper(),logical_size_x1=[1,1],physical_size_x4=[4,4]))
  self.m=dict(schema=composer.PACK_SCHEMA,status='completed',scale=4,registry='EffectAnimations-X4.registry',registry_magic='IEEEFX4',registry_version=1,registry_bytes=len(reg),registry_sha256=hashlib.sha256(reg).hexdigest().upper(),resource_count=1,resources=[dict(resref='FXTEST',frame_count=3,cycles=[dict(cycle=0,lookup_start=0,frame_indices=[0,1,2])])],frame_count=3,frames=frames)
  (self.source/'manifest.json').write_text(json.dumps(self.m),encoding='utf-8')
  self.out=self.root/'shared';build(self.source,self.out,self.root/'receipt.json')
  self.shared=json.loads((self.out/'manifest.json').read_text())
 def test_full_logical_identity_and_flat_materialization(self):
  self.assertEqual(storage.read_map(self.out,self.shared),[0,0,2]);self.assertFalse((self.out/self.m['frames'][1]['asset']).exists())
  pack=composer.validate_pack(self.out)
  with patch.object(composer,'REPO_ROOT',self.root):reg,m,copies=composer.compose([pack])
  composer.write_pack(self.root/'materialized',reg,m,copies)
  for f in self.m['frames']:self.assertEqual((self.root/'materialized'/f['asset']).read_bytes(),(self.source/f['asset']).read_bytes())
 def test_bound_registry_and_canonical_mapping(self):
  reg=(self.source/self.m['registry']).read_bytes()
  for ids,bound in [([1,0,2],reg),([0,9,2],reg),([0,0,2],reg[:-1]+b'X')]:
   raw=storage.encode(bound,ids);(self.out/storage.NAME).write_bytes(raw);self.shared['storage'].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest().upper())
   with self.assertRaises(ValueError):storage.read_map(self.out,self.shared)
 def test_logical_pixels_must_match_canonical(self):
  self.shared['frames'][1]['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'identity differs'):storage.read_map(self.out,self.shared)
 def test_manifest_order_is_registry_bound(self):
  self.shared['frames'][0],self.shared['frames'][1]=self.shared['frames'][1],self.shared['frames'][0]
  with self.assertRaisesRegex(ValueError,'traversal'):storage.read_map(self.out,self.shared)
 def test_missing_physical_and_unexpected_file_rejected(self):
  (self.out/'extra.rgba').write_bytes(b'?')
  with self.assertRaises(composer.PackError):composer.validate_pack(self.out)
  (self.out/'extra.rgba').unlink();(self.out/self.m['frames'][0]['asset']).unlink()
  with self.assertRaises(composer.PackError):composer.validate_pack(self.out)

if __name__=='__main__':unittest.main()
