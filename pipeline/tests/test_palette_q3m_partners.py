import sys
from pathlib import Path
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from palette_q3m_partners import Profile
import palette_partner_registry as registry


class PartnersTests(unittest.TestCase):
    def profile(self,kind=0):
        rgb = np.random.default_rng(3).integers(0,256,(6,256,3),dtype=np.uint8)
        source = np.column_stack((rgb[0,:,::-1],np.zeros(256,np.uint8)))
        return Profile(kind,source,rgb)

    def test_all_partners_scalar_bytes_and_dependencies(self):
        profile = self.profile(); i = np.repeat(np.arange(3,256,dtype=np.uint8),32)[None]
        code = np.tile(np.arange(32,dtype=np.uint8),253)[None]; code[code%8==0] = 0
        rgba = np.column_stack((profile.fitting[0],np.full(256,255,np.uint8)))
        actual = profile.decode(i,code,rgba)
        for n in range(i.size):
            a,c = int(i[0,n]),int(code[0,n]); b = int(profile.table[a,c>>3]); f = c&7
            self.assertEqual(actual[0,n].tolist(),[((8-f)*int(rgba[a,k])+f*int(rgba[b,k])+4)//8 for k in range(3)]+[255])
        deps = profile.dependencies(i,code); profile.validate(i,code,dep=deps)
        with self.assertRaises(ValueError): profile.validate(i,code,dep=deps^1)
        rgba[profile.table[3,1],3] = 127
        with self.assertRaises(ValueError): profile.decode(np.array([[3]],np.uint8),np.array([[9]],np.uint8),rgba)

    def test_classes_specials_and_objective(self):
        for kind in (0,1):
            profile = self.profile(kind); g = np.array([[0,1,2,3,4,15,88,95,255]],np.uint8)
            targets = np.stack([profile.decode(g,np.zeros_like(g),p)/255 for p in profile.fitting])
            result = profile.encode(g,targets); profile.validate(result['I'],result['F'],g,result['dep'])
            for k,palette in enumerate(profile.fitting):
                self.assertTrue(np.array_equal(profile.decode(result['I'],result['F'],palette),np.rint(targets[k]*255).astype(np.uint8)))
            table = profile.table.copy();table[4,1]=1
            with self.assertRaises(ValueError): Profile(kind,profile.source,profile.fitting,table)

    def test_exhaustive_objective_against_direct_distances(self):
        from reboutcx_quantize import srgb_u8_to_oklab
        profile = self.profile(); g = np.array([[3,45,255]],np.uint8)
        targets = np.random.default_rng(8).random((6,1,3,3)).astype(np.float32)
        result = profile.encode(g,targets)
        ci,cc,_,_ = profile.candidates(3)
        chosen = [(int(result['I'][0,n]),int(result['F'][0,n])) for n in range(3)]
        cost = np.zeros((3,len(ci)),np.float64)
        for k,palette in enumerate(profile.fitting):
            f = (cc&7)[:,None].astype(np.uint16)
            candidate_rgb = ((palette[ci].astype(np.uint16)*(8-f)+palette[profile.table[ci,cc>>3]].astype(np.uint16)*f+4)>>3).astype(np.uint8)
            difference = srgb_u8_to_oklab(candidate_rgb)[None]-srgb_u8_to_oklab(targets[k,0].astype(np.float64)*255)[:,None]
            cost += np.einsum('pnc,pnc->pn',difference,difference)
        for n,pair in enumerate(chosen):
            position = np.flatnonzero((ci == pair[0])&(cc == pair[1]))[0]
            self.assertLessEqual(cost[n,position],cost[n].min()+1e-12)

    def test_encoding_identity_excludes_per_resource_palette_metadata(self):
        profile = self.profile(1); source = profile.source.copy(); source[255] ^= 255
        other = Profile(1,source,profile.fitting)
        self.assertEqual(profile.identity,other.identity)
        self.assertNotEqual(profile.metadata(),other.metadata())
        fits = profile.fitting.copy(); fits[5,255,0] ^= 1
        self.assertNotEqual(profile.identity,Profile(1,source,fits).identity)

    def test_dragon_parts_are_not_direction_variants(self):
        import json
        from q3m_family_witnesses import SELECTION,validate_selection
        selection = json.loads(SELECTION.read_text(encoding='utf-8'))
        self.assertEqual(len(validate_selection(selection)),15)
        dragon = next(w for w in selection['witnesses'] if w['family']=='multi_new')
        dragon['refs'] = ['MDR2110'+str(n) for n in range(9)]
        dragon['multipart_groups'] = [dragon['refs']]
        with self.assertRaises(ValueError): validate_selection(selection)

    def test_registry_roundtrip_and_malformed_data(self):
        profile = self.profile(); g = np.array([[0,1],[3,4]],np.uint8); code = np.array([[0,0],[9,31]],np.uint8)
        resource = dict(resref='TEST',source_sha256='00'*32,cycles=[[0,0,65535]],frames=[dict(geometry=(1,1,-3,5,0),representatives=np.full(256,65535,np.uint16),guide=g,I=g,F=code,dep=profile.dependencies(g,code))])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.registry';registry.write(path,[resource],profile,compress=False)
            info = registry.inspect(path,include_frames=True)
            self.assertEqual(info['resources'][0]['cycles'],[[0,0,65535]])
            self.assertTrue(np.array_equal(info['resources'][0]['frames'][0]['F'],code))
            raw = bytearray(path.read_bytes());raw[-1:] = b'\xff';path.write_bytes(raw)
            with self.assertRaises(ValueError): registry.inspect(path)


if __name__ == '__main__': unittest.main()
