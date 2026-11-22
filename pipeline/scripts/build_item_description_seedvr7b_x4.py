"""Run the selected SeedVR2 7B x4 recipe on the item-description BAM inventory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import struct
import time
import zlib
from collections import defaultdict, deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from bam_export import decode_bam, native_palette_alpha
from mos_decode import decode_pvrz_page
from run_seedvr_comfyui import ComfyClient
from workspace_paths import get_service

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "icons/index"
TEMPLATE = ROOT / "pipeline/recipes/icons-item-description-seedvr7b-x4-20261112-v1/four-items.api.json"
SCALE = 4
MATTE = (234, 221, 190)
EXPECTED_ASSETS = 976
EXPECTED_FRAMES = 979
LOAD = "CSW1H01__1"
SAVE = "CSW1H01__9"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def read_verified(row):
    path = ROOT / row["extracted_path"]
    data = path.read_bytes()
    if sha(data).upper() != row["source_sha256"].upper():
        raise ValueError(f"{path}: source hash differs from the inventory")
    return data


def write_json(path, data):
    temporary = path.with_suffix(".partial")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def evidence(path, role):
    return {"role": role, "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha(path.read_bytes()), "bytes": path.stat().st_size}


@dataclass
class SourceFrame:
    image: Image.Image
    center_x: int
    center_y: int


@dataclass
class Task:
    asset: str
    frame_indices: list[int]
    frames: list[SourceFrame]
    image: Image.Image
    boxes: list[tuple[int, int, int, int]]

    @property
    def key(self):
        return f"{self.asset}:{self.frame_indices[0]}"

    def padded(self):
        w, h = self.image.size
        target = Image.new("RGB", (((w + 63) // 64) * 64, ((h + 63) // 64) * 64), MATTE)
        target.paste(self.image, (0, 0), self.image.getchannel("A"))
        return target


class Inventory:
    def __init__(self):
        active = {r["asset_key"] for r in read_csv(INDEX / "families.csv") if r["family"] == "item-description"}
        self.resources = {r["asset_key"]: r for r in read_csv(INDEX / "resources.csv") if r["asset_key"] in active}
        self.frames = defaultdict(list)
        for row in read_csv(INDEX / "frames.csv"):
            if row["asset_key"] in active:
                self.frames[row["asset_key"]].append(row)
        self.pages = {
            r["dependency_resref"]: r for r in read_csv(INDEX / "dependencies.csv")
            if r["asset_key"] in active
        }
        if (len(active) != EXPECTED_ASSETS or active != self.resources.keys() or
                active != self.frames.keys() or sum(map(len, self.frames.values())) != EXPECTED_FRAMES):
            raise ValueError("The indexed item-description inventory does not match this batch")

    @lru_cache(maxsize=32)
    def page(self, number):
        return decode_pvrz_page(read_verified(self.pages[f"MOS{number:04d}"]))

    def decode(self, row):
        data = read_verified(row)
        if data[:4] == b"BAMC":
            data = zlib.decompress(data[12:])
        if data[:8] == b"BAM V1  ":
            decoded, palette, transparency = decode_bam(data)
            alpha = native_palette_alpha(data, transparency)
            return [SourceFrame(Image.fromarray(np.dstack((palette[ind], alpha[ind]))), cx, cy)
                    for ind, cx, cy, _ in decoded]
        if data[:8] != b"BAM V2  ":
            raise ValueError(f"{row['resref']}: unsupported BAM signature")
        count, _, blocks, frame_offset, _, block_offset = struct.unpack_from("<6I", data, 8)
        frames = []
        for number in range(count):
            w, h, cx, cy, first, block_count = struct.unpack_from("<HHhhHH", data, frame_offset + 12 * number)
            image = Image.new("RGBA", (w, h))
            if first + block_count > blocks:
                raise ValueError(f"{row['resref']}:{number}: invalid block range")
            for index in range(first, first + block_count):
                page, sx, sy, bw, bh, dx, dy = struct.unpack_from("<7I", data, block_offset + 28 * index)
                source = self.page(page)
                if sx + bw > source.width or sy + bh > source.height or dx + bw > w or dy + bh > h:
                    raise ValueError(f"{row['resref']}:{number}: invalid block bounds")
                image.paste(source.crop((sx, sy, sx + bw, sy + bh)), (dx, dy))
            frames.append(SourceFrame(image, cx, cy))
        return frames

    def task(self, row):
        asset = row["resref"]
        frames = self.decode(row)
        indexed = self.frames[row["asset_key"]]
        for n, (frame, geometry) in enumerate(zip(frames, indexed, strict=True)):
            if (n, *frame.image.size, frame.center_x, frame.center_y) != tuple(
                int(geometry[key]) for key in ("frame_index", "width", "height", "center_x", "center_y")
            ):
                raise ValueError(f"{asset}:{n}: decoded geometry differs from inventory")
        if len(frames) == 1:
            w, h = frames[0].image.size
            return Task(asset, [0], frames, frames[0].image, [(0, 0, w, h)])
        if asset != "CSHLD20" or len(frames) != 4:
            raise ValueError(f"{asset}: unsupported multipart layout")
        left = min(-f.center_x for f in frames)
        top = min(-f.center_y for f in frames)
        boxes = [(x, y, x + f.image.width, y + f.image.height) for f in frames
                 for x, y in [(-f.center_x - left, -f.center_y - top)]]
        canvas = Image.new("RGBA", (max(b[2] for b in boxes), max(b[3] for b in boxes)))
        coverage = np.zeros((canvas.height, canvas.width), dtype=np.uint8)
        for frame, (x, y, right, bottom) in zip(frames, boxes, strict=True):
            coverage[y:bottom, x:right] += 1
            canvas.paste(frame.image, (x, y))
        if not np.all(coverage == 1):
            raise ValueError("CSHLD20: the four source frames do not tile the illustration")
        return Task(asset, list(range(len(frames))), frames, canvas, boxes)


class Batch:
    def __init__(self, run, inventory):
        self.run = run
        self.inventory = inventory
        self.client = ComfyClient(get_service("comfyui_url"), poll_seconds=0.15, timeout_seconds=240)
        recipe = json.loads(TEMPLATE.read_bytes())
        self.graph = {key: value for key, value in recipe.items()
                      if "__" not in key or key.startswith("CSW1H01__")}
        self.progress_path = run / "progress.json"
        if (run / "run.json").exists():
            raise ValueError(f"{run.name} is already sealed")
        if self.progress_path.exists():
            self.state = json.loads(self.progress_path.read_bytes())
            if self.state["recipe_sha256"] != sha(TEMPLATE.read_bytes()):
                raise ValueError("The workflow changed since this run started")
        else:
            self.state = {"started_at_utc": now(), "recipe_sha256": sha(TEMPLATE.read_bytes()),
                          "completed": {}, "pending": {}, "failures": {}}
            write_json(self.progress_path, self.state)

    def upload(self, task, image):
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        name = f"{task.asset}.png"
        result = self.client.session.post(
            f"{self.client.server}/upload/image", files={"image": (name, stream.getvalue(), "image/png")},
            data={"type": "input", "subfolder": self.run.name, "overwrite": "true"}, timeout=60,
        )
        result.raise_for_status()
        output = result.json()
        return "/".join(filter(None, (output.get("subfolder"), output["name"])))

    def submit(self, task):
        padded = task.padded()
        prompt = self.state["pending"].get(task.key)
        if prompt:
            if self.client.get_json(f"/history/{prompt}"):
                return task, prompt, padded.size
            queue = self.client.get_json("/queue")
            if any(row[1] == prompt for name in ("queue_running", "queue_pending") for row in queue[name]):
                return task, prompt, padded.size
        graph = deepcopy(self.graph)
        graph[LOAD]["inputs"]["image"] = self.upload(task, padded)
        graph[SAVE]["inputs"]["filename_prefix"] = f"{self.run.name}/{task.asset}"
        prompt = self.client.queue(graph)
        self.state["pending"][task.key] = prompt
        write_json(self.progress_path, self.state)
        return task, prompt, padded.size

    def collect(self, task, prompt, padded_size):
        item = self.client.wait_history(prompt)
        [output] = item["outputs"][SAVE]["images"]
        response = self.client.session.get(f"{self.client.server}/view",
            params={key: output[key] for key in ("filename", "subfolder", "type")}, timeout=90)
        response.raise_for_status()
        with Image.open(io.BytesIO(response.content)) as source:
            rgb = source.convert("RGB")
        if rgb.size != tuple(size * SCALE for size in padded_size):
            raise ValueError(f"{task.key}: unexpected output dimensions {rgb.size}")
        directory = self.run / "assets" / task.asset
        directory.mkdir(parents=True, exist_ok=True)
        for number, frame, box in zip(task.frame_indices, task.frames, task.boxes, strict=True):
            result = rgb.crop(tuple(coordinate * SCALE for coordinate in box))
            result.putalpha(frame.image.getchannel("A").resize(result.size, Image.Resampling.NEAREST))
            frame_path = directory / f"frame-{number:03d}-x4.png"
            partial = frame_path.with_suffix(".partial")
            result.save(partial, format="PNG")
            partial.replace(frame_path)
        self.state["completed"][task.key] = prompt
        self.state["pending"].pop(task.key, None)
        self.state["failures"].pop(task.key, None)
        write_json(self.progress_path, self.state)
        completed = len(self.state["completed"])
        if completed % 25 == 0 or completed == EXPECTED_ASSETS:
            print(f"{completed}/{EXPECTED_ASSETS} fiches produites", flush=True)

    def record_failure(self, key, error):
        self.state["failures"][key] = str(error)
        write_json(self.progress_path, self.state)
        print(f"{key}: {error}", flush=True)

    def process(self):
        stats = self.client.get_json("/system_stats")
        self.state["gpu"] = stats["devices"][0]["name"]
        print(f"GPU: {self.state['gpu']}; free VRAM: {stats['devices'][0]['vram_free']/2**30:.1f} GiB", flush=True)
        queue = self.client.get_json("/queue")
        owned = set(self.state["pending"].values())
        if any(row[1] not in owned for name in ("queue_running", "queue_pending") for row in queue[name]):
            raise RuntimeError("The ComfyUI queue has another active workload")
        for attempt in range(3):
            running = deque()
            for row in self.inventory.resources.values():
                key = f"{row['resref']}:0"
                if key in self.state["completed"]:
                    continue
                try:
                    running.append(self.submit(self.inventory.task(row)))
                except Exception as error:
                    self.record_failure(key, error)
                if len(running) >= 2:
                    self.collect_one(running.popleft())
            while running:
                self.collect_one(running.popleft())
            if len(self.state["completed"]) == EXPECTED_ASSETS:
                return
            time.sleep(2 ** attempt)
        raise RuntimeError(f"{len(self.state['failures'])} fiches en erreur après trois passes")

    def collect_one(self, submitted):
        task, prompt, _ = submitted
        try:
            self.collect(*submitted)
        except Exception as error:
            if isinstance(error, RuntimeError) and str(error).startswith("échec ComfyUI"):
                self.state["pending"].pop(task.key, None)
            self.record_failure(task.key, error)

    def seal(self):
        outputs = []
        inputs = [evidence(TEMPLATE, "seedvr2-7b-x4-workflow")]
        geometry = {}
        for key,row in self.inventory.resources.items():
            asset = row["resref"]
            inputs.append(evidence(ROOT / row["extracted_path"], f"{asset}:source-bam"))
            geometry[asset] = []
            for frame in self.inventory.frames[key]:
                i = int(frame["frame_index"])
                path = self.run / "assets" / asset / f"frame-{i:03d}-x4.png"
                w,h,cx,cy = (int(frame[k]) for k in ("width", "height", "center_x", "center_y"))
                with Image.open(path) as image:
                    if image.size != (w * SCALE, h * SCALE) or image.mode != "RGBA":
                        raise ValueError(f"{path}: invalid final RGBA geometry")
                    image.verify()
                outputs.append(evidence(path, f"{asset}:{i}:seedvr2-7b-x4-rgba"))
                geometry[asset].append({"frame_index": i, "size_x4": [w * SCALE, h * SCALE],
                                        "center_native": [cx, cy], "center_x4": [cx * SCALE, cy * SCALE]})
        assert len(outputs) == EXPECTED_FRAMES
        geometry_path = self.run / "geometry.json"
        write_json(geometry_path, geometry)
        outputs.append(evidence(geometry_path, "frame-geometry"))
        inputs.extend(evidence(ROOT / row["extracted_path"], f"{name}:source-pvrz")
                      for name,row in sorted(self.inventory.pages.items()))
        script = Path(__file__).resolve()
        recipe = script.relative_to(ROOT).as_posix()
        write_json(self.run / "run.json", {
            "$schema": "docs/workspace-run.schema.json", "schema_version": 1,
            "run_id": self.run.name, "domain": "icons", "asset_ids": list(geometry),
            "pipeline": {"id": "item-description-seedvr2-7b-x4", "recipe_path": recipe,
                         "recipe_sha256": sha(script.read_bytes()), "version": "1"},
            "inputs": inputs, "outputs": outputs,
            "provenance": {"created_at_utc": self.state["started_at_utc"], "generator": script.name,
                           "command": ["python", "-B", recipe, self.run.name]},
            "result": {"status": "completed", "sealed": True, "completed_at_utc": now(),
                       "notes": "976 illustrations, 979 frames RGBA. Alpha natif x4. CSHLD20 inféré assemblé, puis découpé en quatre frames."},
        })
        print(f"Lot scellé : {self.run.relative_to(ROOT)}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or not args.run_id.startswith("item-description-"):
        parser.error("Provide an item-description-* directory name")
    run = ROOT / "icons/batches" / args.run_id
    run.mkdir(parents=True, exist_ok=True)
    batch = Batch(run, Inventory())
    batch.process()
    batch.seal()


if __name__ == "__main__":
    main()
