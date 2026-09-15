"""Short P11 routing, memory, versioning and registry checks in owned temp dirs."""
from __future__ import annotations
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
sys.path.insert(0, str(ROOT / "pipeline/tests"))
from test_reboutcx_p10 import FakeRuntime, P10Tests, frame, CLASSES
import reboutcx_full as old
import reboutcx_full_p11 as full
import reboutcx_runtime_p11 as stage


def xbr(frames, *_):
    for f in frames:
        rgba = np.frombuffer(f.rgba, dtype=np.uint8).reshape(f.height, f.width, 4)
        yield f, (f.width * 2, f.height * 2, np.repeat(np.repeat(rgba, 2, 0), 2, 1).tobytes())


class P11Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="reboutcx-p11-test-")
        self.root = Path(self.temp.name).resolve()
        assert self.root.parent == Path(tempfile.gettempdir()).resolve()
        self.addCleanup(self.temp.cleanup)

    def test_fixed_group_boundaries_and_oversize_singleton(self):
        def resource(i, area=1):
            return {"source": {"name": str(i)}, "frames": [SimpleNamespace(width=area, height=1)]}
        small = [resource(i) for i in range(19)]
        groups = stage.plan_groups(small)
        self.assertEqual([len(g) for g in groups], [8, 8, 3])
        self.assertEqual([r for g in groups for r in g], small)
        values = [resource(0, 4_000_000), resource(1, 4_000_000), resource(2, 9_000_000), resource(3)]
        self.assertEqual([stage.group_key(g) for g in stage.plan_groups(values)], [("0", "1"), ("2",), ("3",)])

    def test_failed_preparation_releases_whole_group(self):
        rs = [{"source": {"name": name}, "frames": [frame(name)]} for name in ("A", "B")]
        with FakeRuntime() as runtime:
            window = stage.GroupWindow(runtime, scalepix=self.root / "absent", node="node", marker=2,
                                       palette=None, classes=CLASSES)
            with mock.patch.object(stage, "prepare_resource", side_effect=RuntimeError("expected failure")):
                window.submit(rs)
                with self.assertRaisesRegex(RuntimeError, "expected failure"):
                    window.close()
            self.assertEqual(runtime.memory.used, 0)
            self.assertFalse(window.pending)

    def test_cross_resource_index_collision_and_null_routing(self):
        a, b, n = frame("A"), frame("B"), frame("N", null=True)
        b.indices[0, 1] = 4
        b.palette[4] = [0, 0, 255]
        b.rgba = old.reconstruct_rgba(b.indices, b.palette, 0).tobytes()
        rs = [{"source": {"name": f.resref}, "frames": [f]} for f in (a, b, n)]
        states = {}
        with mock.patch.object(old, "xbr_batches", side_effect=xbr):
            for r in rs:
                states[r["source"]["name"]], _ = stage.prepare_resource(r, self.root, "node", 2, None, CLASSES)
        with FakeRuntime() as runtime:
            timing = stage.process_group(runtime, rs, states, fp16=True, classes=CLASSES, required_qa={})
        self.assertEqual(timing["model_frames"], 2)
        self.assertEqual(timing["batches"], 1)
        self.assertEqual(timing["cross_resource_batches"], 1)
        for f in (a, b, n):
            expected = np.repeat(np.repeat(f.indices, 2, 0), 2, 1)
            np.testing.assert_array_equal(states[f.resref][0]["quantized"], expected)

    def test_publish_verify_clone_and_immutable_previous_job(self):
        source, resources = P10Tests.fixture(self)
        before = source.read_bytes()
        path = full.derive_job(source)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(full.derive_job(source), path)
        self.assertEqual(old.read_json(path)["reboutcx_batch"]["canvas_quantum"], 32)
        frames = [f for r in resources for f in r["frames"]]
        with FakeRuntime() as runtime, mock.patch.object(full, "load_source_frames", return_value=(
                frames, resources, {"animation_id": "0x5000"})), \
                mock.patch.object(old, "xbr_batches", side_effect=xbr), \
                mock.patch.object(full, "load_palette_profiles", return_value=([], None)), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            manifest = full.execute(path, runtime)
            report = full.verify(path)
            output = self.root / "runs" / full.RUN_ID
            self.assertEqual(report["manifest_sha256"], old.sha256_file(output / "manifest.json"))
            self.assertEqual(manifest["coverage"]["unique_model_frames"], 1)
            self.assertEqual(manifest["resources"][1]["reused_render_from"], "TEST")
            self.assertEqual(manifest["method"]["resource_groups"], [["TEST", "NULL"]])
            self.assertEqual(runtime.memory.used, 0)
            self.assertFalse(list(output.parent.glob(".*.tmp-*")))
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                full.execute(path, runtime)
        with self.assertRaises(RuntimeError):
            full.validate_job(old.read_json(source))
        altered = old.read_json(path)
        altered["reboutcx_batch"]["canvas_quantum"] = 16
        with self.assertRaises(RuntimeError):
            full.validate_job(altered)

    def test_real_process_worker_routes_tuple_tokens(self):
        f = frame("A")
        with stage.Runtime(pre_workers=1, post_workers=1) as runtime:
            guide = np.array([[0, 3]], dtype=np.uint8)
            crop = np.zeros((2, 4, 3), dtype=np.float32)
            result, _ = runtime.post.submit(stage.postprocess_batch,
                [(("A", 0), guide, f.palette, [0, 3], 0, crop, False)], CLASSES).result(timeout=4)
            self.assertEqual(result[0][0], ("A", 0))
            np.testing.assert_array_equal(result[0][1], guide)


if __name__ == "__main__":
    start = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(P11Tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"tests": result.testsRun, "seconds": time.perf_counter() - start,
                      "success": result.wasSuccessful(), "temporary_directories_cleaned": True}))
    raise SystemExit(not result.wasSuccessful())
