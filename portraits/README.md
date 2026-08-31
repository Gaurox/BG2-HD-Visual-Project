# Portraits BG2EE

Les CSV ci-dessous sont les autorités d'inventaire. Les scripts les régénèrent depuis les sources ;
les dossiers d'images et le registre global ne décrivent jamais seuls l'état.

| Périmètre | Inventaire canonique | Script de génération |
|---|---|---|
| Portraits stock L/M/S (95 séries, 285 BMP) | `portraits/inventaire_portraits.csv` | `pipeline/scripts/extract_character_portraits.py` |
| PNJ recrutables | `portraits-recrutables/inventaire.csv` | `pipeline/scripts/extract_joinable_portraits.py` |
| PNJ rencontrés | `portraits/pnj-rencontres/inventaire.csv` | `pipeline/scripts/extract_encountered_portraits.py` ; diagnostic `survey_creature_portraits.py` |
| Mod PPE | `portraits/mod-PPE/inventaire.csv` | `pipeline/scripts/organize_ppe_portraits.py` |

`grands/`, `moyens/` et `petits/` conservent les BMP stock sans conversion ni upscale. Toute
nouvelle extraction doit préserver la provenance KEY/BIF et être suivie d'un `workspace.py refresh`.
