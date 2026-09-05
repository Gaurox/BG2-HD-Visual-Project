"""Renseigne `name_en` dans areas.csv depuis la table `cheatAreas` de `BGEE.LUA`.

`BGEE.LUA` est livre par le jeu (`data/Patch2.bif`) et contient la liste que le menu de
teleportation de debug affiche : un libelle anglais par zone. Ce sont des etiquettes de
developpement, pas des noms de carte du monde — voir la section « Regles de remplissage » du
README pour leur statut exact.

Regles appliquees :

- ne renseigne qu'une ligne dont `name_en` est vide ; **n'ecrase jamais** un nom existant ;
- `name_fr` reste vide (la table n'est pas localisee) ;
- `name_source` = `BGEE.LUA-cheatAreas`, `name_strref` reprend l'`area_id` ;
- `name_confidence` = `confirmed`, sauf si le libelle est partage par plusieurs zones ou marque
  incertain par les developpeurs : il reste alors vide et la raison est ecrite en `notes`.

Seules les lignes modifiees sont reserialisees ; les autres restent identiques a l'octet pres.

    python import_cheatarea_names.py            # dry-run
    python import_cheatarea_names.py --apply    # ecrit areas.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import re
from pathlib import Path

from bg2lib import load_key, resolve_resource

CSV_PATH = Path(__file__).resolve().parents[2] / 'areas.csv'
SOURCE_LABEL = 'BGEE.LUA-cheatAreas'
LUA_TYPE = 0x409

# Colonnes lues ou ecrites par ce script. Leur position est resolue depuis
# l'en-tete du fichier, jamais codee en dur : le schema d'areas.csv evolue et
# un index fige ecrirait silencieusement dans la mauvaise colonne.
COLUMNS = ('area_id', 'name_en', 'name_source', 'name_strref', 'name_confidence', 'notes')


def column_index(header: list[str]) -> dict[str, int]:
    missing = [name for name in COLUMNS if name not in header]
    if missing:
        raise SystemExit(f"colonnes absentes d'areas.csv : {', '.join(missing)}")
    return {name: header.index(name) for name in COLUMNS}


def load_cheat_areas() -> dict[str, str]:
    """Extrait la table `cheatAreas` de BGEE.LUA depuis les .bif du jeu."""
    bif_entries, res_entries = load_key()
    for name, rtype, locator in res_entries:
        if name.upper() == 'BGEE' and rtype == LUA_TYPE:
            data, _ = resolve_resource(bif_entries, locator)
            text = data.decode('utf-8', errors='replace')
            block = text.split('cheatAreas = {', 1)[1].split('\n}', 1)[0]
            return dict(re.findall(r'\{"([A-Z0-9]+)",\s*"(.*?)"\}', block))
    raise KeyError('BGEE.LUA introuvable dans chitin.key')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help="ecrit areas.csv (sinon dry-run)")
    args = parser.parse_args()

    cheat = load_cheat_areas()
    label_count = collections.Counter(cheat.values())

    def doubt_reason(area_id: str) -> str | None:
        label = cheat[area_id]
        if label_count[label] > 1:
            others = sorted(a for a, l in cheat.items() if l == label and a != area_id)
            return f"libelle cheatAreas partage avec {', '.join(others)}, n'identifie pas la zone"
        if label.rstrip().endswith('?'):
            return 'libelle cheatAreas marque comme incertain par les developpeurs'
        return None

    with open(CSV_PATH, encoding='utf-8', newline='') as handle:
        raw = handle.read()
    lines = raw.split('\r\n')
    column = column_index(next(csv.reader(io.StringIO(lines[0]))))
    stats: collections.Counter[str] = collections.Counter()

    for idx, line in enumerate(lines):
        if idx == 0 or not line.strip():
            continue
        row = next(csv.reader(io.StringIO(line)))
        area = row[column['area_id']]
        if row[column['name_en']].strip() or area not in cheat:
            continue

        reason = doubt_reason(area)
        row[column['name_en']] = cheat[area]
        row[column['name_source']] = SOURCE_LABEL
        if not row[column['name_strref']].strip():
            row[column['name_strref']] = area
        row[column['name_confidence']] = '' if reason else 'confirmed'
        if reason:
            note = f'Nom non retenu comme fiable : {reason}.'
            notes = row[column['notes']]
            row[column['notes']] = f'{notes} {note}'.strip() if notes.strip() else note

        out = io.StringIO()
        csv.writer(out, lineterminator='').writerow(row)
        lines[idx] = out.getvalue()
        stats['doute' if reason else 'confirmed'] += 1

    total = sum(stats.values())
    print(f"confirmed          : {stats['confirmed']}")
    print(f"nom sans confiance : {stats['doute']}")
    print(f"total renseigne    : {total}")

    if not total:
        print('\nRien a faire : aucune zone sans name_en presente dans cheatAreas.')
        return

    if args.apply:
        with open(CSV_PATH, 'w', encoding='utf-8', newline='') as handle:
            handle.write('\r\n'.join(lines))
        print(f'\nECRIT dans {CSV_PATH}')
    else:
        print('\n(dry-run : relancer avec --apply pour ecrire)')


if __name__ == '__main__':
    main()
