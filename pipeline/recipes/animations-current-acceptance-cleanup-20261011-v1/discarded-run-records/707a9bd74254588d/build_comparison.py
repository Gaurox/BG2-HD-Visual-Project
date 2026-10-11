from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
BEFORE = ROOT / "animations/packs-par-zone/ar3016-complete-seedvr-flame-test-20260916/AR3016"
AFTER = ROOT / "animations/packs-par-zone/ar3016-complete-seedvr-flame-anchor-repair-v5-20260916/AR3016"
RESREF = "AM3016E"
FPS = 30
CYCLE_FRAMES = 48
CYCLES = 4
WIDTH, HEIGHT = 1280, 720


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(Path("C:/Windows/Fonts") / name, size)


REGULAR = font("segoeui.ttf", 23)
SMALL = font("segoeui.ttf", 19)
SEMIBOLD = font("seguisb.ttf", 24)
TITLE = font("seguisb.ttf", 40)


def resource(pack: Path) -> tuple[dict, dict[int, dict]]:
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    item = next(value for value in manifest["resources"] if value["resref"] == RESREF)
    frames = {value["frame"]: value for value in item["frames"]}
    target_fps = item["target_fps"]
    if isinstance(target_fps, dict):
        target_fps = target_fps["numerator"] / target_fps["denominator"]
    if target_fps != FPS or len(item["cycles"][0]["timeline_frame_indices"]) != CYCLE_FRAMES:
        raise RuntimeError(f"Contrat temporel inattendu : {pack}")
    return item, frames


def load_frame(pack: Path, meta: dict) -> Image.Image:
    width, height = meta["physical_size_x4"]
    rgba = np.frombuffer((pack / meta["asset"]).read_bytes(), dtype=np.uint8)
    rgba = rgba.reshape((height, width, 4))
    return Image.fromarray(rgba, mode="RGBA")


def fitted(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    return copy


def centered_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str,
                  text_font: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> None:
    left, top, right, bottom = box
    bounds = draw.textbbox((0, 0), text, font=text_font)
    x = left + (right - left - (bounds[2] - bounds[0])) / 2
    y = top + (bottom - top - (bounds[3] - bounds[1])) / 2 - bounds[1]
    draw.text((x, y), text, font=text_font, fill=fill)


def pill(draw: ImageDraw.ImageDraw, x: int, y: int, width: int, text: str,
         color: tuple[int, int, int]) -> None:
    draw.rounded_rectangle((x, y, x + width, y + 38), radius=19, fill=color)
    centered_text(draw, (x, y, x + width, y + 38), text, SEMIBOLD, (255, 255, 255))


def background() -> Image.Image:
    top = np.array([10, 13, 18], dtype=np.float32)
    bottom = np.array([22, 27, 36], dtype=np.float32)
    rows = np.linspace(top, bottom, HEIGHT, dtype=np.float32).astype(np.uint8)
    array = np.repeat(rows[:, None, :], WIDTH, axis=1)
    return Image.fromarray(array, mode="RGB")


def main() -> None:
    before_resource, before_frames = resource(BEFORE)
    after_resource, after_frames = resource(AFTER)
    before_timeline = before_resource["cycles"][0]["timeline_frame_indices"]
    after_timeline = after_resource["cycles"][0]["timeline_frame_indices"]

    cache: dict[tuple[str, int], Image.Image] = {}

    def frame(pack: Path, frames: dict[int, dict], index: int, side: str) -> Image.Image:
        key = (side, index)
        if key not in cache:
            cache[key] = fitted(load_frame(pack, frames[index]), (590, 428))
        return cache[key]

    video_path = OUTPUT / "AM3016E-before-after-interpolation-fix.mp4"
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    assert process.stdin is not None

    poster: Image.Image | None = None
    for number in range(CYCLE_FRAMES * CYCLES):
        phase = number % CYCLE_FRAMES
        canvas = background()
        draw = ImageDraw.Draw(canvas)

        centered_text(draw, (0, 18, WIDTH, 68), "AM3016E · 30 FPS INTERPOLATION", TITLE, (245, 247, 250))
        pill(draw, 188, 82, 244, "BEFORE FIX", (151, 57, 43))
        pill(draw, 838, 82, 254, "AFTER FIX", (28, 126, 102))
        for x in (30, 650):
            draw.rounded_rectangle((x, 130, x + 600, 590), radius=10,
                                   fill=(18, 21, 28), outline=(49, 55, 67), width=2)
        draw.line((640, 140, 640, 580), fill=(65, 71, 84), width=2)

        left = frame(BEFORE, before_frames, before_timeline[phase], "before")
        right = frame(AFTER, after_frames, after_timeline[phase], "after")
        canvas.paste(left, (330 - left.width // 2, 360 - left.height // 2), left)
        canvas.paste(right, (950 - right.width // 2, 360 - right.height // 2), right)

        bar_left, bar_right, bar_y = 300, 980, 664
        draw.rounded_rectangle((bar_left, bar_y, bar_right, bar_y + 5), radius=2, fill=(55, 62, 74))
        progress = phase / (CYCLE_FRAMES - 1)
        marker_x = round(bar_left + progress * (bar_right - bar_left))
        draw.ellipse((marker_x - 7, bar_y - 5, marker_x + 7, bar_y + 9), fill=(255, 183, 77))
        centered_text(draw, (0, 625, WIDTH, 655), "SYNCHRONIZED 1.6 S CYCLE", SMALL, (139, 146, 159))

        if number == 24:
            poster = canvas.copy()
        process.stdin.write(canvas.tobytes())

    process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("Échec de l'encodage ffmpeg")
    if poster is None:
        raise RuntimeError("Poster non généré")
    poster.save(OUTPUT / "AM3016E-before-after-interpolation-fix-poster.png", optimize=True)


if __name__ == "__main__":
    main()
