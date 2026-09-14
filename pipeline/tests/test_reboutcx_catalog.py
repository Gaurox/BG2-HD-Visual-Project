from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import reboutcx_catalog as catalog  # noqa: E402
import reboutcx_full as full  # noqa: E402
from run_creature_sprite_x2 import SourceFrame, inspect_registry  # noqa: E402


def shard(index: int, resref: str) -> dict[str, object]:
    digest = f"{index + 1:064X}"
    return {
        "index": index,
        "registry": f"iee-assets/creature-sprites/CreatureSprites-XN-{digest}.registry",
        "sha256": digest,
        "crc32": index,
        "resource_count": 1,
        "frame_count": 1,
        "index_bytes": 4,
        "registry_bytes": 600,
        "resref": resref,
    }


def component(index: int) -> dict[str, object]:
    return {
        "index": index,
        "digest": f"{index + 11:064X}",
        "shard_start": index,
        "shard_count": 1,
        "resource_count": 1,
        "frame_count": 1,
        "index_bytes": 4,
        "registry_bytes": 600,
    }


def parent(shared_target: bool = False) -> dict[str, object]:
    count = 2 if shared_target else 3
    animations = [
        {"animation_id": "0x0001", "owner": 3, "component_indices": [0]},
        {"animation_id": "0x0002", "owner": 3, "component_indices": [1]},
        {"animation_id": "0x0003", "owner": 2, "component_indices": [1 if shared_target else 2]},
    ]
    resrefs = {"0x0001": "ONE", "0x0002": "TWO", "0x0003": "TWO" if shared_target else "THREE"}
    directory = []
    for animation in animations:
        index = animation["component_indices"][0]
        directory.append(
            {
                "animation_id": animation["animation_id"],
                "resref": resrefs[animation["animation_id"]],
                "component_index": index,
                "shard_index": index,
                "resource_ordinal": 0,
            }
        )
    return {
        "index": {
            "animations": animations,
            "components": [component(index) for index in range(count)],
            "shards": [shard(index, ("ONE", "TWO", "THREE")[index]) for index in range(count)],
            "directory": directory,
        },
        "logical_digests": [f"{index + 21:064X}" for index in range(count)],
    }


def replacement() -> dict[str, object]:
    new_shard = shard(9, "TWO")
    new_shard["resources"] = ["TWO"]
    return {
        "animation_id": "0x0002",
        "old_component_index": 1,
        "new_component_digest": f"{99:064X}",
        "new_shards": [new_shard],
        "new_shard_resources": [["TWO"]],
        "logical_digest": f"{199:064X}",
    }


def multi_component_parent(*, ambiguous: bool = False) -> dict[str, object]:
    weapon_resref = "BODY" if ambiguous else "WEAPON"
    animations = [
        {"animation_id": "0x0001", "owner": 3, "component_indices": [0]},
        {"animation_id": "0x0002", "owner": 1, "component_indices": [1, 2]},
        {"animation_id": "0x0003", "owner": 2, "component_indices": [2]},
    ]
    directory = [
        {
            "animation_id": "0x0001",
            "resref": "BASE",
            "component_index": 0,
            "shard_index": 0,
            "resource_ordinal": 0,
        },
        {
            "animation_id": "0x0002",
            "resref": "BODY",
            "component_index": 1,
            "shard_index": 1,
            "resource_ordinal": 0,
        },
        {
            "animation_id": "0x0002",
            "resref": weapon_resref,
            "component_index": 2,
            "shard_index": 2,
            "resource_ordinal": 0,
        },
        {
            "animation_id": "0x0003",
            "resref": weapon_resref,
            "component_index": 2,
            "shard_index": 2,
            "resource_ordinal": 0,
        },
    ]
    return {
        "index": {
            "animations": animations,
            "components": [component(index) for index in range(3)],
            "shards": [
                shard(0, "BASE"),
                shard(1, "BODY"),
                shard(2, weapon_resref),
            ],
            "directory": directory,
        },
        "logical_digests": [f"{index + 21:064X}" for index in range(3)],
    }


def component_replacement(index: int, resref: str) -> dict[str, object]:
    new_shard = shard(index + 9, resref)
    new_shard["resources"] = [resref]
    return {
        "animation_id": "0x0002",
        "old_component_index": index,
        "new_component_digest": f"{index + 99:064X}",
        "new_shards": [new_shard],
        "new_shard_resources": [[resref]],
        "logical_digest": f"{index + 199:064X}",
    }


