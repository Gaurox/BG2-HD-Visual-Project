"""Required source plan and durable shared results for playable Q3m production."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import os
import sqlite3
import struct
import zipfile
import zlib

import numpy as np

from analyze_playable_frame_dedup import SCHEMA, identities, load_inventory, require
import palette_frac_encode as encoder
from reboutcx_multipal import save_npz
from run_creature_sprite_x2 import SourceFrame
from workspace_paths import get_path

ROOT = Path(__file__).resolve().parents[2]
ACTIVE = ROOT / "sprite/index/palette-work-plan.json"
CACHE_ROOT = ROOT / "sprite/.work/palette-q3m-shared"
POINTER_SCHEMA = "bg2-playable-palette-work-plan-pointer-v1"


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_text(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


class WorkPlan:
    """Read-only exhaustive correspondence; no fallback to per-family inference."""
    def __init__(self, pointer=ACTIVE, *, root=ROOT):
        self.root, self.pointer = Path(root), Path(pointer)
        descriptor = json.loads(self.pointer.read_text(encoding="utf-8"))
        require(descriptor["schema"] == POINTER_SCHEMA, "unknown active work-plan pointer")
        self.path = (self.root / descriptor["path"]).resolve()
        self.path.relative_to(self.root.resolve())
        require(self.path.is_file(), "dedup plan missing: run palette_playable.py restore-plan; production cannot bypass it")
        require(self.path.stat().st_size == descriptor["bytes"] and file_sha(self.path) == descriptor["sha256"],
                "dedup plan file changed; select a freshly verified plan")
        self.db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        self.db.row_factory = sqlite3.Row
        self.meta = {r["key"]: json.loads(r["value_json"]) for r in self.db.execute("SELECT * FROM metadata")}
        require(self.meta["schema"] == SCHEMA and self.meta["status"] == "complete-source-analysis-not-generated", "unfinished plan")
        self.profile = self.meta["profile"]
        self.models = {r["animation_id"]: r["model_id"] for r in self.db.execute("SELECT * FROM models")}
        self.descriptor = descriptor

    def close(self):
        self.db.close()

    def validate_sources(self):
        for relative, expected in self.meta["source_pins"].items():
            require(file_sha(self.root / relative) == expected, f"work-plan source changed: {relative}; rebuild the source plan")
        for name, expected in self.profile["code_sha256"].items():
            require(file_sha(self.root / "pipeline/scripts" / name) == expected, f"Q3m pixel kernel changed: {name}; rebuild the source plan")
        require(file_sha(get_path("mmpx_scalepix", required=True, root=self.root)) == self.profile["scalepix_sha256"],
                "xBR implementation changed; rebuild the source plan")
        current, _, _, resources, _, _ = load_inventory(self.root)
        require(set(self.models) == {m["animation_id"] for m in current}, "dedup plan does not cover every playable Character")
        require(self.db.execute("SELECT count(*) FROM resources").fetchone()[0] == len(resources), "dedup resource coverage is incomplete")
        return self

    def selection(self, ids=None):
        chosen = sorted(self.models) if not ids else sorted({f"0x{int(i, 16):04X}" for i in ids})
        require(set(chosen) <= self.models.keys(), "requested animation is outside the palettized Character plan")
        return chosen, sum(1 << self.models[i] for i in chosen)

    def work_summaries(self, ids=None):
        _, mask = self.selection(ids)
        # Sort small metadata only; do not spool hundreds of MiB of pixel BLOBs
        # and repeated native palettes into SQLite's sort temporary files.
        for row in self.db.execute("""SELECT w.work_id,w.consumer_models_le_bitset,i.needs_model,
                i.current_q3m_processable FROM work_items w JOIN inputs i USING(input_id)
                ORDER BY i.padded_height,i.padded_width,w.work_id"""):
            if mask & int.from_bytes(row["consumer_models_le_bitset"], "little"):
                require(row["current_q3m_processable"], "source geometry is not supported by current Q3m")
                yield row

    def work_rows(self, ids=None):
        for summary in self.work_summaries(ids):
            yield self.db.execute("SELECT * FROM processing_queue WHERE work_id=?", (summary["work_id"],)).fetchone()

    def resources(self, ids=None):
        chosen, _ = self.selection(ids)
        placeholders = ",".join("?" for _ in chosen)
        return self.db.execute(f"""SELECT DISTINCT r.* FROM resources r
                JOIN model_resources mr USING(resource_id) JOIN models m USING(model_id)
                WHERE animation_id IN ({placeholders}) ORDER BY r.resref""", chosen).fetchall()

    def frame(self, row, *, resref=None, index=None, centre=None, palette_bgra=None):
        h, w, tr = row["height"], row["width"], row["transparent_index"]
        require(w > 0 and h > 0 and w * h < 65535 and tr == 0, "unsupported Character frame geometry")
        raw = zlib.decompress(row["indices_zlib"])
        require(len(raw) == w * h, "stored index size differs")
        indices = np.frombuffer(raw, np.uint8).reshape(h, w)
        palette = np.frombuffer(row["palette_bgra"] if palette_bgra is None else palette_bgra, np.uint8).reshape(256, 4)[:, [2, 1, 0]].copy()
        if centre is None:
            position = self.db.execute("SELECT center_x,center_y FROM frames f JOIN work_items w ON w.representative_resource_id=f.resource_id AND w.representative_frame_index=f.frame_index WHERE w.work_id=?", (row["work_id"],)).fetchone()
            centre = tuple(position)
        rgba = np.dstack((palette[indices], np.where(indices == tr, 0, 255).astype(np.uint8))).tobytes()
        frame = SourceFrame(resref or row["representative_resref"], row["representative_frame_index"] if index is None else index,
                            w, h, *centre, tr, indices, palette, rgba)
        require(self.key(frame) == row["work_key"], "stored work key disagrees with its source")
        return frame

    def key(self, frame):
        require(frame.indices.shape == (frame.height, frame.width), "source dimensions differ")
        expected = np.dstack((frame.palette[frame.indices], np.where(frame.indices == frame.transparent, 0, 255).astype(np.uint8))).tobytes()
        require(frame.rgba == expected, "source RGBA differs from indexed pixels/palette")
        _, key, _, _, _ = identities(frame.indices, frame.palette, frame.transparent)
        require(self.db.execute("SELECT 1 FROM work_items WHERE work_key=?", (key,)).fetchone(), "frame is outside active dedup plan")
        return key.hex()

    def fitting(self):
        rows = self.db.execute("SELECT * FROM profile_palettes ORDER BY palette_ordinal").fetchall()
        require(len(rows) == 6, "six Q3m fit palettes required")
        fitting = np.stack([np.frombuffer(r["rgb_u8_256x3"], np.uint8).reshape(256, 3) for r in rows])
        require(hashlib.sha256(fitting.tobytes()).hexdigest() == self.profile["fitting_rgb_sha256"], "fit palette bytes changed")
        return fitting

    def materialize(self, resource, cache):
        """Fan out indexed results; retain this resource's geometry, palette and identity."""
        rid = resource["resource_id"]
        rows = self.db.execute("""SELECT f.*,q.* FROM frames f
                JOIN processing_queue q USING(work_id) WHERE f.resource_id=? ORDER BY f.frame_index""", (rid,)).fetchall()
        records = []
        for row in rows:
            frame = self.frame(row, resref=resource["resref"], index=row["frame_index"],
                               centre=(row["center_x"], row["center_y"]), palette_bgra=resource["palette_bgra"])
            encoded = cache.load(frame)
            representatives = np.full(256, 65535, np.uint16)
            values, offsets = np.unique(frame.indices, return_index=True)
            representatives[values] = offsets
            records.append(dict(geometry=(frame.width, frame.height, frame.center_x, frame.center_y, frame.transparent),
                                representatives=representatives, **encoded))
        cycles = [list(struct.unpack(f"<{c['slot_count']}H", c["frame_indices_le_u16"]))
                  for c in self.db.execute("SELECT * FROM cycles WHERE resource_id=? ORDER BY cycle_index", (rid,))]
        require(len(records) == resource["frame_count"] and len(cycles) == resource["cycle_count"], "resource coverage differs")
        return dict(resref=resource["resref"], source_sha256=resource["canonical_sha256"], frames=records, cycles=cycles)


