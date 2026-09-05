"""Range les portraits du mod Portraits Portraits Everywhere (PPE).

Le mod fournit un portrait par créature parlante, nommé d'après le resref du
CRE. On copie les BMP d'origine, on produit une conversion PNG sans perte, et
on résout le nom affiché de chaque créature dans dialog.tlk pour l'inventaire.

Les portraits « aléatoires », déjà classés par catégorie dans le mod, gardent
leur arborescence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import struct
from pathlib import Path

from PIL import Image

from bg2lib import load_key, resolve_resource
from extract_joinable_portraits import CRE, TLK, load_tlk, tlk_string


def creature_names(bif, resources, tlk) -> dict[str, str]:
    """resref de créature -> nom affiché."""
    names: dict[str, str] = {}
    for entry in resources:
        if entry[1] != CRE:
            continue
        data, _ = resolve_resource(bif, entry[2])
        if data[0:4] != b"CRE ":
            continue
        strref = struct.unpack_from("<i", data, 8)[0]
        if strref > 0:
            label = tlk_string(tlk, strref) if tlk else ""
            if label:
                names[entry[0].upper()] = label
    return names


def convert(src: Path, dst_dir: Path, keep_bmp: bool) -> tuple[int, int, str]:
    with Image.open(src) as image:
        image.load()
        image.convert("RGB").save(dst_dir / (src.stem + ".png"))
        size = image.size
    if keep_bmp:
        shutil.copy2(src, dst_dir / src.name)
    return size[0], size[1], hashlib.sha256(src.read_bytes()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", type=Path, help="dossier PPE extrait du dépôt")
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--no-bmp", action="store_true", help="ne pas copier les BMP d'origine")
    args = ap.parse_args()

    keep_bmp = not args.no_bmp
    bif, resources = load_key()
    tlk = load_tlk(TLK) if TLK.exists() else None
    print("résolution des noms de créatures...")
    names = creature_names(bif, resources, tlk)
    print(f"  {len(names)} créatures nommées")

    rows = []

    named_src = args.source / "Portraits"
    named_dst = args.outdir / "par-creature"
    named_dst.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in named_src.iterdir() if p.suffix.lower() == ".bmp")
    print(f"portraits nommés : {len(files)}")
    matched = 0
    for path in files:
        width, height, digest = convert(path, named_dst, keep_bmp)
        label = names.get(path.stem.upper(), "")
        matched += bool(label)
        rows.append({"ensemble": "par-creature", "categorie": "", "ressource": path.stem,
                     "nom": label, "largeur": width, "hauteur": height, "sha256": digest})
    print(f"  {matched} associés à une créature nommée ({100*matched//max(len(files),1)}%)")

    random_src = args.source / "RandomPortraits"
    random_dst = args.outdir / "par-categorie"
    total = 0
    for category in sorted(p for p in random_src.iterdir() if p.is_dir()):
        target = random_dst / category.name
        target.mkdir(parents=True, exist_ok=True)
        for path in sorted(p for p in category.iterdir() if p.suffix.lower() == ".bmp"):
            width, height, digest = convert(path, target, keep_bmp)
            rows.append({"ensemble": "par-categorie", "categorie": category.name,
                         "ressource": path.stem, "nom": "", "largeur": width,
                         "hauteur": height, "sha256": digest})
            total += 1
    print(f"portraits par catégorie : {total} dans {len(list(random_dst.iterdir()))} catégories")

    with (args.outdir / "inventaire.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["ensemble", "categorie", "ressource", "nom",
                                                "largeur", "hauteur", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} portraits -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
