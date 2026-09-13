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

    def test_sealed_index_reader_never_opens_parent_shards(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog, expected = self.make_catalog(Path(temporary))
            for shard in catalog.parent.glob("CreatureSprites-XN-*.registry"):
                shard.unlink()
            index = pipeline.read_sealed_catalog_index(catalog, expected["sha256"])
        self.assertEqual(index["animations"], [
            {"animation_id": "0x6102", "owner": pipeline.CATALOG_OWNER_CHARACTER, "component_indices": [0]},
            {"animation_id": "0x6110", "owner": pipeline.CATALOG_OWNER_CHARACTER, "component_indices": [1]},
        ])
        self.assertEqual([entry["resref"] for entry in index["directory"]], ["RESA", "RESB"])

    def test_trusted_index_writer_is_runtime_byte_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, expected = self.make_catalog(root)
            index = pipeline.read_sealed_catalog_index(catalog, expected["sha256"])
            rebuilt = root / "rebuilt" / pipeline.XN_REGISTRY_CATALOG_FILENAME
            rebuilt.parent.mkdir()
            for shard in root.glob("CreatureSprites-XN-*.registry"):
                shutil.copyfile(shard, rebuilt.parent / shard.name)
            actual = pipeline.write_registry_catalog_index(
                rebuilt,
                index["scale"],
                index["animations"],
                index["components"],
                index["shards"],
                index["directory"],
                expected["logical_component_digests"],
                {
                    "stored_index_bytes": expected["stored_index_bytes"],
                    "compressed_frame_count": expected["compressed_frame_count"],
                    "raw_frame_count": expected["raw_frame_count"],
                    "index_storage_ratio": expected["index_storage_ratio"],
                },
            )
            verified = pipeline.inspect_registry_catalog(rebuilt)
        self.assertEqual(actual["sha256"], expected["sha256"])
        self.assertEqual(verified["sha256"], expected["sha256"])

    def test_delta_build_reads_only_new_payload_and_parent_index(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "sprite") as temporary:
            root = Path(temporary)
            parent_pack = root / "parent/build/iee-assets/creature-sprites"
            parent_pack.mkdir(parents=True)
            parent_catalog, parent_info = self.make_catalog(parent_pack, compressed=True)
            parent_manifest_path = root / "parent/build/build-manifest.json"
            parent_manifest = {
                "schema": pipeline.CATALOG_BUILD_SCHEMA,
                "status": "built-pending-ingame-qa",
                "generation_id": "PARENT",
                "method": pipeline.direct_upscale_contract(2).method,
                "registry_scale": 2,
                "runtime_profiles": ["character-bg2ee-2.7.3.0"],
                "registry_catalog": "iee-assets/creature-sprites/CreatureSprites-XN.catalog",
                "registry_catalog_sha256": parent_info["sha256"],
                "registry_catalog_logical_component_digests": parent_info["logical_component_digests"],
                "animations": [
                    {"animation_id": value["animation_id"], "runtime_profile": "character-bg2ee-2.7.3.0", "owner": "Character", "component_indices": value["component_indices"]}
                    for value in parent_info["animations"]
                ],
                "source_members": [],
                "storage": {key: parent_info[key] for key in ("stored_index_bytes", "compressed_frame_count", "raw_frame_count", "index_storage_ratio")},
                "locks": {"baldur_real_sha256": "A" * 64},
            }
            pipeline.write_json(parent_manifest_path, parent_manifest)
            source = root / "delta.registry"
            source.write_bytes(self.registry_bytes("RESC", 0x6120))
            records = pipeline.inspect_registry(source, include_resource_records=True)["resource_records"]
            source_digest = pipeline.catalog_source_component_sha256(2, records)
            collection = {
                "generation_id": "unused",
                "components": [{
                    "source_digest": source_digest, "records": records,
                    "resource_count": 1, "frame_count": 1, "index_bytes": 4,
                }],
                "animations": [{
                    "animation_id": "0x6120", "runtime_profile": "character-bg2ee-2.7.3.0",
                    "owner": pipeline.CATALOG_OWNER_CHARACTER,
                    "component_source_digests": [source_digest], "resources": ["RESC"],
                }],
                "source_members": [{
                    "job_file": "delta.json", "job_sha256": "B" * 64,
                    "job_id": "delta", "animation_id": "0x6120",
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                    "build_manifest": "delta-build.json", "build_manifest_sha256": "C" * 64,
                    "component_source_digests": [source_digest], "bam_prefixes": ["RESC"],
                }],
            }
            job_file = root / "delta-job.json"
            job_file.write_text("{}\n", encoding="utf-8")
            input_lock = {"schema": "test-delta", "baldur_real_sha256": "A" * 64}
            catalog = {
                "_kind": "catalog", "_job_file": str(job_file), "_catalog_members": [],
                "_catalog_input_lock": input_lock, "job_id": "delta-test",
                "upscale": pipeline.direct_upscale_contract(2).method,
                "compatibility": {"baldur_real_sha256": "A" * 64},
                "paths": {"run_dir": str(root / "run"), "game_root": str(root / "game")},
                "_catalog_parent": {
                    "manifest_path": parent_manifest_path,
                    "manifest_sha256": pipeline.sha256_file(parent_manifest_path),
                    "catalog_path": parent_catalog,
                    "catalog_sha256": parent_info["sha256"], "manifest": parent_manifest,
                },
            }
            original_inspect = pipeline.inspect_registry
            def reject_parent_shard(path, *args, **kwargs):
                if Path(path).parent == parent_pack and Path(path).suffix == ".registry":
                    raise AssertionError("parent shard was opened")
                return original_inspect(path, *args, **kwargs)
            with (
                mock.patch.object(pipeline, "catalog_source_collection", return_value=collection),
                mock.patch.object(pipeline, "catalog_override_collisions", return_value=[]),
                mock.patch.object(pipeline, "inspect_registry", side_effect=reject_parent_shard),
            ):
                result = pipeline.build_catalog_delta(catalog, resume=False, verify_members=True)
            built = pipeline.catalog_generation_dir(catalog) / "build/iee-assets/creature-sprites/CreatureSprites-XN.catalog"
            verified = pipeline.inspect_registry_catalog(built)
        self.assertEqual(result["status"], "built-delta")
        self.assertEqual([value["animation_id"] for value in verified["animations"]], ["0x6102", "0x6110", "0x6120"])

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

if __name__ == "__main__":
    unittest.main()
