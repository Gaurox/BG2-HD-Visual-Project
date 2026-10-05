"""Guarded ranking: duplicate colours, exact/near ties, special pixels, ROIs."""
import os,sys,unittest
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from unittest.mock import patch
import q3m_guarded_gpu_encode as accelerated
from palette_q3m_partners import Profile

class GuardedGPU(unittest.TestCase):
    def test_default_cpu_does_not_construct_GPU(self):
        profile=type('Stub',(),{'encode':lambda self,g,t:'cpu'})()
        with patch.dict(os.environ,{'Q3M_PALETTE_ENCODER':'cpu'}),patch.object(accelerated,'Encoder',side_effect=AssertionError('GPU constructed')):
            self.assertEqual(accelerated.encode(profile,None,None),'cpu')

    def test_unknown_mode_fails(self):
        with patch.dict(os.environ,{'Q3M_PALETTE_ENCODER':'unknown'}):
            with self.assertRaises(ValueError):accelerated.encode(None,None,None)

    def test_GPU_duplicate_colours_near_ties_and_ROI_match_CPU(self):
        import torch
        if not torch.cuda.is_available():self.skipTest('CUDA unavailable')
        rng=np.random.default_rng(73)
        p=rng.integers(0,256,(256,4),dtype=np.uint8);p[16:32]=p[32:48]
        fitting=np.tile(p[None,:,:3],(6,1,1));profile=Profile(0,p,fitting)
        guide=rng.integers(0,256,(17,19),dtype=np.uint8)
        targets=fitting[:,guide,:].astype(np.float64)/255
        targets[:,0]=0
        targets[:,1]=np.clip(targets[:,1]+1e-13,0,1)
        targets[:,2]=rng.random((6,19,3))
        expected=profile.encode(guide,targets)
        with patch.dict(os.environ,{'Q3M_PALETTE_ENCODER':accelerated.MODE}):
            actual=accelerated.encode(profile,guide,targets)
            self.assertTrue(all(np.array_equal(actual[k],expected[k]) for k in expected))
            roi=guide>=3;g=guide[roi][None,:];t=targets[:,roi,:][:,None,:,:]
            expected=profile.encode(g,t);actual=accelerated.encode(profile,g,t)
            self.assertTrue(all(np.array_equal(actual[k],expected[k]) for k in expected))
        self.assertGreater(accelerated.statistics()['collapsed_candidates'],0)

if __name__=='__main__':unittest.main()
