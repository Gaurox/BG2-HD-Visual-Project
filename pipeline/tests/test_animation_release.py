from __future__ import annotations

from contextlib import contextmanager
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "pipeline" / "scripts" / "animation_release.py"


def load_module():
    spec = importlib.util.spec_from_file_location("animation_release_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load_module()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def create_occlusion_fixture(
    root: Path,
) -> tuple[dict, dict, dict, Path, Path]:
    area = "AR1234"
    source_rel = f"maps/wed-corrections/{area}/validated-output-v1/{area}.WED"
    spec_rel = f"maps/wed-corrections/{area}/occlusion.json"
    evidence_rel = (
        "engine/InfinityEngine-Enhancer/source-patchee/docs/validation/"
        f"native-occlusion-{area.lower()}.md"
    )
    source = root / source_rel
    evidence = root / evidence_rel
    source.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"validated-wed")
    evidence.write_bytes(b"validated-ingame-evidence")
    source_hash = release.sha256_file(source)
    evidence_hash = release.sha256_file(evidence)
    write_json(
        root / spec_rel,
        {
            "schema": "bg2-upscale-wed-wall-polygon-spec-v1",
            "status": "validated-installed",
            "area": area,
            "validated_output": {
                "file": f"{area}.WED",
                "bytes": source.stat().st_size,
                "sha256": source_hash.lower(),
                "release_source": source_rel,
            },
            "qa": {
                "verdict": "validated-installed",
                "validated_by": "user",
                "release_manifest": "selected-pending-content-regeneration",
                "revalidation": {
                    "verdict": "validated-installed",
                    "evidence": evidence_rel,
                    "registry_sha256": "A" * 64,
                },
            },
        },
    )
    write_json(
        release.RUNTIME_COMPATIBILITY,
        {
            "renderer": {
                "area_animation_runtime": {
                    "status": "integrated",
                    "supported_registry_versions": [1, 2, 3],
                    "config_owner": "core-steam",
                    "native_occlusion_bridge": {
                        "required": True,
                        "ini_section": "Shaders",
                        "ini_key": "EnableNativeOcclusionBridge",
                        "qa_evidence": evidence_rel,
                        "wed_correction": spec_rel,
                    },
                }
            },
            "owned_ini_keys": {
                "core-steam": {
                    "Shaders": {"EnableNativeOcclusionBridge": "true"}
                }
            }
        },
    )
    release.AREAS.write_text(
        "area_id,status,build,runs\n"
        "AR1234,validated-installed,yes,test-map-run\n",
        encoding="utf-8",
    )
    contract = {
        "mode": "native-wed-bridge-v1",
        "map_component_id": 1234,
        "map_component_label": "map-ar1234",
        "map_payload_group": "map-ar1234",
        "source_spec": spec_rel,
        "source": source_rel,
        "destination": "override/AR1234.WED",
        "bytes": source.stat().st_size,
        "sha256": source_hash,
        "qa_evidence": evidence_rel,
        "qa_evidence_sha256": evidence_hash,
        "ini_owner": "core-steam",
        "ini_section": "Shaders",
        "ini_key": "EnableNativeOcclusionBridge",
        "ini_value": "true",
    }
    candidate = {
        "area": area,
        "component_id": 3999,
        "component_label": "animation-ar1234",
        "payload_group": "animation-ar1234",
        "registry_version": 3,
        "registry_sha256": "A" * 64,
        "occlusion_contract": contract,
    }
    components = {
        "components": [
            {
                "id": 1234,
                "label": "map-ar1234",
                "status": "validated",
                "depends_on": [0],
                "payload_groups": ["map-ar1234"],
            },
            {
                "id": 3999,
                "label": "animation-ar1234",
                "status": "validated",
                "depends_on": [0, 1234],
                "payload_groups": ["animation-ar1234"],
            },
        ]
    }
    content = {
        "entries": [
            {
                "component_id": 1234,
                "component_label": "map-ar1234",
                "payload_group": "map-ar1234",
                "kind": "map",
                "area": area,
                "source": source_rel,
                "source_run": "maps/wed-corrections/AR1234/validated-output-v1",
                "destination": "override/AR1234.WED",
                "bytes": source.stat().st_size,
                "sha256": source_hash,
                "qa_status": "validated",
                "scale": 4,
                "model": "WED-Native-Occlusion-v1",
                "install_order": 1234,
                "replaces_component_output": False,
            }
        ]
    }
    return candidate, components, content, source, evidence


