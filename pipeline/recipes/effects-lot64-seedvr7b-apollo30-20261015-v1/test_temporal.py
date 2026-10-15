import unittest
from fractions import Fraction

from temporal import distinct_keys, phase_sources, cycle_modes


class NativeTimingTests(unittest.TestCase):
    def test_doubled_poses_keep_original_duration_and_endpoints(self):
        keys=distinct_keys([0,0,1,1,2,2],['a','b','c'],[False]*3,False)
        phases=phase_sources(keys,12,False)
        self.assertEqual(keys,[0,1,2])
        self.assertEqual(phases[0],(0,1,0.0))
        self.assertEqual(phases[-1],(2,2,0.0))
        self.assertEqual(Fraction(len(phases),30),Fraction(6,15))

    def test_loop_does_not_emit_closing_endpoint_twice(self):
        keys=distinct_keys([0,0,1,1,0],['a','b'],[False]*2,True)
        phases=phase_sources(keys,10,True)
        self.assertEqual(keys,[0,1])
        self.assertEqual(phases[0],(0,1,0.0))
        self.assertEqual(phases[-1][0:2],(1,0))
        self.assertAlmostEqual(phases[-1][2],0.8)
        self.assertEqual(Fraction(len(phases),30),Fraction(5,15))

    def test_blank_padding_removed_but_hidden_control_not_animated(self):
        self.assertEqual(distinct_keys([0,0,1,2,0],['blank','a','b'],[True,False,False],False),[1,2])
        self.assertEqual(distinct_keys([0],['blank'],[True],False),[0])
        self.assertEqual(phase_sources([0],2,False),[(0,0,0.0)]*2)

    def test_intro_and_release_are_not_closed_like_sustain(self):
        a={'native_cycles':[{}, {}, {}],'playback':'loop','consumers':[
            {'owner_route':'vvc','consumer_key':'vvc:test','loop':'1','cycles':'1;2;3','orientations':'1'}]}
        self.assertEqual(cycle_modes(a)[0],[{False},{True},{False}])

    def test_directional_loop_and_conflicting_consumers_retained(self):
        a={'native_cycles':[{}]*5,'playback':'loop','consumers':[
            {'owner_route':'vvc','consumer_key':'vvc:dir','loop':'1','cycles':'0;0;0','orientations':'16'}]}
        self.assertEqual(cycle_modes(a)[0],[{True}]*5)
        a['consumers'].append({'owner_route':'vvc','consumer_key':'vvc:once','loop':'0','cycles':'0;0;0','orientations':'1'})
        self.assertEqual(cycle_modes(a)[0][0],{False,True})


if __name__=='__main__':unittest.main()
