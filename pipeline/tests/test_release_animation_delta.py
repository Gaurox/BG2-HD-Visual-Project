from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
RELEASE_ROOT = ROOT / "releases" / "BG2-HD-Upscale"
CONTENT_GENERATOR = RELEASE_ROOT / "tools" / "New-BG2HD-ContentManifest.ps1"
ASSET_VALIDATOR_PATH = RELEASE_ROOT / "tools" / "Validate-BG2HD-Assets.py"


def load_asset_validator():
    spec = importlib.util.spec_from_file_location("bg2hd_asset_validator", ASSET_VALIDATOR_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ASSET_VALIDATOR = load_asset_validator()


class AreaAnimationDeltaTests(unittest.TestCase):
    def test_area_animation_only_validator_skips_maps_and_ui(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            content_path = Path(temporary) / "content.json"
            content_path.write_text(
                json.dumps({"entries": [{"kind": "area-animation"}]}),
                encoding="utf-8",
            )
            with mock.patch.object(
                ASSET_VALIDATOR,
                "validate_area_animations",
                return_value={"components": 1, "frames": 1, "files": 3},
            ) as validate:
                with mock.patch.object(
                    sys,
                    "argv",
                    [
                        "Validate-BG2HD-Assets.py",
                        "--workspace",
                        temporary,
                        "--content",
                        str(content_path),
                        "--area-animation-only",
                    ],
                ):
                    self.assertEqual(ASSET_VALIDATOR.main(), 0)
            validate.assert_called_once()

    def test_area_animation_only_validator_rejects_mixed_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            content_path = Path(temporary) / "content.json"
            content_path.write_text(
                json.dumps({"entries": [{"kind": "map"}, {"kind": "area-animation"}]}),
                encoding="utf-8",
            )
            with mock.patch.object(
                sys,
                "argv",
                [
                    "Validate-BG2HD-Assets.py",
                    "--workspace",
                    temporary,
                    "--content",
                    str(content_path),
                    "--area-animation-only",
                ],
            ):
                with self.assertRaisesRegex(ValueError, "uniquement des area-animation"):
                    ASSET_VALIDATOR.main()

    @unittest.skipUnless(shutil.which("pwsh"), "pwsh is required to exercise the release generator")
    def test_delta_generator_writes_only_requested_animation_area(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            pack = workspace / "testpack"
            pack.mkdir()
            frame = pack / "AAX4-FOO-frame000.rgba"
            frame.write_bytes(b"\x00" * 8)
            registry = pack / "AreaAnimations-X4.registry"
            registry.write_bytes(b"IEEAAX4\0" + struct.pack("<4I", 2, 4, 1, 0))

            def digest(path: Path) -> str:
                return hashlib.sha256(path.read_bytes()).hexdigest().upper()

            manifest = {
                "schema": "bg2-upscale-area-animation-runtime-pack-v2",
                "status": "completed",
                "scale": 4,
                "registry_version": 2,
                "registry_sha256": digest(registry),
                "registry_bytes": registry.stat().st_size,
                "resource_count": 1,
                "frame_count": 1,
                "area_id": "AR1234",
                "runtime_contract": {"feature": "TimedTimeline", "registry_version": 2},
                "resources": [
                    {
                        "resref": "FOO",
                        "frame_count": 1,
                        "frames": [
                            {
                                "frame": 0,
                                "asset": frame.name,
                                "sha256": digest(frame),
                                "bytes": frame.stat().st_size,
                                "physical_size_x4": [1, 2],
                            }
                        ],
                    }
                ],
            }
            pack_manifest = pack / "manifest.json"
            pack_manifest.write_text(json.dumps(manifest), encoding="utf-8")

            index = workspace / "animations" / "index"
            index.mkdir(parents=True)
            (index / "animation_upscale_registry.csv").write_text(
                "resref,status,areas\nFOO,validé-x4,AR1234\n", encoding="utf-8"
            )
            registry_index = index / "animation_upscale_registry.csv"
            qa_approval = (
                workspace
                / "releases"
                / "BG2-HD-Upscale"
                / "manifests"
                / "animation-qa-approvals"
                / "AR1234"
                / "qa-approval.json"
            )
            qa_approval.parent.mkdir(parents=True)
            qa_approval.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "area": "AR1234",
                        "status": "accepted",
                        "decision_date": "2026-08-30",
                        "decision_origin": "preserved-existing-user-qa",
                        "recorded_at_utc": "2026-08-30T00:00:00Z",
                        "source_pack": "testpack",
                        "pack_manifest_sha256": digest(pack_manifest),
                        "registry": registry.name,
                        "registry_version": 2,
                        "registry_sha256": digest(registry),
                        "required_resrefs": ["FOO"],
                        "evidence": [
                            {
                                "kind": "canonical-registry",
                                "path": "animations/index/animation_upscale_registry.csv",
                                "sha256": digest(registry_index),
                                "accepted_resrefs": ["FOO"],
                            }
                        ],
                        "decision": "Existing test approval preserved for provenance validation.",
                    }
                ),
                encoding="utf-8",
            )
            candidates = {
                "schema_version": 2,
                "generated_by": "test",
                "candidates": [
                    {
                        "area": "AR1234",
                        "component_id": 3999,
                        "component_label": "animation-ar1234",
                        "payload_group": "animation-ar1234",
                        "approval_status": "approved-for-release",
                        "qa_approval": "releases/BG2-HD-Upscale/manifests/animation-qa-approvals/AR1234/qa-approval.json",
                        "qa_approval_sha256": digest(qa_approval),
                        "source_pack": "testpack",
                        "source_run": "test-run",
                        "pack_manifest": "manifest.json",
                        "pack_manifest_sha256": digest(pack_manifest),
                        "registry": registry.name,
                        "registry_version": 2,
                        "registry_sha256": digest(registry),
                        "registry_bytes": registry.stat().st_size,
                        "required_resrefs": ["FOO"],
                        "renderer_contract": "area-animation-per-area-registry-v2-timed-timeline",
                    }
                ],
            }
            candidate_path = workspace / "candidates.json"
            candidate_path.write_text(json.dumps(candidates), encoding="utf-8")
            output_path = workspace / "content.json"

            completed = subprocess.run(
                [
                    shutil.which("pwsh"),
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-File",
                    str(CONTENT_GENERATOR),
                    "-WorkspaceRoot",
                    str(workspace),
                    "-AnimationCandidatesPath",
                    str(candidate_path),
                    "-OutputPath",
                    str(output_path),
                    "-OnlyAnimationArea",
                    "AR1234",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            entries = json.loads(output_path.read_text(encoding="utf-8"))["entries"]
            self.assertEqual(len(entries), 3)
            self.assertEqual({entry["area"] for entry in entries}, {"AR1234"})
            self.assertEqual({entry["kind"] for entry in entries}, {"area-animation"})


if __name__ == "__main__":
    unittest.main()
