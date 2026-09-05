from __future__ import annotations

import inspect
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import run_creature_sprite_x2 as pipeline  # noqa: E402


class CreatureSpriteX2PipelineTests(unittest.TestCase):
    def make_frame(self, palette: np.ndarray | None = None) -> pipeline.SourceFrame:
        if palette is None:
            palette = np.zeros((256, 3), dtype=np.uint8)
            palette[1] = [10, 20, 30]
        indices = np.array([[0, 1]], dtype=np.uint8)
        rgba = np.array([[[0, 0, 0, 0], [10, 20, 30, 255]]], dtype=np.uint8)
        return pipeline.SourceFrame("TEST", 0, 2, 1, 0, 0, 0, indices, palette, rgba.tobytes())

    def test_exact_palette_mapping(self) -> None:
        frame = self.make_frame()
        output = np.array(
            [
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [10, 20, 30, 255],
                [10, 20, 30, 255],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [10, 20, 30, 255],
                [10, 20, 30, 255],
            ],
            dtype=np.uint8,
        )
        mapped, representatives = pipeline.map_output(frame, output.tobytes())
        self.assertEqual(mapped.tolist(), [0, 0, 1, 1, 0, 0, 1, 1])
        self.assertEqual(int(representatives[0]), 0)
        self.assertEqual(int(representatives[1]), 1)

    def test_new_color_is_rejected(self) -> None:
        frame = self.make_frame()
        output = np.array([[9, 9, 9, 255]] * 8, dtype=np.uint8)
        with self.assertRaisesRegex(RuntimeError, "introduced"):
            pipeline.map_output(frame, output.tobytes())

    def test_partial_alpha_is_rejected(self) -> None:
        frame = self.make_frame()
        output = np.array([[10, 20, 30, 128]] * 8, dtype=np.uint8)
        with self.assertRaisesRegex(RuntimeError, "partial alpha"):
            pipeline.map_output(frame, output.tobytes())

    def test_duplicate_used_rgba_indices_preserve_source_index_provenance(self) -> None:
        palette = np.zeros((256, 3), dtype=np.uint8)
        palette[1] = [10, 20, 30]
        palette[2] = [10, 20, 30]
        indices = np.array([[1, 2]], dtype=np.uint8)
        rgba = np.array(
            [[[10, 20, 30, 255], [10, 20, 30, 255]]], dtype=np.uint8
        )
        frame = pipeline.SourceFrame(
            "DUPL", 0, 2, 1, 0, 0, 0, indices, palette, rgba.tobytes()
        )
        self.assertTrue(pipeline.has_duplicate_used_rgba_indices(frame))
        with self.assertRaisesRegex(RuntimeError, "duplicate used RGBA"):
            pipeline.map_output(
                frame,
                np.repeat(np.repeat(rgba, 2, axis=0), 2, axis=1).tobytes(),
            )

        output_x2 = np.repeat(np.repeat(rgba, 2, axis=0), 2, axis=1)
        provenance_x2 = pipeline.xbr_provenance_indices(frame, 2)
        mapped_x2, representatives = pipeline.map_output(
            frame, output_x2.tobytes(), provenance_x2
        )
        self.assertEqual(mapped_x2.tolist(), [1, 1, 2, 2, 1, 1, 2, 2])
        self.assertEqual(int(representatives[1]), 0)
        self.assertEqual(int(representatives[2]), 1)

        output_x4 = np.repeat(np.repeat(rgba, 4, axis=0), 4, axis=1)
        mapped_x4, _ = pipeline.map_output(
            frame, output_x4.tobytes(), pipeline.xbr_provenance_indices(frame, 4)
        )
        self.assertEqual(
            mapped_x4.tolist(),
            [1, 1, 1, 1, 2, 2, 2, 2] * 4,
        )

    def test_legacy_job_keeps_x2_v2_contract(self) -> None:
        contract = pipeline.upscale_contract({})
        self.assertFalse(contract.explicit)
        self.assertEqual(contract.scale, 2)
        self.assertEqual(contract.registry_magic, b"IEECSX2\0")
        self.assertEqual(contract.registry_version, 2)
        self.assertEqual(contract.registry_filename, "CreatureSprites-X2.registry")

    def test_legacy_catalog_job_path_resolves_after_layout_migration(self) -> None:
        legacy = (
            ROOT
            / "sprite"
            / "jobs"
            / "creature-sprites-progressive-xn-xbr2x-goblin-mgo1.json"
        )
        current = (
            ROOT
            / "sprite"
            / "catalogs"
            / "creature-x2-nearest"
            / "jobs"
            / legacy.name
        )
        self.assertFalse(legacy.exists())
        self.assertTrue(current.is_file())
        loaded = pipeline.load_work_item(legacy)
        self.assertEqual(Path(loaded["_job_file"]), current.resolve())

    def test_sealed_paths_and_armor_members_accept_only_audited_redirects(self) -> None:
        legacy = "sprite/jobs/dwarf-male-fighter-cdmb1-xbr2x.json"
        current = (
            "sprite/families/playable-characters/6102-dwarf-male-fighter/"
            "cdmb1/variants/xbr2x-legacy/jobs/"
            "dwarf-male-fighter-cdmb1-xbr2x.json"
        )
        expected = pipeline.resolve_path(current)
        self.assertTrue(pipeline.state_path_matches_exact_file(legacy, expected))
        self.assertFalse(
            pipeline.state_path_matches_exact_file(f"../{legacy}", expected)
        )
        recorded = [{"job_file": legacy, "job_id": "member"}]
        current_records = [{"job_file": current, "job_id": "member"}]
        self.assertTrue(
            pipeline.armor_set_member_records_match(recorded, current_records)
        )
        recorded[0]["job_id"] = "changed"
        self.assertFalse(
            pipeline.armor_set_member_records_match(recorded, current_records)
        )

    def test_explicit_x4_uses_direct_xbr4x_v3_contract(self) -> None:
        contract = pipeline.upscale_contract(
            {
                "upscale": {
                    "scale": 4,
                    "algorithm": "XBR/xbr4X",
                    "passes": 1,
                    "antialias": False,
                    "xbr_blend": False,
                }
            }
        )
        self.assertTrue(contract.explicit)
        self.assertEqual(contract.adapter_mode, "xbr4x")
        self.assertEqual(contract.registry_magic, b"IEECSXN\0")
        self.assertEqual(contract.registry_version, 3)
        self.assertEqual(contract.registry_filename, "CreatureSprites-XN.registry")

    def test_creation_scale_switch_is_central_and_keeps_legacy_default(self) -> None:
        template: dict[str, object] = {}
        legacy = pipeline.creation_upscale_contract(template, None)
        explicit_x2 = pipeline.creation_upscale_contract(template, 2)
        explicit_x4 = pipeline.creation_upscale_contract(template, 4)
        self.assertFalse(legacy.explicit)
        self.assertEqual(legacy.scale, 2)
        self.assertTrue(explicit_x2.explicit)
        self.assertEqual(explicit_x2.registry_version, 3)
        self.assertEqual(explicit_x4.method["algorithm"], "XBR/xbr4X")
        self.assertEqual(explicit_x4.scale, 4)
        self.assertNotIn("upscale", template)

    def test_cli_exposes_generic_scale_and_frame_retention_switches(self) -> None:
        parser = pipeline.make_parser()
        explicit = parser.parse_args(
            [
                "new-character-job",
                "--job",
                "sprite/jobs/test-xbr4x.json",
                "--scale",
                "4",
                "--keep-upscaled-frames",
            ]
        )
        self.assertEqual(explicit.scale, 4)
        self.assertTrue(explicit.keep_upscaled_frames)
        legacy_alias = parser.parse_args(
            [
                "build",
                "--job",
                "sprite/jobs/test-xbr2x.json",
                "--keep-x2-frames",
            ]
        )
        self.assertTrue(legacy_alias.keep_upscaled_frames)

    def test_xn_adapter_exposes_direct_xbr4x_and_generic_protocol(self) -> None:
        adapter = (ROOT / "pipeline" / "scripts" / "xbr2x_batch.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("xbr4x(srcBuffer", adapter)
        self.assertIn("XBRNBAT", adapter)
        self.assertIn("XBRNOUT", adapter)

    def test_xn_adapter_executes_both_protocols(self) -> None:
        fake_scalepix = """<script>
let classification = 'sprite';
function classifyBuffer() { return 'sprite'; }
function invertBufferInPlace() {}
function runXBR2X(source, width, height, destination) {
  for (let y = 0; y < height * 2; ++y)
    for (let x = 0; x < width * 2; ++x)
      destination[y * width * 2 + x] = source[Math.floor(y / 2) * width + Math.floor(x / 2)];
}
function xbr4x(source, width, height) {
  const destination = new Uint32Array(width * height * 16);
  for (let y = 0; y < height * 4; ++y)
    for (let x = 0; x < width * 4; ++x)
      destination[y * width * 4 + x] = source[Math.floor(y / 4) * width + Math.floor(x / 4)];
  return destination;
}
</script>"""
        frame = self.make_frame()
        with tempfile.TemporaryDirectory() as temporary:
            scalepix = Path(temporary) / "scalepix.html"
            scalepix.write_text(fake_scalepix, encoding="utf-8")
            legacy = pipeline.run_xbr2x([frame], scalepix, "node")
            explicit = pipeline.run_xbr(
                [frame], scalepix, "node", pipeline.direct_upscale_contract(4)
            )
        self.assertEqual((legacy[0][0], legacy[0][1], len(legacy[0][2])), (4, 2, 32))
        self.assertEqual((explicit[0][0], explicit[0][1], len(explicit[0][2])), (8, 4, 128))

    def test_xbr_output_batches_are_deterministic_ordered_and_budgeted(self) -> None:
        frames = []
        for index in range(5):
            frame = self.make_frame()
            frame.index = index
            frames.append(frame)
        ranges = pipeline.xbr_output_batch_ranges(
            frames, 2, output_budget_bytes=64
        )
        self.assertEqual(ranges, [(0, 2, 64), (2, 4, 64), (4, 5, 32)])
        self.assertEqual(
            [index for start, end, _ in ranges for index in range(start, end)],
            list(range(len(frames))),
        )
        oversized = pipeline.xbr_output_batch_ranges(
            frames[:2], 2, output_budget_bytes=16
        )
        self.assertEqual(oversized, [(0, 1, 32), (1, 2, 32)])
        self.assertTrue(
            all(end - start == 1 for start, end, size in oversized if size > 16)
        )

    def test_explicit_upscale_routes_install_and_restore_to_xn_scripts(self) -> None:
        work_item = {
            "upscale": {
                "scale": 4,
                "algorithm": "XBR/xbr4X",
                "passes": 1,
                "antialias": False,
                "xbr_blend": False,
            }
        }
        self.assertEqual(
            pipeline.install_restore_script(work_item, restore=False).name,
            "Install-CreatureSprite-XN-Test.ps1",
        )
        self.assertEqual(
            pipeline.install_restore_script(work_item, restore=True).name,
            "Restore-CreatureSprite-XN-Test.ps1",
        )
        self.assertEqual(
            pipeline.install_restore_script({}, restore=False).name,
            "Install-CreatureSprite-X2-Test.ps1",
        )

    def test_armor_set_without_upscale_remains_strictly_legacy(self) -> None:
        work_item = {
            "_kind": "armor-set",
            "_members": [
                {
                    "upscale": {
                        "scale": 4,
                        "algorithm": "XBR/xbr4X",
                        "passes": 1,
                        "antialias": False,
                        "xbr_blend": False,
                    }
                }
            ],
        }
        contract = pipeline.effective_upscale_contract(work_item)
        self.assertFalse(contract.explicit)
        self.assertEqual(contract.scale, 2)
        self.assertEqual(
            pipeline.install_restore_script(work_item, restore=False).name,
            "Install-CreatureSprite-X2-Test.ps1",
        )

    def test_explicit_upscale_rejects_non_direct_or_blended_contracts(self) -> None:
        base = {
            "scale": 4,
            "algorithm": "XBR/xbr4X",
            "passes": 1,
            "antialias": False,
            "xbr_blend": False,
        }
        for update, message in (
            ({"passes": 2}, "passes"),
            ({"algorithm": "XBR/xbr2X"}, "algorithm"),
            ({"antialias": True}, "antialias"),
            ({"xbr_blend": True}, "xbr_blend"),
            ({"algorithm": "xbr4x"}, "algorithm"),
        ):
            with self.subTest(update=update):
                with self.assertRaisesRegex(RuntimeError, message):
                    pipeline.upscale_contract({"upscale": {**base, **update}})

    def test_x4_registry_preflight_uses_dense_scale_squared_payload(self) -> None:
        frame = self.make_frame()
        resources = [{"frames": [frame], "cycles": [{"frame_indices": [0]}]}]
        result = pipeline.preflight_registry_layout(resources, 4)
        self.assertEqual(result["index_bytes"], 32)
        self.assertEqual(result["registry_bytes"], 640)
        with self.assertRaisesRegex(RuntimeError, "before xBR"):
            pipeline.preflight_registry_layout(
                resources, 4, maximum_bytes=result["registry_bytes"] - 1
            )

    def test_x4_registry_limit_is_centralized_at_512_mib(self) -> None:
        self.assertEqual(pipeline.MAX_REGISTRY_BYTES, 128 * 1024 * 1024)
        self.assertEqual(pipeline.maximum_registry_bytes(2), pipeline.MAX_REGISTRY_BYTES)
        self.assertEqual(pipeline.maximum_registry_bytes(4), 512 * 1024 * 1024)
        self.assertEqual(
            pipeline.MAX_LAZY_FRAME_INDEX_BYTES, 128 * 1024 * 1024
        )
        frames = []
        for index in range(5):
            frame = self.make_frame()
            frame.index = index
            frame.width = 2048
            frame.height = 2048
            frames.append(frame)
        resources = [
            {
                "frames": frames,
                "cycles": [{"frame_indices": list(range(len(frames)))}],
            }
        ]
        projected = pipeline.preflight_registry_layout(resources, 4)
        self.assertGreater(projected["registry_bytes"], pipeline.MAX_REGISTRY_BYTES)
        self.assertLess(projected["registry_bytes"], pipeline.maximum_registry_bytes(4))
        with self.assertRaisesRegex(RuntimeError, "before xBR"):
            pipeline.preflight_registry_layout(
                resources, 4, maximum_bytes=pipeline.MAX_REGISTRY_BYTES
            )
        oversized_frame = self.make_frame()
        oversized_frame.width = 4096
        oversized_frame.height = 4096
        with self.assertRaisesRegex(RuntimeError, "frame payload"):
            pipeline.preflight_registry_layout(
                [
                    {
                        "frames": [oversized_frame],
                        "cycles": [{"frame_indices": [0]}],
                    }
                ],
                4,
            )

    def test_build_preflight_precedes_xbr_dispatch(self) -> None:
        source = inspect.getsource(pipeline.build_pack)
        self.assertLess(
            source.index("preflight_registry_layout"), source.index("run_xbr(")
        )

    def test_build_pack_batches_streams_identical_registry_and_resumes_without_xbr(self) -> None:
        contract = pipeline.direct_upscale_contract(4)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_dir = root / "source"
            source_dir.mkdir()
            manifest_path = source_dir / "manifest.json"
            manifest_path.write_text("{}\n", encoding="utf-8")
            source_bam = source_dir / "TEST.BAM"
            source_bam.write_bytes(b"fixture-source")
            scalepix = root / "scalepix.html"
            scalepix.write_text("fixture", encoding="utf-8")

            frames = []
            for index in range(8):
                frame = self.make_frame()
                frame.index = index
                frames.append(frame)
            cycles = [{"index": 0, "frame_indices": list(range(len(frames)))}]
            resources = [
                {
                    "source": {"name": "TEST"},
                    "source_path": source_bam,
                    "frames": frames,
                    "cycles": cycles,
                }
            ]
            job = {
                "job_id": "streamed-fixture-xbr4x",
                "animation": {
                    "id": "0xE400",
                    "bam_prefix": "TEST",
                    "runtime_profile": "monster-icewind-bg2ee-2.7.3.0",
                },
                "paths": {
                    "source_dir": str(source_dir),
                    "run_dir": str(root / "run"),
                    "scalepix": str(scalepix),
                },
                "upscale": contract.method,
            }

            def nearest_outputs(batch, _scalepix, _node, batch_contract):
                result = []
                for frame in batch:
                    source = np.frombuffer(frame.rgba, dtype=np.uint8).reshape(
                        frame.height, frame.width, 4
                    )
                    scaled = np.repeat(
                        np.repeat(source, batch_contract.scale, axis=0),
                        batch_contract.scale,
                        axis=1,
                    )
                    result.append(
                        (scaled.shape[1], scaled.shape[0], scaled.tobytes())
                    )
                return result

            all_outputs = nearest_outputs(frames, scalepix, "node", contract)
            expected = bytearray(contract.registry_magic)
            expected.extend(
                struct.pack("<IIII", 3, 4, 1, 0xE400)
            )
            expected.extend(b"TEST\0\0\0\0")
            expected.extend(bytes.fromhex(pipeline.sha256_file(source_bam)))
            expected.extend(struct.pack("<II", len(frames), len(cycles)))
            for frame, (_, _, rgba) in zip(frames, all_outputs, strict=True):
                mapped, representatives = pipeline.map_output(frame, rgba)
                expected.extend(
                    struct.pack(
                        "<HHhhB3xI",
                        frame.width,
                        frame.height,
                        frame.center_x,
                        frame.center_y,
                        frame.transparent,
                        mapped.size,
                    )
                )
                expected.extend(representatives.astype("<u2", copy=False).tobytes())
                expected.extend(mapped.tobytes())
            expected.extend(struct.pack("<I", len(frames)))
            expected.extend(struct.pack(f"<{len(frames)}I", *range(len(frames))))

            qa_sample_counts = []
            original_qa_renderer = pipeline.make_comparison_sheet_samples

            def record_qa_samples(*args, **kwargs):
                qa_sample_counts.append(len(args[1]))
                return original_qa_renderer(*args, **kwargs)

            with (
                mock.patch.object(pipeline, "verify_sources", return_value={}),
                mock.patch.object(
                    pipeline,
                    "load_source_frames",
                    return_value=(frames, resources, {}),
                ),
                mock.patch.object(pipeline, "assert_workspace_child"),
                mock.patch.object(
                    pipeline, "XBR_OUTPUT_BATCH_BUDGET_BYTES", 128
                ),
                mock.patch.object(
                    pipeline, "run_xbr", side_effect=nearest_outputs
                ) as dispatch,
                mock.patch.object(
                    pipeline,
                    "make_comparison_sheet_samples",
                    side_effect=record_qa_samples,
                ),
            ):
                built = pipeline.build_pack(
                    job, force=False, resume=False, keep_frames=False
                )
                verified = pipeline.verify_build(job)
                manifest_path = pipeline.build_dir(job) / "build-manifest.json"
                valid_manifest = pipeline.read_json(manifest_path)
                for field in ("resource_count", "registry_bytes"):
                    tampered_manifest = dict(valid_manifest)
                    tampered_manifest[field] += 1
                    pipeline.write_json(manifest_path, tampered_manifest)
                    with self.assertRaisesRegex(
                        RuntimeError, "top-level counters differ"
                    ):
                        pipeline.verify_build(job)
                pipeline.write_json(manifest_path, valid_manifest)
                source_manifest_file = pipeline.source_manifest_path(job)
                source_manifest_bytes = source_manifest_file.read_bytes()
                source_manifest_file.write_text(
                    '{"changed":true}\n', encoding="utf-8"
                )
                with self.assertRaisesRegex(RuntimeError, "source manifest hash"):
                    pipeline.verify_build(job)
                with self.assertRaisesRegex(RuntimeError, "source manifest hash"):
                    pipeline.armor_set_member_records({"_members": [job]})
                source_manifest_file.write_bytes(source_manifest_bytes)

                scalepix_bytes = scalepix.read_bytes()
                scalepix.write_bytes(b"changed")
                with self.assertRaisesRegex(RuntimeError, "Scalepix hash"):
                    pipeline.verify_build(job)
                scalepix.write_bytes(scalepix_bytes)

                stale_adapter = dict(valid_manifest)
                stale_adapter["xbr_adapter_sha256"] = "0" * 64
                pipeline.write_json(manifest_path, stale_adapter)
                with self.assertRaisesRegex(RuntimeError, "adapter hash"):
                    pipeline.verify_build(job)
                pipeline.write_json(manifest_path, valid_manifest)
                self.assertEqual(dispatch.call_count, 8)
                self.assertEqual(qa_sample_counts, [5])
                dispatch.reset_mock()
                reused = pipeline.build_pack(
                    job, force=False, resume=True, keep_frames=False
                )
                dispatch.assert_not_called()
                stale_manifest = pipeline.read_json(manifest_path)
                del stale_manifest["xbr_batching"]
                pipeline.write_json(manifest_path, stale_manifest)
                legacy_reused = pipeline.build_pack(
                    job, force=False, resume=True, keep_frames=False
                )
                self.assertEqual(legacy_reused["status"], "reused")
                dispatch.assert_not_called()
                invalid_manifest = dict(stale_manifest)
                invalid_manifest["xbr_batching"] = dict(
                    valid_manifest["xbr_batching"]
                )
                invalid_manifest["xbr_batching"]["batch_count"] = 0
                pipeline.write_json(manifest_path, invalid_manifest)
                rebuilt = pipeline.build_pack(
                    job, force=False, resume=True, keep_frames=False
                )
                self.assertEqual(rebuilt["status"], "built")
                self.assertEqual(dispatch.call_count, 8)

            build_root = pipeline.build_dir(job)
            registry = (
                build_root
                / "iee-assets"
                / "creature-sprites"
                / pipeline.XN_REGISTRY_FILENAME
            )
            manifest = pipeline.read_json(build_root / "build-manifest.json")
            self.assertEqual(registry.read_bytes(), bytes(expected))
            self.assertEqual(built["sha256"], pipeline.sha256_file(registry))
            self.assertEqual(verified["sha256"], built["sha256"])
            self.assertEqual(reused["status"], "reused")
            self.assertEqual(
                manifest["xbr_batching"],
                {
                    "output_budget_bytes": 128,
                    "batch_count": 8,
                    "total_projected_output_bytes": 1024,
                    "maximum_projected_batch_bytes": 128,
                    "oversized_singleton_batches": 0,
                    "ordering": "source-resource-frame",
                },
            )
            self.assertEqual(manifest["registry_layout"], "monolith")
            self.assertIsNone(manifest["registry_set"])
            self.assertEqual(manifest["total_registry_bytes"], len(expected))
            self.assertEqual(
                manifest["validation"]["qa_samples_retained_max_per_resource"], 5
            )

    def test_explicit_member_auto_shards_and_aggregate_flattens_its_records(self) -> None:
        contract = pipeline.direct_upscale_contract(2)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_dir = root / "source"
            source_dir.mkdir()
            (source_dir / "manifest.json").write_text("{}\n", encoding="utf-8")
            scalepix = root / "scalepix.html"
            scalepix.write_text("fixture", encoding="utf-8")

            resources = []
            frames = []
            for index, resref in enumerate(("CHFB1A1", "CHFB1A3")):
                source_bam = source_dir / f"{resref}.BAM"
                source_bam.write_bytes(f"fixture-{resref}".encode("ascii"))
                frame = self.make_frame()
                frame.resref = resref
                frame.index = 0
                frames.append(frame)
                resources.append(
                    {
                        "source": {"name": resref},
                        "source_path": source_bam,
                        "frames": [frame],
                        "cycles": [{"index": 0, "frame_indices": [0]}],
                    }
                )

            job = {
                "_job_file": str(root / "member-job.json"),
                "job_id": "member-set-fixture-xbr2x",
                "animation": {
                    "id": "0x6110",
                    "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                    "armor_code": 1,
                    "bam_prefix": "CHFB1",
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                },
                "paths": {
                    "source_dir": str(source_dir),
                    "run_dir": str(root / "member-run"),
                    "scalepix": str(scalepix),
                },
                "upscale": contract.method,
            }

            def nearest_outputs(batch, _scalepix, _node, batch_contract):
                outputs = []
                for frame in batch:
                    source = np.frombuffer(frame.rgba, dtype=np.uint8).reshape(
                        frame.height, frame.width, 4
                    )
                    scaled = np.repeat(
                        np.repeat(source, batch_contract.scale, axis=0),
                        batch_contract.scale,
                        axis=1,
                    )
                    outputs.append(
                        (scaled.shape[1], scaled.shape[0], scaled.tobytes())
                    )
                return outputs

            with (
                mock.patch.object(pipeline, "verify_sources", return_value={}),
                mock.patch.object(
                    pipeline,
                    "load_source_frames",
                    return_value=(frames, resources, {}),
                ),
                mock.patch.object(pipeline, "assert_workspace_child"),
                mock.patch.object(
                    pipeline, "run_xbr", side_effect=nearest_outputs
                ) as dispatch,
                mock.patch.dict(pipeline.MAX_REGISTRY_BYTES_BY_SCALE, {2: 700}),
            ):
                built = pipeline.build_pack(
                    job, force=False, resume=False, keep_frames=False
                )
                verified_member = pipeline.verify_build(job)
                dispatch.reset_mock()
                reused_member = pipeline.build_pack(
                    job, force=False, resume=True, keep_frames=False
                )
                self.assertEqual(reused_member["status"], "reused")
                dispatch.assert_not_called()

                member_build = pipeline.build_dir(job)
                member_manifest = pipeline.read_json(
                    member_build / "build-manifest.json"
                )
                self.assertEqual(built["registry_layout"], "set")
                self.assertEqual(member_manifest["registry_layout"], "set")
                self.assertIsNone(member_manifest["registry"])
                self.assertEqual(len(member_manifest["shards"]), 2)
                self.assertEqual(
                    verified_member["resources"], ["CHFB1A1", "CHFB1A3"]
                )
                pack_dir = member_build / "iee-assets" / "creature-sprites"
                set_path = pack_dir / pipeline.XN_REGISTRY_SET_FILENAME
                valid_set = set_path.read_bytes()
                set_path.write_bytes(valid_set[:-1] + bytes([valid_set[-1] ^ 0x01]))
                with self.assertRaises(RuntimeError):
                    pipeline.verify_build(job)
                set_path.write_bytes(valid_set)
                shard_path = pack_dir / pipeline.XN_REGISTRY_SHARD_FILENAME.format(
                    index=0
                )
                valid_shard = shard_path.read_bytes()
                shard_path.write_bytes(
                    valid_shard[:-1] + bytes([valid_shard[-1] ^ 0x01])
                )
                with self.assertRaises(RuntimeError):
                    pipeline.verify_build(job)
                shard_path.write_bytes(valid_shard)

                aggregate = {
                    "_build_dir": root / "aggregate" / "build",
                    "_members": [job],
                    "job_id": "aggregate-member-set-xbr2x",
                    "animation": {
                        "id": "0x6110",
                        "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                        "runtime_profile": "character-bg2ee-2.7.3.0",
                    },
                    "upscale": contract.method,
                }
                def fake_build_dir(item):
                    return (
                        member_build
                        if item is job
                        else Path(item["_build_dir"])
                    )

                with (
                    mock.patch.object(
                        pipeline, "build_dir", side_effect=fake_build_dir
                    ),
                    mock.patch.object(
                        pipeline, "verify_sources", return_value={"resources": 2}
                    ),
                ):
                    aggregate_result = pipeline.build_armor_set(
                        aggregate, force=False, resume=False
                    )
                    verified_aggregate = pipeline.verify_armor_set_build(aggregate)

            self.assertEqual(aggregate_result["registry_layout"], "set")
            self.assertEqual(
                verified_aggregate["resources"], ["CHFB1A1", "CHFB1A3"]
            )

    def test_character_runtime_profile_is_supported(self) -> None:
        pipeline.require_runtime_profile(
            {"animation": {"runtime_profile": "character-bg2ee-2.7.3.0"}}
        )

    def test_unknown_runtime_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unsupported-runtime-profile"):
            pipeline.require_runtime_profile(
                {"animation": {"runtime_profile": "character-unknown"}}
            )

    def test_verify_runtime_rejects_missing_or_stale_engine_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "engine-source"
            source_files = (
                "CMakeLists.txt",
                "src/iee/hooks.cpp",
                "src/iee/native_occlusion_bridge.cpp",
                "src/iee/native_occlusion_bridge.h",
                "src/iee/dll_main.cpp",
                "src/iee/bridge_transition.cpp",
                "src/iee/bridge_transition.h",
                "src/iee/creature_sprite_x2.cpp",
                "src/iee/creature_sprite_x2.h",
                "src/iee/core/config.cpp",
                "src/iee/core/config.h",
                "src/iee/core/native_occlusion_probe.cpp",
                "src/iee/core/native_occlusion_probe.h",
                "src/iee/game/build_manifest.cpp",
                "src/iee/game/build_manifest.h",
                "tests/iee_tests.cpp",
                "tests/bridge_worker_lifecycle_tests.cpp",
            )
            for index, relative in enumerate(source_files):
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"source-{index}\n", encoding="utf-8")
            job = {
                "job_id": "runtime-contract-gate",
                "animation": {
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                },
                "paths": {
                    "engine_source": str(source),
                    "run_dir": str(root / "run"),
                },
            }
            runtime = pipeline.runtime_dir(job)
            runtime.mkdir(parents=True)
            dll = runtime / "InfinityEngine-Enhancer.dll"
            dll.write_bytes(b"runtime")
            manifest_path = runtime / "runtime-manifest.json"
            manifest = {
                "schema": pipeline.RUNTIME_SCHEMA,
                "status": "built-tested",
                "job_id": job["job_id"],
                "runtime_profile": job["animation"]["runtime_profile"],
                "engine_source_contract_sha256": pipeline.source_tree_hash(source),
                "dll": dll.name,
                "dll_sha256": pipeline.sha256_file(dll),
                "tests_status": "passed",
                "bridge_worker_tests_status": "passed",
            }
            pipeline.write_json(manifest_path, manifest)
            self.assertEqual(pipeline.verify_runtime(job)["tests_status"], "passed")

            missing_contract = dict(manifest)
            del missing_contract["engine_source_contract_sha256"]
            pipeline.write_json(manifest_path, missing_contract)
            with self.assertRaisesRegex(RuntimeError, "source contract differs"):
                pipeline.verify_runtime(job)

            pipeline.write_json(manifest_path, manifest)
            (source / "src/iee/creature_sprite_x2.h").write_text(
                "changed contract\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "source contract differs"):
                pipeline.verify_runtime(job)

    def test_install_and_restore_scripts_accept_character_bundles(self) -> None:
        for script_name in (
            "Install-CreatureSprite-X2-Test.ps1",
            "Restore-CreatureSprite-X2-Test.ps1",
        ):
            script = (ROOT / "pipeline" / "scripts" / script_name).read_text(
                encoding="utf-8"
            )
            self.assertIn(pipeline.JOB_SCHEMA, script)
            self.assertIn(pipeline.ARMOR_SET_SCHEMA, script)

    def test_install_scripts_prevent_registry_masking_and_support_recovery(self) -> None:
        legacy = (
            ROOT / "pipeline" / "scripts" / "Install-CreatureSprite-X2-Test.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("CreatureSprites-XN.registry", legacy)
        self.assertIn("CreatureSprites-XN.set", legacy)
        self.assertIn("restaure le test xN avant tout test legacy x2", legacy)
        self.assertIn("'restoring'", legacy)
        self.assertIn("Test-Path -LiteralPath $xnPriorityFile)", legacy)
        self.assertNotIn(
            "Test-Path -LiteralPath $xnPriorityFile -PathType Leaf", legacy
        )
        xn_install = (
            ROOT / "pipeline" / "scripts" / "Install-CreatureSprite-XN-Test.ps1"
        ).read_text(encoding="utf-8")
        xn_restore = (
            ROOT / "pipeline" / "scripts" / "Restore-CreatureSprite-XN-Test.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("Publier l'état récupérable avant la première mutation", xn_install)
        self.assertIn("-RecoverInstalling", xn_install)
        self.assertIn("'restoring'", xn_install)
        self.assertIn("[switch]$RecoverInstalling", xn_restore)
        self.assertIn("$recoveringInterruptedInstall", xn_restore)
        self.assertIn("function Get-IniKey", xn_install)
        self.assertIn("CreatureSprites-XN.set", xn_install)
        self.assertIn(r"^CreatureSprites-XN-[0-9]{4}\.registry$", xn_install)
        self.assertIn("function Get-MaxLazyFrameIndexBytes", xn_install)
        self.assertIn("$frameBytes -gt (Get-MaxLazyFrameIndexBytes)", xn_install)
        self.assertIn("'restoring'", xn_restore)
        self.assertIn("RecoverInterrupted", xn_restore)
        for script_name in (
            "Install-CreatureSprite-X2-Test.ps1",
            "Restore-CreatureSprite-X2-Test.ps1",
            "Install-CreatureSprite-XN-Test.ps1",
            "Restore-CreatureSprite-XN-Test.ps1",
        ):
            script = (ROOT / "pipeline" / "scripts" / script_name).read_text(
                encoding="utf-8"
            )
            self.assertIn("Global\\BG2UpscaleCreatureSpriteMutation_", script)
            self.assertIn("finally", script)

    def test_character_runtime_has_no_texture_sweep_hook(self) -> None:
        hooks = (
            ROOT
            / "engine"
            / "InfinityEngine-Enhancer"
            / "source-patchee"
            / "src"
            / "iee"
            / "hooks.cpp"
        ).read_text(encoding="utf-8")
        self.assertNotIn("detour_draw_clear_textures", hooks)
        self.assertNotIn("Engine texture pool reset observed", hooks)
        self.assertIn("finish_composite_texture", hooks)
        self.assertLess(
            hooks.index("original(x, y, sourceRect, logicalSize, clipRect, flags)"),
            hooks.index("finish_composite_texture"),
        )

        runtime = (
            ROOT
            / "engine"
            / "InfinityEngine-Enhancer"
            / "source-patchee"
            / "src"
            / "iee"
            / "creature_sprite_x2.cpp"
        ).read_text(encoding="utf-8")
        self.assertNotIn("upload_bound_composite_locked", runtime)
        self.assertIn("delete-pending after queued draw", runtime)
        self.assertIn("descriptor + 0x24, out.secondaryGlName", runtime)
        self.assertIn("clear_private_recycled_secondary", runtime)
        self.assertIn("std::memcpy(secondaryField, &zero", runtime)
        self.assertIn("materialized.secondaryGlName == 0", runtime)

    def test_character_runtime_health_requires_transient_replacement_and_clean_pool(self) -> None:
        healthy = pipeline.runtime_session_health(
            "Composing creature sprite CHFB1A1 frame 000 via transient replacement "
            "id 42 (NEAREST, delete-pending after queued draw)",
            "character-bg2ee-2.7.3.0",
            {
                "CHFB1": [
                    "Composing creature sprite CHFB1A1 frame 000 via transient "
                    "replacement id 42 (NEAREST, delete-pending after queued draw)"
                ]
            },
        )
        self.assertTrue(healthy["runtime_health_pass"])

        unhealthy = pipeline.runtime_session_health(
            "Engine texture pool reset observed\nNo GL texture is bound",
            "character-bg2ee-2.7.3.0",
            {"CHFB1": ["Composing creature sprite CHFB1A1 frame 000 (NEAREST)"]},
        )
        self.assertFalse(unhealthy["runtime_health_pass"])
        self.assertEqual(unhealthy["texture_pool_reset_count"], 1)
        self.assertEqual(unhealthy["unbound_texture_warning_count"], 1)

        destructive = pipeline.runtime_session_health(
            "Composing creature sprite CHFB1A1 frame 000 in-place "
            "(NEAREST, no persistent engine texture id)",
            "character-bg2ee-2.7.3.0",
            {"CHFB1": ["in-place (NEAREST, no persistent engine texture id)"]},
        )
        self.assertFalse(destructive["runtime_health_pass"])
        self.assertEqual(destructive["character_unsafe_in_place_count"], 1)

        lazy_failure = pipeline.runtime_session_health(
            "Creature sprite lazy pack disabled after payload failure: read error\n"
            "Composing creature sprite CHFB1A1 frame 000 via transient replacement "
            "id 42 (NEAREST, delete-pending after queued draw)",
            "character-bg2ee-2.7.3.0",
            {
                "CHFB1": [
                    "Composing creature sprite CHFB1A1 frame 000 via transient "
                    "replacement id 42 (NEAREST, delete-pending after queued draw)"
                ]
            },
        )
        self.assertFalse(lazy_failure["runtime_health_pass"])
        self.assertEqual(lazy_failure["lazy_payload_failure_count"], 1)

    def test_explicit_qa_requires_xn_source_and_installed_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "game"
            run = root / "run"
            game.mkdir()
            runtime = game / "InfinityEngine-Enhancer.dll"
            runtime.write_bytes(b"runtime")
            runtime_ini = game / "InfinityEngine-Enhancer.ini"
            runtime_ini.write_bytes(b"ini")
            registry = game / "iee-assets" / "creature-sprites" / "CreatureSprites-XN.registry"
            registry.parent.mkdir(parents=True)
            registry.write_bytes(b"xn")
            legacy_registry = registry.with_name("CreatureSprites-X2.registry")
            registry_set = registry.with_name("CreatureSprites-XN.set")

            def target_state(path: Path, present: bool) -> dict[str, object]:
                return {
                    "relative_path": path.relative_to(game).as_posix(),
                    "installed_present": present,
                    "installed_sha256": (
                        pipeline.sha256_file(path) if present else None
                    ),
                }

            job = {
                "job_id": "qa-xn",
                "animation": {
                    "id": "0x6110",
                    "bam_prefix": "TEST",
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                },
                "paths": {"game_root": str(game), "run_dir": str(run)},
                "upscale": pipeline.direct_upscale_contract(2).method,
            }
            state = {
                "schema": pipeline.XN_INSTALL_STATE_SCHEMA,
                "installed_at_utc": "2026-08-25T18:00:00+00:00",
                "game_root": str(game),
                "registry_layout": "monolith",
                "registry_relative_path": target_state(registry, True)[
                    "relative_path"
                ],
                "registry_magic": "IEECSXN",
                "registry_version": 3,
                "registry_scale": 2,
                "registry_set_magic": None,
                "registry_set_version": None,
                "registry_shard_count": 0,
                "source_pack_sha256": pipeline.sha256_file(registry),
                "source_shards": [],
                "targets": [
                    target_state(runtime, True),
                    target_state(runtime_ini, True),
                    target_state(registry, True),
                    target_state(legacy_registry, False),
                    target_state(registry_set, False),
                ],
            }
            pipeline.write_json(pipeline.active_state_path(job), state)
            log_template = """[2026-08-25 20:00:00] Creature sprite {ready_kind} pack ready: animation 0x6110, scale=x{scale}, 1 resources, 1 frames, 4 index bytes; source={source}; filter=NEAREST; registry budget=128 MiB
[2026-08-25 20:00:01] Creature sprite xN owner scope installed: Character::Render
[2026-08-25 20:00:02] Creature sprite animation 0x6110 reached CGameAnimationTypeCharacter::Render
[2026-08-25 20:00:03] Creature sprite xBR2x uses an owner-scoped CVidPalette::Realize snapshot
[2026-08-25 20:00:04] Composing creature sprite TESTA1 frame 000 via transient replacement id 42 (NEAREST, delete-pending after queued draw)
"""
            log = game / "InfinityEngine-Enhancer.log"
            log.write_text(
                log_template.format(
                    ready_kind="xBR2x",
                    scale=2,
                    source="CreatureSprites-X2.registry",
                ),
                encoding="utf-8",
            )
            wrong_source = pipeline.qa_log_report(job, write_report=False)
            self.assertFalse(wrong_source["pack_ready"])
            self.assertFalse(wrong_source["technical_pass"])
            log.write_text(
                log_template.format(
                    ready_kind="xBR2x",
                    scale=2,
                    source="CreatureSprites-XN.registry",
                ),
                encoding="utf-8",
            )
            valid = pipeline.qa_log_report(job, write_report=False)
            self.assertTrue(valid["pack_ready"])
            self.assertTrue(valid["installed_files_match"])
            self.assertTrue(valid["technical_pass"])
            state["registry_layout"] = "set"
            pipeline.write_json(pipeline.active_state_path(job), state)
            log.write_text(
                log_template.format(
                    ready_kind="xBR2x",
                    scale=2,
                    source="CreatureSprites-XN.set",
                ),
                encoding="utf-8",
            )
            incomplete_set = pipeline.qa_log_report(job, write_report=False)
            self.assertTrue(incomplete_set["pack_ready"])
            self.assertFalse(incomplete_set["installed_files_match"])
            self.assertFalse(incomplete_set["technical_pass"])

            registry.unlink()
            registry_set.write_bytes(b"set")
            shard = registry.with_name("CreatureSprites-XN-0000.registry")
            shard.write_bytes(b"shard")
            shard_relative = shard.relative_to(game).as_posix()
            state.update(
                {
                    "registry_relative_path": registry_set.relative_to(game).as_posix(),
                    "registry_set_magic": "IEECSNS",
                    "registry_set_version": 1,
                    "registry_shard_count": 1,
                    "source_pack_sha256": pipeline.sha256_file(registry_set),
                    "source_shards": [
                        {
                            "index": 0,
                            "relative_path": shard_relative,
                            "sha256": pipeline.sha256_file(shard),
                            "crc32": pipeline.crc32_file(shard),
                        }
                    ],
                    "targets": [
                        target_state(runtime, True),
                        target_state(runtime_ini, True),
                        target_state(registry, False),
                        target_state(legacy_registry, False),
                        target_state(registry_set, True),
                        target_state(shard, True),
                    ],
                }
            )
            pipeline.write_json(pipeline.active_state_path(job), state)
            valid_set = pipeline.qa_log_report(job, write_report=False)
            self.assertTrue(valid_set["pack_ready"])
            self.assertEqual(valid_set["registry_layout"], "set")
            self.assertTrue(valid_set["installed_files_match"])
            self.assertTrue(valid_set["technical_pass"])

            job["upscale"] = pipeline.direct_upscale_contract(4).method
            state["registry_scale"] = 4
            pipeline.write_json(pipeline.active_state_path(job), state)
            log.write_text(
                log_template.format(
                    ready_kind="xBR",
                    scale=4,
                    source="CreatureSprites-XN.set",
                ),
                encoding="utf-8",
            )
            current_x4_set = pipeline.qa_log_report(job, write_report=False)
            self.assertTrue(current_x4_set["pack_ready"])
            self.assertTrue(current_x4_set["technical_pass"])
            shard.write_bytes(b"changed")
            changed = pipeline.qa_log_report(job, write_report=False)
            self.assertFalse(changed["installed_files_match"])
            self.assertFalse(changed["technical_pass"])

    def test_character_identity_accepts_native_ini_body_family(self) -> None:
        class FakeIndex:
            def resource_map(self, resource_type: int):
                if resource_type == pipeline.INI_TYPE:
                    return {"6110": ("6110", resource_type, 1)}
                if resource_type == pipeline.IDS_TYPE:
                    return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                if resource_type == pipeline.BAM_TYPE:
                    resources = {
                        f"CHFB1{suffix}": (f"CHFB1{suffix}", resource_type, 3)
                        for suffix in pipeline.CHARACTER_BODY_SUFFIXES
                    }
                    resources["CHFB1INV"] = ("CHFB1INV", resource_type, 4)
                    return resources
                return {}

            def resolve(self, entry):
                if entry[0] == "ANIMATE":
                    return b"IDS V1.0\n0x6110 FIGHTER_FEMALE_HUMAN\n", "data/Default.bif"
                return (
                    b"[general]\nanimation_type=6000\n[character]\n"
                    b"armor_max_code=4\nsplit_bams=1\nresref=CHFB\n"
                    b"resref_paperdoll=CHFF\n"
                    b"resref_armor_base=B\nresref_armor_specific=F\n",
                    "data/Patch2.bif",
                )

        job = {
            "animation": {
                "id": "0x6110",
                "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                "armor_code": 1,
                "bam_prefix": "CHFB1",
                "runtime_profile": "character-bg2ee-2.7.3.0",
            }
        }
        result = pipeline.verify_character_animation_identity(job, FakeIndex())
        self.assertEqual(result["body_resref"], "CHFB")
        self.assertEqual(result["armor_code"], 1)
        self.assertEqual(result["ids_symbol"], "FIGHTER_FEMALE_HUMAN")
        self.assertEqual(result["bam_prefix"], "CHFB1")
        self.assertEqual(result["resource_count"], 23)

    def test_legacy_character_job_defaults_to_body_layer(self) -> None:
        job = {"animation": {"armor_code": 1}}
        self.assertEqual(pipeline.character_layer_config(job), {"kind": "body"})

    @staticmethod
    def equipment_index(item_resref: str, item_type: int, animation_code: str):
        body_resources = {
            f"CHFB1{suffix}": (f"CHFB1{suffix}", pipeline.BAM_TYPE, 3)
            for suffix in pipeline.CHARACTER_BODY_SUFFIXES
        }
        equipment_suffixes = {
            "J6": ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "CA", "G1", "SA", "SS", "SX"),
            "C0": ("A1", "A3", "A5", "G1", "SS"),
            "C4": ("A1", "A3", "A5", "G1", "SS"),
            "AX": ("A1", "A3", "A5", "A7", "A8", "A9", "G1", "OA7", "OA8", "OA9", "OG1"),
        }[animation_code]
        equipment_resources = {
            f"WQN{animation_code}{suffix}": (
                f"WQN{animation_code}{suffix}",
                pipeline.BAM_TYPE,
                4,
            )
            for suffix in equipment_suffixes
        }
        equipment_resources[f"WQN{animation_code}INV"] = (
            f"WQN{animation_code}INV",
            pipeline.BAM_TYPE,
            6,
        )
        item = bytearray(0x24)
        item[:8] = b"ITM V1  "
        struct.pack_into("<H", item, 0x1C, item_type)
        item[0x22:0x24] = animation_code.encode("ascii")

        class FakeIndex:
            def resource_map(self, resource_type: int):
                if resource_type == pipeline.INI_TYPE:
                    return {"6110": ("6110", resource_type, 1)}
                if resource_type == pipeline.IDS_TYPE:
                    return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                if resource_type == pipeline.ITM_TYPE:
                    return {item_resref: (item_resref, resource_type, 5)}
                if resource_type == pipeline.BAM_TYPE:
                    return {**body_resources, **equipment_resources}
                return {}

            def resolve(self, entry):
                if entry[0] == "ANIMATE":
                    return b"IDS V1.0\n0x6110 FIGHTER_FEMALE_HUMAN\n", "data/Default.bif"
                if entry[0] == "6110":
                    return (
                        b"[general]\nanimation_type=6000\n[character]\n"
                        b"armor_max_code=4\nsplit_bams=1\nresref=CHFB\n"
                        b"resref_armor_base=B\nresref_armor_specific=F\n"
                        b"height_code=WQN\nheight_code_helmet=WQN\n",
                        "data/Patch2.bif",
                    )
                if entry[0] == item_resref:
                    return bytes(item), "data/Items.bif"
                raise AssertionError(entry)

        return FakeIndex()

    def test_character_helmet_identity_comes_from_stock_itm_and_height_code(self) -> None:
        result = pipeline.character_equipment_spec(
            self.equipment_index("HELM01", 7, "J6"), 0x6110, "helmet", "HELM01"
        )
        self.assertEqual(result["bam_prefix"], "WQNJ6")
        self.assertEqual(result["item_animation_code"], "J6")
        self.assertEqual(result["equipment_height_code"], "WQN")
        self.assertEqual(result["resource_count"], 14)
        self.assertNotIn("WQNJ6INV", result["resources"])
        self.assertEqual(result["resources"][0], "WQNJ6A1")
        self.assertEqual(result["resources"][-1], "WQNJ6SX")

    def test_character_shield_identity_falls_back_to_general_height_code(self) -> None:
        for item_resref, animation_code in (("SHLD01", "C0"), ("SHLD08", "C4")):
            with self.subTest(item_resref=item_resref):
                result = pipeline.character_equipment_spec(
                    self.equipment_index(item_resref, 12, animation_code),
                    0x6110,
                    "shield",
                    item_resref,
                )
                self.assertEqual(result["bam_prefix"], f"WQN{animation_code}")
                self.assertEqual(result["equipment_height_code"], "WQN")
                self.assertEqual(result["resource_count"], 5)

    def test_character_weapon_identity_includes_offhand_bams(self) -> None:
        result = pipeline.character_equipment_spec(
            self.equipment_index("AX1H01", 25, "AX"),
            0x6110,
            "weapon",
            "AX1H01",
        )
        self.assertEqual(result["bam_prefix"], "WQNAX")
        self.assertEqual(result["resource_count"], 11)
        self.assertEqual(
            result["resources"][-4:],
            ["WQNAXOA7", "WQNAXOA8", "WQNAXOA9", "WQNAXOG1"],
        )

    def test_character_equipment_rejects_wrong_item_category(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "is not a helmet"):
            pipeline.character_equipment_spec(
                self.equipment_index("HELM01", 12, "J6"),
                0x6110,
                "helmet",
                "HELM01",
            )

    def test_character_equipment_job_rejects_declared_prefix_mismatch(self) -> None:
        job = {
            "animation": {
                "id": "0x6110",
                "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                "layer": {"kind": "helmet", "item_resref": "HELM01"},
                "bam_prefix": "WQNC0",
                "runtime_profile": "character-bg2ee-2.7.3.0",
            }
        }
        with self.assertRaisesRegex(RuntimeError, "resolves to BAM prefix WQNJ6"):
            pipeline.verify_character_animation_identity(
                job, self.equipment_index("HELM01", 7, "J6")
            )

    def test_character_max_armor_uses_specific_body_resref(self) -> None:
        class FakeIndex:
            def resource_map(self, resource_type: int):
                if resource_type == pipeline.INI_TYPE:
                    return {"6110": ("6110", resource_type, 1)}
                if resource_type == pipeline.IDS_TYPE:
                    return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                if resource_type == pipeline.BAM_TYPE:
                    return {
                        f"CHFF4{suffix}": (f"CHFF4{suffix}", resource_type, 3)
                        for suffix in pipeline.CHARACTER_BODY_SUFFIXES
                    }
                return {}

            def resolve(self, entry):
                if entry[0] == "ANIMATE":
                    return b"IDS V1.0\n0x6110 FIGHTER_FEMALE_HUMAN\n", "data/Default.bif"
                return (
                    b"[general]\nanimation_type=6000\n[character]\n"
                    b"armor_max_code=4\nsplit_bams=1\nresref=CHFB\n"
                    b"resref_armor_base=B\nresref_armor_specific=F\n",
                    "data/Patch2.bif",
                )

        result = pipeline.character_animation_spec(FakeIndex(), 0x6110, 4)
        self.assertEqual(result["base_body_resref"], "CHFB")
        self.assertEqual(result["body_resref"], "CHFF")
        self.assertEqual(result["bam_prefix"], "CHFF4")
        self.assertEqual(result["resource_count"], 23)

    def test_character_max_armor_resolution_matrix(self) -> None:
        cases = (
            (0x6110, "FIGHTER_FEMALE_HUMAN", "CHFB", "B", "F", "CHFF4"),
            (0x6010, "CLERIC_FEMALE_HUMAN", "CHFB", "B", "C", "CHFC4"),
            (0x6310, "THIEF_FEMALE_HUMAN", "CHFT", "T", "T", "CHFT4"),
        )

        for animation_id, symbol, base, armor_base, specific, expected in cases:
            class FakeIndex:
                def resource_map(self, resource_type: int):
                    if resource_type == pipeline.INI_TYPE:
                        name = f"{animation_id:04X}"
                        return {name: (name, resource_type, 1)}
                    if resource_type == pipeline.IDS_TYPE:
                        return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                    if resource_type == pipeline.BAM_TYPE:
                        return {
                            f"{expected}{suffix}": (f"{expected}{suffix}", resource_type, 3)
                            for suffix in pipeline.CHARACTER_BODY_SUFFIXES
                        }
                    return {}

                def resolve(self, entry):
                    if entry[0] == "ANIMATE":
                        return (
                            f"IDS V1.0\n0x{animation_id:04X} {symbol}\n".encode("ascii"),
                            "data/Default.bif",
                        )
                    ini = (
                        f"[general]\nanimation_type={animation_id & 0xF000:04X}\n"
                        f"[character]\narmor_max_code=4\nsplit_bams=1\n"
                        f"resref={base}\nresref_armor_base={armor_base}\n"
                        f"resref_armor_specific={specific}\n"
                    )
                    return ini.encode("ascii"), "data/Patch2.bif"

            with self.subTest(animation_id=animation_id):
                result = pipeline.character_animation_spec(FakeIndex(), animation_id, 4)
                self.assertEqual(result["bam_prefix"], expected)

    def test_character_identity_rejects_thief_id_with_fighter_bams(self) -> None:
        class FakeIndex:
            def resource_map(self, resource_type: int):
                if resource_type == pipeline.INI_TYPE:
                    return {"6310": ("6310", resource_type, 1)}
                if resource_type == pipeline.IDS_TYPE:
                    return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                if resource_type == pipeline.BAM_TYPE:
                    return {
                        f"CHFT1{suffix}": (f"CHFT1{suffix}", resource_type, 3)
                        for suffix in pipeline.CHARACTER_BODY_SUFFIXES
                    }
                return {}

            def resolve(self, entry):
                if entry[0] == "ANIMATE":
                    return b"IDS V1.0\n0x6310 THIEF_FEMALE_HUMAN\n", "data/Default.bif"
                return (
                    b"[general]\nanimation_type=6000\n[character]\n"
                    b"armor_max_code=4\nsplit_bams=1\nresref=CHFT\n"
                    b"resref_armor_base=T\nresref_armor_specific=T\n",
                    "data/Patch2.bif",
                )

        job = {
            "animation": {
                "id": "0x6310",
                "ids_symbol": "THIEF_FEMALE_HUMAN",
                "armor_code": 1,
                "bam_prefix": "CHFB1",
                "runtime_profile": "character-bg2ee-2.7.3.0",
            }
        }
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            pipeline.verify_character_animation_identity(job, FakeIndex())

    def test_animation_symbol_resolves_exact_id(self) -> None:
        class FakeIndex:
            def resource_map(self, resource_type: int):
                return {"ANIMATE": ("ANIMATE", resource_type, 1)}

            def resolve(self, entry):
                return (
                    b"IDS V1.0\n0x6010 CLERIC_FEMALE_HUMAN\n"
                    b"0x6110 FIGHTER_FEMALE_HUMAN\n",
                    "data/Default.bif",
                )

        self.assertEqual(
            pipeline.animation_id_for_symbol(FakeIndex(), "FIGHTER_FEMALE_HUMAN"),
            0x6110,
        )

    def test_runtime_owner_labels_match_real_log_markers(self) -> None:
        self.assertEqual(
            pipeline.runtime_owner_labels("character-bg2ee-2.7.3.0"),
            ("Character::Render", "CGameAnimationTypeCharacter::Render"),
        )

    def test_runtime_health_fails_on_local_catalog_quarantine(self) -> None:
        report = pipeline.runtime_session_health(
            "Creature sprite catalog component 4 quarantined: bad shard; "
            "other validated components remain available",
            "monster-icewind-bg2ee-2.7.3.0",
            {},
        )
        self.assertEqual(report["catalog_component_quarantine_count"], 1)
        self.assertFalse(report["runtime_health_pass"])

    def test_catalog_composition_marker_is_scoped_by_animation_and_prefix(self) -> None:
        session = (
            "Composing creature sprite TESTA1 animation=0x6110 frame 000 via "
            "transient replacement id 42 (NEAREST, delete-pending after queued draw)"
        )
        self.assertEqual(
            len(pipeline.animation_composition_lines(session, "0x6110", "TEST")),
            1,
        )
        self.assertEqual(
            pipeline.animation_composition_lines(session, "0xE400", "TEST"),
            [],
        )

    def test_catalog_qa_shared_prefix_for_a_does_not_satisfy_b(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "game"
            run = root / "run"
            game.mkdir()
            state_path = run / "ingame-installation" / "active-test.json"
            pipeline.write_json(
                state_path,
                {"installed_at_utc": "2000-01-01T00:00:00+00:00"},
            )
            (game / "InfinityEngine-Enhancer.log").write_text(
                "\n".join(
                    (
                        "[2026-08-26 12:00:00.000] Creature sprite xBR catalog ready: "
                        "scale=x2, 2 animations, source=CreatureSprites-XN.catalog; "
                        "filter=NEAREST",
                        "[2026-08-26 12:00:00.100] Creature sprite owner scope installed: "
                        "Character::Render",
                        "[2026-08-26 12:00:00.200] Creature sprite owner-scoped "
                        "CVidPalette::Realize snapshot",
                        "[2026-08-26 12:00:00.300] Creature sprite catalog shard 7 "
                        "ready on demand for animation 0x6110, resref SAMEA1: "
                        "1 resources, 1024 metadata bytes",
                        "[2026-08-26 12:00:00.400] Creature sprite catalog animation "
                        "0xE400 materialized:",
                        "[2026-08-26 12:00:00.500] Creature sprite animation 0x6110 "
                        "reached CGameAnimationTypeCharacter::Render",
                        "[2026-08-26 12:00:00.600] Creature sprite animation 0xE400 "
                        "reached CGameAnimationTypeCharacter::Render",
                        "[2026-08-26 12:00:00.700] Composing creature sprite SAMEA1 "
                        "animation=0x6110 frame 000 via transient replacement id 42 "
                        "(NEAREST, delete-pending after queued draw)",
                    )
                ),
                encoding="utf-8",
            )
            job = {
                "_kind": "catalog",
                "job_id": "shared-prefix-catalog",
                "paths": {"game_root": str(game), "run_dir": str(run)},
                "upscale": pipeline.direct_upscale_contract(2).method,
                "qa": {"animations": []},
            }
            seal = {
                "active_identity_matches_job": True,
                "active_generation_is_sealed": True,
                "active_generation_seal_errors": [],
                "sealed_animation_qa_contract": [
                    {
                        "animation_id": "0x6110",
                        "runtime_profile": "character-bg2ee-2.7.3.0",
                        "bam_prefixes": ["SAME"],
                    },
                    {
                        "animation_id": "0xE400",
                        "runtime_profile": "character-bg2ee-2.7.3.0",
                        "bam_prefixes": ["SAME"],
                    },
                ],
            }
            with (
                mock.patch.object(
                    pipeline,
                    "sealed_catalog_generation_integrity",
                    return_value=seal,
                ),
                mock.patch.object(
                    pipeline,
                    "installed_state_integrity",
                    return_value={
                        "installed_files_match": True,
                        "installed_targets_checked": 1,
                        "installed_integrity_errors": [],
                    },
                ),
            ):
                report = pipeline.catalog_qa_log_report(job, write_report=False)
        animations = {
            entry["animation_id"]: entry for entry in report["animation_results"]
        }
        self.assertTrue(animations["0x6110"]["all_prefixes_composed"])
        self.assertTrue(animations["0x6110"]["payload_ready"])
        self.assertFalse(animations["0x6110"]["materialized"])
        self.assertEqual(animations["0x6110"]["on_demand_resrefs"], ["SAMEA1"])
        self.assertTrue(animations["0xE400"]["payload_ready"])
        self.assertFalse(animations["0xE400"]["all_prefixes_composed"])
        self.assertEqual(report["composition_count"], 1)
        self.assertFalse(report["technical_pass"])

    def test_catalog_qa_requires_declared_representatives_not_every_character_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "game"
            run = root / "run"
            game.mkdir()
            pipeline.write_json(
                run / "ingame-installation" / "active-test.json",
                {"installed_at_utc": "2000-01-01T00:00:00+00:00"},
            )
            (game / "InfinityEngine-Enhancer.log").write_text(
                "\n".join(
                    (
                        "[2026-08-26 12:00:00.000] Creature sprite xBR catalog ready: "
                        "scale=x2, 1 animations, source=CreatureSprites-XN.catalog; filter=NEAREST",
                        "[2026-08-26 12:00:00.100] Creature sprite owner scope installed: Character::Render",
                        "[2026-08-26 12:00:00.200] Creature sprite owner-scoped CVidPalette::Realize snapshot",
                        "[2026-08-26 12:00:00.300] Creature sprite catalog shard 7 ready on demand "
                        "for animation 0x6110, resref CHFB1G17: 1 resources, 1024 metadata bytes",
                        "[2026-08-26 12:00:00.400] Creature sprite animation 0x6110 reached "
                        "CGameAnimationTypeCharacter::Render",
                        "[2026-08-26 12:00:00.500] Composing creature sprite CHFB1 animation=0x6110 "
                        "frame 000 via transient replacement id 42 "
                        "(NEAREST, delete-pending after queued draw)",
                    )
                ),
                encoding="utf-8",
            )
            job = {
                "_kind": "catalog",
                "job_id": "representative-catalog",
                "paths": {"game_root": str(game), "run_dir": str(run)},
                "upscale": pipeline.direct_upscale_contract(2).method,
                "qa": {"animations": []},
            }
            seal = {
                "active_identity_matches_job": True,
                "active_generation_is_sealed": True,
                "active_generation_seal_errors": [],
                "sealed_animation_qa_contract": [
                    {
                        "animation_id": "0x6110",
                        "runtime_profile": "character-bg2ee-2.7.3.0",
                        "bam_prefixes": ["CHFB1", "WQNJ6"],
                        "required_bam_prefixes": ["CHFB1"],
                    }
                ],
            }
            with (
                mock.patch.object(
                    pipeline, "sealed_catalog_generation_integrity", return_value=seal
                ),
                mock.patch.object(
                    pipeline,
                    "installed_state_integrity",
                    return_value={
                        "installed_files_match": True,
                        "installed_targets_checked": 1,
                        "installed_integrity_errors": [],
                    },
                ),
            ):
                report = pipeline.catalog_qa_log_report(job, write_report=False)
        animation = report["animation_results"][0]
        self.assertFalse(animation["all_prefixes_composed"])
        self.assertTrue(animation["required_prefixes_composed"])
        self.assertTrue(report["technical_pass"])

    def test_runtime_log_session_must_be_exact_and_post_install(self) -> None:
        text = "\n".join(
            (
                "[2026-08-25 00:10:00.000] Creature sprite xBR2x pack ready: animation 0x6310, old",
                "[2026-08-25 00:20:00.000] Creature sprite xBR2x pack ready: animation 0x6110, stale",
                "[2026-08-25 00:30:00.000] Creature sprite xBR2x pack ready: animation 0x6110, historical",
                "[2026-08-25 00:31:00.000] Creature sprite xBR pack ready: animation 0x6110, current",
                "[2026-08-25 00:31:01.000] Composing creature sprite CHFB1A1 frame 000",
            )
        )
        session = pipeline.runtime_log_session_after_install(
            text,
            (
                "Creature sprite xBR pack ready: animation 0x6110,",
                "Creature sprite xBR2x pack ready: animation 0x6110,",
            ),
            "2026-08-24T22:25:00+00:00",
        )
        self.assertIn("current", session)
        self.assertNotIn("stale", session)
        self.assertNotIn("historical", session)
        self.assertNotIn("0x6310", session)

    @staticmethod
    def registry_bytes(
        version: int,
        metadata: int,
        *,
        scale: int = 2,
        magic: bytes = pipeline.REGISTRY_MAGIC,
        resref: str = "TEST",
    ) -> bytes:
        data = bytearray(magic)
        data.extend(struct.pack("<IIII", version, scale, 1, metadata))
        data.extend(resref.encode("ascii").ljust(8, b"\0"))
        data.extend(bytes(32))
        data.extend(struct.pack("<II", 1, 1))
        index_bytes = scale * scale
        data.extend(struct.pack("<HHhhB3xI", 1, 1, 0, 0, 0, index_bytes))
        representatives = np.full(256, 0xFFFF, dtype="<u2")
        representatives[1] = 0
        data.extend(representatives.tobytes())
        data.extend(bytes([1]) * index_bytes)
        data.extend(struct.pack("<II", 1, 0))
        return bytes(data)

    def test_registry_v2_carries_animation_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry"
            path.write_bytes(self.registry_bytes(2, 0xE400))
            info = pipeline.inspect_registry(path)
        self.assertEqual(info["version"], 2)
        self.assertEqual(info["scale"], 2)
        self.assertEqual(info["registry_magic"], "IEECSX2")
        self.assertEqual(info["animation_id"], "0xE400")
        self.assertEqual(info["frame_count"], 1)
        self.assertEqual(info["resources"], ["TEST"])

    def test_registry_v3_carries_explicit_x4_scale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry"
            path.write_bytes(
                self.registry_bytes(
                    3, 0x6110, scale=4, magic=pipeline.XN_REGISTRY_MAGIC
                )
            )
            info = pipeline.inspect_registry(path)
        self.assertEqual(info["version"], 3)
        self.assertEqual(info["scale"], 4)
        self.assertEqual(info["registry_magic"], "IEECSXN")
        self.assertEqual(info["animation_id"], "0x6110")
        self.assertEqual(info["index_bytes"], 16)

    def test_creature_sprite_installers_accept_repeated_ini_sections(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for the INI helper test")
        quote = lambda value: str(value).replace("'", "''")
        for script_name in (
            "Install-CreatureSprite-X2-Test.ps1",
            "Install-CreatureSprite-XN-Test.ps1",
        ):
            with self.subTest(script=script_name):
                install_script = ROOT / "pipeline" / "scripts" / script_name
                command = f"""
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
  '{quote(install_script)}', [ref]$tokens, [ref]$errors)
foreach ($name in @('Set-IniKey','Get-IniKey')) {{
  $fn = $ast.FindAll({{ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq $name
  }}, $true) | Select-Object -First 1
  Invoke-Expression $fn.Extent.Text
}}
$fixture = [string]::Join("`r`n", @(
  '; preserved preamble',
  '[Shaders]',
  'KeepFirst = one',
  '[Rendering]',
  'KeepRendering = yes',
  '[shaders]',
  'EnableCreatureSpriteUpscaleTest = false',
  'KeepSecond = two',
  ''
))
$updated = Set-IniKey $fixture 'Shaders' 'EnableCreatureSpriteUpscaleTest' 'true'
$updated = Set-IniKey $updated 'Shaders' 'EnableCreatureSpriteX2Test' 'false'
$duplicateRejected = $false
try {{
  [void](Set-IniKey ([string]::Join("`n", @(
    '[Shaders]',
    'EnableCreatureSpriteX2Test = true',
    '[Shaders]',
    'EnableCreatureSpriteX2Test = false'
  ))) 'Shaders' 'EnableCreatureSpriteX2Test' 'false')
}}
catch {{
  $duplicateRejected = $_.Exception.Message -like 'Clé INI dupliquée*'
}}
[pscustomobject]@{{
  text = $updated
  upscale = Get-IniKey $updated 'Shaders' 'EnableCreatureSpriteUpscaleTest'
  alias = Get-IniKey $updated 'Shaders' 'EnableCreatureSpriteX2Test'
  duplicate_rejected = $duplicateRejected
}} | ConvertTo-Json -Compress
"""
                completed = subprocess.run(
                    [powershell, "-NoProfile", "-Command", command],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                parsed = json.loads(completed.stdout)
                updated = parsed["text"]
                self.assertEqual(parsed["upscale"], "true")
                self.assertEqual(parsed["alias"], "false")
                self.assertTrue(parsed["duplicate_rejected"])
                self.assertEqual(
                    len(re.findall(r"(?im)^\s*\[shaders\]\s*$", updated)), 2
                )
                self.assertEqual(
                    len(
                        re.findall(
                            r"(?im)^\s*EnableCreatureSpriteUpscaleTest\s*=", updated
                        )
                    ),
                    1,
                )
                self.assertEqual(
                    len(
                        re.findall(
                            r"(?im)^\s*EnableCreatureSpriteX2Test\s*=", updated
                        )
                    ),
                    1,
                )
                self.assertIn("KeepFirst = one", updated)
                self.assertIn("KeepRendering = yes", updated)
                self.assertIn("KeepSecond = two", updated)
                self.assertNotIn("\n", updated.replace("\r\n", ""))

    def test_xn_installer_scans_v3_payload_bytes(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for the XN installer parser test")
        install_script = ROOT / "pipeline" / "scripts" / "Install-CreatureSprite-XN-Test.ps1"
        with tempfile.TemporaryDirectory() as temporary:
            registry = Path(temporary) / "CreatureSprites-XN.registry"
            registry.write_bytes(
                self.registry_bytes(
                    3, 0x6110, scale=4, magic=pipeline.XN_REGISTRY_MAGIC
                )
            )
            quote = lambda value: str(value).replace("'", "''")
            command = f"""
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
  '{quote(install_script)}', [ref]$tokens, [ref]$errors)
foreach ($name in @('Get-MaxRegistryBytes','Get-MaxLazyFrameIndexBytes','Read-ExactBytes','Skip-RegistryBytes','Read-RegistryHeader')) {{
  $fn = $ast.FindAll({{ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq $name
  }}, $true) | Select-Object -First 1
  Invoke-Expression $fn.Extent.Text
}}
Read-RegistryHeader '{quote(registry)}' | ConvertTo-Json -Compress
"""
            completed = subprocess.run(
                [powershell, "-NoProfile", "-Command", command],
                check=True,
                capture_output=True,
                text=True,
            )
        info = json.loads(completed.stdout)
        self.assertEqual(info["magic"], "IEECSXN")
        self.assertEqual(info["scale"], 4)
        self.assertEqual(info["index_bytes"], 16)

    def test_xn_installer_reads_generated_registry_set_and_crc32(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for the XN registry-set parser test")
        install_script = ROOT / "pipeline" / "scripts" / "Install-CreatureSprite-XN-Test.ps1"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            member = root / "member.registry"
            member.write_bytes(self.registry_bytes(2, 0x6110, resref="RESA"))
            records = pipeline.inspect_registry(
                member, include_resource_records=True
            )["resource_records"]
            shard_path = root / pipeline.XN_REGISTRY_SHARD_FILENAME.format(index=0)
            shard_info = pipeline.write_registry_records(
                shard_path,
                pipeline.XN_REGISTRY_MAGIC,
                pipeline.XN_REGISTRY_VERSION,
                2,
                0x6110,
                records,
            )
            shard_info["path"] = shard_path
            set_path = root / pipeline.XN_REGISTRY_SET_FILENAME
            expected = pipeline.write_registry_set_index(
                set_path, 2, 0x6110, [shard_info]
            )
            expected_crc32 = pipeline.crc32_file(shard_path)
            quote = lambda value: str(value).replace("'", "''")
            command = f"""
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
  '{quote(install_script)}', [ref]$tokens, [ref]$errors)
foreach ($name in @('Get-MaxRegistryBytes','Read-ExactBytes','Get-Crc32','Read-RegistrySet')) {{
  $fn = $ast.FindAll({{ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq $name
  }}, $true) | Select-Object -First 1
  Invoke-Expression $fn.Extent.Text
}}
$setInfo = Read-RegistrySet '{quote(set_path)}'
[pscustomobject]@{{
  set = $setInfo
  shard_crc32 = [uint64](Get-Crc32 '{quote(shard_path)}')
}} | ConvertTo-Json -Depth 6 -Compress
"""
            completed = subprocess.run(
                [powershell, "-NoProfile", "-Command", command],
                check=True,
                capture_output=True,
                text=True,
            )
        parsed = json.loads(completed.stdout)
        info = parsed["set"]
        self.assertEqual(info["magic"], "IEECSNS")
        self.assertEqual(info["version"], 1)
        self.assertEqual(info["scale"], 2)
        self.assertEqual(info["shard_count"], 1)
        self.assertEqual(info["total_resources"], expected["total_resources"])
        self.assertEqual(info["total_frames"], expected["total_frames"])
        self.assertEqual(info["total_index_bytes"], expected["total_index_bytes"])
        self.assertEqual(info["total_registry_bytes"], expected["total_registry_bytes"])
        self.assertEqual(parsed["shard_crc32"], expected_crc32)
        self.assertEqual(info["entries"][0]["sha256"], shard_info["sha256"])

    def test_xn_registry_set_install_restore_is_transactional_in_fake_game(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for the XN install/restore test")
        temporary_parent = ROOT / "temp"
        temporary_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="xn-install-e2e-", dir=temporary_parent
        ) as temporary:
            workspace = Path(temporary)
            script_root = workspace / "pipeline" / "scripts"
            script_root.mkdir(parents=True)
            install_script = script_root / "Install-CreatureSprite-XN-Test.ps1"
            restore_script = script_root / "Restore-CreatureSprite-XN-Test.ps1"
            shutil.copy2(
                ROOT / "pipeline" / "scripts" / install_script.name,
                install_script,
            )
            shutil.copy2(
                ROOT / "pipeline" / "scripts" / restore_script.name,
                restore_script,
            )
            adapter = script_root / "xbr2x_batch.js"
            shutil.copy2(
                ROOT / "pipeline" / "scripts" / adapter.name,
                adapter,
            )

            engine_source = workspace / "engine-source"
            engine_files = (
                "CMakeLists.txt",
                "src/iee/hooks.cpp",
                "src/iee/native_occlusion_bridge.cpp",
                "src/iee/native_occlusion_bridge.h",
                "src/iee/dll_main.cpp",
                "src/iee/bridge_transition.cpp",
                "src/iee/bridge_transition.h",
                "src/iee/creature_sprite_x2.cpp",
                "src/iee/creature_sprite_x2.h",
                "src/iee/core/config.cpp",
                "src/iee/core/config.h",
                "src/iee/core/native_occlusion_probe.cpp",
                "src/iee/core/native_occlusion_probe.h",
                "src/iee/game/build_manifest.cpp",
                "src/iee/game/build_manifest.h",
                "tests/iee_tests.cpp",
                "tests/bridge_worker_lifecycle_tests.cpp",
            )
            for index, relative in enumerate(engine_files):
                path = engine_source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"contract-{index}\n", encoding="utf-8")

            run_root = workspace / "sprite" / "e2e" / "runs" / "xn-set"
            pack_root = run_root / "build" / "iee-assets" / "creature-sprites"
            pack_root.mkdir(parents=True)
            source_records = []
            member_root = workspace / "members"
            member_root.mkdir()
            for resref in ("RESA", "RESB"):
                member = member_root / f"{resref}.registry"
                member.write_bytes(
                    self.registry_bytes(
                        3,
                        0x6110,
                        scale=2,
                        magic=pipeline.XN_REGISTRY_MAGIC,
                        resref=resref,
                    )
                )
                source_records.extend(
                    pipeline.inspect_registry(
                        member, include_resource_records=True
                    )["resource_records"]
                )
            shard_infos = []
            for index, record in enumerate(source_records):
                shard_path = pack_root / pipeline.XN_REGISTRY_SHARD_FILENAME.format(
                    index=index
                )
                shard_info = pipeline.write_registry_records(
                    shard_path,
                    pipeline.XN_REGISTRY_MAGIC,
                    pipeline.XN_REGISTRY_VERSION,
                    2,
                    0x6110,
                    [record],
                )
                shard_info["path"] = shard_path
                shard_infos.append(shard_info)
            set_path = pack_root / pipeline.XN_REGISTRY_SET_FILENAME
            set_info = pipeline.write_registry_set_index(
                set_path, 2, 0x6110, shard_infos
            )

            job_id = "xn-set-install-e2e"
            method = pipeline.direct_upscale_contract(2).method
            scalepix = workspace / "scalepix.html"
            scalepix.write_bytes(b"fixture-scalepix")
            member_records = []
            member_jobs_root = workspace / "sprite" / "jobs"
            member_jobs_root.mkdir(parents=True)
            for index, prefix in enumerate(("RESA", "RESB")):
                member_id = f"xn-set-member-{index}"
                member_run = workspace / "sprite" / "members" / member_id
                member_source_root = workspace / "sprite" / "member-sources" / member_id
                member_source = member_source_root / "manifest.json"
                pipeline.write_json(
                    member_source,
                    {"schema": pipeline.SOURCE_SCHEMA, "member": member_id},
                )
                member_build = member_run / "build" / "build-manifest.json"
                pipeline.write_json(
                    member_build,
                    {
                        "source_manifest": str(member_source),
                        "source_manifest_sha256": pipeline.sha256_file(
                            member_source
                        ),
                        "scalepix_sha256": pipeline.sha256_file(scalepix),
                        "xbr_adapter_sha256": pipeline.sha256_file(adapter),
                    },
                )
                member_job = member_jobs_root / f"{member_id}.json"
                pipeline.write_json(
                    member_job,
                    {
                        "schema": pipeline.JOB_SCHEMA,
                        "job_id": member_id,
                        "animation": {"bam_prefix": prefix},
                        "upscale": method,
                        "paths": {
                            "source_dir": str(member_source_root),
                            "run_dir": str(member_run),
                            "scalepix": str(scalepix),
                        },
                    },
                )
                member_records.append(
                    {
                        "job_file": str(member_job),
                        "job_id": member_id,
                        "bam_prefix": prefix,
                        "source_manifest_sha256": pipeline.sha256_file(
                            member_source
                        ),
                        "build_manifest_sha256": pipeline.sha256_file(
                            member_build
                        ),
                    }
                )
            pipeline.write_json(
                run_root / "build" / "build-manifest.json",
                {
                    "schema": pipeline.ARMOR_SET_BUILD_SCHEMA,
                    "status": "built-pending-ingame-qa",
                    "job_id": job_id,
                    "animation_id": "0x6110",
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                    "registry_version": 3,
                    "registry_magic": "IEECSXN",
                    "registry_scale": 2,
                    "method": method,
                    "resource_count": set_info["resource_count"],
                    "frame_count": set_info["frame_count"],
                    "x2_index_bytes": set_info["index_bytes"],
                    "registry_layout": "set",
                    "registry": None,
                    "registry_bytes": set_info["registry_bytes"],
                    "registry_sha256": None,
                    "registry_set": (
                        "iee-assets/creature-sprites/CreatureSprites-XN.set"
                    ),
                    "registry_set_sha256": set_info["sha256"],
                    "registry_set_bytes": set_info["registry_set_bytes"],
                    "shards": pipeline.registry_set_manifest_shards(set_info),
                    "total_resources": set_info["resource_count"],
                    "total_frames": set_info["frame_count"],
                    "total_index_bytes": set_info["index_bytes"],
                    "total_registry_bytes": set_info["registry_bytes"],
                    "bam_prefixes": ["RESA", "RESB"],
                    "members": member_records,
                    "source_registry_formats": [
                        {
                            "registry_magic": "IEECSXN",
                            "registry_version": 3,
                            "scale": 2,
                        }
                    ],
                    "promoted_to_xn": False,
                    "validation": {
                        "shard_count": 2,
                        "maximum_shard_resources": pipeline.MAX_RESOURCES,
                        "maximum_shard_bytes": pipeline.maximum_registry_bytes(2),
                        "maximum_set_shards": pipeline.MAX_REGISTRY_SET_SHARDS,
                        "maximum_set_resources": pipeline.MAX_REGISTRY_SET_RESOURCES,
                        "maximum_set_frames": pipeline.MAX_REGISTRY_SET_FRAMES,
                        "maximum_set_registry_bytes": pipeline.MAX_REGISTRY_SET_BYTES,
                    },
                },
            )

            runtime_root = run_root / "runtime"
            runtime_root.mkdir(parents=True)
            source_dll = runtime_root / "InfinityEngine-Enhancer.dll"
            source_dll.write_bytes(b"new-runtime")
            pipeline.write_json(
                runtime_root / "runtime-manifest.json",
                {
                    "schema": pipeline.RUNTIME_SCHEMA,
                    "status": "built-tested",
                    "tests_status": "passed",
                    "bridge_worker_tests_status": "passed",
                    "job_id": job_id,
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                    "engine_source": str(engine_source),
                    "engine_source_contract_sha256": pipeline.source_tree_hash(
                        engine_source
                    ),
                    "dll": source_dll.name,
                    "dll_sha256": pipeline.sha256_file(source_dll),
                },
            )

            game = workspace / "fake-game"
            game_sprite_root = game / "iee-assets" / "creature-sprites"
            game_sprite_root.mkdir(parents=True)
            executable = game / "BaldurReal.exe"
            executable.write_bytes(b"fake-compatible-executable")
            original_files = {
                game / "InfinityEngine-Enhancer.dll": b"old-runtime",
                game / "InfinityEngine-Enhancer.ini": (
                    b"[Shaders]\nEnableCreatureSpriteUpscaleTest = false\n"
                    b"KeepFirstShaderSection = yes\n[Rendering]\n"
                    b"EnableAnisotropicFiltering = true\n"
                    b"EnableFullFrameFXAA = true\n"
                    b"EnableFullFrameSSAA2x = true\n[shaders]\n"
                    b"EnableCreatureSpriteX2Test = true\n"
                    b"KeepSecondShaderSection = yes\n"
                ),
                game_sprite_root / "CreatureSprites-XN.registry": b"old-monolith",
                game_sprite_root / "CreatureSprites-X2.registry": b"old-x2-fallback",
                game_sprite_root / "CreatureSprites-XN.set": b"old-set",
                game_sprite_root / "CreatureSprites-XN-0000.registry": b"old-shard-0",
                game_sprite_root / "CreatureSprites-XN-0002.registry": b"old-stale-shard",
            }
            for path, payload in original_files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
            added_shard = game_sprite_root / "CreatureSprites-XN-0001.registry"
            self.assertFalse(added_shard.exists())

            job_file = workspace / "sprite" / "jobs" / f"{job_id}.json"
            pipeline.write_json(
                job_file,
                {
                    "schema": pipeline.ARMOR_SET_SCHEMA,
                    "job_id": job_id,
                    "animation": {
                        "id": "0x6110",
                        "runtime_profile": "character-bg2ee-2.7.3.0",
                    },
                    "upscale": method,
                    "paths": {
                        "run_dir": str(run_root),
                        "game_root": str(game),
                        "engine_source": str(engine_source),
                    },
                    "compatibility": {
                        "baldur_real_sha256": pipeline.sha256_file(executable)
                    },
                },
            )

            def run_script(script: Path, *arguments: str) -> subprocess.CompletedProcess:
                completed = subprocess.run(
                    [
                        powershell,
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(script),
                        "-JobFile",
                        str(job_file),
                        *arguments,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if completed.returncode != 0:
                    self.fail(
                        f"{script.name} failed ({completed.returncode}):\n"
                        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
                    )
                return completed

            run_script(install_script)
            active_state_path = run_root / "ingame-test" / "active-test.json"
            installed_state = pipeline.read_json(active_state_path)
            self.assertEqual(installed_state["status"], "installed-pending-qa")
            self.assertTrue(
                pipeline.installed_state_integrity(installed_state, 2)[
                    "installed_files_match"
                ]
            )
            self.assertFalse((game_sprite_root / "CreatureSprites-XN.registry").exists())
            self.assertFalse(
                (game_sprite_root / "CreatureSprites-XN-0002.registry").exists()
            )
            self.assertEqual(
                (game_sprite_root / "CreatureSprites-X2.registry").read_bytes(),
                original_files[game_sprite_root / "CreatureSprites-X2.registry"],
            )
            self.assertEqual(pipeline.sha256_file(game_sprite_root / set_path.name), set_info["sha256"])
            for index, shard_info in enumerate(shard_infos):
                installed_shard = game_sprite_root / pipeline.XN_REGISTRY_SHARD_FILENAME.format(
                    index=index
                )
                self.assertEqual(pipeline.sha256_file(installed_shard), shard_info["sha256"])
            installed_ini = (game / "InfinityEngine-Enhancer.ini").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                len(re.findall(r"(?im)^\s*\[shaders\]\s*$", installed_ini)), 2
            )
            self.assertEqual(
                len(
                    re.findall(
                        r"(?im)^\s*EnableCreatureSpriteUpscaleTest\s*=\s*true\s*$",
                        installed_ini,
                    )
                ),
                1,
            )
            self.assertEqual(
                len(
                    re.findall(
                        r"(?im)^\s*EnableCreatureSpriteX2Test\s*=\s*false\s*$",
                        installed_ini,
                    )
                ),
                1,
            )
            self.assertIn("KeepFirstShaderSection = yes", installed_ini)
            self.assertIn("KeepSecondShaderSection = yes", installed_ini)
            self.assertFalse(list(run_root.rglob(".*.tmp")))

            installed_state["status"] = "restoring"
            backup_state_path = (
                Path(installed_state["backup_root"]) / "install-state.json"
            )
            pipeline.write_json(active_state_path, installed_state)
            pipeline.write_json(backup_state_path, installed_state)
            run_script(restore_script, "-RecoverInterrupted")

            restored_state = pipeline.read_json(active_state_path)
            self.assertEqual(restored_state["status"], "restored")
            self.assertTrue(restored_state["recovered_interrupted_install"])
            for path, payload in original_files.items():
                self.assertEqual(path.read_bytes(), payload, path.name)
            self.assertFalse(added_shard.exists())
            self.assertFalse(list(run_root.rglob(".*.tmp")))

    def test_xn_installer_accepts_x4_set_entry_above_legacy_128_mib_cap(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for the XN registry-set cap test")
        install_script = ROOT / "pipeline" / "scripts" / "Install-CreatureSprite-XN-Test.ps1"
        index_bytes = 129 * 1024 * 1024
        registry_bytes = index_bytes + pipeline.REGISTRY_HEADER_BYTES
        with tempfile.TemporaryDirectory() as temporary:
            set_path = Path(temporary) / pipeline.XN_REGISTRY_SET_FILENAME
            raw = bytearray(
                struct.pack(
                    "<8sIIIIIIQQQ",
                    pipeline.XN_REGISTRY_SET_MAGIC,
                    pipeline.XN_REGISTRY_SET_VERSION,
                    4,
                    1,
                    1,
                    0x6110,
                    0,
                    1,
                    index_bytes,
                    registry_bytes,
                )
            )
            raw.extend(
                struct.pack(
                    "<32sIIQQQ",
                    bytes(range(1, 33)),
                    0x12345678,
                    1,
                    1,
                    index_bytes,
                    registry_bytes,
                )
            )
            set_path.write_bytes(raw)
            quote = lambda value: str(value).replace("'", "''")
            command = f"""
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
  '{quote(install_script)}', [ref]$tokens, [ref]$errors)
foreach ($name in @('Get-MaxRegistryBytes','Read-ExactBytes','Read-RegistrySet')) {{
  $fn = $ast.FindAll({{ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq $name
  }}, $true) | Select-Object -First 1
  Invoke-Expression $fn.Extent.Text
}}
Read-RegistrySet '{quote(set_path)}' | ConvertTo-Json -Depth 6 -Compress
"""
            completed = subprocess.run(
                [powershell, "-NoProfile", "-Command", command],
                check=True,
                capture_output=True,
                text=True,
            )
        info = json.loads(completed.stdout)
        self.assertEqual(info["scale"], 4)
        self.assertEqual(info["total_index_bytes"], index_bytes)
        self.assertEqual(info["total_registry_bytes"], registry_bytes)
        self.assertGreater(info["entries"][0]["index_bytes"], pipeline.MAX_REGISTRY_BYTES)
        self.assertLess(
            info["entries"][0]["registry_bytes"],
            pipeline.maximum_registry_bytes(4),
        )

    def test_registry_inspector_matches_runtime_strictness(self) -> None:
        base = self.registry_bytes(
            3, 0x6110, scale=4, magic=pipeline.XN_REGISTRY_MAGIC
        )
        frame_offset = pipeline.REGISTRY_HEADER_BYTES + pipeline.REGISTRY_RESOURCE_HEADER_BYTES
        mutations: list[tuple[str, bytearray]] = []
        zero_width = bytearray(base)
        struct.pack_into("<H", zero_width, frame_offset, 0)
        mutations.append(("frame header", zero_width))
        reserved = bytearray(base)
        reserved[frame_offset + 9] = 1
        mutations.append(("frame header", reserved))
        oversized_cycle = bytearray(base)
        struct.pack_into("<I", oversized_cycle, len(oversized_cycle) - 8, 65537)
        mutations.append(("cycle slot", oversized_cycle))
        duplicate = bytearray(base)
        struct.pack_into("<I", duplicate, 16, 2)
        duplicate.extend(base[pipeline.REGISTRY_HEADER_BYTES :])
        mutations.append(("duplicate", duplicate))
        for message, raw in mutations:
            with self.subTest(message=message):
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary) / "registry"
                    path.write_bytes(raw)
                    with self.assertRaisesRegex(RuntimeError, message):
                        pipeline.inspect_registry(path)

    def test_registry_rejects_crossed_magic_and_version(self) -> None:
        cases = (
            (pipeline.REGISTRY_MAGIC, 3, 4),
            (pipeline.XN_REGISTRY_MAGIC, 2, 2),
        )
        for magic, version, scale in cases:
            with self.subTest(magic=magic, version=version, scale=scale):
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary) / "registry"
                    path.write_bytes(
                        self.registry_bytes(
                            version, 0x6110, scale=scale, magic=magic
                        )
                    )
                    with self.assertRaisesRegex(RuntimeError, "header"):
                        pipeline.inspect_registry(path)

    def test_registry_aggregation_rejects_mixed_identity(self) -> None:
        x4 = {"registry_magic": "IEECSXN", "version": 3, "scale": 4}
        self.assertEqual(
            pipeline.require_compatible_registry_infos([x4, dict(x4)]),
            ("IEECSXN", 3, 4),
        )
        for mixed in (
            {**x4, "scale": 2},
            {**x4, "version": 2},
            {**x4, "registry_magic": "IEECSX2"},
        ):
            with self.subTest(mixed=mixed):
                with self.assertRaisesRegex(RuntimeError, "mixed magic/version/scale"):
                    pipeline.require_compatible_registry_infos([x4, mixed])

    def test_explicit_x2_aggregate_promotes_legacy_and_mixed_member_formats(self) -> None:
        explicit_x2 = {"upscale": pipeline.direct_upscale_contract(2).method}
        legacy = {
            "registry_magic": "IEECSX2",
            "version": 2,
            "scale": 2,
        }
        xn_x2 = {
            "registry_magic": "IEECSXN",
            "version": 3,
            "scale": 2,
        }
        self.assertEqual(
            pipeline.armor_set_output_registry_identity(explicit_x2, [legacy]),
            (pipeline.XN_REGISTRY_MAGIC, pipeline.XN_REGISTRY_VERSION, 2),
        )
        self.assertEqual(
            pipeline.armor_set_output_registry_identity(explicit_x2, [legacy, xn_x2]),
            (pipeline.XN_REGISTRY_MAGIC, pipeline.XN_REGISTRY_VERSION, 2),
        )
        with self.assertRaisesRegex(RuntimeError, "explicit x4"):
            pipeline.armor_set_output_registry_identity(
                {"upscale": pipeline.direct_upscale_contract(4).method}, [legacy]
            )

    def test_explicit_x2_armor_set_loads_legacy_member_jobs_without_rebuild(self) -> None:
        template_path = (
            ROOT
            / "sprite"
            / "families"
            / "playable-characters"
            / "6110-human-female-fighter"
            / "family-runs"
            / "character-set"
            / "jobs"
            / "human-female-fighter-character-set-xbr2x.json"
        )
        promoted = pipeline.read_json(template_path)
        promoted["job_id"] = "test-promoted-character-set-x2"
        promoted["upscale"] = pipeline.direct_upscale_contract(2).method
        promoted["paths"] = dict(promoted["paths"])
        promoted["paths"]["run_dir"] = "sprite/test_promoted/runs/xbr2x-x2-xn"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "promoted.json"
            pipeline.write_json(path, promoted)
            loaded = pipeline.load_armor_set(path)
        self.assertTrue(pipeline.upscale_contract(loaded).explicit)
        self.assertTrue(
            all(not pipeline.upscale_contract(member).explicit for member in loaded["_members"])
        )
        self.assertEqual(pipeline.upscale_contract(loaded).scale, 2)

    def test_promote_armor_set_command_is_reproducible_and_x2_only(self) -> None:
        parser = pipeline.make_parser()
        args = parser.parse_args(
            [
                "promote-armor-set-job",
                "--job",
                "sprite/jobs/example-xn-x2.json",
                "--template-job",
                "sprite/jobs/example-legacy.json",
                "--scale",
                "2",
            ]
        )
        self.assertEqual(args.scale, 2)
        self.assertEqual(args.command, "promote-armor-set-job")
        with self.assertRaisesRegex(RuntimeError, "--scale 2"):
            pipeline.promote_armor_set_job(
                Path("sprite/jobs/example-xn-x4.json"),
                Path("sprite/jobs/example-legacy.json"),
                4,
                False,
            )

    def test_promote_armor_set_force_preserves_destination_on_validation_error(self) -> None:
        source_template = (
            ROOT
            / "sprite"
            / "families"
            / "playable-characters"
            / "6110-human-female-fighter"
            / "family-runs"
            / "character-set"
            / "jobs"
            / "human-female-fighter-character-set-xbr2x.json"
        )
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            jobs = project / "sprite" / "jobs"
            jobs.mkdir(parents=True)
            template = jobs / "legacy-template.json"
            template.write_bytes(source_template.read_bytes())
            destination = jobs / "promoted-xn-x2.json"
            original_destination = source_template.read_bytes()
            destination.write_bytes(original_destination)
            legacy_template = pipeline.read_json(template)
            with (
                mock.patch.object(pipeline, "PROJECT_ROOT", project),
                mock.patch.object(
                    pipeline,
                    "load_armor_set",
                    side_effect=[
                        legacy_template,
                        RuntimeError("post-write validation failed"),
                    ],
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "post-write validation failed"
                ):
                    pipeline.promote_armor_set_job(
                        destination, template, 2, force=True
                    )
            self.assertEqual(destination.read_bytes(), original_destination)
            self.assertFalse(list(jobs.glob(f".{destination.name}.*.tmp")))

    def test_registry_set_binary_contract_and_greedy_resource_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            member_a = root / "member-a.registry"
            member_b = root / "member-b.registry"
            member_a.write_bytes(self.registry_bytes(2, 0x6110, resref="RESA"))
            member_b.write_bytes(self.registry_bytes(2, 0x6110, resref="RESB"))
            records = []
            for member in (member_a, member_b):
                records.extend(
                    pipeline.inspect_registry(
                        member, include_resource_records=True
                    )["resource_records"]
                )
            one_shard_bytes = pipeline.REGISTRY_HEADER_BYTES + int(records[0]["bytes"])
            partitions = pipeline.partition_registry_resources(
                records, maximum_bytes=one_shard_bytes
            )
            self.assertEqual(
                [[record["resref"] for record in shard] for shard in partitions],
                [["RESA"], ["RESB"]],
            )
            shard_infos = []
            for index, shard in enumerate(partitions):
                path = root / pipeline.XN_REGISTRY_SHARD_FILENAME.format(index=index)
                info = pipeline.write_registry_records(
                    path,
                    pipeline.XN_REGISTRY_MAGIC,
                    pipeline.XN_REGISTRY_VERSION,
                    2,
                    0x6110,
                    shard,
                )
                info["path"] = path
                shard_infos.append(info)
            set_path = root / pipeline.XN_REGISTRY_SET_FILENAME
            info = pipeline.write_registry_set_index(set_path, 2, 0x6110, shard_infos)
            raw = set_path.read_bytes()

            self.assertEqual(len(raw), 56 + 2 * 64)
            header = struct.unpack_from("<8sIIIIIIQQQ", raw, 0)
            self.assertEqual(header[:7], (b"IEECSNS\0", 1, 2, 2, 2, 0x6110, 0))
            self.assertEqual(info["resources"], ["RESA", "RESB"])
            self.assertEqual(info["total_resources"], 2)
            self.assertEqual(info["total_registry_bytes"], sum(
                shard["registry_bytes"] for shard in shard_infos
            ))
            manifest_shards = pipeline.registry_set_manifest_shards(info)
            self.assertEqual(
                manifest_shards[0]["registry"],
                "iee-assets/creature-sprites/CreatureSprites-XN-0000.registry",
            )
            self.assertIsInstance(manifest_shards[0]["crc32"], int)

    def test_explicit_aggregate_build_promotes_legacy_records_without_xbr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            member_jobs = []
            member_records = []
            for index, resref in enumerate(("RESA", "RESB"), start=1):
                member_build = root / f"member-{index}" / "build"
                relative_registry = Path(
                    "iee-assets/creature-sprites/CreatureSprites-X2.registry"
                )
                registry = member_build / relative_registry
                registry.parent.mkdir(parents=True)
                registry.write_bytes(
                    self.registry_bytes(2, 0x6110, resref=resref)
                )
                pipeline.write_json(
                    member_build / "build-manifest.json",
                    {
                        "registry": relative_registry.as_posix(),
                        "method": pipeline.LEGACY_UPSCALE.method,
                    },
                )
                member_jobs.append(
                    {
                        "_build_dir": member_build,
                        "animation": {
                            "bam_prefix": f"CHFB{index}",
                            "armor_code": index,
                            "layer": {"kind": "body"},
                        },
                    }
                )
                member_records.append(
                    {
                        "resource_count": 1,
                        "frame_count": 1,
                        "bam_prefix": f"CHFB{index}",
                    }
                )
            armor_set = {
                "_build_dir": root / "aggregate" / "build",
                "_members": member_jobs,
                "job_id": "test-promoted-set-x2",
                "animation": {
                    "id": "0x6110",
                    "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                },
                "upscale": pipeline.direct_upscale_contract(2).method,
            }

            def fake_build_dir(item):
                return Path(item["_build_dir"])

            # A small test-only shard cap forces two shards without allocating
            # a production-sized synthetic registry.  No xBR function is used.
            with (
                mock.patch.object(pipeline, "build_dir", side_effect=fake_build_dir),
                mock.patch.object(
                    pipeline,
                    "armor_set_member_records",
                    return_value=member_records,
                ),
                mock.patch.dict(pipeline.MAX_REGISTRY_BYTES_BY_SCALE, {2: 700}),
                mock.patch.object(pipeline, "run_xbr") as xbr,
            ):
                result = pipeline.build_armor_set(armor_set, force=False, resume=False)
                verified = pipeline.verify_armor_set_build(armor_set)
                manifest_path = (
                    Path(armor_set["_build_dir"]) / "build-manifest.json"
                )
                valid_manifest = pipeline.read_json(manifest_path)
                for field in ("resource_count", "frame_count", "registry_bytes"):
                    tampered_manifest = dict(valid_manifest)
                    tampered_manifest[field] += 1
                    pipeline.write_json(manifest_path, tampered_manifest)
                    with self.assertRaisesRegex(
                        RuntimeError, "top-level counters differ"
                    ):
                        pipeline.verify_armor_set_build(armor_set)
                tampered_validation = json.loads(json.dumps(valid_manifest))
                tampered_validation["validation"]["shard_count"] = 1
                pipeline.write_json(manifest_path, tampered_validation)
                with self.assertRaisesRegex(
                    RuntimeError, "layout validation differs"
                ):
                    pipeline.verify_armor_set_build(armor_set)
                pipeline.write_json(manifest_path, valid_manifest)

            manifest = pipeline.read_json(
                Path(armor_set["_build_dir"]) / "build-manifest.json"
            )
            self.assertEqual(result["registry_layout"], "set")
            self.assertEqual(verified["resources"], ["RESA", "RESB"])
            self.assertEqual(manifest["registry_layout"], "set")
            self.assertEqual(manifest["registry"], None)
            self.assertEqual(len(manifest["shards"]), 2)
            self.assertTrue(manifest["promoted_to_xn"])
            self.assertEqual(
                manifest["source_registry_formats"],
                [
                    {
                        "registry_magic": "IEECSX2",
                        "registry_version": 2,
                        "scale": 2,
                    }
                ],
            )
            self.assertEqual(manifest["total_resources"], 2)
            self.assertEqual(manifest["total_frames"], 2)
            self.assertGreater(manifest["registry_set_bytes"], 0)
            xbr.assert_not_called()

    def test_registry_set_inspector_rejects_header_entry_and_shard_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            member = root / "member.registry"
            member.write_bytes(self.registry_bytes(2, 0x6110, resref="RESA"))
            records = pipeline.inspect_registry(
                member, include_resource_records=True
            )["resource_records"]
            shard_path = root / pipeline.XN_REGISTRY_SHARD_FILENAME.format(index=0)
            shard_info = pipeline.write_registry_records(
                shard_path,
                pipeline.XN_REGISTRY_MAGIC,
                pipeline.XN_REGISTRY_VERSION,
                2,
                0x6110,
                records,
            )
            shard_info["path"] = shard_path
            set_path = root / pipeline.XN_REGISTRY_SET_FILENAME
            pipeline.write_registry_set_index(set_path, 2, 0x6110, [shard_info])
            valid_set = set_path.read_bytes()
            valid_shard = shard_path.read_bytes()

            reserved = bytearray(valid_set)
            struct.pack_into("<I", reserved, 28, 1)
            set_path.write_bytes(reserved)
            with self.assertRaisesRegex(RuntimeError, "header"):
                pipeline.inspect_registry_set(set_path)

            set_path.write_bytes(valid_set)
            crossed_hash = bytearray(valid_set)
            crossed_hash[pipeline.REGISTRY_SET_HEADER_BYTES] ^= 0x01
            set_path.write_bytes(crossed_hash)
            with self.assertRaisesRegex(RuntimeError, "index entry"):
                pipeline.inspect_registry_set(set_path)

            set_path.write_bytes(valid_set)
            changed_shard = bytearray(valid_shard)
            changed_shard[-1] ^= 0x01
            shard_path.write_bytes(changed_shard)
            with self.assertRaises(RuntimeError):
                pipeline.inspect_registry_set(set_path)

    def test_registry_set_limits_cover_full_character_inventory(self) -> None:
        self.assertEqual(pipeline.MAX_REGISTRY_SET_SHARDS, 64)
        self.assertEqual(pipeline.MAX_REGISTRY_SET_RESOURCES, 8192)
        self.assertEqual(pipeline.MAX_REGISTRY_SET_FRAMES, 1_048_576)
        self.assertEqual(pipeline.MAX_REGISTRY_SET_BYTES, 8 * 1024 * 1024 * 1024)
        records = [
            {
                "resref": f"R{index:07d}",
                "bytes": 1,
                "path": Path("unused"),
                "offset": 0,
            }
            for index in range(129)
        ]
        partitions = pipeline.partition_registry_resources(records)
        self.assertEqual([len(shard) for shard in partitions], [128, 1])

    def test_registry_inspectors_reject_oversized_files_before_reading(self) -> None:
        registry = mock.Mock()
        registry.stat.return_value.st_size = pipeline.MAX_REGISTRY_BYTES + 1
        header_stream = mock.MagicMock()
        header_stream.__enter__.return_value.read.return_value = self.registry_bytes(
            2, 0x6110
        )[: pipeline.REGISTRY_HEADER_BYTES]
        registry.open.return_value = header_stream
        with self.assertRaisesRegex(RuntimeError, "header"):
            pipeline.inspect_registry(registry)
        registry.read_bytes.assert_not_called()

        registry_set = mock.Mock()
        registry_set.name = pipeline.XN_REGISTRY_SET_FILENAME
        registry_set.stat.return_value.st_size = (
            pipeline.REGISTRY_SET_HEADER_BYTES
            + pipeline.MAX_REGISTRY_SET_SHARDS * pipeline.REGISTRY_SET_ENTRY_BYTES
            + 1
        )
        with self.assertRaisesRegex(RuntimeError, "header"):
            pipeline.inspect_registry_set(registry_set)
        registry_set.read_bytes.assert_not_called()

    def test_legacy_registry_is_mgo1_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry"
            path.write_bytes(self.registry_bytes(1, 0))
            info = pipeline.inspect_registry(path)
        self.assertEqual(info["animation_id"], "0xE400")

    def test_registry_rejects_invalid_cycle_lookup(self) -> None:
        raw = bytearray(self.registry_bytes(2, 0xE400))
        struct.pack_into("<I", raw, len(raw) - 4, 1)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry"
            path.write_bytes(raw)
            with self.assertRaisesRegex(RuntimeError, "cycle lookup"):
                    pipeline.inspect_registry(path)

    def test_installed_state_integrity_detects_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game = Path(temporary)
            target = game / "InfinityEngine-Enhancer.dll"
            target.write_bytes(b"runtime")
            state = {
                "game_root": str(game),
                "targets": [
                    {
                        "relative_path": "InfinityEngine-Enhancer.dll",
                        "installed_present": True,
                        "installed_sha256": pipeline.sha256_file(target),
                    }
                ],
            }
            self.assertTrue(pipeline.installed_state_integrity(state)["installed_files_match"])
            target.write_bytes(b"changed")
            self.assertFalse(pipeline.installed_state_integrity(state)["installed_files_match"])

    def test_catalog_integrity_allows_unowned_ini_reordering_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game = Path(temporary)
            ini = game / "InfinityEngine-Enhancer.ini"
            original = "\n".join(
                (
                    "[Shaders]",
                    "EnableAreaAnimationX4 = true",
                    "EnableCreatureSpriteUpscaleTest = true",
                    "EnableCreatureSpriteX2Test = false",
                    "EnableCreatureSpriteLinearFiltering = false",
                    "",
                )
            )
            ini.write_text(original, encoding="utf-8")
            state = {
                "schema": pipeline.XN_CATALOG_INSTALL_STATE_SCHEMA,
                "game_root": str(game),
                "targets": [
                    {
                        "relative_path": ini.name,
                        "role": "runtime-ini",
                        "installed_present": True,
                        "installed_sha256": pipeline.sha256_file(ini),
                    }
                ],
            }
            ini.write_text(
                original.replace(
                    "EnableAreaAnimationX4 = true\n", ""
                ).replace(
                    "EnableCreatureSpriteLinearFiltering = false\n",
                    "EnableCreatureSpriteLinearFiltering = false\nEnableAreaAnimationX4 = true\n",
                ),
                encoding="utf-8",
            )
            with mock.patch.object(
                pipeline, "installed_catalog_state_contract_errors", return_value=[]
            ):
                integrity = pipeline.installed_state_integrity(state)
            self.assertTrue(integrity["installed_files_match"])
            self.assertEqual(
                integrity["installed_shared_file_drift"], [ini.name]
            )

            ini.write_text(
                ini.read_text(encoding="utf-8").replace(
                    "EnableCreatureSpriteUpscaleTest = true",
                    "EnableCreatureSpriteUpscaleTest = false",
                ),
                encoding="utf-8",
            )
            with mock.patch.object(
                pipeline, "installed_catalog_state_contract_errors", return_value=[]
            ):
                changed = pipeline.installed_state_integrity(state)
            self.assertFalse(changed["installed_files_match"])

    def test_installed_state_integrity_rejects_reparse_before_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "game"
            outside = root / "outside"
            game.mkdir()
            outside.mkdir()
            target = outside / "InfinityEngine-Enhancer.dll"
            target.write_bytes(b"runtime")
            link = game / "linked"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory symlinks are unavailable: {error}")
            state = {
                "game_root": str(game),
                "targets": [
                    {
                        "relative_path": "linked/InfinityEngine-Enhancer.dll",
                        "installed_present": True,
                        "installed_sha256": pipeline.sha256_file(target),
                    }
                ],
            }
            with mock.patch.object(
                pipeline,
                "sha256_file",
                wraps=pipeline.sha256_file,
            ) as digest:
                integrity = pipeline.installed_state_integrity(state)
            self.assertFalse(integrity["installed_files_match"])
            self.assertEqual(integrity["installed_targets_checked"], 0)
            self.assertTrue(
                any(
                    "reparse point" in error
                    for error in integrity["installed_integrity_errors"]
                )
            )
            digest.assert_not_called()


if __name__ == "__main__":
    unittest.main()
