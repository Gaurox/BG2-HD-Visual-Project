import hashlib
import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALL = ROOT / "pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1"
RESTORE = ROOT / "pipeline/scripts/Restore-CreatureSprite-XN-Catalog-Test.ps1"
SOURCE_FILES = (
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def source_contract(source: Path) -> str:
    digest = hashlib.sha256()
    for relative in SOURCE_FILES:
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update((source / relative).read_bytes())
    return digest.hexdigest().upper()


def xpress_huff_compress(payload: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    cabinet = ctypes.WinDLL("cabinet", use_last_error=True)
    create = cabinet.CreateCompressor
    create.argtypes = [wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    create.restype = wintypes.BOOL
    compress = cabinet.Compress
    compress.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    compress.restype = wintypes.BOOL
    close = cabinet.CloseCompressor
    close.argtypes = [ctypes.c_void_p]
    close.restype = wintypes.BOOL
    handle = ctypes.c_void_p()
    if not create(4, None, ctypes.byref(handle)):
        raise OSError(ctypes.get_last_error(), "CreateCompressor(XPRESS_HUFF)")
    try:
        source = ctypes.create_string_buffer(payload)
        required = ctypes.c_size_t()
        if compress(handle, source, len(payload), None, 0, ctypes.byref(required)):
            raise RuntimeError("XPRESS_HUFF size query unexpectedly succeeded")
        if ctypes.get_last_error() != 122 or required.value == 0:
            raise OSError(ctypes.get_last_error(), "XPRESS_HUFF size query")
        output = ctypes.create_string_buffer(required.value)
        written = ctypes.c_size_t()
        if not compress(
            handle,
            source,
            len(payload),
            output,
            len(output),
            ctypes.byref(written),
        ):
            raise OSError(ctypes.get_last_error(), "XPRESS_HUFF compression")
        return bytes(output.raw[: written.value])
    finally:
        if not close(handle):
            raise OSError(ctypes.get_last_error(), "CloseCompressor")


def registry_artifact(
    resref: str,
    *,
    scale: int = 2,
    version: int = 3,
    semantic_index: int = 0,
    corrupt_compressed: bool = False,
) -> dict[str, object]:
    if version not in (3, 5) or not 0 <= semantic_index <= 255:
        raise ValueError("invalid fake registry contract")
    header = struct.pack("<8sIIII", b"IEECSXN\0", version, scale, 1, 0xFFFF)
    resource = bytearray(48)
    resource[: len(resref)] = resref.encode("ascii")
    resource[8:40] = hashlib.sha256(("source:" + resref).encode("ascii")).digest()
    struct.pack_into("<II", resource, 40, 1, 1)
    width = height = 32
    logical_index_bytes = width * height * scale * scale
    payload = bytes([semantic_index]) * logical_index_bytes
    canonical_frame = bytearray(528)
    struct.pack_into("<HHhhB", canonical_frame, 0, width, height, -2, 3, 0)
    struct.pack_into("<I", canonical_frame, 12, logical_index_bytes)
    frame = bytearray(canonical_frame)
    stored = payload
    codec = 0
    if version == 5:
        compressed = xpress_huff_compress(payload)
        if len(compressed) < len(payload):
            codec = 1
            stored = compressed
            if corrupt_compressed:
                stored = xpress_huff_compress(
                    bytes([semantic_index ^ 1]) * logical_index_bytes
                )
        frame[9] = codec
        struct.pack_into("<I", frame, 12, len(stored))
    cycle = struct.pack("<II", 1, 0)
    logical_record = bytes(resource) + bytes(canonical_frame) + payload + cycle
    raw = header + bytes(resource) + bytes(frame) + stored + cycle
    return {
        "raw": raw,
        "logical_record": logical_record,
        "logical_index_bytes": logical_index_bytes,
        "stored_index_bytes": len(stored),
        "compressed_frame_count": int(codec == 1),
        "raw_frame_count": int(codec == 0),
    }


def registry_bytes(resref: str, scale: int = 2) -> bytes:
    return registry_artifact(resref, scale=scale, version=3)["raw"]  # type: ignore[return-value]


def component_digest(scale: int, entries: list[bytes]) -> str:
    digest = hashlib.sha256()
    digest.update(b"IEECSNC-COMPONENT-V1\0")
    digest.update(struct.pack("<I", scale))
    for entry in entries:
        digest.update(entry)
    return digest.hexdigest().upper()


def source_component_digest(
    scale: int, records: list[tuple[str, bytes]]
) -> str:
    digest = hashlib.sha256()
    digest.update(b"IEECSNC-SOURCE-COMPONENT-V1\0")
    digest.update(struct.pack("<II", scale, len(records)))
    for resref, record in sorted(records):
        digest.update(resref.encode("ascii") + b"\0")
        digest.update(struct.pack("<Q", len(record)))
        digest.update(record)
    return digest.hexdigest().upper()


def logical_content_digest(
    scale: int,
    animations: list[tuple[int, int, list[int]]],
    component_digests: list[str],
) -> str:
    digest = hashlib.sha256()
    digest.update(b"IEECSNC-LOGICAL-CONTENT-V1\0")
    digest.update(struct.pack("<III", scale, len(animations), len(component_digests)))
    for value in component_digests:
        digest.update(bytes.fromhex(value))
    for animation_id, owner, indices in animations:
        digest.update(struct.pack("<III", animation_id, owner, len(indices)))
        digest.update(struct.pack(f"<{len(indices)}I", *indices))
    return digest.hexdigest().upper()


class FakeCatalogWorkspace:
    def __init__(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix=".xn-catalog-install-", dir=ROOT / "sprite"))
        self.game = self.root / "fake-game"
        self.run = self.root / "run"
        self.engine = self.root / "engine"
        self.provenance = self.root / "provenance"
        self.job = self.root / "catalog-job.json"
        self.game.mkdir()
        self.run.mkdir()
        (self.game / "override").mkdir()
        (self.game / "BaldurReal.exe").write_bytes(b"fake-baldur-real")
        (self.game / "InfinityEngine-Enhancer.dll").write_bytes(b"baseline-dll")
        (self.game / "InfinityEngine-Enhancer.ini").write_text(
            "[Shaders]\r\nUnrelated = true\r\n", encoding="utf-8"
        )
        for index, relative in enumerate(SOURCE_FILES):
            path = self.engine / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"source-{index}\n".encode("ascii"))
        self.job_value = {
            "schema": "bg2-upscale-creature-sprite-xn-catalog-job-v1",
            "job_id": "fake-progressive-catalog",
            "paths": {
                "game_root": str(self.game),
                "run_dir": project_relative(self.run),
                "engine_source": project_relative(self.engine),
            },
            "compatibility": {"baldur_real_sha256": sha256(self.game / "BaldurReal.exe")},
            "upscale": {
                "algorithm": "XBR/xbr2X",
                "scale": 2,
                "passes": 1,
                "antialias": False,
                "xbr_blend": False,
            },
        }
        write_json(self.job, self.job_value)

    def add_import_chain(self, *, unrelated: bool = False) -> tuple[Path, Path, Path | None]:
        marker = self.game / "import-top-marker.bin"
        marker.write_bytes(b"top-live")
        top_job = self.root / "import-top-job.json"
        parent_job = self.root / "import-parent-job.json"
        write_json(top_job, {"job_id": "import-top"})
        write_json(parent_job, {"job_id": "import-parent"})
        parent_state = self.root / "import-parent/active-test.json"
        top_state = self.root / "import-top/active-test.json"
        write_json(
            parent_state,
            {
                "schema": "fake-parent-state-v1",
                "status": "installed-pending-qa",
                "job_file": project_relative(parent_job),
                "job_id": "import-parent",
                "game_root": str(self.game),
                "targets": [
                    {
                        "relative_path": "import-parent-marker.bin",
                        "installed_present": False,
                        "installed_sha256": None,
                    }
                ],
            },
        )
        write_json(
            top_state,
            {
                "schema": "fake-overlay-state-v1",
                "status": "installed-pending-qa",
                "job_file": project_relative(top_job),
                "job_id": "import-top",
                "game_root": str(self.game),
                "parent_active_tests": [
                    {
                        "state_path": str(parent_state),
                        "job_id": "import-parent",
                        "status": "installed-pending-qa",
                    }
                ],
                "targets": [
                    {
                        "relative_path": marker.name,
                        "installed_present": True,
                        "installed_sha256": sha256(marker),
                    }
                ],
            },
        )
        extra_state = None
        if unrelated:
            extra_job = self.root / "import-unrelated-job.json"
            write_json(extra_job, {"job_id": "import-unrelated"})
            extra_state = self.root / "import-unrelated/active-test.json"
            write_json(
                extra_state,
                {
                    "schema": "fake-unrelated-state-v1",
                    "status": "installed-pending-qa",
                    "job_file": project_relative(extra_job),
                    "job_id": "import-unrelated",
                    "game_root": str(self.game),
                    "targets": [],
                },
            )
        self.job_value["installation"] = {
            "import_active_state": {
                "state_path": project_relative(top_state),
                "job_id": "import-top",
            }
        }
        write_json(self.job, self.job_value)
        return top_state, parent_state, extra_state

    def close(self) -> None:
        shutil.rmtree(self.root)

    def write_generation(
        self,
        name: str,
        animations: list[tuple[int, str]],
        *,
        job_file: Path | None = None,
        runtime_dll_bytes: bytes = b"catalog-runtime-dll",
        catalog_version: int = 1,
        directory_resref_override: str | None = None,
        shard_version: int | None = None,
        semantic_index: int = 0,
        logical_manifest_semantic_index: int | None = None,
        corrupt_compressed: bool = False,
    ) -> dict:
        if catalog_version not in (1, 2):
            raise ValueError("catalog_version must be 1 or 2")
        if shard_version is None:
            shard_version = 3 if catalog_version == 1 else 5
        if shard_version not in (3, 5) or (catalog_version == 1 and shard_version != 3):
            raise ValueError("invalid fake catalog/shard version pair")
        job_file = self.job if job_file is None else job_file
        job_value = json.loads(job_file.read_text(encoding="utf-8"))
        provisional_id = hashlib.sha256(name.encode("ascii")).hexdigest().upper()
        generation = self.run / "generations" / provisional_id
        build = generation / "build"
        runtime = generation / "runtime"
        sprite_dir = build / "iee-assets/creature-sprites"
        sprite_dir.mkdir(parents=True)
        runtime.mkdir(parents=True)

        shards = []
        components = []
        shard_entries = []
        source_members = []
        leaf_locks = []
        manifest_animations = []
        memberships = []
        logical_component_digests = []
        manifest_logical_component_digests = []
        stored_index_bytes = 0
        compressed_frame_count = 0
        raw_frame_count = 0
        for index, (animation_id, resref) in enumerate(animations):
            artifact = registry_artifact(
                resref,
                version=shard_version,
                semantic_index=semantic_index,
                corrupt_compressed=corrupt_compressed,
            )
            raw_registry = artifact["raw"]
            assert isinstance(raw_registry, bytes)
            logical_record = artifact["logical_record"]
            assert isinstance(logical_record, bytes)
            logical_index_bytes = int(artifact["logical_index_bytes"])
            stored_index_bytes += int(artifact["stored_index_bytes"])
            compressed_frame_count += int(artifact["compressed_frame_count"])
            raw_frame_count += int(artifact["raw_frame_count"])
            registry_hash = hashlib.sha256(raw_registry).hexdigest().upper()
            registry_name = f"CreatureSprites-XN-{registry_hash}.registry"
            registry_path = sprite_dir / registry_name
            registry_path.write_bytes(raw_registry)
            crc32 = zlib.crc32(raw_registry) & 0xFFFFFFFF
            entry = struct.pack(
                "<32sIIQQQ",
                bytes.fromhex(registry_hash),
                crc32,
                1,
                1,
                logical_index_bytes,
                len(raw_registry),
            )
            shard_entries.append(entry)
            shards.append(
                {
                    "index": index,
                    "registry": f"iee-assets/creature-sprites/{registry_name}",
                    "sha256": registry_hash,
                    "crc32": crc32,
                    "resource_count": 1,
                    "frame_count": 1,
                    "index_bytes": logical_index_bytes,
                    "registry_bytes": len(raw_registry),
                }
            )
            digest = component_digest(2, [entry])
            components.append(
                {
                    "index": index,
                    "digest": digest,
                    "shard_start": index,
                    "shard_count": 1,
                    "resource_count": 1,
                    "frame_count": 1,
                    "index_bytes": logical_index_bytes,
                    "registry_bytes": len(raw_registry),
                }
            )
            logical_component_digests.append(
                source_component_digest(2, [(resref, logical_record)])
            )
            manifest_semantic = (
                semantic_index
                if logical_manifest_semantic_index is None
                else logical_manifest_semantic_index
            )
            manifest_artifact = registry_artifact(
                resref,
                version=3,
                semantic_index=manifest_semantic,
            )
            manifest_record = manifest_artifact["logical_record"]
            assert isinstance(manifest_record, bytes)
            manifest_logical_component_digests.append(
                source_component_digest(2, [(resref, manifest_record)])
            )
            memberships.append(index)
            manifest_animations.append(
                {
                    "animation_id": f"0x{animation_id:04X}",
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                    "owner": "Character",
                    "component_indices": [index],
                }
            )
            member_job = self.provenance / f"member-{animation_id:04X}.json"
            member_build = self.provenance / f"member-{animation_id:04X}-build.json"
            member_source = self.provenance / f"member-{animation_id:04X}-source.json"
            member_payload = self.provenance / f"member-{animation_id:04X}-payload.registry"
            if not member_job.exists():
                write_json(member_job, {"job_id": f"member-{animation_id:04X}"})
                write_json(member_build, {"status": "immutable-source"})
                write_json(member_source, {"status": "immutable-source", "resref": resref})
                member_payload.write_bytes(raw_registry)
            source_members.append(
                {
                    "job_file": project_relative(member_job),
                    "job_sha256": sha256(member_job),
                    "job_id": f"member-{animation_id:04X}",
                    "animation_id": f"0x{animation_id:04X}",
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                    "build_manifest": project_relative(member_build),
                    "build_manifest_sha256": sha256(member_build),
                    "component_indices": [index],
                    "bam_prefixes": [resref[:5]],
                }
            )
            leaf_locks.append(
                {
                    "job_file": project_relative(member_job),
                    "job_sha256": sha256(member_job),
                    "job_id": f"member-{animation_id:04X}",
                    "source_manifest": project_relative(member_source),
                    "source_manifest_sha256": sha256(member_source),
                    "build_manifest": project_relative(member_build),
                    "build_manifest_sha256": sha256(member_build),
                    "payloads": [
                        {
                            "path": project_relative(member_payload),
                            "sha256": sha256(member_payload),
                            "crc32": zlib.crc32(member_payload.read_bytes()) & 0xFFFFFFFF,
                            "bytes": member_payload.stat().st_size,
                        }
                    ],
                }
            )

        animation_table = bytearray()
        for index, (animation_id, _resref) in enumerate(animations):
            animation_table.extend(struct.pack("<IIII", animation_id, 1, index, 1))
        component_table = bytearray()
        for component in components:
            component_table.extend(
                struct.pack(
                    "<32sIIIIQQQ",
                    bytes.fromhex(component["digest"]),
                    component["shard_start"],
                    1,
                    1,
                    0,
                    1,
                    component["index_bytes"],
                    component["registry_bytes"],
                )
            )
        total_registry_bytes = sum(item["registry_bytes"] for item in components)
        total_index_bytes = sum(item["index_bytes"] for item in components)
        logical_sha256 = logical_content_digest(
            2,
            [(animation_id, 1, [index]) for index, (animation_id, _resref) in enumerate(animations)],
            logical_component_digests,
        )
        manifest_logical_sha256 = logical_content_digest(
            2,
            [(animation_id, 1, [index]) for index, (animation_id, _resref) in enumerate(animations)],
            manifest_logical_component_digests,
        )
        directory_entries = []
        if catalog_version == 2:
            for index, (animation_id, resref) in enumerate(animations):
                directory_resref = directory_resref_override or resref
                directory_entries.append(
                    struct.pack(
                        "<I8sIII",
                        animation_id,
                        directory_resref.encode("ascii").ljust(8, b"\0"),
                        index,
                        index,
                        0,
                    )
                )
            directory_entries.sort(key=lambda raw: (struct.unpack_from("<I", raw)[0], raw[4:12]))
            directory_digest = hashlib.sha256()
            directory_digest.update(b"IEECSNC-DIRECTORY-V2\0")
            directory_digest.update(struct.pack("<I", 2))
            for entry in directory_entries:
                directory_digest.update(entry)
            catalog_header = struct.pack(
                "<8sIIIIIIQQQQII32s",
                b"IEECSNC\0",
                2,
                2,
                len(animations),
                len(components),
                len(memberships),
                len(shards),
                len(components),
                len(components),
                total_index_bytes,
                total_registry_bytes,
                len(directory_entries),
                24,
                directory_digest.digest(),
            )
            directory_sha256 = directory_digest.hexdigest().upper()
        else:
            catalog_header = struct.pack(
                "<8sIIIIIIQQQQ",
                b"IEECSNC\0",
                1,
                2,
                len(animations),
                len(components),
                len(memberships),
                len(shards),
                len(components),
                len(components),
                total_index_bytes,
                total_registry_bytes,
            )
            directory_sha256 = None
        catalog_raw = bytearray(catalog_header)
        catalog_raw.extend(animation_table)
        catalog_raw.extend(struct.pack(f"<{len(memberships)}I", *memberships))
        catalog_raw.extend(component_table)
        for entry in shard_entries:
            catalog_raw.extend(entry)
        for entry in directory_entries:
            catalog_raw.extend(entry)
        catalog_path = sprite_dir / "CreatureSprites-XN.catalog"
        catalog_path.write_bytes(catalog_raw)

        input_lock = {
            "schema": "bg2-upscale-creature-sprite-xn-catalog-input-lock-v1",
            "job_file": project_relative(job_file),
            "job_sha256": sha256(job_file),
            "method": job_value["upscale"],
            "baldur_real_sha256": sha256(self.game / "BaldurReal.exe"),
            "engine_source": project_relative(self.engine),
            "engine_source_contract_sha256": source_contract(self.engine),
            "catalog_builder": "pipeline/scripts/run_creature_sprite_x2.py",
            "catalog_builder_sha256": sha256(ROOT / "pipeline/scripts/run_creature_sprite_x2.py"),
            "members": [
                {
                    key: member[key]
                    for key in (
                        "job_file",
                        "job_sha256",
                        "job_id",
                        "build_manifest",
                        "build_manifest_sha256",
                    )
                }
                for member in source_members
            ],
            "leaf_jobs": leaf_locks,
        }
        generation_id = hashlib.sha256(
            json.dumps(
                input_lock,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest().upper()
        final_generation = self.run / "generations" / generation_id.lower()
        generation.rename(final_generation)
        generation = final_generation
        build = generation / "build"
        runtime = generation / "runtime"
        sprite_dir = build / "iee-assets/creature-sprites"
        catalog_path = sprite_dir / "CreatureSprites-XN.catalog"

        validation = {
            "records_copied_without_xbr": True,
            "resource_records_sha256_verified": len(components),
            "palette_frames_exactly_remapped": len(components),
            "partial_alpha_pixels": 0,
            "new_colors": 0,
            "override_collisions": 0,
            "maximum_animations": 512,
            "maximum_components": 16384,
            "maximum_memberships": 262144,
            "maximum_shards": 16384,
            "maximum_physical_resources": 32768,
            "maximum_frames": 4194304,
            "maximum_registry_bytes": 137438953472,
            "maximum_resources_per_shard": 128,
            "maximum_shard_bytes": 134217728,
            "game_launch_is_never_automatic": True,
            "release_manifest_is_out_of_scope": True,
        }
        if catalog_version == 2:
            validation["maximum_directory_entries"] = 1_048_576
        if shard_version == 5:
            validation.update(
                {
                    "logical_records_preserved_after_lossless_storage_repack": True,
                    "catalog_shard_registry_version": 5,
                    "frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
                }
            )
        build_manifest = {
            "schema": "bg2-upscale-creature-sprite-xn-catalog-pack-v1",
            "status": "built-pending-ingame-qa",
            "job_file": project_relative(job_file),
            "job_sha256": sha256(job_file),
            "job_id": job_value["job_id"],
            "generation_id": generation_id,
            "method": job_value["upscale"],
            "registry_layout": "catalog",
            "animation_ids": [entry["animation_id"] for entry in manifest_animations],
            "runtime_profiles": ["character-bg2ee-2.7.3.0"],
            "registry_catalog": "iee-assets/creature-sprites/CreatureSprites-XN.catalog",
            "registry_catalog_magic": "IEECSNC",
            "registry_catalog_version": catalog_version,
            "registry_catalog_shard_version": shard_version,
            "registry_catalog_frame_storage": (
                "XPRESS_HUFF-or-raw-per-frame-v1" if shard_version == 5 else "raw-v3"
            ),
            "registry_scale": 2,
            "registry_catalog_sha256": sha256(catalog_path),
            "registry_catalog_bytes": len(catalog_raw),
            "animations": manifest_animations,
            "components": components,
            "shards": shards,
            "totals": {
                "total_resources": len(components),
                "total_frames": len(components),
                "total_index_bytes": total_index_bytes,
                "total_registry_bytes": total_registry_bytes,
            },
            "source_members": source_members,
            "locks": {
                "input_lock_sha256": generation_id,
                "engine_source_contract_sha256": source_contract(self.engine),
                "baldur_real_sha256": sha256(self.game / "BaldurReal.exe"),
                "member_count": len(source_members),
                "leaf_job_count": len(source_members),
                "input_lock": input_lock,
            },
            "validation": validation,
        }
        if catalog_version == 2:
            build_manifest.update(
                {
                    "registry_catalog_directory_count": len(directory_entries),
                    "registry_catalog_directory_entry_bytes": 24,
                    "registry_catalog_directory_sha256": directory_sha256,
                    "registry_catalog_logical_component_digests": (
                        manifest_logical_component_digests
                    ),
                    "registry_catalog_logical_content_sha256": (
                        manifest_logical_sha256
                    ),
                }
            )
        if shard_version == 5:
            build_manifest["storage"] = {
                "shard_registry_version": 5,
                "frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
                "stored_index_bytes": stored_index_bytes,
                "compressed_frame_count": compressed_frame_count,
                "raw_frame_count": raw_frame_count,
                "index_storage_ratio": stored_index_bytes / total_index_bytes,
            }
        build_manifest_path = build / "build-manifest.json"
        write_json(build_manifest_path, build_manifest)

        runtime_dll = runtime / "InfinityEngine-Enhancer.dll"
        runtime_dll.write_bytes(runtime_dll_bytes)
        runtime_manifest = {
            "schema": "bg2-upscale-creature-sprite-runtime-v1",
            "status": "built-tested",
            "job_id": job_value["job_id"],
            "generation_id": generation_id,
            "job_sha256": sha256(job_file),
            "method": job_value["upscale"],
            "runtime_profiles": ["character-bg2ee-2.7.3.0"],
            "engine_source": project_relative(self.engine),
            "engine_source_contract_sha256": source_contract(self.engine),
            "engine_build": "fake-build",
            "dll": "InfinityEngine-Enhancer.dll",
            "dll_sha256": sha256(runtime_dll),
            "tests": "fake-tests.exe",
            "bridge_worker_tests": "fake-bridge-tests.exe",
            "bridge_worker_tests_status": "passed",
            "tests_status": "passed",
            "catalog_magic": "IEECSNC",
            "catalog_version": catalog_version,
            "catalog_shard_registry_magic": "IEECSXN",
            "catalog_shard_registry_version": shard_version,
            "catalog_shard_animation_id_sentinel": "0xFFFF",
            "catalog_limits": {
                "maximum_animations": 512,
                "maximum_components": 16384,
                "maximum_memberships": 262144,
                "maximum_shards": 16384,
                "maximum_physical_resources": 32768,
                "maximum_frames": 4194304,
                "maximum_registry_bytes": 137438953472,
                "maximum_resources_per_shard": 128,
                "maximum_frames_per_resource": 4096,
                "maximum_lazy_frame_index_bytes": 134217728,
                "maximum_x2_shard_bytes": 134217728,
                "maximum_x4_shard_bytes": 536870912,
            },
        }
        if catalog_version == 2:
            runtime_manifest.update(
                {
                    "catalog_directory_count": len(directory_entries),
                    "catalog_directory_entry_bytes": 24,
                    "catalog_directory_sha256": directory_sha256,
                    "catalog_logical_content_sha256": manifest_logical_sha256,
                }
            )
            runtime_manifest["catalog_limits"]["maximum_directory_entries"] = 1_048_576
        if shard_version == 5:
            runtime_manifest["catalog_frame_storage"] = "XPRESS_HUFF-or-raw-per-frame-v1"
        runtime_manifest_path = runtime / "runtime-manifest.json"
        write_json(runtime_manifest_path, runtime_manifest)
        pointer = {
            "schema": "bg2-upscale-creature-sprite-xn-catalog-current-generation-v1",
            "generation_id": generation_id,
            "job_sha256": sha256(job_file),
            "generation_dir": project_relative(generation),
            "build_manifest": "build/build-manifest.json",
            "build_manifest_sha256": sha256(build_manifest_path),
            "runtime_manifest": "runtime/runtime-manifest.json",
            "runtime_manifest_sha256": sha256(runtime_manifest_path),
        }
        write_json(self.run / "current-generation.json", pointer)
        return {
            "id": generation_id,
            "catalog": catalog_path,
            "catalog_sha256": sha256(catalog_path),
            "shards": [sprite_dir / Path(item["registry"]).name for item in shards],
        }

    def powershell(
        self,
        script: Path,
        *switches: str,
        expect_ok: bool = True,
        job_file: Path | None = None,
    ) -> subprocess.CompletedProcess:
        job_file = self.job if job_file is None else job_file
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-JobFile",
            str(job_file),
            *switches,
        ]
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        if expect_ok and result.returncode != 0:
            raise AssertionError(f"PowerShell failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        if not expect_ok and result.returncode == 0:
            raise AssertionError(f"PowerShell unexpectedly succeeded\n{result.stdout}")
        return result


class CreatureSpriteXNCatalogInstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = FakeCatalogWorkspace()

    def tearDown(self) -> None:
        self.fake.close()

    def test_verify_install_is_read_only_and_divergent_shard_fails_closed(self) -> None:
        generation = self.fake.write_generation("generation-one", [(0x6102, "CDMB1")])
        baseline_dll = (self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes()
        baseline_ini = (self.fake.game / "InfinityEngine-Enhancer.ini").read_bytes()
        self.fake.powershell(INSTALL, "-VerifyOnly")
        self.assertEqual((self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes(), baseline_dll)
        self.assertEqual((self.fake.game / "InfinityEngine-Enhancer.ini").read_bytes(), baseline_ini)
        self.assertFalse((self.fake.run / "ingame-installation/active-test.json").exists())

        shard = generation["shards"][0]
        live_shard = self.fake.game / "iee-assets/creature-sprites" / shard.name
        live_shard.parent.mkdir(parents=True)
        live_shard.write_bytes(b"divergent")
        result = self.fake.powershell(INSTALL, expect_ok=False)
        self.assertIn("content-addressed divergent", result.stderr)
        self.assertFalse((self.fake.run / "ingame-installation/active-test.json").exists())

    def test_leaf_payload_change_invalidates_generation(self) -> None:
        self.fake.write_generation("generation-one", [(0x6102, "CDMB1")])
        payload = self.fake.provenance / "member-6102-payload.registry"
        payload.write_bytes(payload.read_bytes() + b"changed")
        result = self.fake.powershell(INSTALL, "-VerifyOnly", expect_ok=False)
        self.assertIn("Payload leaf", result.stderr)
        self.assertFalse((self.fake.run / "ingame-installation/active-test.json").exists())

    def test_reparse_point_in_game_target_is_rejected(self) -> None:
        generation = self.fake.write_generation("generation-one", [(0x6102, "CDMB1")])
        source_shard = generation["shards"][0]
        outside = self.fake.root / "outside-shard.registry"
        outside.write_bytes(source_shard.read_bytes())
        live = self.fake.game / "iee-assets/creature-sprites" / source_shard.name
        live.parent.mkdir(parents=True)
        try:
            os.symlink(outside, live)
        except OSError as error:
            self.skipTest(f"Windows symlink unavailable: {error}")
        try:
            result = self.fake.powershell(INSTALL, "-VerifyOnly", expect_ok=False)
            self.assertIn("ReparsePoint", result.stderr)
            self.assertEqual(outside.read_bytes(), source_shard.read_bytes())
            self.assertFalse((self.fake.run / "ingame-installation/active-test.json").exists())
        finally:
            live.unlink(missing_ok=True)

    def test_reparse_point_game_root_is_rejected_by_install_and_restore(self) -> None:
        self.fake.write_generation("generation-one", [(0x6102, "CDMB1")])
        game = self.fake.game
        backing = self.fake.root / "fake-game-backing"

        def replace_game_with_link() -> None:
            game.rename(backing)
            try:
                os.symlink(backing, game, target_is_directory=True)
            except OSError:
                backing.rename(game)
                raise

        def restore_real_game() -> None:
            if game.is_symlink():
                game.unlink()
            if backing.exists():
                backing.rename(game)

        try:
            try:
                replace_game_with_link()
            except OSError as error:
                self.skipTest(f"Windows directory symlink unavailable: {error}")
            result = self.fake.powershell(
                INSTALL, "-VerifyOnly", expect_ok=False
            )
            self.assertIn("ReparsePoint", result.stderr)
            restore_real_game()

            self.fake.powershell(INSTALL)
            replace_game_with_link()
            result = self.fake.powershell(
                RESTORE, "-VerifyOnly", expect_ok=False
            )
            self.assertIn("ReparsePoint", result.stderr)
        finally:
            restore_real_game()

    def test_install_append_and_two_level_restore_are_exact(self) -> None:
        baseline_dll = (self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes()
        baseline_ini = (self.fake.game / "InfinityEngine-Enhancer.ini").read_bytes()
        first_job = self.fake.root / "catalog-job-generation-one.json"
        second_job = self.fake.root / "catalog-job-generation-two.json"
        first_job_value = dict(self.fake.job_value)
        first_job_value["test_generation"] = "generation-one"
        second_job_value = dict(self.fake.job_value)
        second_job_value["test_generation"] = "generation-two"
        write_json(first_job, first_job_value)
        write_json(second_job, second_job_value)
        self.assertNotEqual(sha256(first_job), sha256(second_job))

        first = self.fake.write_generation(
            "generation-one", [(0x6102, "CDMB1")], job_file=first_job
        )
        self.fake.powershell(INSTALL, job_file=first_job)
        active_path = self.fake.run / "ingame-installation/active-test.json"
        first_state_bytes = active_path.read_bytes()
        first_state = json.loads(first_state_bytes)
        self.assertEqual(first_state["status"], "installed-pending-qa")
        self.assertEqual(first_state["animation_ids"], ["0x6102"])
        live_catalog = self.fake.game / "iee-assets/creature-sprites/CreatureSprites-XN.catalog"
        self.assertEqual(sha256(live_catalog), first["catalog_sha256"])
        owner = json.loads(
            (self.fake.game / "iee-assets/creature-sprites/CreatureSprites-XN.catalog-owner.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(owner["status"], "active")

        second = self.fake.write_generation(
            "generation-two",
            [(0x6102, "CDMB1"), (0x6110, "CHF1")],
            job_file=second_job,
        )
        self.fake.powershell(INSTALL, job_file=second_job)
        second_state = json.loads(active_path.read_text(encoding="utf-8"))
        self.assertEqual(second_state["animation_ids"], ["0x6102", "0x6110"])
        self.assertEqual(sha256(live_catalog), second["catalog_sha256"])
        for shard in second["shards"]:
            self.assertTrue((live_catalog.parent / shard.name).is_file())

        self.fake.powershell(RESTORE, "-VerifyOnly", job_file=second_job)
        self.fake.powershell(RESTORE, job_file=second_job)
        self.assertEqual(active_path.read_bytes(), first_state_bytes)
        self.assertEqual(sha256(live_catalog), first["catalog_sha256"])
        self.assertFalse((live_catalog.parent / second["shards"][1].name).exists())
        restored_pointer = json.loads(
            (self.fake.run / "current-generation.json").read_text(encoding="utf-8")
        )
        self.assertEqual(restored_pointer["generation_id"], first["id"])
        self.assertEqual(restored_pointer["job_sha256"], sha256(first_job))

        # La restauration scellée ne dépend plus des sources de construction
        # live une fois generation-one réactivée.
        for relative in SOURCE_FILES:
            engine_source = self.fake.engine / relative
            engine_source.write_bytes(engine_source.read_bytes() + b"changed-after-build\n")
        for provenance_file in self.fake.provenance.iterdir():
            if provenance_file.is_file():
                provenance_file.write_bytes(provenance_file.read_bytes() + b"changed-after-build\n")
        self.fake.powershell(RESTORE, job_file=first_job)
        restored = json.loads(active_path.read_text(encoding="utf-8"))
        self.assertEqual(restored["status"], "restored")
        self.assertEqual((self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes(), baseline_dll)
        self.assertEqual((self.fake.game / "InfinityEngine-Enhancer.ini").read_bytes(), baseline_ini)
        self.assertFalse(live_catalog.exists())
        self.assertFalse(
            (self.fake.game / "iee-assets/creature-sprites/CreatureSprites-XN.catalog-owner.json").exists()
        )

    def test_runtime_refresh_preserves_catalog_and_restores_previous_runtime(self) -> None:
        first = self.fake.write_generation(
            "runtime-refresh-one",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-one",
        )
        self.fake.powershell(INSTALL)
        active_path = self.fake.run / "ingame-installation/active-test.json"
        first_state_bytes = active_path.read_bytes()
        first_dll = (self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes()
        live_ini = self.fake.game / "InfinityEngine-Enhancer.ini"
        live_ini.write_text(
            "[Rendering]\nUnrelated = preserved\n[Shaders]\n"
            "EnableCreatureSpriteLinearFiltering = false\n"
            "EnableCreatureSpriteUpscaleTest = true\n"
            "EnableCreatureSpriteX2Test = false\n",
            encoding="utf-8",
        )
        live_catalog = self.fake.game / "iee-assets/creature-sprites/CreatureSprites-XN.catalog"
        first_catalog_bytes = live_catalog.read_bytes()
        first_catalog_mtime = live_catalog.stat().st_mtime_ns

        engine_file = self.fake.engine / SOURCE_FILES[0]
        engine_file.write_bytes(engine_file.read_bytes() + b"runtime-refresh\n")
        second = self.fake.write_generation(
            "runtime-refresh-two",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-two",
        )
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["catalog_sha256"], second["catalog_sha256"])

        verified = self.fake.powershell(INSTALL, "-VerifyOnly")
        self.assertIn("runtime-refresh", verified.stdout)
        self.fake.powershell(INSTALL)
        refreshed = json.loads(active_path.read_text(encoding="utf-8"))
        self.assertEqual(refreshed["installation_mode"], "runtime-refresh")
        self.assertEqual(refreshed["generation_id"], second["id"])
        self.assertEqual(live_catalog.read_bytes(), first_catalog_bytes)
        self.assertEqual(live_catalog.stat().st_mtime_ns, first_catalog_mtime)
        self.assertEqual(
            (self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes(), b"runtime-two"
        )
        self.assertIn("Unrelated = preserved", live_ini.read_text(encoding="utf-8"))

        live_ini.write_text(
            "[Shaders]\nEnableCreatureSpriteX2Test = false\n"
            "EnableCreatureSpriteUpscaleTest = true\n"
            "EnableCreatureSpriteLinearFiltering = false\n"
            "[Rendering]\nUnrelated = changed-order\n",
            encoding="utf-8",
        )
        self.fake.powershell(RESTORE, "-VerifyOnly")
        self.fake.powershell(RESTORE)
        self.assertEqual(active_path.read_bytes(), first_state_bytes)
        self.assertEqual(live_catalog.read_bytes(), first_catalog_bytes)
        self.assertEqual((self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes(), first_dll)
        self.assertIn("Unrelated = preserved", live_ini.read_text(encoding="utf-8"))

    def test_runtime_refresh_rejects_unchanged_dll_and_changed_content(self) -> None:
        self.fake.write_generation(
            "runtime-refresh-base",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-one",
        )
        self.fake.powershell(INSTALL)

        engine_file = self.fake.engine / SOURCE_FILES[0]
        engine_file.write_bytes(engine_file.read_bytes() + b"refresh-same-dll\n")
        self.fake.write_generation(
            "runtime-refresh-same-dll",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-one",
        )
        rejected = self.fake.powershell(INSTALL, "-VerifyOnly", expect_ok=False)
        self.assertIn("nouvelle DLL runtime", rejected.stderr)

        engine_file.write_bytes(engine_file.read_bytes() + b"refresh-changed-content\n")
        self.fake.write_generation(
            "runtime-refresh-changed-content",
            [(0x6110, "CHF1")],
            runtime_dll_bytes=b"runtime-three",
        )
        rejected = self.fake.powershell(INSTALL, "-VerifyOnly", expect_ok=False)
        self.assertIn("runtime-refresh", rejected.stderr)

    def test_storage_repack_migrates_v1_v3_to_v2_v5_and_restores_exactly(self) -> None:
        first = self.fake.write_generation(
            "runtime-refresh-v1",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-v1",
            catalog_version=1,
        )
        self.fake.powershell(INSTALL)
        active_path = self.fake.run / "ingame-installation/active-test.json"
        first_state_bytes = active_path.read_bytes()
        live_catalog = self.fake.game / "iee-assets/creature-sprites/CreatureSprites-XN.catalog"
        old_live_shard = (
            self.fake.game
            / "iee-assets/creature-sprites"
            / first["shards"][0].name
        )
        self.assertTrue(old_live_shard.is_file())
        self.assertEqual(live_catalog.read_bytes()[8:12], struct.pack("<I", 1))

        engine_file = self.fake.engine / SOURCE_FILES[0]
        engine_file.write_bytes(engine_file.read_bytes() + b"catalog-v2\n")
        second = self.fake.write_generation(
            "runtime-refresh-v2",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-v2",
            catalog_version=2,
        )
        self.assertNotEqual(first["catalog_sha256"], second["catalog_sha256"])
        verified = self.fake.powershell(INSTALL, "-VerifyOnly")
        self.assertIn("storage-repack", verified.stdout)
        self.fake.powershell(INSTALL)
        refreshed = json.loads(active_path.read_text(encoding="utf-8"))
        self.assertEqual(refreshed["installation_mode"], "storage-repack")
        self.assertEqual(refreshed["catalog_version"], 2)
        self.assertEqual(refreshed["shard_registry_version"], 5)
        self.assertEqual(refreshed["directory_count"], 1)
        self.assertEqual(refreshed["directory_entry_bytes"], 24)
        self.assertEqual(live_catalog.read_bytes()[8:12], struct.pack("<I", 2))
        self.assertFalse(old_live_shard.exists())

        self.fake.powershell(RESTORE, "-VerifyOnly")
        self.fake.powershell(RESTORE)
        self.assertEqual(active_path.read_bytes(), first_state_bytes)
        self.assertEqual(live_catalog.read_bytes()[8:12], struct.pack("<I", 1))
        self.assertEqual(sha256(live_catalog), first["catalog_sha256"])
        self.assertTrue(old_live_shard.is_file())
        self.assertEqual(sha256(old_live_shard), sha256(first["shards"][0]))

    def test_v2_directory_must_match_physical_shard_resource(self) -> None:
        self.fake.write_generation(
            "catalog-v2-bad-directory",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-v2",
            catalog_version=2,
            directory_resref_override="WRONG",
        )
        rejected = self.fake.powershell(INSTALL, "-VerifyOnly", expect_ok=False)
        self.assertIn("directory V2 divergente", rejected.stderr)
        self.assertFalse(
            (self.fake.run / "ingame-installation/active-test.json").exists()
        )

    def test_v5_compressed_payload_and_sealed_logical_digest_tamper_fail_closed(self) -> None:
        self.fake.write_generation(
            "catalog-v5-corrupt-compressed",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-v5-corrupt",
            catalog_version=2,
            corrupt_compressed=True,
        )
        rejected = self.fake.powershell(INSTALL, "-VerifyOnly", expect_ok=False)
        self.assertTrue(
            "XPRESS_HUFF" in rejected.stderr
            or "Digests logiques" in rejected.stderr
        )
        self.assertFalse(
            (self.fake.run / "ingame-installation/active-test.json").exists()
        )

        engine_file = self.fake.engine / SOURCE_FILES[0]
        engine_file.write_bytes(engine_file.read_bytes() + b"logical-manifest-tamper\n")
        self.fake.write_generation(
            "catalog-v5-logical-manifest-tamper",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-v5-logical-tamper",
            catalog_version=2,
            logical_manifest_semantic_index=1,
        )
        rejected = self.fake.powershell(INSTALL, "-VerifyOnly", expect_ok=False)
        self.assertIn("Digests logiques", rejected.stderr)

    def test_storage_repack_rejects_semantic_difference(self) -> None:
        self.fake.write_generation(
            "storage-repack-semantic-v1",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-v1",
            catalog_version=1,
            semantic_index=0,
        )
        self.fake.powershell(INSTALL)
        engine_file = self.fake.engine / SOURCE_FILES[0]
        engine_file.write_bytes(engine_file.read_bytes() + b"semantic-change\n")
        self.fake.write_generation(
            "storage-repack-semantic-v2",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-v2",
            catalog_version=2,
            semantic_index=1,
        )
        rejected = self.fake.powershell(INSTALL, "-VerifyOnly", expect_ok=False)
        self.assertIn("contenu logique", rejected.stderr)

    def test_recover_interrupted_storage_repack_restores_v1_v3_exactly(self) -> None:
        first = self.fake.write_generation(
            "refresh-recovery-v1",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-v1",
            catalog_version=1,
        )
        self.fake.powershell(INSTALL)
        active_path = self.fake.run / "ingame-installation/active-test.json"
        first_state_bytes = active_path.read_bytes()
        old_live_shard = (
            self.fake.game
            / "iee-assets/creature-sprites"
            / first["shards"][0].name
        )
        old_live_shard_sha256 = sha256(old_live_shard)

        engine_file = self.fake.engine / SOURCE_FILES[0]
        engine_file.write_bytes(engine_file.read_bytes() + b"refresh-recovery-v2\n")
        self.fake.write_generation(
            "refresh-recovery-v2",
            [(0x6102, "CDMB1")],
            runtime_dll_bytes=b"runtime-v2",
            catalog_version=2,
        )
        self.fake.powershell(INSTALL)
        self.assertFalse(old_live_shard.exists())
        interrupted = json.loads(active_path.read_text(encoding="utf-8"))
        interrupted["status"] = "installing"
        write_json(active_path, interrupted)

        self.fake.powershell(RESTORE, "-RecoverInterrupted")
        self.assertEqual(active_path.read_bytes(), first_state_bytes)
        self.assertEqual(
            (self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes(), b"runtime-v1"
        )
        live_catalog = self.fake.game / "iee-assets/creature-sprites/CreatureSprites-XN.catalog"
        self.assertEqual(sha256(live_catalog), first["catalog_sha256"])
        self.assertTrue(old_live_shard.is_file())
        self.assertEqual(sha256(old_live_shard), old_live_shard_sha256)
        pointer = json.loads(
            (self.fake.run / "current-generation.json").read_text(encoding="utf-8")
        )
        self.assertEqual(pointer["generation_id"], first["id"])

    def test_recover_interrupted_install_restores_baseline(self) -> None:
        self.fake.write_generation("generation-one", [(0x6102, "CDMB1")])
        baseline_dll = (self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes()
        self.fake.powershell(INSTALL)
        state_path = self.fake.run / "ingame-installation/active-test.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["status"] = "installing"
        write_json(state_path, state)
        self.fake.powershell(RESTORE, "-RecoverInterrupted")
        restored = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertEqual(restored["status"], "restored")
        self.assertTrue(restored["recovered_interrupted_transaction"])
        self.assertEqual((self.fake.game / "InfinityEngine-Enhancer.dll").read_bytes(), baseline_dll)

    def test_initial_migration_accepts_only_declared_parent_chain(self) -> None:
        top, parent, _extra = self.fake.add_import_chain()
        top_bytes = top.read_bytes()
        parent_bytes = parent.read_bytes()
        self.fake.write_generation("generation-import", [(0x6102, "CDMB1")])
        self.fake.powershell(INSTALL)
        state = json.loads(
            (self.fake.run / "ingame-installation/active-test.json").read_text(
                encoding="utf-8"
            )
        )
        imported = state["imported_active_state"]
        self.assertEqual(imported["job_id"], "import-top")
        self.assertEqual([item["job_id"] for item in imported["parents"]], ["import-parent"])
        self.assertEqual(top.read_bytes(), top_bytes)
        self.assertEqual(parent.read_bytes(), parent_bytes)
        self.fake.powershell(RESTORE)
        self.assertEqual(top.read_bytes(), top_bytes)
        self.assertEqual(parent.read_bytes(), parent_bytes)

    def test_initial_migration_rejects_state_outside_parent_chain(self) -> None:
        self.fake.add_import_chain(unrelated=True)
        self.fake.write_generation("generation-import", [(0x6102, "CDMB1")])
        result = self.fake.powershell(INSTALL, "-VerifyOnly", expect_ok=False)
        self.assertIn("parent_active_tests", result.stderr)
        self.assertFalse((self.fake.run / "ingame-installation/active-test.json").exists())


if __name__ == "__main__":
    unittest.main()
