from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_animation_runtime_pack as runtime_v1  # noqa: E402
import run_animation_upscale_30fps_v2 as pipeline  # noqa: E402
import split_animation_pack_by_area as splitter  # noqa: E402
import merge_area_pack_resources as merger  # noqa: E402
import build_blended_rgb_neutral_pack as blend_builder  # noqa: E402


class AreaSplitTests(unittest.TestCase):
    def make_v1_pack(self, root: Path, resrefs: tuple[str, ...]) -> Path:
        """A minimal completed V1 run, built into a real runtime pack."""
        run = root / "run"
        resources = []
        for offset, resref in enumerate(resrefs):
            frames_x1 = run / "resources" / resref / "01_frames_x1"
            upscale = run / "resources" / resref / "02_upscale_x4"
            raw = upscale / "raw_rgba"
            frames_x1.mkdir(parents=True)
            raw.mkdir(parents=True)
            (frames_x1 / "manifest.json").write_text(json.dumps({
                "schema": runtime_v1.FRAME_SCHEMA,
                "frame_count": 2,
                "geometry_mode": "uniform",
                "cycles": [{"cycle": 0, "frame_indices": [0, 1]}],
            }), encoding="utf-8")
            upscale_frames = []
            for index in range(2):
                path = raw / f"frame_{index:03d}.rgba"
                path.write_bytes(bytes([(offset * 8 + index + 1) & 0xFF]) * (2 * 4 * 2 * 4 * 4))
                upscale_frames.append({
                    "frame": index,
                    "logical_size_x1": [2, 2],
                    "physical_size_xn": [8, 8],
                    "centre_x1": [1, 2],
                    "raw_rgba_xn": f"raw_rgba/{path.name}",
                    "raw_rgba_xn_sha256": runtime_v1.sha256_file(path),
                })
            (upscale / "manifest.json").write_text(json.dumps({
                "schema": runtime_v1.UPSCALE_SCHEMA,
                "status": "completed",
                "scale": 4,
                "frames": upscale_frames,
            }), encoding="utf-8")
            resources.append({
                "resref": resref,
                "status": "completed",
                "frames_x1": f"resources/{resref}/01_frames_x1",
                "upscale": f"resources/{resref}/02_upscale_x4",
            })
        (run / "manifest.json").write_text(json.dumps({
            "schema": runtime_v1.RUN_SCHEMA,
            "status": "completed",
            "request": {"scale": 4},
            "resources": resources,
        }), encoding="utf-8")
        runtime_v1.main([str(run)])
        return run / "03_runtime_pack"

    def write_occurrences(self, path: Path, rows: list[tuple[str, str]]) -> None:
        lines = ["area_id,occurrence_index,instance_name,bam_resref,x,y,cell_x,cell_y,"
                 "sequence,initial_frame,flags_hex"]
        for index, (area, resref) in enumerate(rows):
            lines.append(f"{area},{index},{resref},{resref},0,0,0,0,0,0,0x0")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_splits_per_area_and_duplicates_shared_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = self.make_v1_pack(root, ("ALPHA", "SHARED"))
            occurrences = root / "occurrences.csv"
            # SHARED is posed in both areas; ALPHA only in the first.
            self.write_occurrences(occurrences, [
                ("AR0001", "ALPHA"), ("AR0001", "SHARED"),
                ("AR0002", "SHARED"),
                ("AR0003", "ABSENT"),
            ])
            output = root / "by-area"
            index = splitter.split(pack, output, occurrences, resume=False)

            # AR0003 references nothing this pack carries, so it gets no pack at all and
            # the engine keeps rendering its own BAM there.
            self.assertEqual([entry["area_id"] for entry in index["areas"]], ["AR0001", "AR0002"])
            self.assertEqual(index["area_count"], 2)
            self.assertEqual(index["areas_over_budget"], [])

            first, second = index["areas"]
            self.assertEqual(first["resrefs"], ["ALPHA", "SHARED"])
            self.assertEqual(second["resrefs"], ["SHARED"])

            # Each area pack must stand alone and validate through the normal reader.
            for entry in index["areas"]:
                manifest, resources = pipeline.validate_v2_pack(output / entry["area_id"])
                self.assertEqual(manifest["area_id"], entry["area_id"])
                self.assertEqual(sorted(str(item["resref"]) for item in resources),
                                 entry["resrefs"])
                self.assertTrue(manifest.get("runtime_budget_enforced", True))

            # The shared resource is physically duplicated, byte for byte.
            shared_asset = "AAX4-SHARED-frame000.rgba"
            self.assertEqual((output / "AR0001" / shared_asset).read_bytes(),
                             (output / "AR0002" / shared_asset).read_bytes())
            # An area pack carries only its own assets.
            self.assertFalse((output / "AR0002" / "AAX4-ALPHA-frame000.rgba").exists())

            # The registries differ because they describe different resource sets.
            self.assertNotEqual(first["registry_sha256"], second["registry_sha256"])

    def test_resume_revalidates_and_rejects_foreign_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = self.make_v1_pack(root, ("ALPHA",))
            occurrences = root / "occurrences.csv"
            self.write_occurrences(occurrences, [("AR0001", "ALPHA")])
            output = root / "by-area"
            first = splitter.split(pack, output, occurrences, resume=False)

            with self.assertRaises(RuntimeError):
                splitter.split(pack, output, occurrences, resume=False)

            again = splitter.split(pack, output, occurrences, resume=True)
            self.assertEqual(again["source_pack_manifest_sha256"],
                             first["source_pack_manifest_sha256"])

            # A resume pointed at a different source pack must not silently pass.
            other_root = root / "other"
            other_root.mkdir()
            other_pack = self.make_v1_pack(other_root, ("ALPHA", "SHARED"))
            with self.assertRaises(RuntimeError):
                splitter.split(other_pack, output, occurrences, resume=True)

    def test_tampered_area_asset_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = self.make_v1_pack(root, ("ALPHA",))
            occurrences = root / "occurrences.csv"
            self.write_occurrences(occurrences, [("AR0001", "ALPHA")])
            output = root / "by-area"
            splitter.split(pack, output, occurrences, resume=False)

            asset = output / "AR0001" / "AAX4-ALPHA-frame000.rgba"
            asset.write_bytes(b"\x00" * asset.stat().st_size)
            with self.assertRaises(RuntimeError):
                pipeline.validate_v2_pack(output / "AR0001")

    def test_authoring_exemption_requires_explicit_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = self.make_v1_pack(root, ("ALPHA",))
            occurrences = root / "occurrences.csv"
            self.write_occurrences(occurrences, [("AR0001", "ALPHA")])
            output = root / "by-area"
            splitter.split(pack, output, occurrences, resume=False)
            area_pack = output / "AR0001"
            manifest_path = area_pack / "manifest.json"

            # Force the pack over the runtime budget without changing any asset, by
            # claiming a size the reader recomputes from the inventory.
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for resource in manifest["resources"]:
                for asset in resource["assets"]:
                    asset["bytes"] = pipeline.MAX_RAW_BYTES
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                pipeline.validate_v2_pack(area_pack)

            # Exempting it without saying why is still refused...
            manifest["runtime_budget_enforced"] = False
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(RuntimeError) as refused:
                pipeline.validate_v2_pack(area_pack)
            self.assertIn("exemption de budget", str(refused.exception))

            # ...and declaring the authoring use gets past the budget check, leaving the
            # per-asset checks to fail on their own terms rather than on the budget.
            manifest["authoring_pack_for_area_split"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(RuntimeError) as later:
                pipeline.validate_v2_pack(area_pack)
            self.assertNotIn("limite mémoire", str(later.exception))

    def test_v3_variants_survive_merge_split_and_resume(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            occurrences = root / "occurrences.csv"
            self.write_occurrences(occurrences, [("AR0900", "TESTA")])

            inputs = []
            for name in ("north", "south"):
                pack = self.make_v1_pack(root / name, ("TESTA",))
                split_root = root / name / "split"
                splitter.split(pack, split_root, occurrences, resume=False)
                inputs.append(split_root / "AR0900")

            specs = [f"{inputs[0]}::1689,2662", f"{inputs[1]}::2246,2187"]
            merged = root / "merged"
            index = merger.merge(specs, "AR0900", merged, resume=False)
            self.assertEqual(index["areas"][0]["resrefs"], ["TESTA"])
            manifest, resources = pipeline.validate_v2_pack(merged / "AR0900")
            self.assertEqual(manifest["registry_version"], 3)
            self.assertEqual([resource["position"] for resource in resources],
                             [[1689, 2662], [2246, 2187]])
            self.assertEqual([resource["variant_index"] for resource in resources], [0, 1])
            self.assertTrue((merged / "AR0900" / "AAX4-TESTA-frame000.rgba").is_file())
            self.assertTrue((merged / "AR0900" / "AAX4-TESTA-v1-frame000.rgba").is_file())

            again = merger.merge(specs, "AR0900", merged, resume=True)
            self.assertEqual(again["areas"][0]["registry_sha256"],
                             index["areas"][0]["registry_sha256"])

            resplit = root / "resplit"
            split_index = splitter.split(merged / "AR0900", resplit, occurrences, resume=False)
            self.assertEqual(split_index["areas"][0]["resource_count"], 2)
            _manifest, split_resources = pipeline.validate_v2_pack(resplit / "AR0900")
            self.assertEqual([resource["position"] for resource in split_resources],
                             [[1689, 2662], [2246, 2187]])

    def test_merge_refuses_two_variants_at_the_same_position(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            occurrences = root / "occurrences.csv"
            self.write_occurrences(occurrences, [("AR0900", "TESTA")])
            inputs = []
            for name in ("one", "two"):
                pack = self.make_v1_pack(root / name, ("TESTA",))
                split_root = root / name / "split"
                splitter.split(pack, split_root, occurrences, resume=False)
                inputs.append(split_root / "AR0900")
            with self.assertRaisesRegex(RuntimeError, "variante dupliquée"):
                merger.merge([f"{inputs[0]}::1689,2662", f"{inputs[1]}::1689,2662"],
                             "AR0900", root / "merged", resume=False)

            _manifest, resources = pipeline.validate_v2_pack(inputs[0])
            resources[0]["position"] = [1689.5, 2662]
            with self.assertRaisesRegex(RuntimeError, "non entières"):
                pipeline.registry_v2_from_resources(resources)

    def test_validator_keeps_registry_v2_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = self.make_v1_pack(root, ("TESTA",))
            occurrences = root / "occurrences.csv"
            self.write_occurrences(occurrences, [("AR0900", "TESTA")])
            split_root = root / "split"
            splitter.split(pack, split_root, occurrences, resume=False)
            area = split_root / "AR0900"
            manifest = json.loads((area / "manifest.json").read_text(encoding="utf-8"))
            registry = pipeline.registry_v2_from_resources(
                manifest["resources"], pipeline.LEGACY_REGISTRY_VERSION)
            registry_path = area / pipeline.REGISTRY_NAME
            registry_path.write_bytes(registry)
            manifest["registry_version"] = pipeline.LEGACY_REGISTRY_VERSION
            manifest["runtime_contract"]["registry_version"] = pipeline.LEGACY_REGISTRY_VERSION
            manifest["registry_sha256"] = pipeline.sha256_file(registry_path)
            manifest["registry_bytes"] = len(registry)
            pipeline.write_json(area / "manifest.json", manifest)

            validated, _resources = pipeline.validate_v2_pack(area)
            self.assertEqual(validated["registry_version"], 2)
            self.assertEqual(struct.unpack_from("<I", registry, 8)[0], 2)

    def test_mask_anchor_is_written_as_registry_v3_position(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = self.make_v1_pack(root, ("TESTA",))
            occurrences = root / "occurrences.csv"
            self.write_occurrences(occurrences, [("AR0900", "TESTA")])
            split_root = root / "split"
            splitter.split(pack, split_root, occurrences, resume=False)

            output = root / "masked"
            anchor = (1689, 2662)
            # The fixture frames are 8x8 x4 and centred at (1,2) x1.
            mask_origin = ((anchor[0] - 1) * 4, (anchor[1] - 2) * 4)
            mask_source = root / "occlusion-mask.png"
            Image.new("RGBA", (8, 8), (255, 255, 255, 255)).save(mask_source)
            mask = blend_builder.load_occlusion_mask(mask_source)
            blend_builder.build(split_root, output, {"TESTA"}, False, "premultiply", None,
                                mask=mask, mask_origin_x4=mask_origin,
                                mask_anchor_x1=anchor, mask_source=mask_source)

            manifest, resources = pipeline.validate_v2_pack(output / "AR0900")
            self.assertEqual(manifest["registry_version"], 3)
            self.assertEqual(resources[0]["position"], [1689, 2662])
            self.assertEqual(resources[0]["variant_index"], 0)
            self.assertEqual(manifest["rgb_neutralisation"]["occurrence_position"],
                             [1689, 2662])
            sealed = output / blend_builder.OCCLUSION_MASK_ROOT_PATH
            digest = pipeline.sha256_file(sealed)
            self.assertEqual(sealed.read_bytes(), mask_source.read_bytes())
            area_mask = manifest["rgb_neutralisation"]["occlusion_mask"]
            self.assertEqual(area_mask["storage"], blend_builder.OCCLUSION_MASK_STORAGE)
            self.assertEqual(area_mask["source"], blend_builder.OCCLUSION_MASK_AREA_PATH)
            self.assertEqual(area_mask["sha256"], digest)
            root_manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            root_mask = root_manifest["rgb_neutralisation"]["occlusion_mask"]
            self.assertEqual(root_mask["source"], blend_builder.OCCLUSION_MASK_ROOT_PATH)
            self.assertEqual(root_mask["sha256"], digest)

            # Resume depends on the embedded bytes, not on the mutable authoring source.
            mask_source.unlink()
            resumed = blend_builder.build(
                split_root, output, {"TESTA"}, True, "premultiply", None,
                mask=mask, mask_origin_x4=mask_origin, mask_anchor_x1=anchor,
                mask_source=mask_source)
            self.assertEqual(resumed["rgb_neutralisation"]["occlusion_mask"]["sha256"], digest)

            sealed.write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "hash du masque"):
                blend_builder.build(
                    split_root, output, {"TESTA"}, True, "premultiply", None,
                    mask=mask, mask_origin_x4=mask_origin, mask_anchor_x1=anchor,
                    mask_source=mask_source)

    def test_mask_resume_keeps_unversioned_legacy_provenance_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = self.make_v1_pack(root, ("TESTA",))
            occurrences = root / "occurrences.csv"
            self.write_occurrences(occurrences, [("AR0900", "TESTA")])
            split_root = root / "split"
            splitter.split(pack, split_root, occurrences, resume=False)

            mask_source = root / "legacy-mask.png"
            Image.new("RGBA", (8, 8), (255, 255, 255, 255)).save(mask_source)
            mask = blend_builder.load_occlusion_mask(mask_source)
            output = root / "masked-legacy"
            blend_builder.build(
                split_root, output, {"TESTA"}, False, "premultiply", None,
                mask=mask, mask_source=mask_source)

            area_manifest_path = output / "AR0900" / "manifest.json"
            area_manifest = json.loads(area_manifest_path.read_text(encoding="utf-8"))
            area_record = area_manifest["rgb_neutralisation"]["occlusion_mask"]
            area_record.pop("storage")
            area_record["source"] = mask_source.resolve().as_posix()
            pipeline.write_json(area_manifest_path, area_manifest)

            root_manifest_path = output / "manifest.json"
            root_manifest = json.loads(root_manifest_path.read_text(encoding="utf-8"))
            root_record = root_manifest["rgb_neutralisation"]["occlusion_mask"]
            root_record.pop("storage")
            root_record["source"] = mask_source.resolve().as_posix()
            root_manifest["areas"][0]["manifest_sha256"] = pipeline.sha256_file(
                area_manifest_path)
            pipeline.write_json(root_manifest_path, root_manifest)
            (output / blend_builder.OCCLUSION_MASK_ROOT_PATH).unlink()

            resumed = blend_builder.build(
                split_root, output, {"TESTA"}, True, "premultiply", None,
                mask=mask, mask_source=mask_source)
            self.assertEqual(
                resumed["rgb_neutralisation"]["occlusion_mask"]["source"],
                mask_source.resolve().as_posix())


if __name__ == "__main__":
    unittest.main()
