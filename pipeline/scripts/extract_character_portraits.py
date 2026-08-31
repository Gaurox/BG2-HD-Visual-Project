"""Génère l'inventaire logique des portraits natifs réellement exposés par BG2EE.

Un portrait est retenu si sa base est déclarée dans la table ``portraits`` de
``BGEE.lua`` ou référencée par le champ portrait d'au moins un CRE. Les tailles
L/M/S sont des ressources membres, jamais des assets autonomes.

La population et les preuves viennent uniquement de l'installation configurée
par ``config://bg2ee_game_root`` : aucune liste de resrefs n'est maintenue dans
ce script.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image

from bg2lib import load_key, resolve_resource
from extract_joinable_portraits import (
    BMP,
    CRE,
    SIZES as NAMED_SIZES,
    bmp_bases,
    guess_base,
    joinable_npcs,
    portrait_base,
)


LUA = 0x0409
SIZES = (("L", "grands"), ("M", "moyens"), ("S", "petits"))
MEMBER_FIELDS = (
    "ressource",
    "fichier",
    "largeur_px",
    "hauteur_px",
    "mode",
    "octets",
    "bif_source",
    "sha256",
)


def parse_selectable_portraits(lua_text: str) -> set[str]:
    """Retourne les bases déclarées dans la table globale ``portraits``."""

    match = re.search(r"(?ms)^portraits\s*=\s*\{(.*?)^\}", lua_text)
    if match is None:
        raise ValueError("table portraits absente de BGEE.lua")
    bases = {
        item.group(1).upper()
        for item in re.finditer(
            r"\{\s*['\"]([A-Za-z0-9_]+)['\"]\s*,",
            match.group(1),
        )
    }
    if not bases:
        raise ValueError("table portraits vide dans BGEE.lua")
    return bases


def selectable_portraits(bif_entries, resources) -> set[str]:
    candidates = [entry for entry in resources if entry[0].upper() == "BGEE" and entry[1] == LUA]
    if len(candidates) != 1:
        raise RuntimeError(f"BGEE.lua attendu une fois dans KEY, trouvé {len(candidates)}")
    raw, _ = resolve_resource(bif_entries, candidates[0][2])
    return parse_selectable_portraits(raw.decode("utf-8", "replace"))


def cre_portrait_carriers(bif_entries, cre_index, bmp_index) -> dict[str, set[str]]:
    """Associe chaque base de portrait aux CRE qui la référencent."""

    carriers: dict[str, set[str]] = defaultdict(set)
    for cre_name, entry in cre_index.items():
        raw, _ = resolve_resource(bif_entries, entry[2])
        if raw[0:4] != b"CRE ":
            continue
        for offset in (0x34, 0x3C):
            resref = (
                raw[offset : offset + 8]
                .split(b"\0")[0]
                .decode("ascii", "replace")
                .strip()
                .upper()
            )
            if len(resref) > 1 and resref[-1] in "LMS" and resref in bmp_index:
                carriers[resref[:-1]].add(cre_name)
    return carriers


def recruitable_portrait_bases(bif_entries, resources, cre_index, bmp_index) -> set[str]:
    """Résout les bases des entrées PDIALOG sans maintenir de liste locale."""

    available = bmp_bases(bmp_index)
    result: set[str] = set()
    for npc in joinable_npcs(bif_entries, resources):
        base, _ = portrait_base(bif_entries, cre_index, npc)
        if not base or not any((base + suffix) in bmp_index for suffix, _ in NAMED_SIZES):
            base = guess_base(npc, available) or base
        if base and any((base + suffix) in bmp_index for suffix, _ in NAMED_SIZES):
            result.add(base.upper())
    return result


def member_columns(suffix: str, values: dict[str, object] | None) -> dict[str, object]:
    normalized = suffix.lower()
    return {
        f"{field}_{normalized}": "" if values is None else values[field]
        for field in MEMBER_FIELDS
    }


def prune_generated_bmps(output: Path, expected: set[Path]) -> int:
    removed = 0
    for _, folder in SIZES:
        target = output / folder
        if not target.is_dir():
            continue
        for path in target.glob("*.bmp"):
            if path.resolve() not in expected:
                path.unlink()
                removed += 1
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "portraits",
        help="dossier de sortie (défaut : <projet>/portraits)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="supprimer des dossiers grands/moyens/petits les BMP qui ne sont plus inventoriés",
    )
    args = parser.parse_args()
    output = args.output.resolve()

    bif_entries, resources = load_key()
    bmp_index = {entry[0].upper(): entry for entry in resources if entry[1] == BMP}
    cre_index = {entry[0].upper(): entry for entry in resources if entry[1] == CRE}
    selectable = selectable_portraits(bif_entries, resources)
    carriers = cre_portrait_carriers(bif_entries, cre_index, bmp_index)
    recruitable = recruitable_portrait_bases(bif_entries, resources, cre_index, bmp_index)
    logical_bases = sorted(selectable | set(carriers))

    output.mkdir(parents=True, exist_ok=True)
    for _, folder in SIZES:
        (output / folder).mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    expected_files: set[Path] = set()
    resource_count = 0
    for base in logical_bases:
        row: dict[str, object] = {
            "portrait": base,
            "selectable": "yes" if base in selectable else "no",
            "recrutable": "yes" if base in recruitable else "no",
            "rencontre": "yes" if base in carriers and base not in recruitable else "no",
            "creatures": len(carriers.get(base, set())),
        }
        available_sizes: list[str] = []
        for suffix, folder in SIZES:
            resource_name = base + suffix
            entry = bmp_index.get(resource_name)
            if entry is None:
                row.update(member_columns(suffix, None))
                continue
            raw, bif_name = resolve_resource(bif_entries, entry[2])
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                width, height, mode = image.width, image.height, image.mode
            relative_path = Path(folder) / f"{base}_{suffix}.bmp"
            target = output / relative_path
            target.write_bytes(raw)
            expected_files.add(target.resolve())
            available_sizes.append(suffix)
            resource_count += 1
            row.update(
                member_columns(
                    suffix,
                    {
                        "ressource": resource_name,
                        "fichier": relative_path.as_posix(),
                        "largeur_px": width,
                        "hauteur_px": height,
                        "mode": mode,
                        "octets": len(raw),
                        "bif_source": bif_name,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    },
                )
            )
        if not available_sizes:
            raise RuntimeError(f"portrait déclaré sans BMP disponible : {base}")
        row["tailles"] = "".join(available_sizes)
        rows.append(row)

    fields = ["portrait", "selectable", "recrutable", "rencontre", "creatures", "tailles"]
    for suffix, _ in SIZES:
        fields.extend(f"{field}_{suffix.lower()}" for field in MEMBER_FIELDS)
    with (output / "inventaire_portraits.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    removed = prune_generated_bmps(output, expected_files) if args.prune else 0
    print(
        f"Extraction terminée : {len(rows)} portraits logiques, {resource_count} BMP, "
        f"{removed} ancien(s) BMP supprimé(s) -> {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