def make_frame() -> SourceFrame:
    palette = np.zeros((256, 3), dtype=np.uint8)
    palette[0] = (0, 255, 0)
    palette[3] = (180, 40, 20)
    indices = np.asarray([[0, 3]], dtype=np.uint8)
    rgba = np.empty((1, 2, 4), dtype=np.uint8)
    rgba[..., :3] = palette[indices]
    rgba[..., 3] = np.where(indices == 0, 0, 255).astype(np.uint8)
    return SourceFrame("TEST", 0, 2, 1, 1, -2, 0, indices, palette, rgba.tobytes())


class ReboutCXCatalogTests(unittest.TestCase):
    def test_animation_id_uses_catalog_notation(self) -> None:
        self.assertEqual(catalog.normalize_animation_id("0X7f02"), "0x7F02")

    def test_orphaned_parent_component_is_removed_and_indices_are_compacted(self) -> None:
        value = parent()
        assembled = catalog.assemble_catalog(value, [replacement()])
        self.assertEqual(assembled["dropped_components"], [1])
        self.assertEqual(assembled["kept_component_indices"], [0, 2])
        self.assertEqual(assembled["kept_shard_indices"], [0, 2])
        mappings = {
            item["animation_id"]: item["component_indices"]
            for item in assembled["animations"]
        }
        self.assertEqual(mappings, {"0x0001": [0], "0x0002": [2], "0x0003": [1]})
        self.assertEqual(assembled["logical_digests"], [f"{21:064X}", f"{23:064X}", f"{199:064X}"])
        result = catalog.validate_diff(value, assembled, [replacement()])
        self.assertEqual(result["unchanged_animations"], 2)

    def test_shared_parent_component_remains_available_to_unrelated_animation(self) -> None:
        value = parent(shared_target=True)
        assembled = catalog.assemble_catalog(value, [replacement()])
        self.assertEqual(assembled["dropped_components"], [])
        self.assertEqual(assembled["kept_component_indices"], [0, 1])
        mappings = {
            item["animation_id"]: item["component_indices"]
            for item in assembled["animations"]
        }
        self.assertEqual(mappings, {"0x0001": [0], "0x0002": [2], "0x0003": [1]})
        catalog.validate_diff(value, assembled, [replacement()])

    def test_two_components_of_one_animation_are_replaced_without_flattening(self) -> None:
        value = multi_component_parent()
        replacements = [
            component_replacement(1, "BODY"),
            component_replacement(2, "WEAPON"),
        ]
        assembled = catalog.assemble_catalog(value, replacements)
        mappings = {
            item["animation_id"]: item["component_indices"]
            for item in assembled["animations"]
        }
        self.assertEqual(mappings, {"0x0001": [0], "0x0002": [2, 3], "0x0003": [1]})
        self.assertEqual(len(mappings["0x0002"]), 2)
        self.assertEqual(assembled["dropped_components"], [1])
        result = catalog.validate_diff(value, assembled, replacements)
        self.assertEqual(result["targeted_component_memberships_replaced"], 2)
        self.assertEqual(result["untargeted_component_memberships_preserved"], 2)

    def test_ambiguous_resref_across_animation_components_is_refused(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "ambiguous replacement resref"):
            catalog.validate_component_selection(
                multi_component_parent(ambiguous=True), "0x0002", 1, ["BODY"]
            )

    def test_duplicate_component_target_is_refused(self) -> None:
        value = multi_component_parent()
        target = component_replacement(1, "BODY")
        with self.assertRaisesRegex(RuntimeError, "duplicate replacement component target"):
            catalog.assemble_catalog(value, [target, dict(target)])

    def test_resource_contract_ignores_indices_but_pins_metadata(self) -> None:
        frame = make_frame()
        source_hash = hashlib.sha256(b"source").hexdigest().upper()
        payloads = (
            np.asarray([[0, 0, 3, 3], [0, 0, 3, 3]], dtype=np.uint8),
            np.asarray([[0, 3, 3, 3], [0, 0, 0, 3]], dtype=np.uint8),
        )
        with tempfile.TemporaryDirectory() as temporary:
            digests = []
            for index, payload in enumerate(payloads):
                path = Path(temporary) / f"component-{index}.registry"
                with path.open("wb") as stream:
                    full.write_component_header(
                        stream,
                        animation_id=0x7F02,
                        resref="TEST",
                        source_sha256=source_hash,
                        frame_count=1,
                        cycle_count=1,
                    )
                    full.write_frame_record(stream, frame, payload)
                    full.write_cycles(stream, [{"index": 0, "frame_indices": [0]}])
                record = inspect_registry(path, include_resource_records=True)["resource_records"][0]
                digests.append(catalog.resource_contract_digest(record))
            self.assertEqual(digests[0], digests[1])


if __name__ == "__main__":
    unittest.main()
