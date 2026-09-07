from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pipeline" / "scripts"
TOOLS = ROOT / "engine" / "InfinityEngine-Enhancer" / "source-patchee" / "tools"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(TOOLS))

import compose_effect_runtime_packs as compose  # noqa: E402
import install_renderer_candidate as installer  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class ComposeEffectRuntimePacksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_pack(self, name: str, resref: str, version: int = 2) -> Path:
        root = self.root / name
        root.mkdir()
        asset = f"EFX4-{resref}-frame000.rgba"
        (root / asset).write_bytes(resref.encode("ascii") * 8)
        record = resref.encode("ascii").ljust(8, b"\0") + struct.pack("<II", 1, 1)
        record += struct.pack("<II", 1, 1) + struct.pack("<II", 1, 0)
        if version == 2:
            record += struct.pack("<IIIII", 15, 1, 30, 1, 1) + struct.pack("<I", 0)
        registry = compose.REGISTRY_HEADER.pack(
            compose.REGISTRY_MAGIC, version, 4, 1, 0
        ) + record
        registry_path = root / compose.REGISTRY_NAME
        registry_path.write_bytes(registry)
        manifest = {
            "schema": compose.PACK_SCHEMA,
            "status": "completed",
            "resref": resref,
            "scale": 4,
            "registry": compose.REGISTRY_NAME,
            "registry_magic": "IEEEFX4",
            "registry_version": version,
            "registry_bytes": len(registry),
            "registry_sha256": sha256(registry_path),
            "frame_count": 1,
            "cycles": [{"cycle": 0, "frame_indices": [0]}],
            "frames": [
                {
                    "frame": 0,
                    "asset": asset,
                    "bytes": (root / asset).stat().st_size,
                    "sha256": sha256(root / asset),
                }
            ],
            "source": {"fixture": name},
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest) + "\n", encoding="utf-8"
        )
        return root

    def test_composes_v2_packs_and_remains_installer_compatible(self) -> None:
        first = self.write_pack("first", "FXONE")
        second = self.write_pack("second", "FXTWO")
        output = self.root / "combined"
        with mock.patch.object(compose, "REPO_ROOT", self.root):
            packs = [compose.validate_pack(first), compose.validate_pack(second)]
            registry, manifest, copies = compose.compose(packs)
            compose.write_pack(output, registry, manifest, copies)

        header = compose.REGISTRY_HEADER.unpack_from(
            output.joinpath(compose.REGISTRY_NAME).read_bytes()
        )
        self.assertEqual(header[1:4], (2, 4, 2))
        self.assertEqual([item["resref"] for item in manifest["resources"]], ["FXONE", "FXTWO"])
        self.assertEqual([item["frame"] for item in manifest["frames"]], [0, 1])
        self.assertEqual(len(installer.validate_effect_pack(output)), 4)

    def test_rejects_duplicate_resrefs(self) -> None:
        first = self.write_pack("first", "DUPFX")
        second = self.write_pack("second", "DUPFX")
        with mock.patch.object(compose, "REPO_ROOT", self.root):
            packs = [compose.validate_pack(first), compose.validate_pack(second)]
            with self.assertRaisesRegex(compose.PackError, "plusieurs packs"):
                compose.compose(packs)

    def test_rejects_mixed_native_and_timeline_versions(self) -> None:
        first = self.write_pack("native", "NATIVE", version=1)
        second = self.write_pack("timeline", "TIMELINE", version=2)
        with mock.patch.object(compose, "REPO_ROOT", self.root):
            packs = [compose.validate_pack(first), compose.validate_pack(second)]
            with self.assertRaisesRegex(compose.PackError, "ne peuvent pas être mélangés"):
                compose.compose(packs)


if __name__ == "__main__":
    unittest.main()
