"""Read-only phase-2 Monster plan; fixed-profile durable results, independent of Character."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import zlib

import numpy as np

from analyze_playable_frame_dedup import identities
from palette_monster_contract import CONTRACT, ROOT, documents, get_profile
from palette_work_plan import ResultCache, file_sha, json_text
from run_creature_sprite_x2 import SourceFrame

DESCRIPTOR = ROOT / "docs/measurements/q3m-monster-work-plan-x2-20261003-v1/plan.json"


def require(ok, label):
    if not ok:
        raise ValueError(label)


@dataclass
class Work:
    row: dict
    frame: SourceFrame

    @property
    def width(self): return self.frame.width
    @property
    def height(self): return self.frame.height


class WorkPlan:
    def __init__(self, descriptor=DESCRIPTOR):
        self.descriptor = json.loads(Path(descriptor).read_text(encoding="utf-8"))
        d = self.descriptor
        require(d["schema"] == "bg2-monster-q3m-local-plan-descriptor-v1", "unknown Monster plan")
        self.path = (ROOT / d["path"]).resolve()
        self.path.relative_to(ROOT)
        require(self.path.stat().st_size == d["bytes"] and file_sha(self.path) == d["sha256"], "Monster plan changed")
        require(file_sha(CONTRACT) == d["contract_sha256"], "Monster contract changed")
        documents()
        self.db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        self.db.row_factory = sqlite3.Row
        self.meta = {r["key"]: json.loads(r["value_json"]) for r in self.db.execute("SELECT * FROM metadata")}
        require(self.meta["schema"] == "bg2-monster-q3m-source-work-plan-v1" and
                self.meta["status"] == "complete-source-analysis-not-generated", "unfinished Monster plan")
        self.guide_files = {}

    def close(self): self.db.close()

    def resources(self, ids=None, refs=None):
        chosen = None if not ids else {f"0x{int(i, 16):04X}" for i in ids}
        named = None if not refs else {r.upper() for r in refs}
        rows = [dict(r) for r in self.db.execute("SELECT * FROM resources ORDER BY resref")]
        require(chosen is None or chosen <= {r["animation_id"] for r in rows}, "animation outside Monster plan")
        require(named is None or named <= {r["resref"] for r in rows}, "resref outside Monster plan")
        result = [r for r in rows if (chosen is None or r["animation_id"] in chosen) and
                  (named is None or r["resref"] in named)]
        require(bool(result), "empty Monster selection")
        return result

    def work_rows(self, resources):
        ids = [r["resource_id"] for r in resources]
        return [dict(r) for r in self.db.execute(f"""SELECT q.* FROM processing_queue q WHERE work_id IN
            (SELECT work_id FROM frames WHERE resource_id IN ({','.join('?' for _ in ids)}))
            ORDER BY padded_height,padded_width,profile_id,work_id""", ids)]

    def validate_sources(self, resources):
        for name in ("reboutcx_batch_p12.py", "reboutcx_multipal.py", "reboutcx_quantize.py"):
            require(file_sha(ROOT / "pipeline/scripts" / name) == self.meta["kernels"][name], f"acquired pixel kernel changed: {name}")
        for r in resources:
            get_profile(r["profile_id"]).check_resource(r["resref"], r["canonical_sha256"])
            require(file_sha(ROOT / r["canonical_path"]) == r["canonical_sha256"], f"source changed: {r['resref']}")
        return self

    def work(self, row, *, resource=None, position=None):
        r = resource or dict(self.db.execute("SELECT * FROM resources WHERE resource_id=?",
                                           (row["representative_resource_id"],)).fetchone())
        w, h = row["width"], row["height"]
        require(w > 0 and h > 0 and w * h < 65535 and row["transparent_index"] == 0, "unsupported Monster geometry")
        raw = zlib.decompress(row["indices_zlib"])
        require(len(raw) == w*h, "stored source pixels changed")
        i = np.frombuffer(raw, np.uint8).reshape(h, w)
        p = np.frombuffer(r["palette_bgra"], np.uint8).reshape(256, 4)[:, [2, 1, 0]].copy()
        if position is None:
            position = dict(self.db.execute("SELECT * FROM frames WHERE resource_id=? AND frame_index=?",
                            (r["resource_id"], row["representative_frame_index"])).fetchone())
        rgba = np.dstack((p[i], np.where(i == 0, 0, 255).astype(np.uint8))).tobytes()
        frame = SourceFrame(r["resref"], position["frame_index"], w, h, position["center_x"],
                            position["center_y"], 0, i, p, rgba)
        _, source_key, _, _, needs_model = identities(i, p, 0)
        key = hashlib.sha256(b"BG2-MONSTER-Q3M-CONTRACT-WORK-v1\0" +
                             bytes.fromhex(row["contract_namespace"]) + source_key).hexdigest()
        require(key == row["work_key_hex"] and bool(needs_model) == bool(row["needs_model"]), "work identity changed")
        require(r["profile_id"] == row["profile_id"], "resource profile changed")
        return Work(row, frame)

    def key(self, work): return work.row["work_key_hex"]

    def guide(self, work):
        loc = json.loads(work.row["guide_locator_json"])
        path = (ROOT / loc["registry"]).resolve()
        path.relative_to(ROOT)
        if path not in self.guide_files:
            require(file_sha(path) == loc["registry_sha256"], "acquired xBR guide registry changed")
            self.guide_files[path] = loc["registry_sha256"]
        require(self.guide_files[path] == loc["registry_sha256"], "guide registry identity conflict")
        require(loc["shape"] == [work.height*2, work.width*2] and
                loc["bytes"] == work.width*work.height*4, "guide dimensions changed")
        with path.open("rb") as stream:
            stream.seek(loc["offset"])
            raw = stream.read(loc["bytes"])
        require(hashlib.sha256(raw).hexdigest() == work.row["guide_sha256"], "acquired xBR guide pixels changed")
        g = np.frombuffer(raw, np.uint8).reshape(loc["shape"]).copy()
        require(np.isin(g, np.unique(work.frame.indices)).all(), "guide uses absent native index")
        return g

    def materialize(self, resource, cache):
        records = []
        rows = self.db.execute("""SELECT f.*,q.* FROM frames f JOIN processing_queue q USING(work_id)
                                  WHERE f.resource_id=? ORDER BY f.frame_index""", (resource["resource_id"],))
        for row in rows:
            row = dict(row)
            work = self.work(row, resource=resource, position=row)
            encoded = cache.load(work)
            reps = np.full(256, 65535, np.uint16)
            values, offsets = np.unique(work.frame.indices, return_index=True)
            reps[values] = offsets
            records.append(dict(geometry=(work.width, work.height, row["center_x"], row["center_y"], 0),
                                representatives=reps, **encoded))
        cycles = [list(struct.unpack(f"<{r['slot_count']}H", r["frame_indices_le_u16"])) for r in
                  self.db.execute("SELECT * FROM cycles WHERE resource_id=? ORDER BY cycle_index", (resource["resource_id"],))]
        require(len(records) == resource["frame_count"] and len(cycles) == resource["cycle_count"], "incomplete native frame/cycle coverage")
        return dict(resref=resource["resref"], source_sha256=resource["canonical_sha256"], frames=records, cycles=cycles)


class Cache(ResultCache):
    """Reuse acquired atomic ZIP/lock machinery; replace Character identity and validation."""
    def __init__(self, plan, root, backend):
        self.plan, self.scale = plan, 2
        kernels = ("palette_monster_contract.py", "palette_monster_work_plan.py", "palette_monster.py",
                   "palette_work_plan.py", "reboutcx_quantize.py", "reboutcx_multipal.py",
                   "reboutcx_batch.py", "reboutcx_batch_p10.py", "reboutcx_batch_p12.py",
                   "palette_frac_encode.py", "analyze_playable_frame_dedup.py", "run_creature_sprite_x2.py")
        require(backend.get("batch_size") == 86 and backend.get("canvas_quantum") == 32 and
                backend.get("fp16") is True and len(backend.get("model_sha256", "")) == 64,
                "incomplete inference backend identity")
        recipe = dict(schema="bg2-monster-q3m-fixed-cache-v1", scale=2, k=6, boundary_mixing=False,
                      dithering=False, encoder="monster-fixed-exhaustive-oklab-f64-integer-k6-v1",
                      contract_sha256=plan.descriptor["contract_sha256"], inference=backend,
                      code_sha256={n: file_sha(ROOT / "pipeline/scripts" / n) for n in kernels})
        self.namespace = hashlib.sha256(json_text(recipe).encode()).hexdigest()
        self.recipe = dict(recipe, namespace=self.namespace)
        self.root = Path(root) / "x2" / self.namespace
        self.directory = self.root / "work/encoded"

    def validate(self, work, arrays):
        require(set(arrays) == {"guide", "I", "F", "dep"}, "incomplete Monster cache entry")
        shape = (work.height*2, work.width*2)
        require(all(arrays[n].dtype == np.uint8 and arrays[n].shape == shape for n in ("guide", "I", "F")), "cache plane geometry/dtype differs")
        require(arrays["dep"].dtype == np.uint8 and arrays["dep"].shape == (32,), "cache dependency dtype/shape differs")
        require(hashlib.sha256(arrays["guide"].tobytes()).hexdigest() == work.row["guide_sha256"], "cached guide differs from acquired xBR")
        get_profile(work.row["profile_id"]).check_contract(arrays["guide"], arrays["I"], arrays["F"], arrays["dep"])
        return arrays
