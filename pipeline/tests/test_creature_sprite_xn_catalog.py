from __future__ import annotations

import shutil
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import run_creature_sprite_x2 as pipeline  # noqa: E402


class CreatureSpriteXnCatalogTests(unittest.TestCase):
    @staticmethod
    def registry_bytes(
        resref: str,
        animation_id: int,
        scale: int = 2,
        width: int = 1,
        height: int = 1,
    ) -> bytes:
        data = bytearray(pipeline.XN_REGISTRY_MAGIC)
        data.extend(
            struct.pack(
                "<IIII", pipeline.XN_REGISTRY_VERSION, scale, 1, animation_id
            )
        )
        data.extend(resref.encode("ascii").ljust(8, b"\0"))
        data.extend(bytes(32))
        data.extend(struct.pack("<II", 1, 1))
        index_bytes = width * height * scale * scale
        data.extend(
            struct.pack("<HHhhB3xI", width, height, 0, 0, 0, index_bytes)
        )
        representatives = np.full(256, 0xFFFF, dtype="<u2")
        representatives[1] = 0
        data.extend(representatives.tobytes())
        data.extend(bytes([1]) * index_bytes)
        data.extend(struct.pack("<II", 1, 0))
        return bytes(data)

    def make_catalog(
        self,
        root: Path,
        scale: int = 2,
        *,
        compressed: bool = False,
        dimension: int = 1,
    ) -> tuple[Path, dict]:
        source_a = root / "source-a.registry"
        source_b = root / "source-b.registry"
        source_a.write_bytes(
            self.registry_bytes(
                "RESA", 0x6102, scale, width=dimension, height=dimension
            )
        )
        source_b.write_bytes(
            self.registry_bytes(
                "RESB", 0x6110, scale, width=dimension, height=dimension
            )
        )
        sources = [source_a, source_b]
        shards = []
        components = []
        for index, source in enumerate(sources):
            records = pipeline.inspect_registry(
                source, include_resource_records=True
            )["resource_records"]
            scratch = root / f"scratch-{index}.registry"
            if compressed:
                info = pipeline.write_compressed_catalog_registry_records(
                    scratch, scale, records
                )
            else:
                info = pipeline.write_registry_records(
                    scratch,
                    pipeline.XN_REGISTRY_MAGIC,
                    pipeline.XN_REGISTRY_VERSION,
                    scale,
                    pipeline.CATALOG_SHARD_ANIMATION_SENTINEL,
                    records,
                )
            shard = root / pipeline.catalog_shard_filename(info["sha256"])
            scratch.replace(shard)
            info["index"] = index
            info["path"] = shard
            shards.append(info)
            raw_entry = pipeline.catalog_shard_entry_bytes(info, shard)
            components.append(
                {
                    "index": index,
                    "digest": pipeline.catalog_component_digest(scale, [raw_entry]),
                    "shard_start": index,
                    "shard_count": 1,
                    "resource_count": info["resource_count"],
                    "frame_count": info["frame_count"],
                    "index_bytes": info["index_bytes"],
                    "registry_bytes": info["registry_bytes"],
                }
            )
        catalog = root / pipeline.XN_REGISTRY_CATALOG_FILENAME
        info = pipeline.write_registry_catalog(
            catalog,
            scale,
            [
                {
                    "animation_id": "0x6102",
                    "owner": pipeline.CATALOG_OWNER_CHARACTER,
                    "component_indices": [0],
                },
                {
                    "animation_id": "0x6110",
                    "owner": pipeline.CATALOG_OWNER_CHARACTER,
                    "component_indices": [1],
                },
            ],
            components,
            shards,
        )
        source_a.unlink()
        source_b.unlink()
        return catalog, info

    def make_sealed_generation(
        self, root: Path
    ) -> tuple[dict, dict, Path]:
        run = root / "run"
        run.mkdir()
        job_file = root / "catalog-job.json"
        pipeline.write_json(
            job_file,
            {
                "schema": pipeline.CATALOG_JOB_SCHEMA,
                "job_id": "sealed-catalog-test",
            },
        )
        job_sha256 = pipeline.sha256_file(job_file)
        job_path = pipeline.relative_project_path(job_file)
        method = {
            "algorithm": "xbr",
            "scale": 2,
            "passes": 1,
            "antialias": False,
            "xbr_blend": False,
        }
        input_lock = {
            "schema": "bg2-upscale-creature-sprite-xn-catalog-input-lock-v1",
            "job_file": job_path,
            "job_sha256": job_sha256,
            "method": method,
            "baldur_real_sha256": "A" * 64,
            "engine_source": "sealed-engine-source",
            "engine_source_contract_sha256": "B" * 64,
            "catalog_builder": "sealed-runner.py",
            "catalog_builder_sha256": "C" * 64,
            "members": [],
            "leaf_jobs": [],
        }
        generation_id = pipeline.canonical_json_sha256(input_lock)
        generation = run / "generations" / generation_id.lower()
        build = generation / "build"
        runtime = generation / "runtime"
        sprite_dir = build / "iee-assets" / "creature-sprites"
        sprite_dir.mkdir(parents=True)
        runtime.mkdir(parents=True)
        _, catalog_info = self.make_catalog(sprite_dir)

        runtime_profile = "character-bg2ee-2.7.3.0"
        animation_ids = [
            entry["animation_id"] for entry in catalog_info["animations"]
        ]
        animations = [
            {
                "animation_id": entry["animation_id"],
                "runtime_profile": runtime_profile,
                "owner": "Character",
                "component_indices": entry["component_indices"],
            }
            for entry in catalog_info["animations"]
        ]
        totals = {
            "total_resources": catalog_info["total_resources"],
            "total_frames": catalog_info["total_frames"],
            "total_index_bytes": catalog_info["total_index_bytes"],
            "total_registry_bytes": catalog_info["total_registry_bytes"],
        }
        build_manifest_path = build / "build-manifest.json"
        pipeline.write_json(
            build_manifest_path,
            {
                "schema": pipeline.CATALOG_BUILD_SCHEMA,
                "status": "built-pending-ingame-qa",
                "job_file": job_path,
                "job_sha256": job_sha256,
                "job_id": "sealed-catalog-test",
                "generation_id": generation_id,
                "method": method,
                "registry_layout": "catalog",
                "animation_ids": animation_ids,
                "runtime_profiles": [runtime_profile],
                "registry_catalog": (
                    "iee-assets/creature-sprites/"
                    + pipeline.XN_REGISTRY_CATALOG_FILENAME
                ),
                "registry_catalog_magic": "IEECSNC",
                "registry_catalog_version": pipeline.XN_REGISTRY_CATALOG_VERSION,
                "registry_scale": 2,
                "registry_catalog_sha256": catalog_info["sha256"],
                "registry_catalog_bytes": catalog_info[
                    "registry_catalog_bytes"
                ],
                "registry_catalog_directory_count": catalog_info[
                    "directory_count"
                ],
                "registry_catalog_directory_entry_bytes": catalog_info[
                    "directory_entry_bytes"
                ],
                "registry_catalog_directory_sha256": catalog_info[
                    "directory_sha256"
                ],
                "animations": animations,
                "components": catalog_info["components"],
                "shards": catalog_info["shards"],
                "totals": totals,
                "source_members": [
                    {
                        "animation_id": animation["animation_id"],
                        "runtime_profile": runtime_profile,
                        "component_indices": animation["component_indices"],
                        "bam_prefixes": [
                            "RESA" if index == 0 else "RESB"
                        ],
                    }
                    for index, animation in enumerate(animations)
                ],
                "locks": {
                    "input_lock_sha256": generation_id,
                    "engine_source_contract_sha256": "B" * 64,
                    "baldur_real_sha256": "A" * 64,
                    "member_count": 0,
                    "leaf_job_count": 0,
                    "input_lock": input_lock,
                },
            },
        )
        runtime_dll = runtime / "InfinityEngine-Enhancer.dll"
        runtime_dll.write_bytes(b"sealed-runtime-dll")
        runtime_manifest_path = runtime / "runtime-manifest.json"
        pipeline.write_json(
            runtime_manifest_path,
            {
                "schema": pipeline.RUNTIME_SCHEMA,
                "status": "built-tested",
                "tests_status": "passed",
                "job_id": "sealed-catalog-test",
                "generation_id": generation_id,
                "job_sha256": job_sha256,
                "method": method,
                "runtime_profiles": [runtime_profile],
                "catalog_magic": "IEECSNC",
                "catalog_version": pipeline.XN_REGISTRY_CATALOG_VERSION,
                "catalog_directory_count": catalog_info["directory_count"],
                "catalog_directory_entry_bytes": catalog_info[
                    "directory_entry_bytes"
                ],
                "catalog_directory_sha256": catalog_info["directory_sha256"],
                "catalog_shard_registry_magic": "IEECSXN",
                "catalog_shard_registry_version": 3,
                "catalog_shard_animation_id_sentinel": "0xFFFF",
                "dll": "InfinityEngine-Enhancer.dll",
                "dll_sha256": pipeline.sha256_file(runtime_dll),
                "bridge_worker_tests_status": "passed",
            },
        )
        state = {
            "schema": pipeline.XN_CATALOG_INSTALL_STATE_SCHEMA,
            "status": "installed-pending-qa",
            "job_file": job_path,
            "job_id": "sealed-catalog-test",
            "job_sha256": job_sha256,
            "generation_id": generation_id,
            "method": {**method, "sampling": "NEAREST"},
            "registry_layout": "catalog",
            "catalog_magic": "IEECSNC",
            "catalog_version": pipeline.XN_REGISTRY_CATALOG_VERSION,
            "catalog_scale": 2,
            "catalog_sha256": catalog_info["sha256"],
            "catalog_bytes": catalog_info["registry_catalog_bytes"],
            "animation_ids": animation_ids,
            "runtime_profiles": [runtime_profile],
            "animation_count": catalog_info["animation_count"],
            "component_count": catalog_info["component_count"],
            "membership_count": catalog_info["membership_count"],
            "shard_count": catalog_info["shard_count"],
            "directory_count": catalog_info["directory_count"],
            "directory_entry_bytes": catalog_info["directory_entry_bytes"],
            "directory_sha256": catalog_info["directory_sha256"],
            **totals,
            "source_dll_sha256": pipeline.sha256_file(runtime_dll),
            "build_manifest": pipeline.relative_project_path(
                build_manifest_path
            ),
            "build_manifest_sha256": pipeline.sha256_file(
                build_manifest_path
            ),
            "runtime_manifest": pipeline.relative_project_path(
                runtime_manifest_path
            ),
            "runtime_manifest_sha256": pipeline.sha256_file(
                runtime_manifest_path
            ),
        }
        job = {
            "_kind": "catalog",
            "_job_file": str(job_file),
            "job_id": "sealed-catalog-test",
            "paths": {"run_dir": str(run)},
        }
        return job, state, runtime_dll

    def test_catalog_round_trip_scopes_resources_by_animation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog, expected = self.make_catalog(Path(temporary))
            info = pipeline.inspect_registry_catalog(catalog)
        self.assertEqual(info["sha256"], expected["sha256"])
        self.assertEqual(info["animation_count"], 2)
        self.assertEqual(info["component_count"], 2)
        self.assertEqual(info["membership_count"], 2)
        self.assertEqual(info["shard_count"], 2)
        self.assertEqual(info["version"], pipeline.XN_REGISTRY_CATALOG_VERSION)
        self.assertEqual(info["directory_count"], 2)
        self.assertEqual(
            info["directory_entry_bytes"],
            pipeline.REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES,
        )
        self.assertEqual(
            [(entry["animation_id"], entry["resref"]) for entry in info["directory"]],
            [("0x6102", "RESA"), ("0x6110", "RESB")],
        )
        self.assertEqual(info["animation_resources"]["0x6102"], ["RESA"])
        self.assertEqual(info["animation_resources"]["0x6110"], ["RESB"])
        self.assertEqual(
            [entry["owner"] for entry in info["animations"]],
            [pipeline.CATALOG_OWNER_CHARACTER] * 2,
        )

    def test_installed_catalog_contract_accepts_only_retired_storage_repack_shards(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog_sha = "A" * 64
            installed_sha = "B" * 64
            retired_sha = "C" * 64
            state = {
                "schema": pipeline.XN_CATALOG_INSTALL_STATE_SCHEMA,
                "registry_layout": "catalog",
                "catalog_magic": "IEECSNC",
                "catalog_version": pipeline.XN_REGISTRY_CATALOG_VERSION,
                "catalog_scale": 2,
                "directory_count": 1,
                "directory_entry_bytes": pipeline.REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES,
                "directory_sha256": "D" * 64,
                "shard_registry_version": pipeline.XN_COMPRESSED_REGISTRY_VERSION,
                "logical_content_sha256": "E" * 64,
                "animation_count": 1,
                "component_count": 1,
                "membership_count": 1,
                "shard_count": 1,
                "total_resources": 1,
                "total_frames": 1,
                "total_index_bytes": 4,
                "total_registry_bytes": 600,
                "animation_ids": ["0x6102"],
                "runtime_profiles": ["character-bg2ee-2.7.3.0"],
                "catalog_relative_path": (
                    "iee-assets/creature-sprites/"
                    + pipeline.XN_REGISTRY_CATALOG_FILENAME
                ),
                "catalog_sha256": catalog_sha,
                "catalog_bytes": 256,
                "game_root": temporary,
                "transaction_id": "transaction",
                "generation_id": "generation",
                "job_id": "job",
                "job_sha256": "F" * 64,
                "method": {"scale": 2, "sampling": "NEAREST"},
                "installation_mode": "storage-repack",
            }

            def target(relative: str, role: str, sha256: str) -> dict:
                return {
                    "relative_path": relative,
                    "role": role,
                    "immutable_noop": False,
                    "installed_present": True,
                    "installed_sha256": sha256,
                }

            targets = [
                target(state["catalog_relative_path"], "catalog", catalog_sha),
                target(
                    "iee-assets/creature-sprites/CreatureSprites-XN.catalog-owner.json",
                    "catalog-owner",
                    "1" * 64,
                ),
                target("InfinityEngine-Enhancer.dll", "runtime-dll", "2" * 64),
                target("InfinityEngine-Enhancer.ini", "runtime-ini", "3" * 64),
                target(
                    "iee-assets/creature-sprites/CreatureSprites-XN-"
                    + installed_sha
                    + ".registry",
                    "content-addressed-shard",
                    installed_sha,
                ),
                {
                    "relative_path": (
                        "iee-assets/creature-sprites/CreatureSprites-XN-"
                        + retired_sha
                        + ".registry"
                    ),
                    "role": "retired-content-addressed-shard",
                    "immutable_noop": False,
                    "existed_before": True,
                    "original_sha256": retired_sha,
                    "restore_source_path": "sealed/" + retired_sha + ".registry",
                    "restore_source_sha256": retired_sha,
                    "installed_present": False,
                    "installed_sha256": None,
                },
            ]
            targets_by_path = {
                item["relative_path"].replace("\\", "/").casefold(): item
                for item in targets
            }
            owner = {
                "schema": "bg2-upscale-creature-sprite-xn-catalog-owner-v1",
                "status": "active",
                "transaction_id": state["transaction_id"],
                "generation_id": state["generation_id"],
                "job_id": state["job_id"],
                "job_sha256": state["job_sha256"],
                "catalog_relative_path": state["catalog_relative_path"],
                "catalog_sha256": catalog_sha,
                "catalog_bytes": state["catalog_bytes"],
                "animation_ids": state["animation_ids"],
                "method": state["method"],
                "game_root": temporary,
            }
            with mock.patch.object(pipeline, "read_json", return_value=owner):
                self.assertEqual(
                    pipeline.installed_catalog_state_contract_errors(
                        state, targets_by_path
                    ),
                    [],
                )
                state["installation_mode"] = "append"
                errors = pipeline.installed_catalog_state_contract_errors(
                    state, targets_by_path
                )
            self.assertIn(
                "retired catalog shards require a storage-repack state", errors
            )

    def test_catalog_round_trip_supports_x4_nearest_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog, _ = self.make_catalog(Path(temporary), scale=4)
            info = pipeline.inspect_registry_catalog(catalog)
        self.assertEqual(info["scale"], 4)
        self.assertEqual(info["total_index_bytes"], 32)

    @unittest.skipUnless(sys.platform == "win32", "V5 uses the Windows codec")
    def test_v5_frame_storage_is_lossless_bounded_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.registry"
            source.write_bytes(
                self.registry_bytes("RESA", 0x6102, width=64, height=64)
            )
            source_info = pipeline.inspect_registry(
                source, include_resource_records=True
            )
            target = root / "compressed.registry"
            info = pipeline.write_compressed_catalog_registry_records(
                target, 2, source_info["resource_records"]
            )
            compressed_records = pipeline.inspect_registry(
                target, include_resource_records=True
            )["resource_records"]
            self.assertEqual(
                pipeline.catalog_source_component_sha256(
                    2, source_info["resource_records"]
                ),
                pipeline.catalog_source_component_sha256(2, compressed_records),
            )
            self.assertEqual(info["version"], pipeline.XN_COMPRESSED_REGISTRY_VERSION)
            self.assertEqual(info["compressed_frame_count"], 1)
            self.assertEqual(info["raw_frame_count"], 0)
            self.assertEqual(info["index_bytes"], 64 * 64 * 4)
            self.assertLess(info["stored_index_bytes"], info["index_bytes"])
            self.assertLess(info["registry_bytes"], source_info["registry_bytes"])

            valid = target.read_bytes()
            invalid_codec = bytearray(valid)
            invalid_codec[
                pipeline.REGISTRY_HEADER_BYTES
                + pipeline.REGISTRY_RESOURCE_HEADER_BYTES
                + 9
            ] = 2
            target.write_bytes(invalid_codec)
            with self.assertRaisesRegex(RuntimeError, "payload"):
                pipeline.inspect_registry(target)

            corrupted = bytearray(valid)
            corrupted[
                pipeline.REGISTRY_HEADER_BYTES
                + pipeline.REGISTRY_RESOURCE_HEADER_BYTES
                + pipeline.REGISTRY_FRAME_HEADER_BYTES
            ] ^= 0x01
            target.write_bytes(corrupted)
            with self.assertRaises(RuntimeError):
                pipeline.inspect_registry(target)

    @unittest.skipUnless(sys.platform == "win32", "V5 uses the Windows codec")
    def test_v5_keeps_incompressible_tiny_frames_raw_and_supports_x4(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for scale in (2, 4):
                source = root / f"source-x{scale}.registry"
                source.write_bytes(self.registry_bytes("RESA", 0x6102, scale))
                records = pipeline.inspect_registry(
                    source, include_resource_records=True
                )["resource_records"]
                target = root / f"target-x{scale}.registry"
                info = pipeline.write_compressed_catalog_registry_records(
                    target, scale, records
                )
                self.assertEqual(info["scale"], scale)
                self.assertEqual(info["raw_frame_count"], 1)
                self.assertEqual(info["compressed_frame_count"], 0)

    def test_catalog_v1_remains_readable_for_transactional_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, v2 = self.make_catalog(root)
            raw = catalog.read_bytes()
            directory_bytes = (
                v2["directory_count"]
                * pipeline.REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES
            )
            table_end = len(raw) - directory_bytes
            legacy = bytearray(raw[: pipeline.REGISTRY_CATALOG_V1_HEADER_BYTES])
            struct.pack_into(
                "<I", legacy, 8, pipeline.LEGACY_XN_REGISTRY_CATALOG_VERSION
            )
            legacy.extend(raw[pipeline.REGISTRY_CATALOG_HEADER_BYTES : table_end])
            catalog.write_bytes(legacy)
            info = pipeline.inspect_registry_catalog(catalog)
        self.assertEqual(info["version"], pipeline.LEGACY_XN_REGISTRY_CATALOG_VERSION)
        self.assertEqual(info["directory_count"], 0)
        self.assertEqual(info["directory"], [])
        self.assertIsNone(info["directory_sha256"])
        self.assertEqual(info["animation_resources"], v2["animation_resources"])

    def test_catalog_v2_directory_is_digest_bound_and_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, info = self.make_catalog(root)
            valid = catalog.read_bytes()
            directory_offset = (
                len(valid)
                - info["directory_count"]
                * pipeline.REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES
            )

            digest_tampered = bytearray(valid)
            digest_tampered[directory_offset + 4] ^= 0x01
            catalog.write_bytes(digest_tampered)
            with self.assertRaisesRegex(RuntimeError, "directory digest"):
                pipeline.inspect_registry_catalog(catalog)

            route_tampered = bytearray(valid)
            struct.pack_into("<I", route_tampered, directory_offset + 12, 1)
            raw_directory = bytes(route_tampered[directory_offset:])
            route_tampered[72:104] = bytes.fromhex(
                pipeline.catalog_directory_digest(2, raw_directory)
            )
            catalog.write_bytes(route_tampered)
            with self.assertRaisesRegex(RuntimeError, "directory"):
                pipeline.inspect_registry_catalog(catalog)

    @unittest.skipUnless(sys.platform == "win32", "V5 uses the Windows codec")
    def test_catalog_v2_v5_has_same_logical_identity_as_v3(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            v3_root = root / "v3"
            v5_root = root / "v5"
            v3_root.mkdir()
            v5_root.mkdir()
            _, v3 = self.make_catalog(v3_root, dimension=64)
            v5_catalog, v5 = self.make_catalog(
                v5_root, compressed=True, dimension=64
            )
            self.assertEqual(
                v3["logical_component_digests"],
                v5["logical_component_digests"],
            )
            self.assertEqual(
                v3["logical_content_sha256"], v5["logical_content_sha256"]
            )
            self.assertEqual(
                v5["shard_registry_version"],
                pipeline.XN_COMPRESSED_REGISTRY_VERSION,
            )
            self.assertGreater(v5["total_index_bytes"], v5["total_registry_bytes"])

            raw = v5_catalog.read_bytes()
            table_end = (
                len(raw)
                - v5["directory_count"]
                * pipeline.REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES
            )
            legacy = bytearray(raw[: pipeline.REGISTRY_CATALOG_V1_HEADER_BYTES])
            struct.pack_into(
                "<I", legacy, 8, pipeline.LEGACY_XN_REGISTRY_CATALOG_VERSION
            )
            legacy.extend(raw[pipeline.REGISTRY_CATALOG_HEADER_BYTES : table_end])
            v5_catalog.write_bytes(legacy)
            with self.assertRaisesRegex(RuntimeError, "header|V3 shards"):
                pipeline.inspect_registry_catalog(v5_catalog)

    def test_catalog_rejects_relationship_digest_and_shard_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, _ = self.make_catalog(root)
            valid_catalog = catalog.read_bytes()

            invalid_membership = bytearray(valid_catalog)
            membership_offset = (
                pipeline.REGISTRY_CATALOG_HEADER_BYTES
                + 2 * pipeline.REGISTRY_CATALOG_ANIMATION_ENTRY_BYTES
            )
            struct.pack_into("<I", invalid_membership, membership_offset, 99)
            catalog.write_bytes(invalid_membership)
            with self.assertRaisesRegex(RuntimeError, "membership"):
                pipeline.inspect_registry_catalog(catalog)

            invalid_digest = bytearray(valid_catalog)
            component_offset = membership_offset + 2 * pipeline.REGISTRY_CATALOG_MEMBERSHIP_BYTES
            invalid_digest[component_offset] ^= 0x01
            catalog.write_bytes(invalid_digest)
            with self.assertRaisesRegex(RuntimeError, "digest"):
                pipeline.inspect_registry_catalog(catalog)

            catalog.write_bytes(valid_catalog)
            shard = next(root.glob("CreatureSprites-XN-" + "?" * 64 + ".registry"))
            valid_shard = shard.read_bytes()
            changed = bytearray(valid_shard)
            changed[-1] ^= 0x01
            shard.write_bytes(changed)
            with self.assertRaises(RuntimeError):
                pipeline.inspect_registry_catalog(catalog)
            shard.write_bytes(valid_shard)

            sentinel = bytearray(valid_shard)
            struct.pack_into("<I", sentinel, 20, 0x6102)
            shard.write_bytes(sentinel)
            with self.assertRaises(RuntimeError):
                pipeline.inspect_registry_catalog(catalog)

    def test_catalog_rejects_unindexed_content_addressed_shard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, info = self.make_catalog(root)
            existing = next(root.glob("CreatureSprites-XN-" + "?" * 64 + ".registry"))
            extra = root / pipeline.catalog_shard_filename("A" * 64)
            shutil.copy2(existing, extra)
            with self.assertRaisesRegex(RuntimeError, "filenames are not exact"):
                pipeline.inspect_registry_catalog(catalog)
            relaxed = pipeline.inspect_registry_catalog(
                catalog, require_exact_shards=False
            )
        self.assertEqual(relaxed["sha256"], info["sha256"])

    def test_catalog_component_digest_is_domain_and_scale_separated(self) -> None:
        entry = bytes(range(pipeline.REGISTRY_CATALOG_SHARD_ENTRY_BYTES))
        digest_x2 = pipeline.catalog_component_digest(2, [entry])
        self.assertNotEqual(digest_x2, pipeline.catalog_component_digest(4, [entry]))
        self.assertNotEqual(
            digest_x2, pipeline.catalog_component_digest(2, [entry, entry])
        )

    def test_catalog_cas_reuses_hardlinked_shards_without_game_hardlinks(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            root = Path(temporary)
            run = root / "run"
            first_dir = run / "generations" / "first" / "build"
            second_dir = run / "generations" / "second" / "build"
            first_dir.mkdir(parents=True)
            second_dir.mkdir(parents=True)
            payload = b"sealed-content-addressed-shard"
            digest = pipeline.hashlib.sha256(payload).hexdigest().upper()
            filename = pipeline.catalog_shard_filename(digest)
            catalog = {"paths": {"run_dir": str(run)}}

            scratch_one = first_dir / ".one.tmp"
            scratch_one.write_bytes(payload)
            first = first_dir / filename
            object_path = pipeline.publish_catalog_shard_object(
                catalog, scratch_one, first, digest
            )

            scratch_two = second_dir / ".two.tmp"
            scratch_two.write_bytes(payload)
            second = second_dir / filename
            reused = pipeline.publish_catalog_shard_object(
                catalog, scratch_two, second, digest
            )
            self.assertEqual(object_path, reused)
            self.assertTrue(object_path.samefile(first))
            self.assertTrue(object_path.samefile(second))

            game_copy = root / "game-copy.registry"
            shutil.copy2(first, game_copy)
            self.assertFalse(os.path.samefile(object_path, game_copy))
            self.assertEqual(game_copy.read_bytes(), payload)

    def test_catalog_payload_lock_covers_monolith_set_index_and_shards(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            build = Path(temporary) / "build"
            pack = build / "iee-assets" / "creature-sprites"
            pack.mkdir(parents=True)
            monolith = pack / pipeline.XN_REGISTRY_FILENAME
            monolith.write_bytes(b"monolith-payload")
            monolith_manifest = {
                "registry_layout": "monolith",
                "registry": (
                    "iee-assets/creature-sprites/" + monolith.name
                ),
            }
            self.assertEqual(
                pipeline.catalog_leaf_payload_paths(build, monolith_manifest),
                [monolith],
            )
            fingerprint = pipeline.catalog_payload_fingerprint(monolith)
            self.assertEqual(fingerprint["bytes"], len(b"monolith-payload"))
            self.assertEqual(fingerprint["sha256"], pipeline.sha256_file(monolith))
            self.assertEqual(fingerprint["crc32"], pipeline.crc32_file(monolith))

            set_index = pack / pipeline.XN_REGISTRY_SET_FILENAME
            shard_zero = pack / pipeline.XN_REGISTRY_SHARD_FILENAME.format(index=0)
            shard_one = pack / pipeline.XN_REGISTRY_SHARD_FILENAME.format(index=1)
            set_index.write_bytes(b"set-index")
            shard_zero.write_bytes(b"shard-zero")
            shard_one.write_bytes(b"shard-one")
            set_manifest = {
                "registry_layout": "set",
                "registry_set": (
                    "iee-assets/creature-sprites/" + set_index.name
                ),
                "shards": [
                    {
                        "registry": (
                            "iee-assets/creature-sprites/" + shard_zero.name
                        )
                    },
                    {
                        "registry": (
                            "iee-assets/creature-sprites/" + shard_one.name
                        )
                    },
                ],
            }
            locked = pipeline.catalog_leaf_payload_paths(build, set_manifest)
            self.assertEqual(set(locked), {set_index, shard_zero, shard_one})
            with self.assertRaisesRegex(RuntimeError, "canonical relative path"):
                pipeline.catalog_payload_path(
                    build, "../outside.registry", "test payload"
                )

    def test_catalog_component_copy_is_bound_to_locked_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_a = root / "source-a.registry"
            source_b = root / "source-b.registry"
            output = root / "output.registry"
            source_a.write_bytes(self.registry_bytes("RESA", 0x6102))
            source_b.write_bytes(self.registry_bytes("RESB", 0x6102))
            records_a = pipeline.inspect_registry(
                source_a, include_resource_records=True
            )["resource_records"]
            records_b = pipeline.inspect_registry(
                source_b, include_resource_records=True
            )["resource_records"]
            pipeline.write_registry_records(
                output,
                pipeline.XN_REGISTRY_MAGIC,
                pipeline.XN_REGISTRY_VERSION,
                2,
                pipeline.CATALOG_SHARD_ANIMATION_SENTINEL,
                records_a,
            )
            digest_a = pipeline.catalog_source_component_sha256(2, records_a)
            digest_b = pipeline.catalog_source_component_sha256(2, records_b)
            pipeline.verify_catalog_component_copy(2, digest_a, [output])
            with self.assertRaisesRegex(RuntimeError, "locked source records"):
                pipeline.verify_catalog_component_copy(2, digest_b, [output])

    def test_catalog_cmake_root_fails_closed_before_filetracker_limit(self) -> None:
        supported = Path("X:/" + "a" * 117)
        rejected = Path("X:/" + "a" * 118)
        self.assertEqual(
            len(str(supported)), pipeline.MAX_WINDOWS_CMAKE_BUILD_ROOT_CHARS
        )
        with mock.patch.object(pipeline.os, "name", "nt"):
            pipeline.assert_cmake_build_root_supported(supported)
            with self.assertRaisesRegex(RuntimeError, "FileTracker"):
                pipeline.assert_cmake_build_root_supported(rejected)

    def test_sealed_generation_uses_recorded_manifests_not_live_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            job, state, _ = self.make_sealed_generation(Path(temporary))
            with (
                mock.patch.object(
                    pipeline,
                    "catalog_generation_id",
                    side_effect=AssertionError("live generation must not be read"),
                ),
                mock.patch.object(
                    pipeline,
                    "verify_catalog_pointer",
                    side_effect=AssertionError("live pointer must not be read"),
                ),
                mock.patch.object(
                    pipeline,
                    "source_tree_hash",
                    side_effect=AssertionError("live engine must not be read"),
                ),
            ):
                integrity = pipeline.sealed_catalog_generation_integrity(
                    job, state
                )
        self.assertTrue(integrity["active_identity_matches_job"])
        self.assertTrue(integrity["active_generation_is_sealed"])
        self.assertEqual(integrity["active_generation_seal_errors"], [])

    def test_sealed_job_snapshot_preserves_recipe_after_live_job_evolves(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            job, state, _ = self.make_sealed_generation(Path(temporary))
            generation = (
                Path(job["paths"]["run_dir"])
                / "generations"
                / state["generation_id"].lower()
            )
            build_manifest_path = generation / "build" / "build-manifest.json"
            build_manifest = pipeline.read_json(build_manifest_path)
            snapshot_path = generation / "build" / "provenance" / "job.json"
            snapshot_path.parent.mkdir(parents=True)
            shutil.copyfile(Path(job["_job_file"]), snapshot_path)
            build_manifest["job_snapshot"] = "provenance/job.json"
            build_manifest["job_snapshot_sha256"] = state["job_sha256"]
            pipeline.write_json(build_manifest_path, build_manifest)
            state["build_manifest_sha256"] = pipeline.sha256_file(
                build_manifest_path
            )

            live_job = pipeline.read_json(Path(job["_job_file"]))
            live_job["layout_revision"] = 2
            pipeline.write_json(Path(job["_job_file"]), live_job)
            integrity = pipeline.sealed_catalog_generation_integrity(job, state)

            self.assertFalse(integrity["active_identity_matches_live_job"])
            self.assertTrue(integrity["sealed_job_snapshot_matches"])
            self.assertTrue(integrity["active_identity_matches_job"])
            self.assertTrue(integrity["active_generation_is_sealed"])

            snapshot_path.write_text("{}\n", encoding="utf-8")
            tampered = pipeline.sealed_catalog_generation_integrity(job, state)
            self.assertFalse(tampered["sealed_job_snapshot_matches"])
            self.assertFalse(tampered["active_generation_is_sealed"])
            self.assertTrue(
                any(
                    "job snapshot" in error
                    for error in tampered["active_generation_seal_errors"]
                )
            )

    def test_sealed_generation_rejects_changed_runtime_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            job, state, runtime_dll = self.make_sealed_generation(Path(temporary))
            runtime_dll.write_bytes(b"changed-runtime-dll")
            integrity = pipeline.sealed_catalog_generation_integrity(job, state)
        self.assertTrue(integrity["active_identity_matches_job"])
        self.assertFalse(integrity["active_generation_is_sealed"])
        self.assertTrue(
            any(
                "runtime DLL" in error
                for error in integrity["active_generation_seal_errors"]
            )
        )

    def test_record_qa_accepts_sealed_generation_after_live_sources_evolve(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job, state, _ = self.make_sealed_generation(root)
            active_state = pipeline.active_state_path(job)
            pipeline.write_json(active_state, state)
            with (
                mock.patch.object(
                    pipeline,
                    "catalog_generation_id",
                    side_effect=AssertionError("live generation must not be read"),
                ),
                mock.patch.object(
                    pipeline,
                    "verify_catalog_pointer",
                    side_effect=AssertionError("live pointer must not be read"),
                ),
                mock.patch.object(
                    pipeline,
                    "source_tree_hash",
                    side_effect=AssertionError("live engine must not be read"),
                ),
                mock.patch.object(
                    pipeline,
                    "qa_log_report",
                    return_value={"technical_pass": True},
                ),
            ):
                decision = pipeline.record_qa(job, "pass", "sealed QA")
        self.assertEqual(decision["status"], "validated-installed")


if __name__ == "__main__":
    unittest.main()
