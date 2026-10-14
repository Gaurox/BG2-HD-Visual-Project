import copy
import unittest
from analyze import analyze_capture,parse_log

TIMELINE={'target_fps':[30,1],'timeline_frame_indices':list(range(118))}


def capture():
    rows=[dict(epoch=i,qpc=1000000+round(i*1000000/60),active=1,owner=True,draws=1,
        swapOk=True,hd=True,phase=i//2,backing=i//2,conflict=False) for i in range(236)]
    return dict(header=dict(id=1,frequency=1000000,rows=len(rows),overflow=False,droppedOwners=0),rows=rows,end=True)


class PresentationAnalysisTests(unittest.TestCase):
    def test_60hz_repeated_presentations_are_normal_30fps(self):
        result=analyze_capture(capture(),TIMELINE)
        self.assertTrue(result['cadence_30_confirmed_for_observed_segment'])
        self.assertTrue(result['all_phases_seen'])
        self.assertEqual(result['normal_same_phase_presentations'],118)
        self.assertAlmostEqual(result['observed_unique_fps'],30,places=3)

    def test_15fps_holds_are_not_reported_as_30fps(self):
        c=capture()
        template=c['rows'][0]
        c['rows']=[dict(template,epoch=i,qpc=1000000+round(i*1000000/60),phase=i//4,backing=i//4) for i in range(472)]
        c['header']['rows']=len(c['rows'])
        r=analyze_capture(c,TIMELINE)
        self.assertFalse(r['cadence_30_confirmed_for_observed_segment'])
        self.assertAlmostEqual(r['observed_unique_fps'],15,places=3)
        self.assertTrue(r['long_holds'])

    def test_skipped_phase_and_wrong_backing_are_detected(self):
        c=capture();c['rows']=[r for r in c['rows'] if r['phase']!=12];c['header']['rows']=len(c['rows'])
        r=analyze_capture(c,TIMELINE);self.assertEqual(r['phase_skips'],1);self.assertFalse(r['all_phases_seen'])
        c=capture();c['rows'][10]['backing']=99
        self.assertTrue(analyze_capture(c,TIMELINE)['wrong_backing_epochs'])

    def test_fallback_pause_conflict_and_incomplete_capture(self):
        c=capture();c['rows'][10]['hd']=False
        self.assertEqual(analyze_capture(c,TIMELINE)['native_fallback_presentations'],1)
        c=capture();c['rows'][10]['active']=0
        self.assertEqual(analyze_capture(c,TIMELINE)['paused_presentations'],1)
        c=capture();c['rows'][10]['conflict']=True
        self.assertFalse(analyze_capture(c,TIMELINE)['cadence_30_confirmed_for_observed_segment'])
        c=capture();c['end']=False
        self.assertFalse(analyze_capture(c,TIMELINE)['capture_complete'])

    def test_latest_session_only(self):
        text='SPIMPFR_PRESENT_BEGIN id=1 frequency=100 rows=0 overflow=false droppedOwners=0\nInfinity Engine Enhancer initializing...\n'
        self.assertEqual(parse_log(text),[])

    def test_native_hd_frame_without_interpolation_is_not_accepted(self):
        c=capture();c['rows'][10]['phase']=-1
        r=analyze_capture(c,TIMELINE)
        self.assertEqual(r['timeline_fallback_presentations'],1)
        self.assertFalse(r['cadence_30_confirmed_for_observed_segment'])


if __name__=='__main__':unittest.main()
