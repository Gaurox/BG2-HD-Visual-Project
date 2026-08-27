"""Generate an isolated SeedVR2 3B title comparison without color transfer."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = next(parent for parent in ROOT.parents if (parent / "pipeline" / "scripts").is_dir())
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "scripts"))
from run_seedvr_comfyui import ComfyClient  # noqa: E402


SOURCE = ROOT / "source" / "TITLE-frame-00-original.png"
WORKFLOW = PROJECT_ROOT / "pipeline" / "comfyui" / "workflows" / "SeedVR-Image-BG2-Pipeline-3B.api.json"
SEED = 959948902156062
COLOR_CORRECTION = "none"


def main() -> None:
    with Image.open(SOURCE) as opened:
        source = opened.convert("RGBA")
    width, height = source.size
    padded_width = ((width + 63) // 64) * 64
    padded_height = ((height + 63) // 64) * 64
    padded = Image.new("RGBA", (padded_width, padded_height), (0, 0, 0, 0))
    padded.paste(source, (0, 0), source)
    intermediate = ROOT / "intermediates" / "TITLE-frame-00-padded.png"
    intermediate.parent.mkdir(parents=True, exist_ok=True)
    padded.save(intermediate)

    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    workflow["66:54"]["inputs"]["seed"] = SEED
    workflow["66:59"]["inputs"]["color_correction_method"] = COLOR_CORRECTION
    client = ComfyClient("http://127.0.0.1:8188", poll_seconds=2, timeout_seconds=1800)
    client.preflight()
    uploaded = client.upload(intermediate, "BG2_Upscale/exports-seedvr3b-title-none")
    for scale in (2, 4):
        output = ROOT / f"x{scale}" / f"TITLE-frame-00-seedvr2-3b-none-x{scale}.png"
        if output.exists():
            print(f"x{scale}: existing output kept")
            continue
        prompt = copy.deepcopy(workflow)
        prompt["66:57"]["inputs"]["resize_type.multiplier"] = scale
        prompt["1"]["inputs"]["image"] = uploaded
        prompt["9"]["inputs"]["filename_prefix"] = f"BG2_Upscale/exports-seedvr3b-title-none/TITLE-frame-00-x{scale}"
        prompt_id = client.queue(prompt)
        print(f"x{scale}: prompt {prompt_id}", flush=True)
        history = client.wait_history(prompt_id)
        images = history.get("outputs", {}).get("9", {}).get("images", [])
        if len(images) != 1:
            raise RuntimeError(f"x{scale}: {len(images)} sortie(s), une attendue")
        downloaded = output.with_name(output.stem + "-padded.png")
        client.download(images[0], downloaded)
        with Image.open(downloaded) as opened:
            result = opened.convert("RGBA")
        expected = (padded_width * scale, padded_height * scale)
        if result.size != expected:
            raise RuntimeError(f"x{scale}: sortie {result.size}, attendu {expected}")
        output.parent.mkdir(parents=True, exist_ok=True)
        result.crop((0, 0, width * scale, height * scale)).save(output)
        downloaded.unlink()
        print(f"x{scale}: wrote {output}")


if __name__ == "__main__":
    main()
