# Iconographie ITM/SPL

Ce domaine suit un asset physique par resref BAM référencé par un champ graphique ITM ou SPL.
Un BAM partagé entre plusieurs familles reste un seul asset et un seul remplacement runtime.

## Autorités

| Information | Fichier | Édition |
|---|---|---|
| Snapshot et compteurs | `index/manifest.json` | généré |
| BAM, format, provenance et extraction | `index/resources.csv` | généré |
| Appartenance normalisée aux familles | `index/families.csv` | généré |
| Références propriétaires ITM/SPL | `index/usages.csv` | généré |
| Géométrie des frames | `index/frames.csv` | généré |
| Pages PVRZ des BAM V2 | `index/dependencies.csv` | généré |
| Resrefs référencées mais absentes | `index/missing-resources.csv` | généré |
| Production, sélection, QA, installation, release | `index/processing.csv` | autorité métier |
| Décisions QA futures | `index/qa-decisions/<RESREF>/*.json` | immuable |

Familles admises : `item-inventory`, `item-description`, `item-ground`, `spellbook`.
Ne jamais déduire la famille depuis le nom du resref. Une resref multirôle possède plusieurs lignes
dans `families.csv`; elle n'est ni copiée ni classée dans un dossier de famille.

## Layout

```text
icons/
  index/
  ressources/<RESREF>/
    source.bam
    runs/<run-id>/
      run.json
  dependencies/pvrz/<RESREF>.pvrz
  batches/<run-id>/assets/<RESREF>/
```

- `ressources/<RESREF>/source.bam` : octets BAM stock, ignorés Git, hashés dans `resources.csv`.
- `dependencies/pvrz/` : pages partagées extraites une fois, hashées dans `dependencies.csv`.
- `runs/` : nouveaux runs mono-asset immuables.
- `batches/` : réservé aux runs multi-assets avec `asset_ids` et sorties par resref explicites.
- `icons/runs/` et les dossiers physiques par famille sont interdits.
- Le layout historique `icons/source/` reste une extraction locale legacy ; aucun nouveau chemin
  canonique ne doit le référencer.

Un nouveau `run.json` suit `../docs/workspace-run.schema.json`. La sélection reste dans
`index/processing.csv`; ni la présence d'un run ni un fichier interne ne prouvent QA, installation
ou release. Le contenu interne des runs sera défini avec le pipeline d'upscale, pas par ce document.

## Test runtime x2 des icônes d'inventaire

- Source scellée : `batches/item-inventory-xbr2x-aa-v1/`.
- Correction RGB sous alpha nul : `batches/item-inventory-xbr2x-aa-alpha-bleed-v1/` ; alpha et
  géométrie inchangés.
- Registre dérivé : `batches/item-inventory-xbr2x-aa-runtime-v3/ItemIcons-X2.registry`.
- Builds : `build_item_icon_alpha_bleed.py`, puis `build_item_icon_x2_registry.py` avec les ids de
  runs et le suffixe de frame explicites.
- Installation : `pipeline/scripts/Install-ItemIcon-X2-Test.ps1`.
- Restauration : `pipeline/scripts/Restore-ItemIcon-X2-Test.ps1`.
- Contrat : scope propriétaire `CVidCell::Render`, identité `resref + cycle + slot`, substitution à
  la composition texture commune ; centres et géométrie UI x1, texture physique RGBA x2 dédiée ;
  repli vanilla si l’identité ou l’état OpenGL n’est pas sûr.
- Installation = `installed-pending-qa`; aucune validation ingame ou release implicite.
- État courant : proposition x2 conservée, `qa=pending`, installation restaurée. Réinstallation à
  la demande avec le script ci-dessus et le runtime v3.

`processing.csv` contient une ligne par `asset_key` :

```text
asset_key,asset_id,asset_directory,upscale_run,upscale_state,selected_run,
qa_state,qa_evidence,installation_state,installation_receipt,release_state,
release_candidate,notes
```

`sync_icon_processing.py` conserve toute ligne existante, ajoute seulement les nouveaux assets et
refuse les identités obsolètes. Les valeurs d'état suivent `../docs/ASSET_TRACKING_CONTRACT.md`.

## Extraction

Entrée : `config://bg2ee_game_root`. Aucun chemin absolu personnel.

```powershell
python pipeline/scripts/build_graphics_inventory.py --scope icons --extract-icons --run
python pipeline/scripts/sync_icon_processing.py
# Relire le plan, puis ajouter --run pour initialiser/compléter processing.csv.
```

L'extraction écrit chaque BAM présent et chaque PVRZ partagée, puis génère les index. Les resrefs
absentes restent dans `missing-resources.csv`; ne jamais créer de source fictive. Ne pas exporter
de PNG de frames hors d'un run.

## Nommage des runs

`<resref-lower>-<pipeline>-<correctif>-vN`, ASCII. Ne pas inclure QA, installation ou release dans
le nom. Ne jamais modifier un run scellé ; une correction crée un nouveau run avec parents/hashs.
