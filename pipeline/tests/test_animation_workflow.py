from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workflow = load_module(
    "animation_workflow_under_test",
    PROJECT_ROOT / "pipeline" / "scripts" / "animation_workflow.py",
)
sync_registry = load_module(
    "sync_animation_upscale_registry_under_test",
    PROJECT_ROOT / "pipeline" / "scripts" / "sync_animation_upscale_registry.py",
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AnimationWorkflowFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.registry = root / "animations/index/animation_upscale_registry.csv"
        self.inventory = root / "animations/index/ressources.csv"
        self.resource = root / "animations/ressources/AMTEST"
        self.final_run = self.resource / "runs/amtest-alpha-v1"
        self.qa_pack = root / "animations/packs-par-zone/amtest-qa"
        self.payload = bytes((index % 251 for index in range(64)))
        self.runtime = workflow._runtime_v2_module()

    def build(self) -> None:
        self.resource.mkdir(parents=True)
        source = self.resource / "source.bam"
        source.write_bytes(b"canonical-native-amtest")
        self.inventory.parent.mkdir(parents=True, exist_ok=True)
        with self.inventory.open("w", encoding="utf-8", newline="") as stream:
            fields = (
                "bam_resref",
                "format",
                "frames",
                "max_frame_width",
                "max_frame_height",
                "occurrences",
                "areas",
                "area_ids",
                "external_palette_occurrences",
                "external_palette_resrefs",
                "relative_path",
                "sha256",
            )
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerow(
                {
                    "bam_resref": "AMTEST",
                    "format": "BAM V1",
                    "frames": "1",
                    "max_frame_width": "1",
                    "max_frame_height": "1",
                    "occurrences": "2",
                    "areas": "2",
                    "area_ids": "AR0001;AR0002",
                    "external_palette_occurrences": "0",
                    "external_palette_resrefs": "",
                    "relative_path": "ressources/AMTEST",
                    "sha256": file_sha256(source),
                }
            )

        self.registry.parent.mkdir(parents=True, exist_ok=True)
        with self.registry.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=workflow.REGISTRY_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerow(
                {
                    "resref": "AMTEST",
                    "status": "non-traité",
                    "areas": "AR0001;AR0002",
                    "occurrences": "2",
                    "frames": "1",
                    "max_frame_size_x1": "1x1",
                    "format": "BAM V1",
                    "selected_run": "",
                    "qa_decision": "",
                    "qa_date": "",
                    "correction_id": "legacy-correction",
                    "notes": "note AMTEST à préserver si non remplacée",
                }
            )
            writer.writerow(
                {
                    "resref": "OTHER",
                    "status": "validé-natif",
                    "areas": "AR0003",
                    "occurrences": "1",
                    "frames": "8",
                    "max_frame_size_x1": "10x10",
                    "format": "BAM V1",
                    "selected_run": "",
                    "qa_decision": "",
                    "qa_date": "",
                    "correction_id": "other-current",
                    "notes": "données utilisateur inchangées",
                }
            )

        runtime_pack = self.final_run / "03_runtime_pack"
        self.build_runtime_pack(runtime_pack, self.payload)
        write_json(
            self.final_run / "manifest.json",
            {
                "schema": "bg2-upscale-area-animation-correction-run-v1",
                "status": "completed",
                "resref": "AMTEST",
                "pack": "03_runtime_pack",
                "pack_manifest_sha256": file_sha256(runtime_pack / "manifest.json"),
            },
        )
        self.build_qa_pack(self.qa_pack, self.payload)

    def _v2_resource(self, pack_root: Path, payload: bytes, playback_mode: str) -> dict:
        if len(payload) != 64:
            raise ValueError("a 1x1 logical RGBA frame must contain 64 x4 bytes")
        pack_root.mkdir(parents=True, exist_ok=True)
        asset_name = self.runtime.asset_name("AMTEST", 0)
        asset_path = pack_root / asset_name
        asset_path.write_bytes(payload)
        digest = file_sha256(asset_path)
        native = playback_mode == "Native"
        return {
            "resref": "AMTEST",
            "frame_count": 1,
            "cycle_count": 1,
            "geometry_mode": "uniform",
            "playback_mode": playback_mode,
            "native_fps": (
                {"numerator": 0, "denominator": 0}
                if native
                else {"numerator": 15, "denominator": 1}
            ),
            "target_fps": (
                {"numerator": 0, "denominator": 0}
                if native
                else {"numerator": 30, "denominator": 1}
            ),
            "frames": [
                {
                    "frame": 0,
                    "logical_size_x1": [1, 1],
                    "physical_size_x4": [4, 4],
                    "centre_x1": [0, 0],
                    "asset": asset_name,
                    "sha256": digest,
                    "bytes": len(payload),
                }
            ],
            "cycles": [
                {
                    "cycle": 0,
                    "native_frame_indices": [0],
                    "timeline_frame_indices": [] if native else [0, 0],
                }
            ],
            "assets": [{"name": asset_name, "sha256": digest, "bytes": len(payload)}],
        }

    def build_runtime_pack(
        self,
        pack_root: Path,
        payload: bytes,
        *,
        area: str | None = None,
        playback_mode: str = "TimedTimeline",
    ) -> dict:
        resource = self._v2_resource(pack_root, payload, playback_mode)
        registry = self.runtime.registry_v2_from_resources(
            [resource], self.runtime.REGISTRY_VERSION
        )
        registry_path = pack_root / self.runtime.REGISTRY_NAME
        registry_path.write_bytes(registry)
        manifest = {
            "schema": self.runtime.PACK_SCHEMA,
            "status": "completed",
            "scale": 4,
            "registry_version": self.runtime.REGISTRY_VERSION,
            "runtime_contract": {
                "feature": "TimedTimeline",
                "clock": "QPC-pause-aware",
                "registry_version": self.runtime.REGISTRY_VERSION,
            },
            "registry": self.runtime.REGISTRY_NAME,
            "registry_sha256": file_sha256(registry_path),
            "registry_bytes": registry_path.stat().st_size,
            "resource_count": 1,
            "frame_count": 1,
            "raw_bytes": len(payload),
            "timed_resources": [] if playback_mode == "Native" else ["AMTEST"],
            "runtime_budget_enforced": True,
            "authoring_pack_for_area_split": False,
            "resources": [resource],
        }
        if area is not None:
            manifest["area_id"] = area
        write_json(pack_root / "manifest.json", manifest)
        return manifest

    def build_v1_runtime_pack(self, pack_root: Path, payload: bytes) -> dict:
        if len(payload) != 64:
            raise ValueError("a 1x1 logical RGBA frame must contain 64 x4 bytes")
        pack_root.mkdir(parents=True, exist_ok=True)
        runtime_v1 = self.runtime.runtime_v1
        asset_name = runtime_v1.asset_name("AMTEST", 0)
        asset_path = pack_root / asset_name
        asset_path.write_bytes(payload)
        digest = file_sha256(asset_path)
        resource = {
            "resref": "AMTEST",
            "frame_count": 1,
            "cycle_count": 1,
            "geometry_mode": "uniform",
            "frames": [
                {
                    "frame": 0,
                    "logical_size_x1": [1, 1],
                    "physical_size_x4": [4, 4],
                    "centre_x1": [0, 0],
                    "asset": asset_name,
                    "sha256": digest,
                    "bytes": len(payload),
                }
            ],
            "cycles": [{"cycle": 0, "frame_indices": [0]}],
            "assets": [{"name": asset_name, "sha256": digest, "bytes": len(payload)}],
        }
        registry = runtime_v1.registry_from_resources([resource])
        registry_path = pack_root / self.runtime.REGISTRY_NAME
        registry_path.write_bytes(registry)
        manifest = {
            "schema": runtime_v1.PACK_SCHEMA,
            "status": "completed",
            "scale": 4,
            "registry": self.runtime.REGISTRY_NAME,
            "registry_sha256": file_sha256(registry_path),
            "registry_bytes": registry_path.stat().st_size,
            "resource_count": 1,
            "frame_count": 1,
            "raw_bytes": len(payload),
            "resources": [resource],
        }
        write_json(pack_root / "manifest.json", manifest)
        return manifest

    def build_qa_pack(
        self,
        pack_root: Path,
        payload: bytes,
        *,
        playback_mode: str = "TimedTimeline",
    ) -> None:
        entries = []
        for area in ("AR0001", "AR0002"):
            area_root = pack_root / area
            manifest = self.build_runtime_pack(
                area_root, payload, area=area, playback_mode=playback_mode
            )
            entries.append(
                {
                    "area_id": area,
                    "directory": area,
                    "manifest_sha256": file_sha256(area_root / "manifest.json"),
                    "registry_sha256": manifest["registry_sha256"],
                }
            )
        write_json(
            pack_root / "manifest.json",
            {
                "schema": "bg2-upscale-area-animation-pack-index-v1",
                "status": "completed",
                "areas": entries,
            },
        )

    def finalize(self, **overrides):
        arguments = {
            "workspace_root": self.root,
            "raw_resref": "AMTEST",
            "final_run": self.final_run,
            "qa_pack": self.qa_pack,
            "areas": ["AR0001", "AR0002"],
            "decision_status": "accepted",
            "decision_date": "2026-09-02",
            "decision_text": "QA ingame validée explicitement.",
            "decision_id": "2026-09-02-accepted-amtest-alpha-v1",
            "recipe_id": "alpha-v1",
            "correction_id": "alpha-clean-v1",
            "apply": True,
        }
        arguments.update(overrides)
        return workflow.finalize(**arguments)


class AnimationWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = AnimationWorkflowFixture(Path(self.temporary.name))
        self.fixture.build()

    def test_list_filters_and_sorts_assets(self) -> None:
        result = workflow.list_assets(self.fixture.root, ["non-traité"])
        self.assertEqual(["AMTEST"], [item["resref"] for item in result["assets"]])

    def test_new_run_plan_is_read_only_and_apply_reserves_without_creating_leaf(self) -> None:
        rows, _ = workflow._read_registry(self.fixture.root)
        rows.append(
            {
                **{field: "" for field in workflow.REGISTRY_FIELDS},
                "resref": "AMNEW",
                "status": "non-traité",
                "areas": "AR0001",
            }
        )
        self.fixture.registry.write_bytes(workflow._render_registry(rows))
        resource_root = self.fixture.root / "animations/ressources/AMNEW"
        resource_root.mkdir(parents=True)
        before_plan = {
            path.relative_to(self.fixture.root).as_posix()
            for path in self.fixture.root.rglob("*")
        }
        result = workflow.new_run(
            self.fixture.root,
            "AMNEW",
            "alpha",
            "spline-v2",
            "amnew-alpha-spline-v2",
            False,
        )
        run_path = resource_root / "runs/amnew-alpha-spline-v2"
        self.assertEqual("planned", result["mode"])
        self.assertFalse(run_path.exists())
        self.assertFalse(run_path.parent.exists())
        self.assertFalse((self.fixture.root / workflow.AUTHORITY_LOCK_REL).exists())
        self.assertEqual(
            before_plan,
            {
                path.relative_to(self.fixture.root).as_posix()
                for path in self.fixture.root.rglob("*")
            },
        )

        result = workflow.new_run(
            self.fixture.root,
            "AMNEW",
            "alpha",
            "spline-v2",
            "amnew-alpha-spline-v2",
            True,
        )
        self.assertEqual("applied", result["mode"])
        self.assertFalse(run_path.exists())
        self.assertFalse(run_path.parent.exists())
        reservation = self.fixture.root / result["reservation_path"]
        self.assertTrue(reservation.is_file())
        reservation_record = json.loads(reservation.read_text(encoding="utf-8"))
        self.assertEqual(workflow.RUN_RESERVATION_SCHEMA, reservation_record["schema"])
        self.assertEqual("reserved", reservation_record["status"])
        self.assertEqual("AMNEW", reservation_record["resref"])
        self.assertEqual(
            "animations/ressources/AMNEW/runs/amnew-alpha-spline-v2",
            reservation_record["destination"],
        )
        self.assertEqual(
            ["animations/ressources/AMNEW/.amnew-alpha-spline-v2.reservation.json"],
            result["changed_paths"],
        )
        self.assertEqual(
            run_path.resolve(),
            workflow.ANIMATION_PATHS.resolve_run_destination(
                "amnew-alpha-spline-v2",
                ["AMNEW"],
                animations_root=self.fixture.root / "animations",
            ),
        )
        self.assertTrue((self.fixture.root / workflow.AUTHORITY_LOCK_REL).is_file())

        before_collision = reservation.read_bytes()
        with self.assertRaisesRegex(workflow.WorkflowError, "déjà utilisé"):
            workflow.new_run(
                self.fixture.root,
                "AMNEW",
                "alpha",
                "spline-v2",
                "amnew-alpha-spline-v2",
                True,
            )
        self.assertEqual(before_collision, reservation.read_bytes())

    def test_new_run_auto_id_uses_microseconds_and_suffixes_same_instant_collision(self) -> None:
        fixed = workflow.datetime(
            2026, 9, 2, 1, 2, 3, 123456, tzinfo=workflow.timezone.utc
        )
        recipe = "r" * 128
        with mock.patch.object(workflow, "datetime") as clock:
            clock.now.return_value = fixed
            first = workflow.new_run(
                self.fixture.root, "AMTEST", "occurrence", recipe, None, True)
            second = workflow.new_run(
                self.fixture.root, "AMTEST", "occurrence", recipe, None, True)

        self.assertLessEqual(len(first["run_id"]), 128)
        self.assertLessEqual(len(second["run_id"]), 128)
        self.assertTrue(first["run_id"].endswith("-20260902-010203-123456"))
        self.assertTrue(second["run_id"].endswith("-20260902-010203-123456-2"))
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertTrue((self.fixture.root / first["reservation_path"]).is_file())
        self.assertTrue((self.fixture.root / second["reservation_path"]).is_file())

    def test_run_reservation_exclusive_create_never_replaces_existing_claim(self) -> None:
        reservation = self.fixture.resource / ".claimed.reservation.json"
        reservation.write_bytes(b"existing-claim")
        with self.assertRaisesRegex(workflow.WorkflowError, "déjà réservé"):
            workflow._write_run_reservation(
                reservation,
                {"schema": workflow.RUN_RESERVATION_SCHEMA, "run_id": "claimed"},
            )
        self.assertEqual(b"existing-claim", reservation.read_bytes())

    def test_new_run_detects_physical_run_created_during_reservation(self) -> None:
        run_path = self.fixture.resource / "runs/amtest-race-reservation"
        reservation = self.fixture.resource / ".amtest-race-reservation.reservation.json"
        calls = 0

        def race_destination(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                run_path.mkdir(parents=True)
            return run_path

        with mock.patch.object(
            workflow.ANIMATION_PATHS,
            "resolve_run_destination",
            side_effect=race_destination,
        ):
            with self.assertRaisesRegex(workflow.WorkflowError, "créé pendant sa réservation"):
                workflow.new_run(
                    self.fixture.root,
                    "AMTEST",
                    "alpha",
                    "spline-v2",
                    "amtest-race-reservation",
                    True,
                )
        self.assertTrue(run_path.is_dir())
        self.assertFalse(reservation.exists())

    def test_finalize_consumes_matching_reservation_after_validating_run(self) -> None:
        reservation = self.fixture.resource / ".amtest-alpha-v1.reservation.json"
        reservation_relative = reservation.relative_to(self.fixture.root).as_posix()
        write_json(
            reservation,
            {
                "schema": workflow.RUN_RESERVATION_SCHEMA,
                "status": "reserved",
                "created_utc": "2026-09-02T01:02:03.123456Z",
                "resref": "AMTEST",
                "stage": "alpha",
                "recipe": "alpha-v1",
                "run_id": "amtest-alpha-v1",
                "destination": "animations/ressources/AMTEST/runs/amtest-alpha-v1",
            },
        )

        planned = self.fixture.finalize(apply=False)
        self.assertEqual(reservation_relative, planned["reservation_to_consume"])
        self.assertIsNone(planned["consumed_reservation"])
        self.assertTrue(reservation.is_file())

        applied = self.fixture.finalize()
        self.assertEqual(reservation_relative, applied["consumed_reservation"])
        self.assertFalse(reservation.exists())

    def test_finalize_refuses_incoherent_reservation_without_consuming_it(self) -> None:
        reservation = self.fixture.resource / ".amtest-alpha-v1.reservation.json"
        write_json(
            reservation,
            {
                "schema": workflow.RUN_RESERVATION_SCHEMA,
                "status": "reserved",
                "created_utc": "2026-09-02T01:02:03.123456Z",
                "resref": "AMTEST",
                "stage": "alpha",
                "recipe": "alpha-v1",
                "run_id": "amtest-alpha-v1",
                "destination": "animations/ressources/AMTEST/runs/another-run",
            },
        )
        registry_before = self.fixture.registry.read_bytes()
        with self.assertRaisesRegex(workflow.WorkflowError, "incohérent"):
            self.fixture.finalize()
        self.assertTrue(reservation.is_file())
        self.assertEqual(registry_before, self.fixture.registry.read_bytes())

    def test_new_run_converts_path_resolver_failure_to_workflow_error(self) -> None:
        with mock.patch.object(
            workflow.ANIMATION_PATHS,
            "resolve_run_destination",
            side_effect=RuntimeError("synthetic invalid destination"),
        ):
            with self.assertRaises(workflow.WorkflowError):
                workflow.new_run(
                    self.fixture.root,
                    "AMTEST",
                    "alpha",
                    "spline-v2",
                    "amtest-alpha-spline-v2",
                    False,
                )

    def test_status_discovers_matching_batch_run(self) -> None:
        batch = self.fixture.root / "animations/batches/shared-batch"
        write_json(
            batch / "manifest.json",
            {
                "schema": "bg2-upscale-area-animation-run-v1",
                "status": "completed",
                "resources": [{"resref": "AMTEST"}, {"resref": "OTHER"}],
            },
        )
        status = workflow.status_asset(self.fixture.root, "AMTEST")
        self.assertIn(
            "animations/batches/shared-batch",
            [item["path"] for item in status["runs"]],
        )

    def test_finalize_plan_then_apply_is_relative_hashed_and_preserves_other_rows(self) -> None:
        before = self.fixture.registry.read_bytes()
        planned = self.fixture.finalize(apply=False)
        decision_path = self.fixture.root / planned["tracked_files"][0]
        self.assertEqual("planned", planned["mode"])
        self.assertFalse(decision_path.exists())
        self.assertEqual(before, self.fixture.registry.read_bytes())

        applied = self.fixture.finalize()
        self.assertEqual("applied", applied["mode"])
        self.assertTrue(
            (self.fixture.root / ".tmp/workflow-locks/animation-authority.lock").exists()
        )
        selection_path = self.fixture.root / "animations/index/selections/AMTEST.json"
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        self.assertEqual("accepted", decision["status"])
        self.assertEqual("explicit-user-ingame-qa", decision["decision_origin"])
        self.assertEqual(["AR0001", "AR0002"], decision["tested_areas"])
        self.assertFalse(Path(decision["final_run"]["path"]).is_absolute())
        self.assertEqual(
            file_sha256(self.fixture.final_run / "manifest.json").upper(),
            decision["final_run"]["manifest_sha256"],
        )
        self.assertEqual(file_sha256(decision_path).upper(), selection["qa_decision"]["sha256"])
        self.assertEqual([], decision["lineage"]["source_runs"])
        self.assertEqual([], decision["lineage"]["source_packs"])

        with self.fixture.registry.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            self.assertEqual(list(workflow.REGISTRY_FIELDS), reader.fieldnames)
            rows = {row["resref"]: row for row in reader}
        self.assertEqual("validé-natif", rows["OTHER"]["status"])
        self.assertEqual("other-current", rows["OTHER"]["correction_id"])
        self.assertEqual("données utilisateur inchangées", rows["OTHER"]["notes"])
        self.assertEqual("alpha-clean-v1", rows["AMTEST"]["correction_id"])
        self.assertEqual("note AMTEST à préserver si non remplacée", rows["AMTEST"]["notes"])

        checked = workflow.check_workspace(self.fixture.root, "AMTEST")
        self.assertTrue(checked["ok"], checked["errors"])

    def test_finalize_apply_uses_shared_animation_authority_lock(self) -> None:
        lock = self.fixture.root / ".tmp/workflow-locks/animation-authority.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("stale unlocked metadata\n", encoding="ascii")
        planned = self.fixture.finalize(apply=False)
        self.assertEqual("planned", planned["mode"])
        applied = self.fixture.finalize()
        self.assertEqual("applied", applied["mode"])
        self.assertTrue(lock.is_file())

    def test_finalize_wraps_advisory_lock_contention(self) -> None:
        lock_error = workflow.ANIMATION_AUTHORITY_LOCK.AnimationAuthorityLockError(
            "transaction animation déjà verrouillée"
        )
        with mock.patch.object(
            workflow.ANIMATION_AUTHORITY_LOCK,
            "animation_authority_lock",
            side_effect=lock_error,
        ):
            with self.assertRaisesRegex(workflow.WorkflowError, "déjà verrouillée") as raised:
                self.fixture.finalize()
        self.assertIs(raised.exception.__cause__, lock_error)

    def test_advisory_lock_file_persists_after_release(self) -> None:
        lock = self.fixture.root / workflow.AUTHORITY_LOCK_REL
        owner_environment = (
            workflow.ANIMATION_AUTHORITY_LOCK.AUTHORITY_LOCK_OWNER_ENV
        )
        previous_owner = workflow.os.environ.get(owner_environment)
        with workflow.ANIMATION_AUTHORITY_LOCK.animation_authority_lock(self.fixture.root):
            self.assertTrue(lock.is_file())
            self.assertEqual(
                str(workflow.os.getpid()),
                workflow.os.environ.get(owner_environment),
            )
            with workflow.ANIMATION_AUTHORITY_LOCK.animation_authority_lock(
                self.fixture.root
            ):
                self.assertTrue(lock.is_file())
        self.assertTrue(lock.is_file())
        self.assertEqual(previous_owner, workflow.os.environ.get(owner_environment))
        self.fixture.finalize()

    def test_finalize_refuses_an_interrupted_release_transaction(self) -> None:
        release_journal = self.fixture.root / workflow.RELEASE_JOURNAL_REL
        release_journal.parent.mkdir(parents=True, exist_ok=True)
        release_journal.write_text("{}\n", encoding="utf-8")
        registry_before = self.fixture.registry.read_bytes()

        with self.assertRaisesRegex(workflow.WorkflowError, "transaction release animation"):
            self.fixture.finalize()

        self.assertEqual(registry_before, self.fixture.registry.read_bytes())
        self.assertFalse(
            (self.fixture.root / "animations/index/selections/AMTEST.json").exists()
        )

    def test_finalize_is_idempotent(self) -> None:
        first = self.fixture.finalize()
        snapshot = {
            relative: (self.fixture.root / relative).read_bytes()
            for relative in first["tracked_files"]
        }
        second = self.fixture.finalize()
        self.assertEqual([], second["changed_files"])
        self.assertEqual(
            snapshot,
            {relative: (self.fixture.root / relative).read_bytes() for relative in first["tracked_files"]},
        )

    def test_immutable_decision_id_collision_is_rejected(self) -> None:
        self.fixture.finalize()
        with self.assertRaises(workflow.WorkflowError):
            self.fixture.finalize(decision_text="Une autre décision sous le même identifiant.")

    def test_rejected_decision_does_not_change_registry_or_selection(self) -> None:
        before = self.fixture.registry.read_bytes()
        result = self.fixture.finalize(
            decision_status="rejected",
            decision_id="2026-09-02-rejected-amtest-alpha-v1",
        )
        self.assertEqual(1, len(result["changed_files"]))
        self.assertEqual(before, self.fixture.registry.read_bytes())
        self.assertFalse((self.fixture.root / "animations/index/selections/AMTEST.json").exists())

    def test_finalize_rejects_area_outside_inventory(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            self.fixture.finalize(areas=["AR9999"])

    def test_finalize_rejects_partial_inventory_coverage(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            self.fixture.finalize(areas=["AR0001"])

    def test_finalize_rejects_unknown_registry_status(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            self.fixture.finalize(registry_status="QA-ok")

    def test_finalize_resolves_a_simple_run_id_through_shared_path_rules(self) -> None:
        result = self.fixture.finalize(final_run="amtest-alpha-v1", apply=False)
        self.assertEqual("planned", result["mode"])
        self.assertIn(
            "animations/ressources/AMTEST/runs/amtest-alpha-v1",
            result["data_paths"],
        )

    def test_finalize_native_hashes_source_without_x4_bindings(self) -> None:
        result = self.fixture.finalize(
            final_run=None,
            qa_pack=None,
            registry_status="validé-natif",
            decision_id="2026-09-02-accepted-amtest-native",
            recipe_id=None,
            correction_id=None,
        )
        decision_path = self.fixture.root / result["tracked_files"][0]
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        selection = json.loads(
            (self.fixture.root / "animations/index/selections/AMTEST.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("native", decision["result_kind"])
        self.assertEqual("native", selection["result_kind"])
        self.assertNotIn("final_run", decision)
        self.assertNotIn("source_pack", decision)
        self.assertNotIn("selected_run", selection)
        self.assertEqual(
            file_sha256(self.fixture.resource / "source.bam").upper(),
            decision["native_source"]["sha256"],
        )
        self.assertEqual(decision["native_source"], selection["native_source"])
        with self.fixture.registry.open("r", encoding="utf-8", newline="") as stream:
            row = next(row for row in csv.DictReader(stream) if row["resref"] == "AMTEST")
        self.assertEqual("validé-natif", row["status"])
        self.assertEqual("", row["selected_run"])
        self.assertEqual("", row["correction_id"])
        checked = workflow.check_workspace(self.fixture.root, "AMTEST")
        self.assertTrue(checked["ok"], checked["errors"])

    def test_finalize_native_rejects_run_or_pack_bindings(self) -> None:
        with self.assertRaises(workflow.WorkflowError):
            self.fixture.finalize(registry_status="validé-natif")

    def test_finalize_native_rejects_correction_id(self) -> None:
        with self.assertRaisesRegex(workflow.WorkflowError, "correction-id interdit"):
            self.fixture.finalize(
                final_run=None,
                qa_pack=None,
                registry_status="validé-natif",
                correction_id="legacy-correction",
            )

    def test_finalize_x4_inherits_existing_correction_when_omitted(self) -> None:
        result = self.fixture.finalize(correction_id=None)
        decision = json.loads(
            (self.fixture.root / result["tracked_files"][0]).read_text(encoding="utf-8")
        )
        selection = json.loads(
            (self.fixture.root / "animations/index/selections/AMTEST.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual("legacy-correction", decision["correction_id"])
        self.assertEqual("legacy-correction", selection["correction_id"])
        with self.fixture.registry.open("r", encoding="utf-8", newline="") as stream:
            row = next(row for row in csv.DictReader(stream) if row["resref"] == "AMTEST")
        self.assertEqual("legacy-correction", row["correction_id"])

    def test_finalize_rejects_valid_but_different_qa_pack(self) -> None:
        other_pack = self.fixture.root / "animations/packs-par-zone/amtest-other"
        other_payload = bytes(((index + 17) % 251 for index in range(64)))
        self.fixture.build_qa_pack(other_pack, other_payload)
        with self.assertRaisesRegex(workflow.WorkflowError, "différente du run final"):
            self.fixture.finalize(qa_pack=other_pack, apply=False)

    def test_finalize_accepts_exact_output_split_root_binding(self) -> None:
        manifest_path = self.fixture.final_run / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("pack")
        manifest.pop("pack_manifest_sha256")
        manifest["output_split_root"] = "animations/packs-par-zone/amtest-qa"
        manifest["output_manifest_sha256"] = file_sha256(self.fixture.qa_pack / "manifest.json")
        write_json(manifest_path, manifest)
        result = self.fixture.finalize(apply=False)
        self.assertEqual("planned", result["mode"])

    def test_finalize_accepts_v1_final_pack_against_normalized_v2_qa_pack(self) -> None:
        final_run = self.fixture.resource / "runs/amtest-v1-final"
        runtime_pack = final_run / "03_runtime_pack"
        self.fixture.build_v1_runtime_pack(runtime_pack, self.fixture.payload)
        write_json(
            final_run / "manifest.json",
            {
                "schema": "bg2-upscale-area-animation-run-v1",
                "status": "completed",
                "resref": "AMTEST",
                "pack": "03_runtime_pack",
                "pack_manifest_sha256": file_sha256(runtime_pack / "manifest.json"),
            },
        )
        qa_pack = self.fixture.root / "animations/packs-par-zone/amtest-native-v2"
        self.fixture.build_qa_pack(qa_pack, self.fixture.payload, playback_mode="Native")
        result = self.fixture.finalize(final_run=final_run, qa_pack=qa_pack, apply=False)
        self.assertEqual("planned", result["mode"])

    def test_source_pack_converts_runtime_conversion_failure(self) -> None:
        manifest_path = self.fixture.qa_pack / "AR0001/manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["registry_version"] = "not-an-integer"
        write_json(manifest_path, manifest)
        with self.assertRaisesRegex(workflow.WorkflowError, "pack runtime invalide"):
            self.fixture.finalize(apply=False)

    def test_check_detects_tampered_selected_run_manifest(self) -> None:
        self.fixture.finalize()
        manifest = self.fixture.final_run / "manifest.json"
        value = json.loads(manifest.read_text(encoding="utf-8"))
        value["tampered"] = True
        write_json(manifest, value)
        result = workflow.check_workspace(self.fixture.root, "AMTEST")
        self.assertFalse(result["ok"])
        self.assertTrue(any("hash" in error for error in result["errors"]))

    def test_check_rejects_qa_when_inventory_gains_an_area(self) -> None:
        self.fixture.finalize()
        rows, _ = workflow._read_registry(self.fixture.root)
        for row in rows:
            if row["resref"] == "AMTEST":
                row["areas"] = "AR0001;AR0002;AR0003"
        self.fixture.registry.write_bytes(workflow._render_registry(rows))
        result = workflow.check_workspace(self.fixture.root, "AMTEST")
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("zones non testées AR0003" in error for error in result["errors"]),
            result["errors"],
        )

    def test_release_evidence_validation_can_ignore_later_registry_area_changes(self) -> None:
        applied = self.fixture.finalize()
        decision_path = self.fixture.root / applied["tracked_files"][0]
        rows, _ = workflow._read_registry(self.fixture.root)
        for row in rows:
            if row["resref"] == "AMTEST":
                row["areas"] = "AR0001;AR0002;AR0003"
        self.fixture.registry.write_bytes(workflow._render_registry(rows))

        errors: list[str] = []
        decision = workflow._validate_decision_record(
            self.fixture.root,
            decision_path,
            "AMTEST",
            errors,
            validate_registry=False,
        )
        self.assertIsNotNone(decision)
        self.assertEqual([], errors)

    def test_transaction_rolls_back_an_already_replaced_file(self) -> None:
        first = (
            self.fixture.root
            / "animations/index/qa-decisions/AMTEST/rollback-test.json"
        )
        second = self.fixture.root / "animations/index/selections/AMTEST.json"
        first.parent.mkdir(parents=True, exist_ok=True)
        second.parent.mkdir(parents=True, exist_ok=True)
        first.write_bytes(b"first-before")
        second.write_bytes(b"second-before")
        real_replace = workflow.os.replace
        failed = False

        def fail_second_replace(source, destination):
            nonlocal failed
            if Path(destination).resolve() == second.resolve() and not failed:
                failed = True
                raise OSError("synthetic commit failure")
            return real_replace(source, destination)

        with mock.patch.object(workflow.os, "replace", side_effect=fail_second_replace):
            with self.assertRaisesRegex(workflow.WorkflowError, "rollback complet"):
                workflow._write_transaction(
                    self.fixture.root,
                    {first: b"first-after", second: b"second-after"},
                )
        self.assertEqual(b"first-before", first.read_bytes())
        self.assertEqual(b"second-before", second.read_bytes())
        self.assertFalse(
            (self.fixture.root / workflow.AUTHORITY_JOURNAL_REL).exists()
        )
        self.assertEqual([], list(self.fixture.root.rglob("*.partial")))

    def test_transaction_rejects_directory_target_before_journal(self) -> None:
        target = self.fixture.root / "animations/index/selections/AMTEST.json"
        target.mkdir(parents=True)
        with self.assertRaisesRegex(workflow.WorkflowError, "non fichier"):
            workflow._write_transaction(self.fixture.root, {target: b"selection"})
        self.assertFalse(
            (self.fixture.root / workflow.AUTHORITY_JOURNAL_REL).exists()
        )

    def test_transaction_rejects_symlinked_authority_leaf(self) -> None:
        target = (
            self.fixture.root
            / "animations/index/qa-decisions/AMTEST/symlink-test.json"
        )
        redirected = self.fixture.root / "animations/index/selections/AMTEST.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        redirected.parent.mkdir(parents=True, exist_ok=True)
        redirected.write_bytes(b"selection-before")
        try:
            target.symlink_to(redirected)
        except OSError as error:
            self.skipTest(f"symlink unavailable: {error}")
        with self.assertRaisesRegex(workflow.WorkflowError, "lien/reparse"):
            workflow._write_transaction(self.fixture.root, {target: b"decision"})
        self.assertEqual(b"selection-before", redirected.read_bytes())
        self.assertFalse(
            (self.fixture.root / workflow.AUTHORITY_JOURNAL_REL).exists()
        )

    def test_finalize_recovers_durable_journal_after_abrupt_interruption(self) -> None:
        decision = (
            self.fixture.root
            / "animations/index/qa-decisions/AMTEST/2026-09-02-accepted-amtest-alpha-v1.json"
        )
        selection = self.fixture.root / "animations/index/selections/AMTEST.json"
        journal = self.fixture.root / workflow.AUTHORITY_JOURNAL_REL
        real_replace = workflow.os.replace
        interrupted = False

        def interrupt_before_selection(source, destination):
            nonlocal interrupted
            if Path(destination).resolve() == selection.resolve() and not interrupted:
                interrupted = True
                raise KeyboardInterrupt("synthetic abrupt stop")
            return real_replace(source, destination)

        with mock.patch.object(
            workflow.os, "replace", side_effect=interrupt_before_selection
        ):
            with self.assertRaises(KeyboardInterrupt):
                self.fixture.finalize()
        self.assertTrue(decision.is_file())
        self.assertFalse(selection.exists())
        self.assertTrue(journal.is_file())
        self.assertTrue(
            (self.fixture.root / workflow.AUTHORITY_LOCK_REL).exists()
        )

        result = self.fixture.finalize()
        self.assertIn(
            "animations/index/qa-decisions/AMTEST/2026-09-02-accepted-amtest-alpha-v1.json",
            result["recovered_before_apply"],
        )
        self.assertFalse(journal.exists())
        checked = workflow.check_workspace(self.fixture.root, "AMTEST")
        self.assertTrue(checked["ok"], checked["errors"])

    def test_recovery_refuses_to_overwrite_a_post_crash_user_edit(self) -> None:
        first = (
            self.fixture.root
            / "animations/index/qa-decisions/AMTEST/no-clobber-test.json"
        )
        second = self.fixture.root / "animations/index/selections/AMTEST.json"
        journal = self.fixture.root / workflow.AUTHORITY_JOURNAL_REL
        real_replace = workflow.os.replace
        interrupted = False

        def interrupt_before_second(source, destination):
            nonlocal interrupted
            if Path(destination).resolve() == second.resolve() and not interrupted:
                interrupted = True
                raise KeyboardInterrupt("synthetic abrupt stop")
            return real_replace(source, destination)

        with mock.patch.object(
            workflow.os, "replace", side_effect=interrupt_before_second
        ):
            with self.assertRaises(KeyboardInterrupt):
                workflow._write_transaction(
                    self.fixture.root,
                    {first: b"published-first", second: b"published-second"},
                )
        self.assertTrue(journal.is_file())
        first.write_bytes(b"post-crash-user-edit")

        with self.assertRaisesRegex(workflow.WorkflowError, "cible modifiée"):
            workflow._recover_authority_transaction(self.fixture.root)
        self.assertEqual(b"post-crash-user-edit", first.read_bytes())
        self.assertTrue(journal.is_file())

    def test_rollback_continues_and_keeps_journal_when_one_restore_fails(self) -> None:
        first = (
            self.fixture.root
            / "animations/index/qa-decisions/AMTEST/rollback-all-test.json"
        )
        second = self.fixture.root / "animations/index/selections/AMTEST.json"
        third = self.fixture.registry
        first.parent.mkdir(parents=True, exist_ok=True)
        second.parent.mkdir(parents=True, exist_ok=True)
        first.write_bytes(b"first-before")
        second.write_bytes(b"second-before")
        third_before = third.read_bytes()
        target_counts = {first.resolve(): 0, second.resolve(): 0, third.resolve(): 0}
        real_replace = workflow.os.replace

        def fail_publication_then_one_restore(source, destination):
            target = Path(destination).resolve()
            if target in target_counts:
                target_counts[target] += 1
                if target == third.resolve() and target_counts[target] == 1:
                    raise OSError("synthetic publication failure")
                if target == second.resolve() and target_counts[target] == 2:
                    raise OSError("synthetic rollback failure")
            return real_replace(source, destination)

        with mock.patch.object(
            workflow.os,
            "replace",
            side_effect=fail_publication_then_one_restore,
        ):
            with self.assertRaisesRegex(workflow.WorkflowError, "journal conservé"):
                workflow._write_transaction(
                    self.fixture.root,
                    {
                        first: b"first-after",
                        second: b"second-after",
                        third: b"third-after",
                    },
                )
        journal = self.fixture.root / workflow.AUTHORITY_JOURNAL_REL
        self.assertTrue(journal.is_file())
        self.assertEqual(b"first-before", first.read_bytes())
        self.assertEqual(b"second-after", second.read_bytes())
        self.assertEqual(third_before, third.read_bytes())

        restored = workflow._recover_authority_transaction(self.fixture.root)
        self.assertEqual(3, len(restored))
        self.assertFalse(journal.exists())
        self.assertEqual(b"first-before", first.read_bytes())
        self.assertEqual(b"second-before", second.read_bytes())
        self.assertEqual(third_before, third.read_bytes())


class AnimationRegistrySyncTests(unittest.TestCase):
    def test_sync_preserves_selection_and_qa_manual_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / "resources.csv"
            occurrences = root / "occurrences.csv"
            current = root / "current.csv"
            resources.write_text(
                "bam_resref,frames,max_frame_width,max_frame_height,format,area_ids,occurrences\n"
                "AMTEST,6,20,21,BAM V1,AR0001,1\n",
                encoding="utf-8",
            )
            occurrences.write_text(
                "resource_kind,resource_resref,area_id\nBAM,AMTEST,AR0001\n",
                encoding="utf-8",
            )
            current.write_text(
                ",".join(sync_registry.FIELDS)
                + "\n"
                + "AMTEST,validé-x4,AR0001,1,6,20x21,BAM V1,"
                + "animations/ressources/AMTEST/runs/final,"
                + "animations/index/qa-decisions/AMTEST/qa.json,"
                + "2026-09-02,corr-v1,note\n",
                encoding="utf-8",
            )
            rows = sync_registry.build_rows(resources, occurrences, current)
            self.assertEqual("animations/ressources/AMTEST/runs/final", rows[0]["selected_run"])
            self.assertEqual("animations/index/qa-decisions/AMTEST/qa.json", rows[0]["qa_decision"])
            self.assertEqual("2026-09-02", rows[0]["qa_date"])


if __name__ == "__main__":
    unittest.main()
