"""Short P12 cache, concurrency and registry tests; owned temporary outputs only."""
from __future__ import annotations
import copy
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import Future, ThreadPoolExecutor
from unittest import mock
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / "pipeline/scripts"))
sys.path.insert(0,str(ROOT / "pipeline/tests"))
from test_reboutcx_p10 import P10Tests, frame, CLASSES
from test_reboutcx_p11 import xbr
import reboutcx_full as old
import reboutcx_full_p12 as full
import reboutcx_runtime_p12 as stage
import reboutcx_playable_p12 as controller
from reboutcx_cache_p12 import FrameCache, frame_key, context_key
from reboutcx_plan_p12 import plan_cache


class FakeRuntime(stage.Runtime):
    def __init__(self, **kwargs):
        super().__init__(pre_workers=2,post_workers=2,process_pools=False,**kwargs)
        self.calls = []

    def model_info(self,*_args,**_kwargs):
        return {"test":"no-cuda"}

    def infer(self,rgbs,canvas,fp16):
        self.calls.append(len(rgbs))
        future = Future()
        future.set_result(([np.repeat(np.repeat(rgb.astype(np.float32)/255,4,0),4,1) for rgb in rgbs],
                           {"dispatch_wall_seconds":0.0,"gpu_slots":86,"gpu_filler_frames":86-len(rgbs)}))
        return future


