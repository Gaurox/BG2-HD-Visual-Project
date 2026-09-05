"""Exporte les portraits des PNJ rencontrés en jeu (hors compagnons recrutables).

Un portrait est retenu s'il est cité par au moins un fichier CRE : c'est la
preuve qu'une créature du jeu le porte. Les portraits sélectionnables à la
création de personnage, qu'aucune créature n'utilise, sont donc exclus.

Le dossier est nommé d'après le nom affiché le plus fréquent parmi les créatures
qui portent le portrait ; les autres porteurs sont listés dans l'inventaire.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import struct
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from bg2lib import load_key, resolve_resource
from extract_joinable_portraits import (BMP, CRE, SIZES, TLK, guess_base, bmp_bases,
                                        joinable_npcs, load_tlk, portrait_base,
                                        safe_dir, tlk_string)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--bmp", action="store_true", help="copier aussi le BMP source")
    args = ap.parse_args()

    bif, resources = load_key()
    bmp_index = {r[0].upper(): r for r in resources if r[1] == BMP}
    cre_index = {r[0].upper(): r for r in resources if r[1] == CRE}
    bases_all = bmp_bases(bmp_index)
    tlk = load_tlk(TLK) if TLK.exists() else None

    # portraits des compagnons, resolus exactement comme a l'export precedent
    companions = set()
    for npc in joinable_npcs(bif, resources):
        base, _ = portrait_base(bif, cre_index, npc)
        if not base or not any((base + s) in bmp_index for s, _ in SIZES):
            base = guess_base(npc, bases_all) or base
        if base:
            companions.add(base)

    names: dict[str, Counter] = defaultdict(Counter)
    carriers: dict[str, set] = defaultdict(set)
    for name, entry in cre_index.items():
        data, _ = resolve_resource(bif, entry[2])
        if data[0:4] != b"CRE ":
            continue
        strref = struct.unpack_from("<i", data, 8)[0]
        label = tlk_string(tlk, strref) if (tlk and strref > 0) else ""
        for offset in (0x34, 0x3C):
            ref = data[offset:offset + 8].split(b"\0")[0].decode("ascii", "replace").strip().upper()
            if len(ref) > 1 and ref[-1] in "LMS":
                carriers[ref[:-1]].add(name)
                if label:
                    names[ref[:-1]][label] += 1

    targets = sorted(b for b in carriers
                     if b not in companions and any((b + s) in bmp_index for s, _ in SIZES))
    args.outdir.mkdir(parents=True, exist_ok=True)

    rows = []
    for base in targets:
        top = names[base].most_common()
        label = top[0][0] if top else base
        others = [n for n, _ in top[1:]]
        folder = args.outdir / safe_dir(f"{label} ({base})")
        folder.mkdir(exist_ok=True)

        details = []
        for suffix, french in SIZES:
            res_name = base + suffix
            if res_name not in bmp_index:
                continue
            data, bif_name = resolve_resource(bif, bmp_index[res_name][2])
            image = Image.open(io.BytesIO(data))
            image.load()
            image.convert("RGB").save(folder / f"{res_name}_{french}.png")
            if args.bmp:
                (folder / f"{res_name}.bmp").write_bytes(data)
            details.append(f"{french} {image.width}x{image.height}")
            rows.append({
                "nom": label, "base": base, "taille": french, "ressource": res_name,
                "largeur": image.width, "hauteur": image.height, "mode": image.mode,
                "bif_source": bif_name, "sha256": hashlib.sha256(data).hexdigest(),
                "creatures": len(carriers[base]),
                "autres_noms": " / ".join(others[:6]),
            })
        print(f"  {base:<10} {label:<24} {', '.join(details)}"
              + (f"   aussi : {', '.join(others[:3])}" if others else ""))

    with (args.outdir / "inventaire.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["nom", "base", "taille", "ressource", "largeur",
                                                "hauteur", "mode", "bif_source", "sha256", "creatures",
                                                "autres_noms"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(targets)} portraits, {len(rows)} images -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
