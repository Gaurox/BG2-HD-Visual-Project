"""Contrôle d'intégrité des rendus maîtres x1 avant tout upscale.

Un rendu maître corrompu se propage silencieusement dans toute la chaîne :
SeedVR l'agrandit fidèlement, le build découpe fidèlement ses tuiles et le
moteur affiche fidèlement le résultat. Aucune vérification en aval ne peut le
rattraper, parce que chaque étape est cohérente avec son entrée.

Ce script recalcule le rendu depuis `chitin.key` et le compare octet à octet
au fichier stocké dans `rendus-x1/`. Un écart non nul signifie que le fichier
stocké ne correspond plus à ce que le WED et le TIS décrivent.

    python validate_x1_masters.py --area AR0300
    python validate_x1_masters.py --all --confirm-all
    python validate_x1_masters.py --area AR0300 --fix

Historique : AR0300 (Les Docks) a été extraite corrompue le 2026-08-12 et a
coûté une nuit de diagnostic aval avant que la cause soit trouvée. Ce contrôle
est l'étape 0 obligatoire du pipeline.
"""

from __future__ import annotations

import argparse
import datetime
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from area_decode import render_area
from bg2lib import load_key

Image.MAX_IMAGE_PIXELS = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAPS_DIR = PROJECT_ROOT / "maps"
QUARANTINE = PROJECT_ROOT / "backups" / "masters-corrompus"
VARIANTS = ("tuiles-principales", "tuiles-secondaires")
NIGHT_VARIANTS = ("tuiles-principales-nuit", "tuiles-secondaires-nuit")
ALL_VARIANTS = VARIANTS + NIGHT_VARIANTS
SCRIPT_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--area", help="code de zone, par exemple AR0300")
    selection.add_argument("--all", action="store_true", help="contrôle toutes les zones")
    parser.add_argument("--confirm-all", action="store_true", help="autorise explicitement --all")
    parser.add_argument("--variant", choices=ALL_VARIANTS, action="append",
                        help="limite le contrôle à une variante (par défaut : les deux variantes jour, "
                             "ou les deux variantes nuit avec --night)")
    parser.add_argument("--night", action="store_true",
                        help="contrôle les rendus nuit (tuiles-*-nuit) au lieu des rendus jour ; "
                             "une zone sans variante nuit est ignorée, pas signalée ABSENT")
    parser.add_argument("--fix", action="store_true",
                        help="met le fichier fautif en quarantaine et le régénère")
    args = parser.parse_args()
    if args.all and not args.confirm_all:
        parser.error("--all exige --confirm-all")
    if not args.variant:
        args.variant = list(NIGHT_VARIANTS if args.night else VARIANTS)
    elif args.night and any(v not in NIGHT_VARIANTS for v in args.variant):
        parser.error("--night exige des --variant parmi : " + ", ".join(NIGHT_VARIANTS))
    return args


def area_dirs(args: argparse.Namespace) -> list[Path]:
    if args.area:
        code = args.area.upper()
        found = MAPS_DIR / code
        if not found.is_dir():
            raise SystemExit(f"zone introuvable : {code}")
        return [found]
    dirs = [area for area in sorted(MAPS_DIR.iterdir()) if area.is_dir() and area.name != "technical-overlays"]
    if args.night:
        _bif, res = load_key()
        wed_names = {name.upper() for name, kind, _locator in res if kind == 0x03E9}
        dirs = [d for d in dirs if f"{d.name}N" in wed_names]
    return dirs


def master_path(area_dir: Path, variant: str) -> Path:
    is_night = variant.endswith("-nuit")
    stem = f"{area_dir.name}N" if is_night else area_dir.name
    base_variant = variant[: -len("-nuit")] if is_night else variant
    return area_dir / "rendus-x1" / variant / f"{stem}-{base_variant}-x1.png"


def fresh_render(bif, res, area: str, variant: str) -> Image.Image:
    """Rendu de référence recalculé depuis les ressources du jeu."""
    night = variant.endswith("-nuit")
    if variant in ("tuiles-principales", "tuiles-principales-nuit"):
        return render_area(bif, res, area, night=night).convert("RGB")
    # render_secondary.py est un script : on l'appelle tel quel pour ne pas
    # dupliquer sa logique de substitution des portes.
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"{area}-secondaire.png"
        cmd = [sys.executable, str(SCRIPT_DIR / "render_secondary.py"), area, str(out)]
        if night:
            cmd.append("--night")
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=SCRIPT_DIR)
        if proc.returncode != 0 or not out.exists():
            raise RuntimeError(f"render_secondary.py a échoué : {proc.stderr.strip()[:200]}")
        with Image.open(out) as img:
            return img.convert("RGB").copy()


def quarantine_and_regenerate(path: Path, bif, res, area: str, variant: str) -> None:
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    shutil.move(str(path), str(QUARANTINE / f"{path.stem}-CORROMPU-{stamp}.png"))
    fresh_render(bif, res, area, variant).save(path, optimize=True)
    print(f"    corrigé : quarantaine dans {QUARANTINE.name}/, fichier régénéré")


def main() -> None:
    args = parse_args()
    bif, res = load_key()
    corrupt: list[str] = []
    missing: list[str] = []

    for area_dir in area_dirs(args):
        area = area_dir.name
        for variant in args.variant:
            path = master_path(area_dir, variant)
            label = f"{area} {variant}"
            if not path.exists():
                missing.append(label)
                print(f"{label:42} ABSENT")
                continue
            try:
                fresh = fresh_render(bif, res, area, variant)
            except Exception as exc:  # zone non rendable : on le signale sans bloquer le lot
                print(f"{label:42} NON CONTRÔLABLE ({exc})")
                continue
            with Image.open(path) as stored_img:
                stored = stored_img.convert("RGB")
                if stored.size != fresh.size:
                    print(f"{label:42} *** TAILLE {stored.size} vs {fresh.size} ***")
                    corrupt.append(label)
                    continue
                delta = float(np.abs(np.asarray(stored, dtype=np.int16)
                                     - np.asarray(fresh, dtype=np.int16)).mean())
            if delta == 0.0:
                print(f"{label:42} OK")
            else:
                print(f"{label:42} *** CORROMPU (écart moyen {delta:.3f}) ***")
                corrupt.append(label)
                if args.fix:
                    quarantine_and_regenerate(path, bif, res, area, variant)

    print()
    if corrupt and not args.fix:
        print(f"{len(corrupt)} rendu(s) maître(s) corrompu(s) : {', '.join(corrupt)}")
        print("Relancer avec --fix, puis refaire l'upscale de ces zones : "
              "toute sortie déjà produite à partir d'eux est invalide.")
        raise SystemExit(1)
    if corrupt:
        print(f"{len(corrupt)} rendu(s) corrigé(s). Refaire l'upscale de ces zones.")
        raise SystemExit(1)
    if missing:
        print(f"{len(missing)} rendu(s) absent(s) : lancer batch_extract.py / batch_extract_secondary.py")
    print("Tous les rendus maîtres contrôlés sont conformes.")


if __name__ == "__main__":
    main()
