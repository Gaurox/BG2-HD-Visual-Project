"""Short CPU-only P10 contract tests; all outputs live in owned temporary directories."""
from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import reboutcx_full as old
import reboutcx_quantize as old_cpu
import reboutcx_cpu_p10 as cpu
import reboutcx_full_p10 as full
import reboutcx_playable_p10 as controller
import reboutcx_runtime_p10 as runtime_module
from reboutcx_batch_p10 import pack_normalized
from run_creature_sprite_x2 import SourceFrame


def frame(name="TEST", *, null=False):
    palette = np.zeros((256, 3), dtype=np.uint8)
    palette[0], palette[2], palette[3] = (0, 255, 0), (20, 30, 40), (180, 40, 20)
    indices = np.array([[2]] if null else [[0, 3]], dtype=np.uint8)
    rgba = old.reconstruct_rgba(indices, palette, 0)
    return SourceFrame(name, 0, indices.shape[1], indices.shape[0], 0 if null else 1, 0 if null else -2, 0,
                       indices, palette, rgba.tobytes())


CLASSES = {"transparent": [0], "shadow": [1], "null": [2], "material": list(range(3, 256))}


class FakeRuntime(runtime_module.Runtime):
    def __init__(self):
        super().__init__(pre_workers=1, post_workers=1, process_pools=False)

    def model_info(self, *_args, **_kwargs):
        return {"test": "synthetic-no-cuda"}

    def infer(self, rgbs, canvas, fp16):
        future = Future()
        future.set_result(([np.repeat(np.repeat(rgb.astype(np.float32) / 255, 4, 0), 4, 1)
                            for rgb in rgbs], {"dispatch_wall_seconds": 0.0}))
        return future


