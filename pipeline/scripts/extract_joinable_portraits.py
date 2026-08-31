"""Extrait les portraits des PNJ recrutables, triés par personnage.

La liste des recrutables vient de PDIALOG.2DA, qui est la table canonique des
PNJ pouvant rejoindre le groupe. Pour chacun, le nom de base du portrait est lu
dans ses fichiers CRE (les CRE sont déclinés par niveau, on retient la référence
majoritaire), puis toutes les tailles disponibles sont extraites.

Sortie : un dossier par personnage, contenant le BMP source tel quel et sa
conversion PNG sans perte, plus un inventaire CSV global.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import struct
from collections import Counter
from pathlib import Path

from PIL import Image

from bg2lib import load_key, resolve_resource
from workspace_paths import get_path

BMP, CRE, TDA = 0x0001, 0x03F1, 0x03F4
SIZES = (("L", "grand"), ("M", "moyen"), ("S", "petit"))
TLK = get_path("bg2ee_game_root") / "lang/fr_FR/dialog.tlk"

# Entrées de PDIALOG.2DA qui ne sont pas des compagnons du jeu principal.
SPECIAL = {
    "TTBRAN": "variante tutoriel", "TTIMOEN": "variante tutoriel",
    "TTJAHEIR": "variante tutoriel", "TTMINSC": "variante tutoriel",
    "IMOEN2": "version Trône de Bhaal", "IDIOT01": "entrée technique",
    "OHHFAK": "Hexxat (déguisement)", "XAN": "hérité de BG1",
}

# PNJ dont le nom de table ne permet pas de deviner la ressource de portrait.
ALIASES = {"TTJAHEIR": "JAHEIRA"}


def load_tlk(path: Path):
    data = path.read_bytes()
    if data[0:4] != b"TLK ":
        raise ValueError(f"{path}: signature {data[0:4]!r}")
    count, str_off = struct.unpack_from("<II", data, 0x0A)
    return data, count, str_off


def tlk_string(tlk, strref: int) -> str:
    """Les Enhanced Editions encodent dialog.tlk en UTF-8 ; les versions
    classiques en cp1252. On tente l'UTF-8 puis on retombe sur cp1252."""
    data, count, str_off = tlk
    if not 0 <= strref < count:
        return ""
    base = 0x12 + strref * 26
    off, length = struct.unpack_from("<II", data, base + 0x12)
    raw = data[str_off + off:str_off + off + length]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", "replace")
    return text.replace(" ", " ").strip()


def joinable_npcs(bif, resources) -> list[str]:
    table = {n.upper(): r for n, t, r in ((x[0], x[1], x) for x in resources) if t == TDA}
    data, _ = resolve_resource(bif, table["PDIALOG"][2])
    lines = [l for l in data.decode("cp1252", "replace").splitlines() if l.strip()]
    return [l.split()[0].upper() for l in lines[3:]]      # 3 lignes d'en-tête


def bmp_bases(bmp_index) -> dict[str, int]:
    """Bases de portrait présentes en BMP, avec leur nombre de tailles."""
    bases: dict[str, int] = {}
    for name in bmp_index:
        if name[-1] in "LMS":
            bases[name[:-1]] = bases.get(name[:-1], 0) + 1
    return {b: n for b, n in bases.items() if n >= 2}


def guess_base(npc: str, bases: dict[str, int]) -> str | None:
    """Repli : rapprocher le nom du PNJ d'une base de portrait.

    Les portraits de compagnons sont préfixés `N` (BG2) ou `OH` (contenu EE) et
    tronqués, donc on compare après retrait du préfixe et on garde le plus long
    préfixe commun.
    """
    target = ALIASES.get(npc, npc)
    if target.startswith("TT"):
        target = target[2:]
    best, best_score = None, 0
    for base in bases:
        stripped = base[2:] if base.startswith("OH") else base.lstrip("N") if base.startswith("N") else base
        common = 0
        for a, b in zip(stripped, target):
            if a != b:
                break
            common += 1
        if common >= 3 and (common > best_score or
                            (common == best_score and bases[base] > bases.get(best, 0))):
            best, best_score = base, common
    return best


