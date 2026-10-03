import sys,tempfile,unittest,struct
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sprite_spline_coverage import coverage,apply
from palette_q3m_partners import Profile
import palette_partner_registry as registry

class SplineCoverageTests(unittest.TestCase):
    def profile(self):
        rgb=np.random.default_rng(9).integers(0,256,(6,256,3),dtype=np.uint8)
        return Profile(0,np.column_stack((rgb[0,:,::-1],np.zeros(256,np.uint8))),rgb)
    def resource(self,profile):
        i=np.full((8,8),3,np.uint8);i[0,:3]=[0,1,2];f=np.zeros_like(i)
        a=np.full_like(i,255);a[3:5,3:5]=[0,64]
        frame=dict(geometry=(4,4,2,3,0),I=i,F=f,guide=i.copy(),dep=profile.dependencies(i,f),
                   representatives=np.full(256,0xffff,np.uint16),A=a)
        return dict(resref='MAKHG1',source_sha256='11'*32,frames=[frame],cycles=[[0]])
    def test_special_and_thin_masks_remain_identity(self):
        for i in (np.array([[0,1,2]],np.uint8),np.pad(np.full((1,30),3,np.uint8),5)):
            a,_=coverage(i);self.assertTrue(np.all(a==255))
    def test_border_only_holes_and_specials_preserved(self):
        i=np.zeros((48,48),np.uint8);i[5:43,5:43]=3;i[18:28,18:28]=0
        for y in range(5,18):i[y,5:5+(18-y)//2]=0
        i[42:47,24]=3;i[44:47,40:43]=1
        a,report=coverage(i)
        self.assertGreater(report['changed_pixels'],0)
        self.assertTrue(np.all(a[i<3]==255));self.assertTrue(np.all(a[44:47,24]==255))
        self.assertEqual(int(a[14,24]),255)
    def test_opacity_math_keeps_visible_RGB_and_zeroes_clear_pixels(self):
        rgb=np.array([[[17,35,61,255],[9,8,7,127],[6,5,4,0]]],np.uint8)
        a=np.array([[128,255,255]],np.uint8);out=apply(rgb,a)
        np.testing.assert_array_equal(out[0,0],[17,35,61,128]);np.testing.assert_array_equal(out[0,1],rgb[0,1])
        np.testing.assert_array_equal(out[0,2],np.zeros(4,np.uint8))
    def test_v8_raw_and_compressed_roundtrip(self):
        p=self.profile();r=self.resource(p)
        with tempfile.TemporaryDirectory() as tmp:
            for zipped in (False,True):
                path=Path(tmp)/str(zipped);registry.write(path,[r],p,version=8,compress=zipped)
                checked=registry.inspect(path,include_frames=True)['resources'][0]['frames'][0]
                for plane in ('I','F','A'):np.testing.assert_array_equal(checked[plane],r['frames'][0][plane])
    def test_v7_rejects_coverage_and_v8_rejects_special_attenuation(self):
        p=self.profile();r=self.resource(p)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):registry.write(Path(tmp)/'v7',[r],p)
            r['frames'][0]['A'][0,0]=0
            with self.assertRaises(ValueError):registry.write(Path(tmp)/'special',[r],p,version=8)
    def test_corrupt_coverage_length_and_special_payload_rejected(self):
        p=self.profile();r=self.resource(p)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'valid';registry.write(path,[r],p,version=8,compress=False);raw=path.read_bytes()
            header=32+48+2052+568;payload=header+8+64
            for name,pos,value in [('length',header,63),('special',payload,0)]:
                corrupt=bytearray(raw)
                if name=='length':struct.pack_into('<I',corrupt,pos,value)
                else:corrupt[pos]=value
                bad=Path(tmp)/name;bad.write_bytes(corrupt)
                with self.assertRaises((ValueError,RuntimeError)):registry.inspect(bad)

if __name__=='__main__':unittest.main()