class P12Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="reboutcx-p12-test-")
        self.root = Path(temporary.name).resolve()
        assert self.root.parent == Path(tempfile.gettempdir()).resolve()
        self.addCleanup(temporary.cleanup)

    def transform(self,runtime,resources,required_qa=None):
        window = stage.GroupWindow(runtime,scalepix=self.root,node="node",marker=2,palette=None,
                                   classes=CLASSES,cache_context=b"test-context")
        try:
            states,pre = window.get(resources)
            timing = stage.process_group(runtime,resources,states,fp16=True,classes=CLASSES,required_qa=required_qa or {})
            return states,{**pre,**timing}
        finally:
            window.close()

    def test_key_ignores_metadata_and_separates_every_pixel_input(self):
        f = frame("A")
        key = frame_key(f,None,b"context")
        other = copy.deepcopy(f)
        other.resref,other.index,other.center_x,other.center_y = "B",17,52,-17
        self.assertEqual(frame_key(other,None,b"context"),key)
        for field in ("indices","palette","rgba","transparent","width"):
            other = copy.deepcopy(f)
            if field in ("indices","palette"):
                getattr(other,field).flat[-1] ^= 1
            elif field == "rgba":
                other.rgba = other.rgba[:-1]+bytes([other.rgba[-1]^1])
            else:
                setattr(other,field,getattr(other,field)+1)
            self.assertNotEqual(frame_key(other,None,b"context"),key,field)
        self.assertNotEqual(frame_key(f,f.palette,b"context"),key)
        self.assertNotEqual(frame_key(f,None,b"other-context"),key)

    def test_context_excludes_item_but_keeps_classes_model_and_tools(self):
        source,_ = P10Tests.fixture(self)
        job = old.read_json(source)
        a = context_key(job,CLASSES,"tool")
        job["item_resref"],job["layer"] = "OTHER","helmet"
        self.assertEqual(a,context_key(job,CLASSES,"tool"))
        self.assertNotEqual(a,context_key(job,{"all":list(range(256))},"tool"))
        self.assertNotEqual(a,context_key(job,CLASSES,"new-tool"))
        job["reboutcx"]["fp16"] = False
        self.assertNotEqual(a,context_key(job,CLASSES,"tool"))

    def test_cache_immutable_eviction_failure_and_retry(self):
        cache = FrameCache(8000)
        first = cache.claim(b"A")
        follower = cache.claim(b"A")
        cache.publish(first,{"pixels":np.zeros(1200,dtype=np.uint8)})
        self.assertIs(first.future.result(),follower.future.result())
        with self.assertRaises(ValueError):
            follower.future.result()["pixels"][0] = 1
        second = cache.claim(b"B")
        cache.publish(second,{"pixels":np.ones(1200,dtype=np.uint8)})
        self.assertEqual(cache.snapshot()["evictions"],1)
        self.assertLessEqual(cache.used,cache.limit)
        retry = cache.claim(b"A")
        consumer = cache.claim(b"A")
        cache.fail(retry,RuntimeError("injected"))
        with self.assertRaisesRegex(RuntimeError,"injected"):
            consumer.future.result()
        self.assertTrue(cache.claim(b"A").owner)
        cache.clear()
        self.assertEqual(cache.used,0)

    def test_repeated_only_admission_releases_after_last_use(self):
        cache = FrameCache(1024*1024)
        cache.declare_counts({b"A":2,b"unique":1})
        unique = cache.claim(b"unique")
        cache.publish(unique,{"pixels":np.zeros(2,dtype=np.uint8)})
        self.assertEqual(cache.snapshot()["ready_entries"],0)
        first = cache.claim(b"A")
        cache.publish(first,{"pixels":np.zeros(2,dtype=np.uint8)})
        self.assertEqual(cache.snapshot()["ready_entries"],1)
        last = cache.claim(b"A")
        self.assertFalse(last.owner)
        self.assertEqual(cache.used,0)
        self.assertEqual(cache.snapshot()["remaining_plan_keys"],0)
        self.assertLessEqual(cache.peak,cache.limit)

    def test_zero_retention_still_coalesces_inflight_work(self):
        cache = FrameCache(0)
        cache.declare_counts({b"A":2})
        first,last = cache.claim(b"A"),cache.claim(b"A")
        cache.publish(first,{"pixels":np.zeros(2,dtype=np.uint8)})
        self.assertIs(first.future.result(),last.future.result())
        self.assertEqual(cache.used,0)
        self.assertEqual(cache.snapshot()["ready_entries"],0)
        self.assertTrue(cache.claim(b"A").owner)
        cache.clear()

    def test_cross_component_hot_cache_preserves_pixels_qa_and_metadata(self):
        a,b = frame("A"),frame("B")
        b.center_x,b.center_y = 12,-7
        ra,rb = {"source":{"name":"A"},"frames":[a]},{"source":{"name":"B"},"frames":[b]}
        with FakeRuntime() as runtime, mock.patch.object(old,"xbr_batches",side_effect=xbr) as preparer:
            first,_ = self.transform(runtime,[ra])
            second,timing = self.transform(runtime,[rb],{"B":{0}})
            self.assertEqual(sum(runtime.calls),1)
            self.assertEqual(preparer.call_count,1)
            self.assertEqual(timing["logical_model_frames"],1)
            self.assertEqual(timing.get("model_frames",0),0)
            self.assertEqual(second["B"][0]["frame"].center_x,12)
            self.assertIn("xbr_rgba",second["B"][0])
            np.testing.assert_array_equal(first["A"][0]["quantized"],second["B"][0]["quantized"])
            self.assertEqual(runtime.memory.used,0)

    def test_interleaved_owners_do_not_wait_on_each_other_before_publishing(self):
        x,y = frame("A"),frame("A")
        y.indices[0,1] = 4
        y.palette[4] = [0,0,255]
        y.rgba = old.reconstruct_rgba(y.indices,y.palette,0).tobytes()
        a,b = [copy.deepcopy(x),copy.deepcopy(y)],[copy.deepcopy(y),copy.deepcopy(x)]
        for name,frames in (("A",a),("B",b)):
            for index,f in enumerate(frames):
                f.resref,f.index = name,index
        barrier,seen,lock = threading.Barrier(2),set(),threading.Lock()
        with FakeRuntime() as runtime, mock.patch.object(old,"xbr_batches",side_effect=xbr):
            original = runtime.cache.claim
            def claim(key):
                ticket = original(key)
                ident = threading.get_ident()
                with lock:
                    first = ident not in seen
                    seen.add(ident)
                if first:
                    barrier.wait(timeout=2)
                return ticket
            with mock.patch.object(runtime.cache,"claim",side_effect=claim),ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(self.transform,runtime,[{"source":{"name":name},"frames":frames}])
                           for name,frames in (("A",a),("B",b))]
                outputs = [f.result(timeout=4) for f in futures]
            self.assertEqual(sum(runtime.calls),2)
            self.assertEqual(runtime.cache.snapshot()["inflight_entries"],0)
            self.assertEqual(runtime.memory.used,0)
            np.testing.assert_array_equal(outputs[0][0]["A"][0]["quantized"],outputs[1][0]["B"][1]["quantized"])

    def test_preparation_failure_releases_memory_and_completes_followers(self):
        rs = [{"source":{"name":"A"},"frames":[frame("A"),frame("A")]}]
        rs[0]["frames"][1].index = 1
        with FakeRuntime() as runtime,mock.patch.object(stage,"prepare_resource",side_effect=RuntimeError("prepare failed")):
            with self.assertRaisesRegex(RuntimeError,"prepare failed"):
                self.transform(runtime,rs)
            self.assertEqual(runtime.memory.used,0)
            self.assertEqual(runtime.cache.snapshot()["inflight_entries"],0)

    def test_post_failure_releases_memory_and_completes_followers(self):
        rs = [{"source":{"name":"A"},"frames":[frame("A"),frame("A")]}]
        rs[0]["frames"][1].index = 1
        with FakeRuntime() as runtime,mock.patch.object(old,"xbr_batches",side_effect=xbr), \
                mock.patch.object(stage,"postprocess_batch",side_effect=RuntimeError("post failed")):
            with self.assertRaisesRegex(RuntimeError,"post failed"):
                self.transform(runtime,rs)
            self.assertEqual(runtime.memory.used,0)
            self.assertEqual(runtime.cache.snapshot()["inflight_entries"],0)

    def test_full_run_publish_clone_verify_and_previous_job_immutable(self):
        source,resources = P10Tests.fixture(self)
        before = source.read_bytes()
        path = full.derive_job(source)
        frames = [f for r in resources for f in r["frames"]]
        with FakeRuntime() as runtime,mock.patch.object(old,"xbr_batches",side_effect=xbr), \
                mock.patch.object(full,"load_source_frames",return_value=(frames,resources,{"animation_id":"0x5000"})), \
                mock.patch.object(full,"load_palette_profiles",return_value=([],None)), \
                mock.patch("sys.stdout",new_callable=io.StringIO):
            manifest = full.execute(path,runtime)
            report = full.verify(path)
            self.assertEqual(manifest["coverage"]["logical_model_frames"],1)
            self.assertEqual(manifest["coverage"]["unique_model_frames"],1)
            self.assertEqual(manifest["coverage"]["gpu_slots"],86)
            self.assertEqual(manifest["coverage"]["gpu_filler_frames"],85)
            self.assertEqual(manifest["resources"][1]["reused_render_from"],"TEST")
            self.assertEqual(report["manifest_sha256"],old.sha256_file(self.root/"runs"/full.RUN_ID/"manifest.json"))
            with self.assertRaisesRegex(RuntimeError,"already exists"):
                full.execute(path,runtime)
            self.assertEqual(runtime.memory.used,0)
        self.assertEqual(source.read_bytes(),before)
        self.assertFalse(list(self.root.glob("runs/.*.tmp-*")))

    def test_admission_plan_matches_runtime_key_and_excludes_resource_clones(self):
        source,_ = P10Tests.fixture(self)
        job = old.read_json(source)
        f = frame("A")
        palette = np.zeros((256,4),dtype=np.uint8)
        palette[:,:3] = f.palette[:,[2,1,0]]
        pixel_offset = 24+24+1024
        raw = b"BAM V1  "+struct.pack("<HBBIII",2,0,0,24,48,pixel_offset)
        raw += b"".join(struct.pack("<HHhhI",2,1,1,-2,(pixel_offset+i*2)|0x80000000) for i in range(2))
        raw += palette.tobytes()+f.indices.tobytes()*2
        bam = self.root/"sample.bam"
        bam.write_bytes(raw)
        source_manifest = Path(job["paths"]["source_manifest"])
        source_manifest.write_text(json.dumps({"bams":[{"name":n,"source":"sample.bam","canonical_bam":"sample.bam"} for n in ("A","B")]}))
        job["source_inventory"] = [{"name":n} for n in ("A","B")]
        job["source_manifest_sha256"] = old.sha256_file(source_manifest)
        source.write_text(json.dumps(job))
        import reboutcx_plan_p12 as planner
        with mock.patch.object(planner,"load_palette_profiles",return_value=([],None)):
            counts,report = plan_cache([source])
        context = context_key(job,CLASSES,old.sha256_file(Path(job["paths"]["scalepix"])))
        self.assertEqual(counts,{frame_key(f,None,context):2})
        self.assertEqual(report["resources"],1)
        self.assertEqual(report["duplicate_frames"],1)

    def test_real_spawn_post_preserves_tuple_token(self):
        f = frame()
        with stage.Runtime(pre_workers=1,post_workers=1) as runtime:
            guide = np.array([[0,3]],dtype=np.uint8)
            crop = np.zeros((2,4,3),dtype=np.float32)
            result,_ = runtime.post.submit(stage.postprocess_batch,[(('A',0),guide,f.palette,[0,3],0,crop,True)],CLASSES).result(timeout=4)
            self.assertEqual(result[0][0],('A',0))
            np.testing.assert_array_equal(result[0][1],guide)

    def test_controller_counts_logical_computed_and_fillers_through_verification(self):
        queue = self.root/"queue.json"
        queue.write_text("{}")
        jobs = []
        for index in range(3):
            job = self.root/f"job-{index}.json"
            output = self.root/f"output-{index}"
            job.write_text(json.dumps({"paths":{"run_dir":str(output)}}))
            jobs.append(job)
        output.mkdir()
        (output/"manifest.json").write_text("{}")
        verified = []
        def execute(job,runtime):
            runtime.execution_reports[str(job.resolve())] = {"test":True}
            return {"coverage":{"unique_model_frames":3,"logical_model_frames":5,
                "frames":8,"gpu_slots":86,"gpu_filler_frames":83}}
        def verify(job):
            verified.append(job)
            return {"manifest_sha256":"test"}
        with mock.patch.object(controller,"load_queue",return_value=jobs), \
                mock.patch.object(controller,"plan_cache",return_value=({}, {"seconds":0,"duplicate_frames":0})) as planner, \
                mock.patch.object(controller,"Runtime",side_effect=lambda **_:FakeRuntime()), \
                mock.patch.object(controller,"ProcessPoolExecutor",side_effect=lambda **_:ThreadPoolExecutor(max_workers=1)), \
                mock.patch.object(controller,"execute",side_effect=execute), \
                mock.patch.object(controller,"verify",side_effect=verify), \
                mock.patch("sys.stdout",new_callable=io.StringIO):
            report = controller.run_queue(queue,components=1,log_dir=self.root/"logs")
        planner.assert_called_once_with(jobs)
        self.assertEqual(set(verified),set(jobs))
        self.assertEqual(report["completed"],3)
        self.assertEqual(report["new_model_frames"],6)
        self.assertEqual(report["logical_model_frames"],10)
        self.assertEqual(report["source_frames"],16)
        self.assertEqual(report["gpu_slots"],172)
        self.assertEqual(report["gpu_filler_frames"],166)
        elapsed = report["wall_through_verification_seconds"]
        self.assertAlmostEqual(report["logical_model_frames_per_second"],10/elapsed)
        events = [json.loads(s)["event"] for s in next((self.root/"logs").glob("*.jsonl")).read_text().splitlines()]
        self.assertLess(events.index("cache-plan"),events.index("render-start"))
        self.assertEqual(events[-1],"complete")


if __name__ == "__main__":
    start = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(P12Tests))
    print(json.dumps({"tests":result.testsRun,"seconds":time.perf_counter()-start,
                      "success":result.wasSuccessful(),"temporary_directories_cleaned":True}))
    raise SystemExit(not result.wasSuccessful())
