"""Tuiles « jeu d'origine » (x1, plus proche voisin) pour la page pédagogique 0x6110.

Même cadrage, même fond et même règle d'ombre que les tuiles E3b de
ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/figures_v2/tiles (outils/e3b_experiment.py,
fonction composite). Aucune inférence : indices BAM d'origine recolorés par la palette réalisée.
Lecture seule sur les sources ; écrit uniquement à côté de ce script (tiles/).

    python make_vanilla_tiles.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
sys.path.insert(0, str(REPO / "pipeline" / "scripts"))

from reboutcx_quantize import character_chmb1_palette_rgb  # noqa: E402
from run_creature_sprite_x2 import load_source_frames  # noqa: E402

FAMILY = REPO / "sprite/families/playable-characters/6110-human-female-fighter"
E3B_TILES = STUDY / "ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/figures_v2/tiles"
MPALETTE_PNG = STUDY / "CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/palette/MPALETTE.png"
OUT = HERE / "tiles"

# Identique à e3b_experiment.py
LAYERS = [("chff4", {"idle_s": "CHFF4G12", "walk_s": "CHFF4G11"}), ("helm01-wqnj6", "WQNJ6G1"),
          ("ishld03-wqnd3", "WQND3G1"), ("bdsw1h06-wqns1", "WQNS1G1")]
CYCLES = {"idle_s": 18, "walk_s": 0}
FRAME_SEL = [("idle_s", 0), ("walk_s", 3)]
PALETTES = {
    "REF": [30, 47, 57, 12, 39, 21, 3],
    "B": [21, 57, 47, 8, 66, 30, 0],
    "D_heldout": [67, 68, 47, 84, 25, 57, 2],
    "E_armorblue_heldout": [30, 47, 57, 12, 39, 68, 3],
}
BACKGROUND = (58, 52, 44)
ZOOM = 4


def frame_of(comp: str, resref, cycle: str, pos: int):
    name = resref[cycle] if isinstance(resref, dict) else resref
    _, resources, _ = load_source_frames(FAMILY / comp / "source" / "manifest.json")
    res = next(r for r in resources if r["source"]["name"].upper() == name)
    return res["frames"][res["cycles"][CYCLES[cycle]]["frame_indices"][pos]]


def composite(parts, palette: np.ndarray) -> np.ndarray:
    left = min(-f.center_x for f in parts)
    top = min(-f.center_y for f in parts)
    right = max(-f.center_x + f.width for f in parts)
    bottom = max(-f.center_y + f.height for f in parts)
    canvas = np.zeros(((bottom - top) * ZOOM, (right - left) * ZOOM, 3), np.uint8)
    canvas[:] = BACKGROUND
    for f in parts:
        indices = f.indices.repeat(ZOOM, 0).repeat(ZOOM, 1)
        x = (-f.center_x - left) * ZOOM
        y = (-f.center_y - top) * ZOOM
        sub = canvas[y:y + indices.shape[0], x:x + indices.shape[1]]
        shadow = indices == 1
        opaque = (indices != 0) & ~shadow
        sub[opaque] = palette[indices][opaque]
        sub[shadow] = (sub[shadow] * 0.5).astype(np.uint8)
    return canvas


def main() -> None:
    ranges = np.asarray(Image.open(MPALETTE_PNG).convert("RGB"))
    if ranges.shape != (256, 12, 3):
        raise RuntimeError("MPALETTE.png : 256 lignes de 12 nuances attendues")
    OUT.mkdir(parents=True, exist_ok=True)
    for cycle, pos in FRAME_SEL:
        parts = [frame_of(comp, resref, cycle, pos) for comp, resref in LAYERS]
        for name, rows in PALETTES.items():
            tile = composite(parts, character_chmb1_palette_rgb(ranges[rows]))
            witness = Image.open(E3B_TILES / f"{cycle}{pos}_{name}_xBR_x4.png")
            if witness.size != (tile.shape[1], tile.shape[0]):
                raise RuntimeError(f"{cycle}{pos} {name}: cadrage différent de la tuile E3b {witness.size}")
            target = OUT / f"{cycle}{pos}_{name}_vanilla_x1.png"
            Image.fromarray(tile).save(target, optimize=True)
            print(target.relative_to(STUDY), tile.shape[1], "x", tile.shape[0])


if __name__ == "__main__":
    main()
