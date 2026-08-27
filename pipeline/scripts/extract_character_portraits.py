"""Extract the BMP portrait triplets embedded in the BG2EE game data.

Each detected portrait has a complete Large/Medium/Small (`L`, `M`, `S`) set.
The source BMP bytes are copied without conversion and an inventory records the
dimensions, colour mode, source BIF and SHA-256 checksum for review.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
from pathlib import Path

from PIL import Image

from bg2lib import load_key, resolve_resource


BMP_TYPE = 1
SIZES = (("L", "grands"), ("M", "moyens"), ("S", "petits"))


def portrait_bases(resources: list[tuple[str, int, int]]) -> list[str]:
    """Return resource-name bases which have a complete L/M/S portrait triplet."""
    names = {name.upper() for name, resource_type, _ in resources if resource_type == BMP_TYPE}
    return sorted(
        name[:-1]
        for name in names
        if name.endswith("L") and all(name[:-1] + suffix in names for suffix, _ in SIZES)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "portraits",
        help="dossier de sortie (défaut : <projet>/portraits)",
    )
    args = parser.parse_args()
    output = args.output.resolve()

    bif_entries, resources = load_key()
    bmp_entries = {name.upper(): (name, locator) for name, resource_type, locator in resources if resource_type == BMP_TYPE}
    bases = portrait_bases(resources)

    rows: list[dict[str, str | int]] = []
    for suffix, folder in SIZES:
        (output / folder).mkdir(parents=True, exist_ok=True)

    for base in bases:
        for suffix, folder in SIZES:
            resource_name, locator = bmp_entries[base + suffix]
            resolved = resolve_resource(bif_entries, locator)
            if resolved is None:
                raise RuntimeError(f"Ressource introuvable : {resource_name}")
            raw, bif_name = resolved
            with Image.open(io.BytesIO(raw)) as image:
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                width, height, mode = image.size[0], image.size[1], image.mode

            relative_path = Path(folder) / f"{base}_{suffix}.bmp"
            (output / relative_path).write_bytes(raw)
            rows.append(
                {
                    "portrait": base,
                    "taille": suffix,
                    "fichier": relative_path.as_posix(),
                    "largeur_px": width,
                    "hauteur_px": height,
                    "mode": mode,
                    "octets": len(raw),
                    "bif_source": bif_name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )

    fields = list(rows[0]) if rows else []
    with (output / "inventaire_portraits.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    with (output / "README.md").open("w", encoding="utf-8") as handle:
        handle.write(
            "# Portraits BG2EE\n\n"
            "Extraction directe des BMP inclus dans les BIF de l'installation BG2EE. "
            "Aucune conversion, compression ou mise à l'échelle n'a été appliquée.\n\n"
            f"- Séries de portraits : {len(bases)}\n"
            f"- Fichiers : {len(rows)}\n"
            "- `grands/` : affichage grand format (suffixe `L`)\n"
            "- `moyens/` : affichage moyen (suffixe `M`)\n"
            "- `petits/` : affichage petit (suffixe `S`)\n"
            "- `inventaire_portraits.csv` : dimensions, taille des fichiers, BIF d'origine et checksum.\n"
        )

    print(f"Extraction terminée : {len(bases)} portraits, {len(rows)} BMP dans {output}")


if __name__ == "__main__":
    main()
