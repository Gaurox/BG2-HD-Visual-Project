import sys,unittest
from pathlib import Path
import numpy as np
from scipy import ndimage
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sprite_alpha_coverage import coverage,apply

class AlphaCoverageTests(unittest.TestCase):
    def test_steps_holes_and_component_topology_preserved(self):
        i=np.zeros((52,52),np.uint8);i[5:44,5:44]=3;i[18:28,18:28]=0
        for y in range(5,18):i[y,5:5+(18-y)//2]=0
        i[47,47]=3;i[43:49,24]=3;i[46:49,40:43]=1
        a,r=coverage(i)
        self.assertGreater(r['changed_pixels'],0);self.assertEqual(r['cleared_pixels'],0)
        rgba=np.zeros((*i.shape,4),np.uint8);rgba[i>=2]=[60,80,90,255];rgba[i==1]=[0,0,0,127]
        out=apply(rgba,a);before=rgba[...,3]>0;after=out[...,3]>0
        np.testing.assert_array_equal(before,after)
        for connectivity in (ndimage.generate_binary_structure(2,1),np.ones((3,3))):
            np.testing.assert_array_equal(ndimage.label(before,connectivity)[0],ndimage.label(after,connectivity)[0])
        np.testing.assert_array_equal(out[before,:3],rgba[before,:3])
        self.assertEqual(a[12,28],255);self.assertEqual(a[47,47],255)
        self.assertTrue(np.all(a[i<3]==255));self.assertGreaterEqual(a.min(),176)
    def test_no_feather_outside_source_and_no_shadow_change(self):
        i=np.zeros((24,24),np.uint8);i[6:18,6:18]=3;i[20:22,8:16]=1;i[6,12]=2
        a,_=coverage(i);self.assertTrue(np.all(a[i<3]==255));self.assertLess(a[6,11],255)
        rgba=np.zeros((24,24,4),np.uint8);rgba[i>=2]=[255,64,32,255];rgba[i==1]=[0,0,0,127]
        out=apply(rgba,a);np.testing.assert_array_equal(out[i<3],rgba[i<3])
    def test_opaque_reserved_colour_contributes_to_gaussian_context(self):
        i=np.zeros((24,24),np.uint8);i[3:21,3:21]=3;i[12,12]=2
        a,_=coverage(i);self.assertEqual(a[12,11],255);self.assertEqual(a[12,12],255)
    def test_thin_features_and_special_only_unchanged(self):
        for i in (np.array([[0,1,2]],np.uint8),np.pad(np.full((1,30),3,np.uint8),5)):
            a,_=coverage(i);self.assertTrue(np.all(a==255))
    def test_rounded_alpha_math_preserves_rgb(self):
        rgba=np.array([[[17,35,61,255],[9,8,7,127],[0,0,0,0]]],np.uint8)
        a=np.array([[176,255,255]],np.uint8)
        np.testing.assert_array_equal(apply(rgba,a),[[[17,35,61,176],[9,8,7,127],[0,0,0,0]]])
    def test_invalid_recipe_rejected(self):
        i=np.zeros((4,4),np.uint8)
        for args in (dict(sigma=0),dict(sigma=float('nan')),dict(minimum=0),dict(strength=2)):
            with self.assertRaises(ValueError):coverage(i,**args)

if __name__=='__main__':unittest.main()
