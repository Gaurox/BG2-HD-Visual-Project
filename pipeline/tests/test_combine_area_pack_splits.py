from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_animation_runtime_pack as runtime_v1  # noqa: E402
import run_animation_upscale_30fps_v2 as pipeline  # noqa: E402
import split_animation_pack_by_area as splitter  # noqa: E402
import combine_area_pack_splits as combiner  # noqa: E402


class CombineAreaPackSplitsTests(unittest.TestCase):
    def make_v1_pack(self, root: Path, resrefs: tuple[str, ...]) -> Path:
        run = root / "run"
        resources = []
        for offset, resref in enumerate(resrefs):
            frames_x1 = run / "resources" / resref / "01_frames_x1"
            upscale = run / "resources" / resref / "02_upscale_x4"
            raw = upscale / "raw_rgba"
            frames_x1.mkdir(parents=True)
            raw.mkdir(parents=True)
            (frames_x1 / "manifest.json").write_text(json.dumps({
                "schema": runtime_v1.FRAME_SCHEMA, "frame_count": 2,
                "geometry_mode": "uniform", "cycles": [{"cycle": 0, "frame_indices": [0, 1]}],
            }), encoding="utf-8")
            upscale_frames = []
            for index in range(2):
                path = raw / f"frame_{index:03d}.rgba"
                path.write_bytes(bytes([(offset * 8 + index + 1) & 0xFF]) * (2 * 4 * 2 * 4 * 4))
                upscale_frames.append({
                    "frame": index, "logical_size_x1": [2, 2], "physical_size_xn": [8, 8],
                    "centre_x1": [1, 2], "raw_rgba_xn": f"raw_rgba/{path.name}",
                    "raw_rgba_xn_sha256": runtime_v1.sha256_file(path),
                })
            (upscale / "manifest.json").write_text(json.dumps({
                "schema": runtime_v1.UPSCALE_SCHEMA, "status": "completed", "scale": 4,
                "frames": upscale_frames,
            }), encoding="utf-8")
            resources.append({
                "resref": resref, "status": "completed",
                "frames_x1": f"resources/{resref}/01_frames_x1",
                "upscale": f"resources/{resref}/02_upscale_x4",
            })
        (run / "manifest.json").write_text(json.dumps({
            "schema": runtime_v1.RUN_SCHEMA, "status": "completed",
            "request": {"scale": 4}, "resources": resources,
        }), encoding="utf-8")
        runtime_v1.main([str(run)])
        return run / "03_runtime_pack"

    def write_occurrences(self, path: Path, rows: list[tuple[str, str]]) -> None:
        lines = ["area_id,occurrence_index,instance_name,bam_resref,x,y,cell_x,cell_y,"
                 "sequence,initial_frame,flags_hex"]
        for index, (area, resref) in enumerate(rows):
            lines.append(f"{area},{index},{resref},{resref},0,0,0,0,0,0,0x0")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def make_split(self, root: Path, name: str, resrefs: tuple[str, ...],
                   area: str) -> Path:
        pack = self.make_v1_pack(root / name, resrefs)
        occurrences = root / name / "occurrences.csv"
        self.write_occurrences(occurrences, [(area, r) for r in resrefs])
        output = root / name / "split"
        splitter.split(pack, output, occurrences, resume=False)
        return output

    def test_combines_disjoint_areas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            split_a = self.make_split(root, "batch-a", ("ALPHA",), "AR0001")
            split_b = self.make_split(root, "batch-b", ("BETA",), "AR0002")

            combined = root / "combined"
            index = combiner.combine([split_a, split_b], combined, resume=False)

            self.assertEqual(sorted(item["area_id"] for item in index["areas"]),
                             ["AR0001", "AR0002"])
            for area_id in ("AR0001", "AR0002"):
                manifest, _resources = pipeline.validate_v2_pack(combined / area_id)
                self.assertEqual(manifest["area_id"], area_id)

    def test_refuses_area_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            split_a = self.make_split(root, "batch-a", ("ALPHA",), "AR0001")
            split_b = self.make_split(root, "batch-b", ("GAMMA",), "AR0001")

            with self.assertRaises(RuntimeError) as failure:
                combiner.combine([split_a, split_b], root / "combined", resume=False)
            self.assertIn("AR0001", str(failure.exception))

    def test_replaces_explicit_area_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            split_a = self.make_split(root, "batch-a", ("ALPHA",), "AR0001")
            split_b = self.make_split(root, "batch-b", ("GAMMA",), "AR0001")

            combined = root / "combined"
            index = combiner.combine(
                [split_a, split_b], combined, resume=False, replace_areas={"AR0001"},
            )

            self.assertEqual(index["replaced_areas"], ["AR0001"])
            _manifest, resources = pipeline.validate_v2_pack(combined / "AR0001")
            self.assertEqual([resource["resref"] for resource in resources], ["GAMMA"])

    def test_resume_revalidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            split_a = self.make_split(root, "batch-a", ("ALPHA",), "AR0001")
            combined = root / "combined"
            first = combiner.combine([split_a], combined, resume=False)

            with self.assertRaises(RuntimeError):
                combiner.combine([split_a], combined, resume=False)

            again = combiner.combine([split_a], combined, resume=True)
            self.assertEqual(sorted(i["area_id"] for i in again["areas"]),
                             sorted(i["area_id"] for i in first["areas"]))

    def test_tampered_input_area_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            split_a = self.make_split(root, "batch-a", ("ALPHA",), "AR0001")
            asset = next((split_a / "AR0001").glob("AAX4-ALPHA-*.rgba"))
            asset.write_bytes(b"\x00" * asset.stat().st_size)

            with self.assertRaises(RuntimeError):
                combiner.combine([split_a], root / "combined", resume=False)


if __name__ == "__main__":
    unittest.main()
