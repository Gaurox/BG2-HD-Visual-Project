import unittest
from fractions import Fraction

from temporal import distinct_keys, phase_sources, cycle_modes, native_slot, frame_durations, phase_count


class NativeTimingTests(unittest.TestCase):
    def test_eight_fps_duration_and_slot_mapping(self):
        durations=frame_durations(9,8)
        self.assertEqual(len(durations),34)
        self.assertEqual(sum(durations),Fraction(9,8))
        self.assertEqual(durations[-1],Fraction(1,40))
        for slot in range(9):
            phase=(slot*30+7)//8
            self.assertEqual(native_slot(phase,8,9),slot)

    def test_projectile_modes_retained_without_guessing_owner_lifetime(self):
        a={'native_cycles':[{}]*3,'playback':'unknown','consumers':[
            {'owner_route':'projectile','consumer_key':'pro:test','relation':'travel-animation'}]}
        self.assertEqual(cycle_modes(a)[0],[{False,True}]*3)

    def test_nonconsecutive_repeated_native_poses_removed_within_cycle(self):
        keys=distinct_keys([0,1,2,1,0],['a','b','c'],[False]*3,False)
        self.assertEqual(keys,[0,1,2])
        self.assertEqual(Fraction(len(phase_sources(keys,10,False)),30),Fraction(5,15))

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