class ResultCache:
    """Persistent I/F/dep cache; unrelated scales/profiles never share filenames."""
    def __init__(self, plan, scale, root=CACHE_ROOT):
        require(scale in (2, 4), "Q3m scale must be 2 or 4")
        self.plan, self.scale = plan, scale
        self.namespace = plan.profile["namespace_by_scale"][str(scale)]
        self.root = Path(root) / f"x{scale}" / self.namespace
        self.directory = self.root / "work/encoded"
        self.recipe = dict(schema="bg2-playable-q3m-shared-results-v1", scale=scale,
                           namespace=self.namespace, profile=plan.profile, input_identity=plan.meta["contract"])

    @contextmanager
    def exclusive(self):
        self.root.mkdir(parents=True, exist_ok=True)
        lock = (self.root / ".writer.lock").open("a+b")
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b"\0"); lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            lock.close()
            raise ValueError("another Q3m producer owns this shared cache") from error
        try:
            recipe = self.root / "recipe.json"
            if recipe.exists():
                require(json.loads(recipe.read_text()) == self.recipe, "shared cache profile changed")
            else:
                write_json(recipe, self.recipe)
            self.directory.mkdir(parents=True, exist_ok=True)
            yield self
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()

    def path(self, frame):
        return self.directory / (self.plan.key(frame) + ".npz")

    def validate(self, frame, arrays):
        require(set(arrays) == {"guide", "I", "F", "dep"}, "incomplete shared result")
        shape = (frame.height * self.scale, frame.width * self.scale)
        require(all(arrays[n].dtype == np.uint8 and arrays[n].shape == shape for n in ("guide", "I", "F")), "cached plane dtype/geometry differs")
        require(arrays["dep"].dtype == np.uint8 and arrays["dep"].shape == (32,), "cached dependencies differ")
        require(np.isin(arrays["guide"], np.unique(frame.indices)).all(), "guide uses an absent source index")
        encoder.check_contract(arrays["guide"], arrays["I"], arrays["F"], arrays["dep"])
        return arrays

    def load(self, frame):
        recipe = self.root / "recipe.json"
        require(recipe.is_file() and json.loads(recipe.read_text()) == self.recipe, "missing or incompatible shared-cache recipe")
        path = self.path(frame)
        try:
            # Inspect sizes before numpy allocates a corrupted/truncated ZIP member.
            with zipfile.ZipFile(path) as archive:
                members = archive.infolist()
                require(len(members) == 4 and {m.filename for m in members} == {n + ".npy" for n in ("guide", "I", "F", "dep")}, "invalid cache members")
                for member in members:
                    bound = (32 if member.filename == "dep.npy" else frame.width * frame.height * self.scale**2) + 4096
                    require(member.file_size <= bound, "cached plane exceeds expected size")
                    require(member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) and not member.flag_bits & 1,
                            "unsupported cached compression")
                    with archive.open(member) as stream:
                        version = np.lib.format.read_magic(stream)
                        require(version == (1, 0), "unknown cached NPY version")
                        shape, _, dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=4096)
                        expected = (32,) if member.filename == "dep.npy" else (frame.height * self.scale, frame.width * self.scale)
                        require(shape == expected and dtype == np.dtype(np.uint8), "cached NPY header shape/dtype differs")
            with np.load(path, allow_pickle=False) as data:
                arrays = {name: data[name].copy() for name in data.files}
            return self.validate(frame, arrays)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile, EOFError) as error:
            raise ValueError(f"missing or invalid shared result: {path}") from error

    def contains(self, frame):
        if not self.path(frame).is_file():
            return False
        self.load(frame)  # Invalid data fails closed; never silently counted as a hit.
        return True

    def save(self, frame, arrays):
        self.validate(frame, arrays)
        save_npz(self.path(frame), **arrays)
