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
            pack_root = workspace / "animations" / "packs-par-zone" / "testpack"
            pack = pack_root / "AR1234"
            pack.mkdir(parents=True)
            pack_root_relative = "animations/packs-par-zone/testpack"
            pack_relative = f"{pack_root_relative}/AR1234"
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
                "registry": registry.name,
                "registry_version": 2,
                "registry_sha256": digest(registry),
                "registry_bytes": registry.stat().st_size,
                "resource_count": 1,
                "frame_count": 1,
                "area_id": "AR1234",
                "runtime_budget_enforced": True,
                "authoring_pack_for_area_split": False,
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
            pack_root_manifest = pack_root / "manifest.json"
            pack_root_manifest.write_text(
                json.dumps(
                    {
                        "schema": "bg2-upscale-area-animation-pack-index-v1",
                        "status": "completed",
                        "areas": [
                            {
                                "area_id": "AR1234",
                                "directory": "AR1234",
                                "manifest_sha256": digest(pack_manifest),
                                "registry_sha256": digest(registry),
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            index = workspace / "animations" / "index"
            index.mkdir(parents=True)
            (index / "animation_upscale_registry.csv").write_text(
                "resref,status,areas\nFOO,validé-x4,AR1234\n", encoding="utf-8"
            )
            schema_root = workspace / "animations" / "schemas"
            schema_root.mkdir(parents=True)
            shutil.copy2(
                ROOT / "animations" / "schemas" / "animation-qa-decision.schema.json",
                schema_root / "animation-qa-decision.schema.json",
            )
            verifier = (
                workspace
                / "pipeline"
                / "scripts"
                / "verify_animation_release_candidate.py"
            )
            verifier.parent.mkdir(parents=True)
            shutil.copy2(
                ROOT / "pipeline" / "scripts" / "animation_authority_lock.py",
                verifier.parent / "animation_authority_lock.py",
            )
            verifier.write_text(
                """import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--workspace-root", type=Path, required=True)
parser.add_argument("--animation-candidates-path", type=Path, required=True)
parser.add_argument("--area", required=True)
parser.add_argument("--animation-qa-approval-override-path", type=Path)
parser.add_argument("--allow-pending", action="store_true")
arguments = parser.parse_args()
if arguments.workspace_root.resolve() != Path(__file__).resolve().parents[2] or arguments.area != "AR1234":
    raise SystemExit(2)
if not arguments.animation_candidates_path.is_file():
    raise SystemExit(2)
(arguments.workspace_root / "structured-verifier.called").write_text("ok", encoding="utf-8")
""",
                encoding="utf-8",
            )
            run_root = workspace / "animations" / "ressources" / "FOO" / "runs" / "final-v1"
            run_root.mkdir(parents=True)
            run_manifest = run_root / "manifest.json"
            run_manifest.write_text(
                json.dumps(
                    {
                        "schema": "bg2-upscale-area-animation-run-v1",
                        "status": "completed",
                        "resref": "FOO",
                    }
                ),
                encoding="utf-8",
            )
            run_artifact = {
                "path": "animations/ressources/FOO/runs/final-v1",
                "manifest_path": "animations/ressources/FOO/runs/final-v1/manifest.json",
                "manifest_sha256": digest(run_manifest),
                "schema": "bg2-upscale-area-animation-run-v1",
                "status": "completed",
            }
            decision = (
                workspace
                / "animations"
                / "index"
                / "qa-decisions"
                / "FOO"
                / "accepted-v1.json"
            )
            decision.parent.mkdir(parents=True)
            decision.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "decision_id": "accepted-v1",
                        "asset_id": "animations:bam:FOO",
                        "resref": "FOO",
                        "status": "accepted",
                        "result_kind": "x4",
                        "decision_origin": "explicit-user-ingame-qa",
                        "decision_date": "2026-09-02",
                        "recorded_at_utc": "2026-09-02T12:00:00Z",
                        "decision": "QA ingame explicite du pack exact.",
                        "final_run": run_artifact,
                        "source_pack": {
                            "path": pack_root_relative,
                            "manifest_path": f"{pack_root_relative}/manifest.json",
                            "manifest_sha256": digest(pack_root_manifest),
                            "schema": "bg2-upscale-area-animation-pack-index-v1",
                            "status": "completed",
                            "areas": [
                                {
                                    "area": "AR1234",
                                    "path": pack_relative,
                                    "manifest_path": f"{pack_relative}/manifest.json",
                                    "manifest_sha256": digest(pack_manifest),
                                    "registry_sha256": digest(registry),
                                    "resource_entries": 1,
                                }
                            ],
                        },
                        "tested_areas": ["AR1234"],
                        "lineage": {"source_runs": [], "source_packs": []},
                    }
                ),
                encoding="utf-8",
            )
            qa_approval = (
                workspace
                / "releases"
                / "BG2-HD-Upscale"
                / "manifests"
                / "animation-qa-approvals"
                / "AR1234"
                / "qa-v2-test.json"
            )
            qa_approval.parent.mkdir(parents=True)
            qa_approval.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "area": "AR1234",
                        "status": "accepted",
                        "decision_date": "2026-09-02",
                        "decision_origin": "explicit-user-ingame-qa",
                        "recorded_at_utc": "2026-09-02T12:00:00Z",
                        "source_pack": pack_relative,
                        "pack_manifest_sha256": digest(pack_manifest),
                        "registry": registry.name,
                        "registry_version": 2,
                        "registry_sha256": digest(registry),
                        "required_resrefs": ["FOO"],
                        "evidence": [
                            {
                                "kind": "ingame-qa-decision",
                                "path": "animations/index/qa-decisions/FOO/accepted-v1.json",
                                "sha256": digest(decision),
                                "accepted_resrefs": ["FOO"],
                            }
                        ],
                        "decision": "Décision ingame explicite consolidée pour la zone.",
                    }
                ),
                encoding="utf-8",
            )
            candidates = {
                "schema_version": 3,
                "generated_by": "test",
                "candidates": [
                    {
                        "area": "AR1234",
                        "component_id": 3999,
                        "component_label": "animation-ar1234",
                        "payload_group": "animation-ar1234",
                        "approval_status": "approved-for-release",
                        "qa_approval": "releases/BG2-HD-Upscale/manifests/animation-qa-approvals/AR1234/qa-v2-test.json",
                        "qa_approval_sha256": digest(qa_approval),
                        "source_pack": pack_relative,
                        "source_runs": [
                            {
                                "path": run_artifact["path"],
                                "manifest_path": run_artifact["manifest_path"],
                                "manifest_sha256": run_artifact["manifest_sha256"],
                                "role": "final",
                                "asset_ids": ["FOO"],
                            }
                        ],
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

            def bind_decision(decision_document: dict) -> None:
                decision.write_text(json.dumps(decision_document), encoding="utf-8")
                approval_document = json.loads(qa_approval.read_text(encoding="utf-8"))
                approval_document["evidence"][0]["sha256"] = digest(decision)
                qa_approval.write_text(json.dumps(approval_document), encoding="utf-8")
                candidates["candidates"][0]["qa_approval_sha256"] = digest(qa_approval)
                candidate_path.write_text(json.dumps(candidates), encoding="utf-8")

            def bind_pack_budget_flags(
                runtime_budget_enforced: bool,
                authoring_pack_for_area_split: bool,
            ) -> None:
                manifest["runtime_budget_enforced"] = runtime_budget_enforced
                manifest["authoring_pack_for_area_split"] = authoring_pack_for_area_split
                pack_manifest.write_text(json.dumps(manifest), encoding="utf-8")
                pack_hash = digest(pack_manifest)

                decision_document = json.loads(decision.read_text(encoding="utf-8"))
                decision_document["source_pack"]["areas"][0]["manifest_sha256"] = pack_hash
                approval_document = json.loads(qa_approval.read_text(encoding="utf-8"))
                approval_document["pack_manifest_sha256"] = pack_hash
                qa_approval.write_text(json.dumps(approval_document), encoding="utf-8")
                candidate = candidates["candidates"][0]
                candidate["pack_manifest_sha256"] = pack_hash
                bind_decision(decision_document)

            command = [
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
            ]
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                (workspace / "structured-verifier.called").read_text(encoding="utf-8"),
                "ok",
            )
            entries = json.loads(output_path.read_text(encoding="utf-8"))["entries"]
            self.assertEqual(len(entries), 3)
            self.assertEqual({entry["area"] for entry in entries}, {"AR1234"})
            self.assertEqual({entry["kind"] for entry in entries}, {"area-animation"})

            (index / "animation_upscale_registry.csv").write_text(
                "registre,courant,volontairement,invalide\n",
                encoding="utf-8",
            )
            regenerated = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(regenerated.returncode, 0, regenerated.stderr)

            transaction_root = workspace / ".tmp" / "workflow-transactions"
            transaction_root.mkdir(parents=True)
            active_journal = transaction_root / "animation-authority-active.json"
            active_journal.write_text("{}", encoding="utf-8")
            guarded = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(guarded.returncode, 0)
            self.assertIn("Transaction animation interrompue active", guarded.stderr)
            active_journal.unlink()

            bind_pack_budget_flags(False, True)
            rejected = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Pack auteur ou budget runtime non confirme", rejected.stderr)
            bind_pack_budget_flags(True, True)
            rejected = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Pack auteur non decoupe", rejected.stderr)
            bind_pack_budget_flags(True, False)

            x4_decision = json.loads(decision.read_text(encoding="utf-8"))
            native_decision = dict(x4_decision)
            for field in ("final_run", "source_pack", "lineage"):
                native_decision.pop(field)
            native_decision["result_kind"] = "native"
            native_decision["native_source"] = {
                "path": "animations/ressources/FOO/source.bam",
                "sha256": "0" * 64,
                "bytes": 1,
                "format": "BAM V1",
                "frames": 1,
                "inventory_path": "animations/index/ressources.csv",
                "inventory_row_sha256": "0" * 64,
            }
            bind_decision(native_decision)
            rejected = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Decision ingame non x4", rejected.stderr)
            bind_decision(x4_decision)

            candidates["candidates"][0]["source_runs"][0]["role"] = "spatial"
            candidate_path.write_text(json.dumps(candidates), encoding="utf-8")
            rejected = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Role de run source non final", rejected.stderr)

            candidates["candidates"][0]["source_runs"][0]["role"] = "final"
            candidates["candidates"][0]["source_runs"].append(
                dict(candidates["candidates"][0]["source_runs"][0])
            )
            candidate_path.write_text(json.dumps(candidates), encoding="utf-8")
            rejected = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Run source duplique pour FOO", rejected.stderr)
            candidates["candidates"][0]["source_runs"].pop()

            other_run = (
                workspace / "animations" / "ressources" / "FOO" / "runs" / "other-v1"
            )
            other_run.mkdir(parents=True)
            shutil.copy2(run_manifest, other_run / "manifest.json")
            candidates["candidates"][0]["source_runs"][0]["manifest_path"] = (
                "animations/ressources/FOO/runs/other-v1/manifest.json"
            )
            candidate_path.write_text(json.dumps(candidates), encoding="utf-8")
            rejected = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Manifest hors run source ou non canonique", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