class P10Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="reboutcx-p10-test-")
        self.root = Path(self.temporary.name).resolve()
        assert self.root.parent == Path(tempfile.gettempdir()).resolve()
        self.addCleanup(self.temporary.cleanup)

    def test_representatives_exact_small_large_and_uint16_boundary(self):
        rng = np.random.default_rng(42)
        for a in (np.array([], dtype=np.uint8), rng.integers(0, 256, (113, 151), dtype=np.uint8),
                  np.arange(65535, dtype=np.uint32).astype(np.uint8),
                  np.zeros((256, 256), dtype=np.uint8)):
            np.testing.assert_array_equal(cpu.source_representatives(a), old_cpu.source_representatives(a))

    def test_normalization_and_padding_are_exact_float32(self):
        rgb = np.array([[[0, 127, 255], [13, 128, 254]]], dtype=np.uint8)
        packed = pack_normalized([rgb], 64, 64)
        np.testing.assert_array_equal(packed[0, :1, :2], rgb.astype(np.float32) / 255.0)
        self.assertEqual(packed.dtype, np.float32)
        self.assertEqual(np.count_nonzero(packed[0, 1:]), 0)
        self.assertEqual(np.count_nonzero(packed[0, :1, 2:]), 0)
        with self.assertRaises(RuntimeError):
            pack_normalized([rgb], 1, 1)

    def test_quantizer_cache_preserves_metrics_classes_and_ties(self):
        f = frame()
        palette = f.palette.copy()
        palette[4] = palette[3]
        guide = np.array([[0, 1, 2, 4, 3]], dtype=np.uint8)
        target = np.full((1, 5, 3), palette[3], dtype=np.uint8)
        args = (target, guide, palette, np.arange(5), CLASSES)
        expected, metrics = old_cpu.quantize_classed_oklab(*args, transparent_index=0)
        for _ in range(2):
            actual, measured = cpu.quantize_classed_oklab(*args, transparent_index=0)
            np.testing.assert_array_equal(actual, expected)
            self.assertEqual(measured, metrics)
        self.assertEqual(actual[0].tolist(), [0, 1, 2, 3, 3])
        with self.assertRaises(RuntimeError):
            cpu.quantize_classed_oklab(target, guide, palette, [0, 1, 3, 4], CLASSES, transparent_index=0)

    def test_mapping_duplicate_rgba_needs_matching_provenance(self):
        f = frame()
        f.palette[4] = f.palette[3]
        f.indices[0] = [3, 4]
        rgba = old.reconstruct_rgba(f.indices, f.palette, 0)
        output = np.repeat(np.repeat(rgba, 2, 0), 2, 1).tobytes()
        guide = np.repeat(np.repeat(f.indices, 2, 0), 2, 1)
        with self.assertRaisesRegex(RuntimeError, "duplicate used RGBA"):
            cpu.map_output(f, output)
        actual, reps = cpu.map_output(f, output, guide)
        np.testing.assert_array_equal(actual, guide.reshape(-1))
        np.testing.assert_array_equal(reps, old_cpu.source_representatives(f.indices))

    def test_registry_bytes_equal_and_independent_validation_rejects_corruption(self):
        f = frame()
        output = np.repeat(np.repeat(f.indices, 2, 0), 2, 1)
        a, b = io.BytesIO(), io.BytesIO()
        old.write_frame_record(a, f, output)
        cpu.write_frame_record(b, f, output, cpu.source_representatives(f.indices))
        self.assertEqual(a.getvalue(), b.getvalue())
        source_path = self.root / "source"
        source_path.write_bytes(b"source")
        resource = {"source": {"name": "TEST"}, "source_path": source_path, "frames": [f],
                    "cycles": [{"index": 0, "frame_indices": [0, 0]}]}
        path = self.root / "TEST.registry"
        with path.open("wb") as stream:
            old.write_component_header(stream, animation_id=0x5000, resref="TEST",
                                       source_sha256=old.sha256_file(source_path), frame_count=1, cycle_count=1)
            stream.write(b.getvalue())
            old.write_cycles(stream, resource["cycles"])
        evidence = [{"indices_sha256": old.sha256_array(output)}]
        expected = old.validate_component_registry(path, animation_id=0x5000, resource=resource, frame_manifest=evidence)
        actual = cpu.validate_component_registry(path, animation_id=0x5000, resource=resource, frame_manifest=evidence)
        self.assertEqual(expected, actual)
        raw = bytearray(path.read_bytes())
        raw[old.REGISTRY_HEADER_BYTES + old.REGISTRY_RESOURCE_HEADER_BYTES] ^= 1
        path.write_bytes(raw)
        with self.assertRaisesRegex(RuntimeError, "geometry"):
            cpu.validate_component_registry(path, animation_id=0x5000, resource=resource, frame_manifest=evidence)

    def test_memory_bounds_and_failed_preparation_release(self):
        budget = runtime_module.ByteBudget(10)
        self.assertTrue(budget.acquire(8))
        self.assertFalse(budget.acquire(3, blocking=False))
        budget.release(8)
        with self.assertRaises(RuntimeError):
            budget.acquire(11)
        with FakeRuntime() as runtime:
            window = runtime_module.ResourceWindow(runtime, scalepix=self.root / "absent", node="node",
                                                  marker=2, palette=None, classes=CLASSES)
            with mock.patch.object(runtime_module, "prepare_resource", side_effect=RuntimeError("prepare failed")):
                window.submit({"source": {"name": "TEST"}, "frames": [frame()]})
                with self.assertRaisesRegex(RuntimeError, "prepare failed"):
                    window.close()
            self.assertEqual(runtime.memory.used, 0)

    def test_model_loaded_once_across_concurrent_components(self):
        with FakeRuntime() as runtime, mock.patch.object(runtime, "_load", return_value={"fake": "model"}) as load:
            with ThreadPoolExecutor(max_workers=3) as pool:
                results = [pool.submit(runtime_module.Runtime.model_info, runtime, self.root / "model",
                                       device="cuda:0", fp16=True) for _ in range(3)]
                for result in results:
                    self.assertEqual(result.result(), {"fake": "model"})
            self.assertEqual(load.call_count, 1)
            with self.assertRaises(RuntimeError):
                runtime_module.Runtime.model_info(runtime, self.root / "other", device="cuda:0", fp16=True)

    def fixture(self):
        resources = []
        for name in ("TEST", "COPY", "NULL"):
            source = self.root / ("null" if name == "NULL" else "source")
            source.write_bytes(b"null" if name == "NULL" else b"source")
            resources.append({"source": {"name": name}, "source_path": source, "bam_path": source,
                              "frames": [frame(name, null=name == "NULL")],
                              "cycles": [{"index": 0, "frame_indices": [0, 0]}]})
        source_manifest = self.root / "source.json"
        source_manifest.write_text('{}')
        model, scalepix = self.root / "model", self.root / "scalepix"
        model.write_bytes(b"fake-model")
        scalepix.write_bytes(b"fake-scalepix")
        job = {"schema": full.JOB_SCHEMA, "scope": "full-animation", "installable": False,
               "job_id": "test-reboutcx-p9-batch86-v1", "animation_id": "0x5000",
               "source_inventory": [{"name": r["source"]["name"]} for r in resources],
               "paths": {"run_dir": str(self.root / "runs/reboutcx-p9-batch86-v1"),
                         "source_manifest": str(source_manifest), "reboutcx_model": str(model),
                         "scalepix": str(scalepix), "chainner_python": sys.executable},
               "source_manifest_sha256": old.sha256_file(source_manifest),
               "reboutcx": {"target_scale": 2, "model_sha256": old.sha256_file(model),
                            "device": "cuda:0", "fp16": True}, "tools": {"node": "node"},
               "null_frame_marker": 2, "semantic_classes": CLASSES,
               "qa": {"groups": [{"name": "tiny", "resref": "TEST", "frames": [0], "duration_ms": 80}]}}
        path = self.root / "p9.json"
        path.write_text(json.dumps(job))
        return path, resources

    def test_tiny_component_publish_verify_clone_and_immutability(self):
        source, resources = self.fixture()
        before = source.read_bytes()
        path = full.derive_job(source)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(full.derive_job(source), path)
        frames = [f for r in resources for f in r["frames"]]
        def xbr(frames, *_):
            for f in frames:
                rgba = np.frombuffer(f.rgba, dtype=np.uint8).reshape(f.height, f.width, 4)
                yield f, (f.width * 2, f.height * 2, np.repeat(np.repeat(rgba, 2, 0), 2, 1).tobytes())
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
            self.assertEqual(runtime.memory.used, 0)
            self.assertFalse(list(output.parent.glob('.*.tmp-*')))
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                full.execute(path, runtime)
        with self.assertRaises(RuntimeError):
            full.validate_job(old.read_json(source))

    def test_real_spawn_workers_null_preparation_and_quantization(self):
        f = frame("NULL", null=True)
        resource = {"source": {"name": "NULL"}, "frames": [f]}
        with runtime_module.Runtime(pre_workers=1, post_workers=1) as runtime:
            states, _ = runtime.pre.submit(runtime_module.prepare_resource, resource,
                                           self.root / "absent", "node", 2, None, CLASSES).result(timeout=4)
            self.assertTrue(states[0]["metrics"]["model_bypassed"])
            guide = np.array([[0, 3]], dtype=np.uint8)
            crop = np.zeros((2, 4, 3), dtype=np.float32)
            result, _ = runtime.post.submit(runtime_module.postprocess_batch,
                                            [(0, guide, f.palette, [0, 3], 0, crop, False)], CLASSES).result(timeout=4)
            np.testing.assert_array_equal(result[0][1], guide)

    def test_controller_starts_next_component_while_verifying(self):
        original, _ = self.fixture()
        source_job = old.read_json(original)
        source_job["runtime_profile"] = "character-bg2ee-2.7.3.0"
        Path(source_job["paths"]["source_manifest"]).write_text('{"bams": []}')
        jobs = []
        for i in range(3):
            source = self.root / f"job-{i}" / "source.json"
            source.parent.mkdir()
            job = copy.deepcopy(source_job)
            job["paths"]["run_dir"] = str(source.parent / "runs/reboutcx-p9-batch86-v1")
            source.write_text(json.dumps(job))
            jobs.append(full.derive_job(source))
        queue = self.root / "queue.json"
        queue.write_text(json.dumps({"schema": controller.QUEUE_SCHEMA, "installable": False,
            "members": [{"job": str(p), "sha256": old.sha256_file(p)} for p in jobs]}))
        second_started = threading.Event()
        def execute(path, runtime):
            if path == jobs[1]:
                second_started.set()
            runtime.execution_reports[str(path.resolve())] = {"execute_wall_seconds": 0.0}
            return {"coverage": {"unique_model_frames": 1}}
        def verify(path):
            if path == jobs[0] and not second_started.wait(timeout=1):
                raise RuntimeError("verification blocked the next render")
            return {"manifest_sha256": "test"}
        with mock.patch.object(controller, "Runtime", side_effect=lambda **_: FakeRuntime()), \
                mock.patch.object(controller, "ProcessPoolExecutor", side_effect=lambda **_: ThreadPoolExecutor(max_workers=1)), \
                mock.patch.object(controller, "execute", side_effect=execute), \
                mock.patch.object(controller, "verify", side_effect=verify), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            result = controller.run_queue(queue, components=1, log_dir=self.root / "logs")
        self.assertEqual(result["completed"], 3)
        self.assertEqual(result["new_model_frames"], 3)
        self.assertTrue(second_started.is_set())
        data = old.read_json(queue)
        data["members"].append(data["members"][0])
        queue.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, "duplicate output"):
            controller.load_queue(queue)


if __name__ == "__main__":
    started = time.perf_counter()
    result = unittest.main(exit=False)
    print(json.dumps({"test_wall_seconds": time.perf_counter() - started,
                      "cuda_calls": 0, "temporary_directories_cleaned": True}))
    raise SystemExit(not result.result.wasSuccessful())
