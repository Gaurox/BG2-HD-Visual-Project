"""General water RGB seams: all interface kinds covered, native banks excluded."""
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from repair_water_rgb_edges import water_art_edge_masks


class AllWaterEdgeTests(unittest.TestCase):
    def fixture(self):
        cells = [{'x':x,'y':0,'primary':[x],'secondary':65535 if x<2 else x+4,
                  'count':1,'flags':1<<(1+x%4)} for x in range(4)]
        parsed = {'layers':[{'width':4,'height':1}],'cells':cells}
        def stock(tile):
            rgba = np.zeros((64,64,4),np.uint8)
            rgba[:,:,3] = 0 if tile in (2,3) else 255
            return rgba
        return parsed,stock

    def test_covers_every_interface_kind_in_both_directions(self):
        parsed,stock = self.fixture()
        interfaces = water_art_edge_masks(parsed,[1,2,3,4],stock,{(0,0):0,(1,0):1})
        self.assertEqual(len(interfaces),6)
        self.assertEqual({i['kind'] for i in interfaces},{'full-full','full-pair','pair-full','pair-pair'})
        self.assertEqual({i['tile'] for i in interfaces},{0,1,6,7})

    def test_bank_and_bridge_protection_includes_compression_footprint(self):
        parsed,stock = self.fixture()
        def bank_stock(tile):
            image = stock(tile)
            if tile == 2: image[:10,:,3] = 255
            return image
        interfaces = water_art_edge_masks(parsed,[1,2,3,4],bank_stock,{(0,0):0,(1,0):1})
        edge = next(i['mask'] for i in interfaces if i['tile']==6 and i['side']=='left')
        self.assertFalse(edge[:44].any())
        self.assertTrue(edge[44:252,:4].all())
        self.assertFalse(edge[:,7:].any())


if __name__=='__main__': unittest.main()
