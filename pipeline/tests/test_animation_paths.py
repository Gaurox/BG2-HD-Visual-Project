from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import animation_paths  # noqa: E402


class AnimationPathTests(unittest.TestCase):
    def test_new_mono_resref_run_uses_resource_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            actual = animation_paths.resolve_run_destination(
                "am0602j-seedvr-v1",
                ["am0602j"],
                animations_root=root,
            )
            self.assertEqual(
                actual,
                root.resolve() / "ressources" / "AM0602J" / "runs" / "am0602j-seedvr-v1",
            )
            self.assertFalse(actual.exists())

    def test_new_multi_resref_run_uses_batch_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            actual = animation_paths.resolve_run_destination(
                "ar0602-seedvr-v1",
                ["AM0602C", "AM0602D"],
                animations_root=root,
            )
            self.assertEqual(actual, root.resolve() / "batches" / "ar0602-seedvr-v1")

    def test_existing_legacy_run_is_resumed_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            legacy = root / "runs" / "legacy-run"
            legacy.mkdir(parents=True)
            actual = animation_paths.resolve_run_destination(
                "legacy-run",
                ["AM0602J"],
                animations_root=root,
            )
            self.assertEqual(actual, legacy.resolve())

    def test_existing_partial_legacy_run_is_resumed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            partial = root / "runs" / "legacy-run.partial"
            partial.mkdir(parents=True)
            actual = animation_paths.resolve_run_destination(
                "legacy-run",
                ["AM0602J"],
                animations_root=root,
            )
            self.assertEqual(actual, root.resolve() / "runs" / "legacy-run")

    def test_explicit_legacy_root_is_honoured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            actual = animation_paths.resolve_run_destination(
                "legacy-run",
                ["AM0602J"],
                runs_root=root / "runs",
                animations_root=root,
            )
            self.assertEqual(actual, root.resolve() / "runs" / "legacy-run")

    def test_explicit_root_outside_standard_layout_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            with self.assertRaisesRegex(RuntimeError, "non canonique"):
                animation_paths.resolve_run_destination(
                    "new-run",
                    ["AM0602J"],
                    runs_root=root / "misc",
                    animations_root=root,
                )

    def test_source_run_id_resolves_current_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            current = root / "ressources" / "AM0602J" / "runs" / "spatial-v1"
            current.mkdir(parents=True)
            actual = animation_paths.resolve_existing_run(
                "spatial-v1",
                ["AM0602J"],
                animations_root=root,
            )
            self.assertEqual(actual, current.resolve())

    def test_explicit_source_path_outside_standard_layout_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            outside = Path(temporary) / "misc" / "run-v1"
            outside.mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, "hors du workspace animations"):
                animation_paths.resolve_existing_run(
                    outside,
                    ["AM0602J"],
                    animations_root=root,
                )

    def test_duplicate_run_id_across_layouts_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            (root / "ressources" / "AM0602J" / "runs" / "duplicate").mkdir(
                parents=True
            )
            (root / "runs" / "duplicate").mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, "ambigu"):
                animation_paths.resolve_run_destination(
                    "duplicate",
                    ["AM0602J"],
                    animations_root=root,
                )

    def test_invalid_run_id_is_rejected(self) -> None:
        for run_id in ("../outside", "name.", "CON", "com1.preview", "x" * 129):
            with self.subTest(run_id=run_id):
                with self.assertRaisesRegex(RuntimeError, "identifiant de run invalide"):
                    animation_paths.validate_run_id(run_id)

    def test_multi_resref_run_cannot_use_one_resource_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            with self.assertRaisesRegex(RuntimeError, "non canonique"):
                animation_paths.validate_run_location(
                    root / "ressources" / "AM0602J" / "runs" / "batch-v1",
                    ["AM0602J", "AM0602K"],
                    animations_root=root,
                )

    def test_multi_resref_lookup_does_not_resume_a_mono_asset_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            mono = root / "ressources" / "AM0602J" / "runs" / "shared-id"
            mono.mkdir(parents=True)
            destination = animation_paths.resolve_run_destination(
                "shared-id",
                ["AM0602J", "AM0602K"],
                animations_root=root,
            )
            self.assertEqual(destination, root.resolve() / "batches" / "shared-id")
            with self.assertRaisesRegex(RuntimeError, "introuvable"):
                animation_paths.resolve_existing_run(
                    "shared-id",
                    ["AM0602J", "AM0602K"],
                    animations_root=root,
                )

    def test_selection_location_accepts_current_batch_and_legacy_roots_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "animations"
            for path in (
                root / "ressources" / "AM0602J" / "runs" / "final-v1",
                root / "batches" / "batch-v1",
                root / "runs" / "legacy-v1",
            ):
                self.assertEqual(
                    animation_paths.validate_run_location(
                        path, ["AM0602J"], animations_root=root
                    ),
                    path.resolve(),
                )
            with self.assertRaisesRegex(RuntimeError, "non canonique"):
                animation_paths.validate_run_location(
                    root / "runs" / "legacy-v1" / "03_runtime_pack",
                    ["AM0602J"],
                    animations_root=root,
                )


if __name__ == "__main__":
    unittest.main()
