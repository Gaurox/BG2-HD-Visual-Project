# Portraits BG2EE

## Autorité d'assets

[`inventaire_portraits.csv`](inventaire_portraits.csv) contient une ligne par base de portrait
native réellement exposée par BG2EE : déclaration dans la table `portraits` de `BGEE.lua` ou
référence portée par un CRE. Les BMP L/M/S sont des ressources membres avec BIF et SHA-256 complet,
pas des assets supplémentaires.

Génération depuis `config://bg2ee_game_root` :

```powershell
python pipeline/scripts/extract_character_portraits.py --output portraits --prune
```

## Vues d'usage et corpus externe

| Périmètre | Inventaire | Rôle | Générateur |
|---|---|---|---|
| PNJ recrutables | `portraits-recrutables/inventaire.csv` | occurrences PDIALOG/CRE ; pas de nouveaux assets | `extract_joinable_portraits.py` |
| PNJ rencontrés | `portraits/pnj-rencontres/inventaire.csv` | occurrences CRE hors recrutables ; pas de nouveaux assets | `extract_encountered_portraits.py` |
| Mod PPE | `portraits/mod-PPE/inventaire.csv` | corpus tiers non installé ; exclu du registre du patch | `organize_ppe_portraits.py` |

`grands/`, `moyens/` et `petits/` sont des données extraites reconstructibles. Ne pas lancer
`workspace.py ... --run` automatiquement après régénération : préparer avec
`python pipeline/scripts/workspace.py refresh --changed`, puis demander scopes ciblés/toutes/aucune
conformément à
[`../docs/WORKSPACE_INTEGRITY.md`](../docs/WORKSPACE_INTEGRITY.md).
