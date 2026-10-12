from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import effect_tracking as tracking
import effect_workflow as workflow


def bam() -> bytes:
    # Two 1x1 frames; one empty cycle and one two-slot cycle.
    palette_offset = 24 + 24 + 8
    lookup_offset = palette_offset + 1024
    pixel_offset = lookup_offset + 4
    palette = bytearray(1024)
    palette[4:8] = bytes((20, 30, 40, 0))
    palette[8:12] = bytes((50, 60, 70, 0))
    return (struct.pack("<8sHBBIII", b"BAM V1  ", 2, 2, 0, 24, palette_offset, lookup_offset)
            + struct.pack("<HHhhI", 1, 1, 0, 0, pixel_offset | 0x80000000)
            + struct.pack("<HHhhI", 1, 1, 0, 0, (pixel_offset + 1) | 0x80000000)
            + struct.pack("<HHHH", 0, 0, 2, 0) + palette + struct.pack("<HH", 0, 1) + bytes((1, 2)))


class EffectTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        assets, processing = [], []
        for name in ("FXA", "FXB", "MISSING"):
            source = self.root / f"effects/ressources/{name}/source.bam"
            source.parent.mkdir(parents=True)
            missing = name == "MISSING"
            if not missing:
                source.write_bytes(bam())
            assets.append({"asset_key": f"effects:bam:{name}", "resref": name,
                           "source_state": "missing" if missing else "available",
                           "source_sha256": "" if missing else workflow.sha256_file(source),
                           "source_size": "" if missing else len(bam()),
                           "extracted_path": source.relative_to(self.root).as_posix()})
            processing.append({**dict.fromkeys(workflow.PROCESSING_FIELDS, ""),
                               "asset_key": f"effects:bam:{name}", "asset_directory": f"effects/ressources/{name}",
                               "spatial_state": "blocked" if missing else "not-started", "interpolation_state": "not-started",
                               "qa_state": "not-assessed", "installation_state": "not-installed", "release_state": "not-evaluated"})
        self.write_csv("effects/index/bam-assets.csv", assets)
        (self.root / "effects/index/processing.csv").write_bytes(workflow.csv_bytes(processing))
        vvc = bytearray(492)
        vvc[:8] = b"VVC V1.0"
        vvc[8:16] = b"FXA\0\0\0\0\0"
        struct.pack_into("<H", vvc, 0x18, 8)
        struct.pack_into("<I", vvc, 0x20, 1)
        struct.pack_into("<I", vvc, 0x34, 8)
        struct.pack_into("<I", vvc, 0x38, 16)
        path = self.root / "effects/source/vvc/OWNER.vvc"
        path.parent.mkdir(parents=True)
        path.write_bytes(vvc)
        self.write_csv("effects/index/resources.csv", [{"asset_key": "effect:vvc:OWNER", "format": "VVC",
                                                       "extracted_path": path.relative_to(self.root).as_posix(), "source_sha256": workflow.sha256_file(path)}])
        self.write_csv("effects/index/dependencies.csv", [{"asset_key": "effect:vvc:OWNER", "relation": "animation",
                                                          "dependency_resref": "FXA", "resolved_format": "BAM", "present": "yes"}])

    def write_csv(self, path, rows):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(stream.getvalue(), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_generated_hints_preserve_authority_and_share_only_source_work(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        planned = tracking.refresh(self.root)
        after = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(planned["unique_sources"], 1)
        self.assertEqual(planned["native_frames"], 4)
        self.assertEqual(planned["unique_rgba_geometry_frames"], 2)
        tracking.refresh(self.root, True)
        self.assertEqual((self.root / "effects/index/processing.csv").read_bytes(), before["effects/index/processing.csv"])
        item = tracking.work_item(self.root, "FXA")
        self.assertEqual(item["reuse_bams"], "FXB")
        self.assertIn("runtime-empty-cycles-unsupported", item["technical_notes"])
        self.assertIn("interpolation-noninteger-rate-unsupported", item["technical_notes"])
        self.assertEqual(tracking.work_item(self.root, "FXB")["usage"], "unresolved")
        tracking.classify(self.root, "FXA", {"recipe": "my-recipe", "priority": 1}, True)
        tracking.refresh(self.root, True)
        self.assertEqual(tracking.work_item(self.root, "FXA")["recipe"], "my-recipe")
        queued = tracking.queue(self.root)
        self.assertEqual(queued["counts"], {"pending": 1, "unresolved": 1, "blocked": 1})
        self.assertEqual(queued["items"][0]["resref"], "FXA")
        self.assertEqual(queued["items"][0]["recipe"], "my-recipe")

    def test_new_trial_remains_visible_while_previous_qa_stays_accepted(self):
        tracking.refresh(self.root, True)
        rows = workflow.read_csv(self.root / "effects/index/processing.csv")
        rows[0].update({"qa_state": "passed", "selected_run": "old", "spatial_run": "new", "spatial_state": "produced"})
        (self.root / "effects/index/processing.csv").write_bytes(workflow.csv_bytes(rows))
        selected = workflow.selection_path(self.root, "FXA")
        selected.parent.mkdir(parents=True)
        selected.write_text(json.dumps({"contract": {"source": {"spatial_run": "old"}}}), encoding="utf-8")
        queued = tracking.queue(self.root)
        self.assertEqual(queued["items"][0]["queue_state"], "working")
        self.assertEqual(queued["items"][0]["acquired_qa"], "passed")

    def test_projectile_role_and_palette_are_preserved_without_claiming_a_recipe(self):
        data = bytearray(512)
        data[:8] = b"PRO V1.0"
        struct.pack_into("<I", data, 0x100, 1)
        data[0x104:0x10C] = b"FXA\0\0\0\0\0"
        data[0x11C:0x124] = b"PALETTE\0"
        data[0x133] = 5
        path = self.root / "projectiles/source/TRAVEL.pro"
        path.parent.mkdir(parents=True)
        path.write_bytes(data)
        self.write_csv("projectiles/index/resources.csv", [{"asset_key": "projectile:TRAVEL", "extracted_path": path.relative_to(self.root).as_posix(), "source_sha256": workflow.sha256_file(path)}])
        self.write_csv("projectiles/index/dependencies.csv", [{"asset_key": "projectile:TRAVEL", "relation": "travel-animation", "resolved_format": "BAM", "dependency_resref": "FXA"}])
        tracking.refresh(self.root, True)
        rows = workflow.read_csv(self.root / tracking.CONSUMERS)
        projectile = next(r for r in rows if r["consumer_key"] == "projectile:TRAVEL")
        self.assertEqual(projectile["palette"], "PALETTE")
        self.assertEqual(projectile["owner_route"], "projectile")
        item = tracking.work_item(self.root, "FXA")
        self.assertIn("palette", item["tags"])
        self.assertEqual(item["recipe"], "")

    def test_vef_keeps_timing_for_nested_vvc_and_direct_bam_members(self):
        data = bytearray(24 + 2 * 224)
        data[:8] = b"VEF     "
        struct.pack_into("<IIII", data, 8, 24, 2, len(data), 0)
        for pos, name, start in [(24, b"OWNER\0\0\0", 12), (248, b"FXB\0\0\0\0\0", 6)]:
            struct.pack_into("<I", data, pos, start)
            struct.pack_into("<I", data, pos + 12, 1)
            data[pos + 16:pos + 24] = name
        path = self.root / "effects/source/vef/COMBO.vef"
        path.parent.mkdir(parents=True)
        path.write_bytes(data)
        resources = workflow.read_csv(self.root / "effects/index/resources.csv")
        resources.append({"asset_key": "effect:vef:COMBO", "format": "VEF", "extracted_path": path.relative_to(self.root).as_posix(), "source_sha256": workflow.sha256_file(path)})
        self.write_csv("effects/index/resources.csv", resources)
        deps = workflow.read_csv(self.root / "effects/index/dependencies.csv")
        deps.extend([{"asset_key": "effect:vef:COMBO", "relation": f"component-1-{i}",
                      "dependency_resref": name, "resolved_format": fmt, "present": "yes"}
                     for i, name, fmt in [(0, "OWNER", "VVC"), (1, "FXB", "BAM")]])
        self.write_csv("effects/index/dependencies.csv", deps)
        rows = tracking.build_consumers(self.root)
        for name, start in [("FXA", 12), ("FXB", 6)]:
            member = next(r for r in rows if r["consumer_key"] == "effect:vef:COMBO" and r["asset_key"] == f"effects:bam:{name}")
            self.assertEqual(json.loads(member["flags_json"])["vef"][0]["start_ticks"], start)


if __name__ == "__main__":
    unittest.main()