@contextmanager
def configured_workspace(root: Path):
    release.configure_workspace_root(root)
    try:
        yield
    finally:
        release.configure_workspace_root(PROJECT_ROOT)


class AnimationReleaseTests(unittest.TestCase):
    def test_occlusion_contract_validates_physical_and_release_authorities(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with configured_workspace(root):
                candidate, components, content, _, _ = create_occlusion_fixture(root)
                release.validate_occlusion_contracts(
                    [candidate],
                    validate_release_mapping=True,
                    components_document=components,
                    content_document=content,
                    require_animation_dependencies=True,
                )

    def test_occlusion_contract_rejects_stale_wed_and_evidence(self) -> None:
        cases = ("wed-size", "wed-hash", "evidence-missing", "evidence-hash")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with configured_workspace(root):
                    candidate, components, content, source, evidence = create_occlusion_fixture(root)
                    contract = candidate["occlusion_contract"]
                    if case == "wed-size":
                        contract["bytes"] += 1
                    elif case == "wed-hash":
                        source.write_bytes(b"tampered-wed!")
                    elif case == "evidence-missing":
                        evidence.unlink()
                    else:
                        evidence.write_bytes(b"tampered-ingame-evidence")
                    with self.assertRaises(release.ReleasePromotionError):
                        release.validate_occlusion_contracts(
                            [candidate],
                            validate_release_mapping=True,
                            components_document=components,
                            content_document=content,
                        )

    def test_occlusion_contract_requires_runtime_and_spec_links(self) -> None:
        cases = (
            "runtime-evidence",
            "runtime-spec",
            "spec-evidence",
            "spec-registry",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with configured_workspace(root):
                    candidate, components, content, _, _ = create_occlusion_fixture(root)
                    contract = candidate["occlusion_contract"]
                    if case.startswith("runtime-"):
                        runtime = json.loads(
                            release.RUNTIME_COMPATIBILITY.read_text(encoding="utf-8")
                        )
                        bridge = runtime["renderer"]["area_animation_runtime"][
                            "native_occlusion_bridge"
                        ]
                        bridge[
                            "qa_evidence" if case == "runtime-evidence" else "wed_correction"
                        ] = "wrong"
                        write_json(release.RUNTIME_COMPATIBILITY, runtime)
                    else:
                        spec_path = root / contract["source_spec"]
                        spec = json.loads(spec_path.read_text(encoding="utf-8"))
                        revalidation = spec["qa"]["revalidation"]
                        revalidation[
                            "evidence" if case == "spec-evidence" else "registry_sha256"
                        ] = "wrong"
                        write_json(spec_path, spec)
                    with self.assertRaises(release.ReleasePromotionError):
                        release.validate_occlusion_contracts(
                            [candidate],
                            validate_release_mapping=True,
                            components_document=components,
                            content_document=content,
                        )

    def test_occlusion_contract_requires_zone_linked_fields(self) -> None:
        cases = (
            ("map_component_label", "map-ar9999"),
            ("map_payload_group", "map-ar9999"),
            ("source_spec", "maps/wed-corrections/AR9999/occlusion.json"),
            ("source", "maps/wed-corrections/AR9999/validated-output-v1/AR9999.WED"),
            ("destination", "override/AR9999.WED"),
        )
        for field, value in cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with configured_workspace(root):
                    candidate, components, content, _, _ = create_occlusion_fixture(root)
                    candidate["occlusion_contract"][field] = value
                    with self.assertRaises(release.ReleasePromotionError):
                        release.validate_occlusion_contracts(
                            [candidate],
                            validate_release_mapping=True,
                            components_document=components,
                            content_document=content,
                        )

    def test_occlusion_contract_requires_map_projection_and_animation_dependency(self) -> None:
        cases = ("map-component", "wed-content", "animation-dependency")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with configured_workspace(root):
                    candidate, components, content, _, _ = create_occlusion_fixture(root)
                    if case == "map-component":
                        components["components"][0]["label"] = "map-ar9999"
                    elif case == "wed-content":
                        content["entries"][0]["source"] = "maps/wrong.WED"
                    else:
                        components["components"][1]["depends_on"] = [0]
                    with self.assertRaises(release.ReleasePromotionError):
                        release.validate_occlusion_contracts(
                            [candidate],
                            validate_release_mapping=True,
                            components_document=components,
                            content_document=content,
                            require_animation_dependencies=True,
                        )

    def test_write_atomic_removes_partial_after_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.json"
            with mock.patch.object(release.os, "replace", side_effect=OSError("synthetic")):
                with self.assertRaises(OSError):
                    release.write_atomic(target, b"new")
            self.assertFalse(target.exists())
            self.assertEqual([], list(root.glob("*.partial")))

    def test_merge_animation_delta_replaces_only_requested_area(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            content = root / "content.json"
            delta = root / "delta.json"
            output = root / "merged.json"
            write_json(
                content,
                {
                    "schema_version": 1,
                    "entries": [
                        {
                            "component_id": 1000,
                            "install_order": 1000,
                            "kind": "map",
                            "area": "AR0001",
                            "destination": "override/A.PVRZ",
                            "source": "maps/A.PVRZ",
                        },
                        {
                            "component_id": 3000,
                            "install_order": 3000,
                            "kind": "area-animation",
                            "area": "AR0001",
                            "destination": "iee-assets/areas/AR0001/old.rgba",
                            "source": "animations/old.rgba",
                        },
                        {
                            "component_id": 3001,
                            "install_order": 3001,
                            "kind": "area-animation",
                            "area": "AR0002",
                            "destination": "iee-assets/areas/AR0002/kept.rgba",
                            "source": "animations/kept.rgba",
                        },
                    ],
                },
            )
            replacement = {
                "component_id": 3000,
                "install_order": 3000,
                "kind": "area-animation",
                "area": "AR0001",
                "destination": "iee-assets/areas/AR0001/new.rgba",
                "source": "animations/new.rgba",
            }
            write_json(delta, {"schema_version": 1, "entries": [replacement]})
            with mock.patch.object(release, "CONTENT", content):
                release.merge_animation_delta("AR0001", delta, output)
            merged = json.loads(output.read_text(encoding="utf-8"))["entries"]
            self.assertIn(replacement, merged)
            self.assertTrue(any(item.get("area") == "AR0002" for item in merged))
            self.assertTrue(any(item.get("kind") == "map" for item in merged))
            self.assertFalse(any(item.get("source") == "animations/old.rgba" for item in merged))

    def test_merge_animation_delta_rejects_foreign_area(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            content = root / "content.json"
            delta = root / "delta.json"
            write_json(content, {"entries": []})
            write_json(
                delta,
                {
                    "entries": [
                        {
                            "kind": "area-animation",
                            "area": "AR0002",
                        }
                    ]
                },
            )
            with mock.patch.object(release, "CONTENT", content):
                with self.assertRaises(release.ReleasePromotionError):
                    release.merge_animation_delta("AR0001", delta, root / "merged.json")

    def test_publish_transaction_rolls_back_prior_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.json"
            second = root / "second.json"
            first.write_bytes(b"before-first")
            second.write_bytes(b"before-second")
            real_write = release.write_atomic
            calls = 0

            def fail_second(path: Path, data: bytes) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic publication failure")
                real_write(path, data)

            with mock.patch.object(release, "write_atomic", side_effect=fail_second):
                with self.assertRaises(OSError):
                    release.publish_transaction(
                        {first: b"after-first", second: b"after-second"}
                    )
            self.assertEqual(b"before-first", first.read_bytes())
            self.assertEqual(b"before-second", second.read_bytes())

    def test_journal_recovery_refuses_post_crash_edit_then_restores_published_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with configured_workspace(root):
                target = release.CANDIDATES
                target.parent.mkdir(parents=True)
                old = b"old-authority"
                published = b"published-authority"
                target.write_bytes(b"post-crash-user-edit")
                backup_root = release.TRANSACTION_ROOT / "animation-release-test"
                backup_root.mkdir(parents=True)
                backup = backup_root / "000.bin"
                backup.write_bytes(old)
                write_json(
                    release.PUBLICATION_JOURNAL,
                    {
                        "schema": release.PUBLICATION_JOURNAL_SCHEMA,
                        "backup_root": release.repo_path(backup_root),
                        "entries": [
                            {
                                "target": release.repo_path(target),
                                "existed": True,
                                "published_sha256": digest_bytes(published),
                                "backup": release.repo_path(backup),
                                "backup_sha256": digest_bytes(old),
                            }
                        ],
                    },
                )
                with self.assertRaisesRegex(
                    release.ReleasePromotionError, "cible modifiée"
                ):
                    release.recover_publication_journal()
                self.assertEqual(b"post-crash-user-edit", target.read_bytes())
                self.assertTrue(release.PUBLICATION_JOURNAL.is_file())

                target.write_bytes(published)
                restored = release.recover_publication_journal()
                self.assertEqual([release.repo_path(target)], restored)
                self.assertEqual(old, target.read_bytes())
                self.assertFalse(release.PUBLICATION_JOURNAL.exists())
                self.assertFalse(backup_root.exists())

    def test_publish_transaction_rejects_directory_target_before_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with configured_workspace(root):
                release.CANDIDATES.mkdir(parents=True)
                with self.assertRaisesRegex(
                    release.ReleasePromotionError, "non fichier"
                ):
                    release.publish_transaction(
                        {release.CANDIDATES: b"candidate"},
                        journal_path=release.PUBLICATION_JOURNAL,
                    )
                self.assertFalse(release.PUBLICATION_JOURNAL.exists())

    def test_immediate_rollback_keeps_journal_instead_of_clobbering_external_edit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with configured_workspace(root):
                first = release.CANDIDATES
                second = release.CONTENT
                first.parent.mkdir(parents=True)
                first.write_bytes(b"first-before")
                second.write_bytes(b"second-before")
                real_write = release.write_atomic

                def fail_after_external_edit(path: Path, data: bytes) -> None:
                    if path == second.resolve() and data == b"second-after":
                        first.write_bytes(b"external-edit")
                        raise OSError("synthetic publication failure")
                    real_write(path, data)

                with mock.patch.object(
                    release, "write_atomic", side_effect=fail_after_external_edit
                ):
                    with self.assertRaisesRegex(
                        release.ReleasePromotionError, "récupération sûre refusée"
                    ):
                        release.publish_transaction(
                            {first: b"first-after", second: b"second-after"},
                            journal_path=release.PUBLICATION_JOURNAL,
                        )
                self.assertEqual(b"external-edit", first.read_bytes())
                self.assertEqual(b"second-before", second.read_bytes())
                self.assertTrue(release.PUBLICATION_JOURNAL.is_file())

    def test_structured_source_runs_require_a_physical_final_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with configured_workspace(root):
                run = root / "animations" / "ressources" / "FOO" / "runs" / "final-v1"
                manifest = run / "manifest.json"
                write_json(
                    manifest,
                    {
                        "schema": "test-run-v1",
                        "status": "completed",
                        "resref": "FOO",
                    },
                )
                candidate = {
                    "source_runs": [
                        {
                            "path": "animations/ressources/FOO/runs/final-v1",
                            "manifest_path": "animations/ressources/FOO/runs/final-v1/manifest.json",
                            "manifest_sha256": release.sha256_file(manifest),
                            "role": "final",
                            "asset_ids": ["FOO"],
                        }
                    ]
                }
                validated = release.validate_candidate_source_runs(
                    candidate,
                    area="AR1234",
                    expected_asset_ids=["FOO"],
                    require_structured=True,
                )
                self.assertEqual(candidate["source_runs"], validated)
                candidate["source_runs"][0]["role"] = "correction"
                with self.assertRaisesRegex(
                    release.ReleasePromotionError, "non final"
                ):
                    release.validate_candidate_source_runs(
                        candidate,
                        area="AR1234",
                        expected_asset_ids=["FOO"],
                        require_structured=True,
                    )

    def test_complete_registry_preflight_verifies_every_candidate_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidates_path = root / "candidates.json"
            approval_override = root / "new-approval.json"
            write_json(candidates_path, {"candidates": []})
            candidates = [{"area": "AR0001"}, {"area": "OH6000"}]

            def verified(**kwargs):
                return {"area": kwargs["area"]}

            with mock.patch.object(
                release,
                "validate_candidates_document_shape",
                return_value=candidates,
            ), mock.patch.object(
                release,
                "_verify_release_candidate_from_validated_registry",
                side_effect=verified,
            ) as verify_one:
                result = release.verify_release_candidate_registry(
                    candidates_path=candidates_path,
                    approval_overrides={"OH6000": approval_override},
                    allow_pending=True,
                )

            self.assertEqual([{"area": "AR0001"}, {"area": "OH6000"}], result)
            self.assertEqual(2, verify_one.call_count)
            first = verify_one.call_args_list[0].kwargs
            second = verify_one.call_args_list[1].kwargs
            self.assertIs(first["candidates"], candidates)
            self.assertIs(second["candidates"], candidates)
            self.assertIs(first["approval_cache"], second["approval_cache"])
            self.assertIs(
                first["legacy_evidence_cache"], second["legacy_evidence_cache"]
            )
            self.assertIsNone(first["approval_override_path"])
            self.assertEqual(approval_override.resolve(), second["approval_override_path"])
            self.assertTrue(first["allow_pending"])
            self.assertTrue(second["allow_pending"])

    def test_apply_preflights_complete_registry_before_generators_or_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            approval_path = root / "approvals" / "new.json"
            plan = {
                "area": "AR0001",
                "qa_approval_path": approval_path,
                "qa_approval_bytes": b"{}\n",
                "candidate_bytes": b"{}\n",
            }
            with mock.patch.object(
                release,
                "verify_release_candidate_registry",
                side_effect=release.ReleasePromotionError("candidat existant invalide"),
            ) as preflight, mock.patch.object(
                release, "powershell"
            ) as find_powershell, mock.patch.object(
                release, "publish_transaction"
            ) as publish:
                with self.assertRaisesRegex(
                    release.ReleasePromotionError, "candidat existant invalide"
                ):
                    release.apply_promotion(plan, test_delta=False)

            preflight.assert_called_once()
            find_powershell.assert_not_called()
            publish.assert_not_called()

    def test_v3_continuity_registry_version_requires_a_json_integer(self) -> None:
        approval = {
            "schema_version": 3,
            "area": "AR1234",
            "status": "accepted",
            "decision_date": "2026-09-02",
            "decision_origin": "explicit-user-ingame-qa-with-byte-identical-carry-forward",
            "recorded_at_utc": "2026-09-02T12:00:00Z",
            "source_pack": "animations/packs-par-zone/pack/AR1234",
            "pack_manifest_sha256": "A" * 64,
            "registry": "AreaAnimations-X4.registry",
            "registry_version": 3,
            "registry_sha256": "B" * 64,
            "required_resrefs": ["BAR", "FOO"],
            "evidence": [
                {
                    "kind": "ingame-qa-decision",
                    "path": "animations/index/qa-decisions/BAR/accepted.json",
                    "sha256": "C" * 64,
                    "accepted_resrefs": ["BAR"],
                },
                {
                    "kind": "byte-identical-release-continuity",
                    "path": "releases/BG2-HD-Upscale/manifests/animation-qa-approvals/AR1234/previous.json",
                    "sha256": "D" * 64,
                    "accepted_resrefs": ["FOO"],
                    "source_pack": "animations/packs-par-zone/previous/AR1234",
                    "pack_manifest_sha256": "E" * 64,
                    "registry_version": 3,
                    "renderer_contract": "area-animation-per-area-registry-v3-position-timed-timeline",
                    "resource_sha256": "F" * 64,
                },
            ],
            "decision": "QA explicite et continuité binaire.",
        }
        self.assertEqual(
            release.validate_approval_shape(approval, area="AR1234", label="test"),
            3,
        )
        approval["evidence"][1]["registry_version"] = "3"
        with self.assertRaisesRegex(
            release.ReleasePromotionError, "entier JSON invalide"
        ):
            release.validate_approval_shape(approval, area="AR1234", label="test")

    def test_legacy_candidate_verifier_checks_shape_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with configured_workspace(root):
                approval_path = (
                    release.QA_APPROVALS / "AR1234" / "legacy-v1.json"
                )
                approval = {
                    "schema_version": 1,
                    "area": "AR1234",
                    "status": "accepted",
                    "decision_date": "2026-09-02",
                    "decision_origin": "preserved-existing-user-qa",
                    "recorded_at_utc": "2026-09-02T12:00:00Z",
                    "source_pack": "animations/packs-par-zone/pack/AR1234",
                    "pack_manifest_sha256": "A" * 64,
                    "registry": "AreaAnimations-X4.registry",
                    "registry_version": 2,
                    "registry_sha256": "B" * 64,
                    "required_resrefs": ["FOO"],
                    "evidence": [
                        {
                            "kind": "canonical-registry",
                            "path": "animations/index/animation_upscale_registry.csv",
                            "sha256": "C" * 64,
                            "accepted_resrefs": ["FOO"],
                        }
                    ],
                    "decision": "QA historique préservée.",
                }
                write_json(approval_path, approval)
                candidate = {
                    "area": "AR1234",
                    "component_id": 3999,
                    "component_label": "animation-ar1234",
                    "payload_group": "animation-ar1234",
                    "approval_status": "approved-for-release",
                    "qa_approval": release.repo_path(approval_path),
                    "qa_approval_sha256": release.sha256_file(approval_path),
                    "source_pack": approval["source_pack"],
                    "source_run": "legacy provenance",
                    "pack_manifest": "manifest.json",
                    "pack_manifest_sha256": "A" * 64,
                    "registry": "AreaAnimations-X4.registry",
                    "registry_version": 2,
                    "registry_sha256": "B" * 64,
                    "registry_bytes": 1,
                    "required_resrefs": ["FOO"],
                    "renderer_contract": "area-animation-per-area-registry-v2-timed-timeline",
                }
                candidates_path = root / "candidate.json"
                candidate_document = {
                    "schema_version": 2,
                    "generated_by": "test",
                    "candidates": [candidate],
                }
                write_json(candidates_path, candidate_document)
                pack_manifest = root / "pack-manifest.json"
                registry = root / "registry.bin"
                pack_manifest.write_bytes(b"manifest")
                registry.write_bytes(b"registry")
                approval["pack_manifest_sha256"] = release.sha256_file(pack_manifest)
                approval["registry_sha256"] = release.sha256_file(registry)
                write_json(approval_path, approval)
                candidate["qa_approval_sha256"] = release.sha256_file(approval_path)
                write_json(candidates_path, candidate_document)
                pack = {
                    "registry_version": 2,
                    "runtime_budget_enforced": True,
                    "authoring_pack_for_area_split": False,
                }
                with mock.patch.object(
                    release,
                    "validate_pack",
                    return_value=(pack, [], ["FOO"], pack_manifest, registry),
                ), mock.patch.object(
                    release, "validate_candidate_pack_metadata"
                ), mock.patch.object(
                    release, "verify_legacy_evidence"
                ) as evidence_check:
                    result = release.verify_release_candidate(
                        area="AR1234", candidates_path=candidates_path
                    )
                self.assertTrue(result["legacy_qa"])
                evidence_check.assert_called_once()

                candidate["registry_version"] = "2"
                write_json(candidates_path, candidate_document)
                with self.assertRaisesRegex(
                    release.ReleasePromotionError, "entier JSON invalide"
                ):
                    release.verify_release_candidate(
                        area="AR1234", candidates_path=candidates_path
                    )
                candidate["registry_version"] = 2

                approval["schema_version"] = True
                write_json(approval_path, approval)
                candidate["qa_approval_sha256"] = release.sha256_file(approval_path)
                write_json(candidates_path, candidate_document)
                with mock.patch.object(
                    release,
                    "validate_pack",
                    return_value=(pack, [], ["FOO"], pack_manifest, registry),
                ), mock.patch.object(release, "validate_candidate_pack_metadata"):
                    with self.assertRaisesRegex(
                        release.ReleasePromotionError, "version d'approbation invalide"
                    ):
                        release.verify_release_candidate(
                            area="AR1234", candidates_path=candidates_path
                        )


if __name__ == "__main__":
    unittest.main()