def portrait_base(bif, cre_index, npc: str) -> tuple[str | None, int | None]:
    """Référence de portrait majoritaire et strref du nom, lus dans les CRE du PNJ."""
    variants = [k for k in cre_index if k == npc or re.fullmatch(re.escape(npc) + r"\d*[A-Z]?", k)]
    if not variants:
        stem = npc[:6]
        variants = [k for k in cre_index if k.startswith(stem)]

    refs, strrefs = Counter(), Counter()
    for name in variants:
        data, _ = resolve_resource(bif, cre_index[name][2])
        if data[0:4] != b"CRE ":
            continue
        strref = struct.unpack_from("<i", data, 8)[0]
        if strref > 0:
            strrefs[strref] += 1
        for offset in (0x34, 0x3C):
            ref = data[offset:offset + 8].split(b"\0")[0].decode("ascii", "replace").strip()
            if ref and ref[-1].upper() in "LMS":
                refs[ref[:-1].upper()] += 1
    base = refs.most_common(1)[0][0] if refs else None
    strref = strrefs.most_common(1)[0][0] if strrefs else None
    return base, strref


def safe_dir(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name.replace(" ", " "))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".")
    return cleaned or "sans-nom"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--bmp", action="store_true", help="copier aussi le BMP source")
    args = ap.parse_args()

    bif, resources = load_key()
    bmp_index = {n.upper(): r for r in resources for n, t in [(r[0], r[1])] if t == BMP}
    cre_index = {n.upper(): r for r in resources for n, t in [(r[0], r[1])] if t == CRE}
    bases = bmp_bases(bmp_index)
    tlk = load_tlk(TLK) if TLK.exists() else None

    args.outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for npc in joinable_npcs(bif, resources):
        base, strref = portrait_base(bif, cre_index, npc)
        if not base or not any((base + sfx) in bmp_index for sfx, _ in SIZES):
            base = guess_base(npc, bases) or base
        display = tlk_string(tlk, strref) if (tlk and strref) else ""
        fallback = ALIASES.get(npc, npc[2:] if npc.startswith("TT") else npc)
        label = display or fallback.title()
        note = SPECIAL.get(npc, "")

        found = [(sfx, fr) for sfx, fr in SIZES if base and (base + sfx) in bmp_index]
        if not found:
            rows.append({"pnj": npc, "nom": label, "base": base or "", "tailles": 0,
                         "note": (note + " | portrait introuvable").strip(" |")})
            print(f"  {npc:<9} {label:<22} AUCUN PORTRAIT (base={base})")
            continue

        folder = args.outdir / safe_dir(f"{label} ({npc})" if note else label)
        folder.mkdir(exist_ok=True)
        details = []
        for sfx, fr in found:
            res_name = base + sfx
            data, bif_name = resolve_resource(bif, bmp_index[res_name][2])
            image = Image.open(io.BytesIO(data))
            image.load()
            image.convert("RGB").save(folder / f"{res_name}_{fr}.png")
            if args.bmp:
                (folder / f"{res_name}.bmp").write_bytes(data)
            details.append(f"{fr} {image.width}x{image.height}")
            rows.append({"pnj": npc, "nom": label, "base": base, "taille": fr,
                         "ressource": res_name, "largeur": image.width,
                         "hauteur": image.height, "mode": image.mode,
                         "bif_source": bif_name,
                         "sha256": hashlib.sha256(data).hexdigest(), "note": note})
        print(f"  {npc:<9} {label:<22} {base:<9} {', '.join(details)}"
              + (f"   [{note}]" if note else ""))

    fields = ["pnj", "nom", "base", "taille", "ressource", "largeur", "hauteur",
              "mode", "bif_source", "sha256", "note", "tailles"]
    with (args.outdir / "inventaire.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    people = len({r["pnj"] for r in rows})
    images = sum(1 for r in rows if r.get("ressource"))
    print(f"\n{people} personnages, {images} portraits -> {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
