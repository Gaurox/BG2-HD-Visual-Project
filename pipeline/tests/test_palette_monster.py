from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline/scripts"))
from palette_monster_contract import get_profile
from palette_monster_work_plan import Cache, WorkPlan
from palette_monster import Processor, produce
import palette_registry as v6
from reboutcx_quantize import srgb_u8_to_oklab

BACKEND = dict(batch_size=86, canvas_quantum=32, fp16=True, model_sha256="12"*32, device="CPU-test-fixture-only")


def resource(pid, *, fraction=3):
    p = get_profile(pid)
    ref = next(iter(p.sources))
    i = np.full((4, 4), 3, np.uint8)
    f = np.full_like(i, fraction)
    reps = np.full(256, 65535, np.uint16); reps[3] = 0
    return dict(resref=ref, source_sha256=p.sources[ref]["canonical_sha256_registered"], cycles=[[0, 0], []],
                frames=[dict(geometry=(2, 2, -3, 5, 0), representatives=reps, guide=i.copy(), I=i, F=f,
                             dep=p.dependency_mask(i, f))])


class MonsterTests(unittest.TestCase):
    def test_materialization_keeps_unused_native_frames_centres_and_cycles(self):
        plan=WorkPlan()
        try:
            rid=plan.db.execute("SELECT resource_id FROM frames WHERE cycle_referenced=0 LIMIT 1").fetchone()[0]
            r=dict(plan.db.execute("SELECT * FROM resources WHERE resource_id=?",(rid,)).fetchone())
            class FixtureCache:
                def load(self,work):
                    g=np.repeat(np.repeat(work.frame.indices,2,0),2,1);f=np.zeros_like(g)
                    return dict(guide=g,I=g.copy(),F=f,dep=get_profile(work.row["profile_id"]).dependency_mask(g,f))
            material=plan.materialize(r,FixtureCache())
            positions=plan.db.execute("SELECT * FROM frames WHERE resource_id=? ORDER BY frame_index",(rid,)).fetchall()
            self.assertEqual(len(material["frames"]),r["frame_count"])
            self.assertTrue(any(not x["cycle_referenced"] for x in positions))
            for encoded,position in zip(material["frames"],positions,strict=True):
                self.assertEqual(encoded["geometry"][2:4],(position["center_x"],position["center_y"]))
            self.assertEqual(sum(map(len,material["cycles"])),r["cycle_slots"])
            self.assertEqual(len(material["cycles"]),r["cycle_count"])
        finally: plan.close()

    def test_new_processor_dispatches_six_correct_fits_and_float_box_targets(self):
        from concurrent.futures import ThreadPoolExecutor
        from chainner_ext import ResizeFilter,resize
        plan=WorkPlan()
        try:
            rows=plan.work_rows(plan.resources(refs=["NBOHG1","NBOHG2"]))
            works=[plan.work(next(r for r in rows if r["needs_model"] and r["profile_id"]==pid)) for pid in (4,5)]
            processor=Processor.__new__(Processor)
            processor.cache=type("FixtureCache",(),dict(plan=plan))()
            processor.descriptor=None;processor.resize=resize;processor.box=ResizeFilter.Box
            processor.pool=ThreadPoolExecutor(max_workers=1)
            from collections import Counter
            processor.stats=Counter();received={};requests=[]
            def inference(descriptor,rgbs,*,canvas,fp16):
                self.assertTrue(fp16)
                self.assertLessEqual(len(rgbs),86)
                self.assertEqual((canvas[0]%32,canvas[1]%32),(0,0))
                requests.extend(rgbs)
                return [np.repeat(np.repeat(rgb.astype(np.float32)/255,4,0),4,1) for rgb in rgbs],{}
            def encode(work,guide,targets):
                self.assertEqual(targets.shape,(6,work.height*2,work.width*2,3))
                self.assertEqual(targets.dtype,np.float32)
                received[work.row["profile_id"]]=targets
            try:
                with patch("palette_monster.infer_float_crops",side_effect=inference),patch.object(processor,"encode",side_effect=encode):
                    processor.process(works)
                self.assertEqual(len(requests),12)
                self.assertEqual(set(received),{4,5})
                from reboutcx_batch import prepare_inference_rgb
                for work in works:
                    p=get_profile(work.row["profile_id"])
                    expected=np.stack([resize(np.repeat(np.repeat(prepare_inference_rgb(work.frame,p.fitting[k,:,:3]).astype(np.float32)/255,4,0),4,1),
                                             (work.width*2,work.height*2),ResizeFilter.Box,False) for k in range(6)])
                    np.testing.assert_array_equal(received[p.profile_id],expected)
            finally: processor.close()
        finally: plan.close()

    def test_all_profiles_integer_scalar_decoder_specials_alpha_and_dependencies(self):
        for pid in range(2, 8):
            p = get_profile(pid)
            i = np.concatenate((np.arange(3, dtype=np.uint8), np.repeat(np.arange(3, 256, dtype=np.uint8), 8)))[None]
            f = np.concatenate((np.zeros(3, np.uint8), np.tile(np.arange(8, dtype=np.uint8), 253)))[None]
            for palette in p.fitting:
                expected = []
                for n, t in zip(i[0], f[0]):
                    n, t = int(n), int(t); s = int(p.succ[n])
                    expected.append([((8-t)*int(palette[n,c])+t*int(palette[s,c])+4)//8 for c in range(3)] +
                                    [0 if n == 0 else int(palette[n,3])])
                np.testing.assert_array_equal(p.decode(i, f, palette)[0], expected)
            bits = p.dependency_mask(np.array([[3]], np.uint8), np.array([[7]], np.uint8))
            self.assertEqual(set(np.flatnonzero(np.unpackbits(bits, bitorder="little"))), {3, int(p.succ[3])})
            bad = p.fitting[0].copy(); bad[p.succ[3], 3] = 128
            with self.assertRaisesRegex(ValueError, "unequal live alpha"): p.decode(i, f, bad)
            for special in (0,1,2):
                with self.assertRaises(ValueError): p.validate_planes(np.array([[special]],np.uint8), np.ones((1,1),np.uint8))
            with self.assertRaises(ValueError): p.check_contract(np.array([[1]],np.uint8), np.array([[3]],np.uint8), np.zeros((1,1),np.uint8))
            with self.assertRaises(ValueError): p.check_contract(i, i, f, np.zeros(32,np.uint8))

    def test_exhaustive_encoder_matches_independent_enumeration_and_preserves_specials(self):
        for pid in range(2,8):
            p = get_profile(pid)
            g = np.array([[0,1,2,3,255]], np.uint8)
            targets = np.random.default_rng(pid).random((6,1,5,3))
            result = p.encode(g, targets, chunk_pixels=1)
            self.assertEqual(result["I"][0,:3].tolist(), [0,1,2])
            self.assertFalse(result["F"][0,:3].any())
            for x in (3,4):
                best = None
                for n in range(3,256):
                    for f in range(8):
                        rgb = np.array([[((8-f)*int(pa[n,c])+f*int(pa[p.succ[n],c])+4)//8 for c in range(3)] for pa in p.fitting])
                        delta = srgb_u8_to_oklab(rgb) - srgb_u8_to_oklab(targets[:,0,x]*255)
                        score = float(np.sum(delta*delta))
                        if best is None or score < best[0]: best = (score,n,f)
                self.assertEqual((int(result["I"][0,x]),int(result["F"][0,x])),best[1:])
            # Exact duplicated candidate colors must choose the earliest I, then F.
            target = np.stack([p.decode(np.array([[3]],np.uint8),np.zeros((1,1),np.uint8),pa)[...,:3] for pa in p.fitting])/255
            result = p.encode(np.array([[255]],np.uint8),target)
            self.assertEqual((int(result["I"][0,0]),int(result["F"][0,0])),(3,0))

    def test_v6_all_profiles_roundtrip_and_reject_cross_profile_source_rule_scale(self):
        with tempfile.TemporaryDirectory() as td:
            for pid in range(2,8):
                path=Path(td)/str(pid); r=resource(pid)
                v6.write(path,2,[r],class_profile_id=pid,decode_rule_id=2)
                info=v6.inspect(path,include_frames=True)
                self.assertEqual((info["class_profile_id"],info["decode_rule_id"]),(pid,2))
                frame=info["frame_data"][0]["frames"][0]
                self.assertEqual(frame["geometry"],(2,2,-3,5,0))
                self.assertEqual(info["frame_data"][0]["cycles"],[[0,0],[]])
                self.assertEqual(frame["I"],bytes([3])*16)
                self.assertEqual(frame["F"],bytes([3])*16)
                for profile,rule,scale in ((pid,1,2),(pid,2,4),(99,2,2),(3 if pid==2 else 2,2,2)):
                    with self.assertRaises(RuntimeError): v6.write(Path(td)/"bad",scale,[r],class_profile_id=profile,decode_rule_id=rule)
                bad=copy.deepcopy(r);bad["source_sha256"]="00"*32
                with self.assertRaises(RuntimeError): v6.write(Path(td)/"badsha",2,[bad],class_profile_id=pid,decode_rule_id=2)
            with self.assertRaises(RuntimeError):
                v6.write_catalog(Path(td)/"wrong-owner",2,[[resource(4)]],profile_ids=[4],
                                 animations=[dict(animation_id="0x7F07",owner=3,component_indices=[0])])

    def test_source_plan_counts_cache_namespace_corruption_and_all_hit_without_processor(self):
        plan=WorkPlan()
        try:
            rs=plan.resources(refs=["NBOHG1","NBOHG2"]);rows=plan.work_rows(rs)
            self.assertEqual((sum(r["frame_count"] for r in rs),len(rows),sum(r["needs_model"] for r in rows)),(1242,272,270))
            with tempfile.TemporaryDirectory() as td:
                cache=Cache(plan,td,BACKEND)
                other=Cache(plan,td,dict(BACKEND,device="different backend"))
                self.assertNotEqual(cache.namespace,other.namespace)
                # A tiny real subset covers new special, cache hit and corruption; model is replaced by a CPU fixture.
                selected=[next(r for r in rows if not r["needs_model"]),next(r for r in rows if r["needs_model"])]
                class FixtureProcessor:
                    def __init__(self,c,w): self.cache=c
                    def process(self,works):
                        for work in works:
                            g=plan.guide(work);f=np.zeros_like(g)
                            self.cache.save(work,dict(guide=g,I=g.copy(),F=f,dep=get_profile(work.row["profile_id"]).dependency_mask(g,f)))
                    def close(self): pass
                with patch.object(plan,"work_rows",return_value=selected):
                    s=produce(plan,rs,cache,processor_factory=FixtureProcessor)
                    self.assertEqual((s["model_work"],s["special_work"]),(1,1))
                    def forbidden(*args): raise AssertionError("all-hit resume initialized GPU")
                    s=produce(plan,rs,cache,processor_factory=forbidden)
                    self.assertEqual(s["cache_hits"],2)
                work=plan.work(selected[1]);arrays=cache.load(work)
                arrays["guide"][0,0]^=1
                with self.assertRaisesRegex(ValueError,"cached guide"): cache.save(work,arrays)
                cache.path(work).write_bytes(b"broken ZIP")
                with self.assertRaises(ValueError): cache.contains(work)
        finally: plan.close()


if __name__ == "__main__": unittest.main()
