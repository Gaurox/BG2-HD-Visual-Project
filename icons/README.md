# Iconographie ITM/SPL

Ce domaine suit un asset physique par resref BAM référencé par un champ graphique ITM ou SPL.
Un BAM partagé entre plusieurs familles reste un seul asset et un seul remplacement runtime.
La production quotidienne suit [`../docs/PRODUCTION_RAPIDE.md`](../docs/PRODUCTION_RAPIDE.md) ; les
inventaires globaux ne sont pas reconstruits après chaque icône.

## Autorités

| Information | Fichier | Édition |
|---|---|---|
| Inventaire source et compteurs bruts | `index/manifest.json` | généré |
| Périmètre de production actif | `index/production-scope.json` | décision utilisateur |
| BAM, format, provenance et extraction | `index/resources.csv` | généré |
| Appartenance normalisée aux familles | `index/families.csv` | généré |
| Références propriétaires ITM/SPL | `index/usages.csv` | généré |
| Géométrie des frames | `index/frames.csv` | généré |
| Pages PVRZ des BAM V2 | `index/dependencies.csv` | généré |
| Resrefs référencées mais absentes | `index/missing-resources.csv` | généré |
| Production, sélection, QA, installation, release | `index/processing.csv` | autorité métier |
| Décisions QA | `index/qa-decisions/<RESREF>/*.json` ou `index/qa-decisions/batches/*.json` | immuable |

Familles inventoriées : `item-inventory`, `item-description`, `item-ground`, `spellbook`.
Périmètre actif depuis le 2026-11-12 : **1451 BAM uniques** = 976 `item-description` +
67 `item-ground` + 408 `spellbook`. `item-inventory` exclu sur demande utilisateur :
1480 BAM exclusivement inventaire hors production ; inventaire brut2931 conservé.
Quatre BAM multirôles restent pour leurs autres usages : FIST/OHNIKEY1 (description),
IBLUN04/ISTAF01 (sorts). Aucune production de leur usage inventaire demandée.
Autorité : `index/production-scope.json` ; filtre = au moins une famille active.
Sources, essais historiques, processing, QA, installation et release conservés.
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

## Illustrations de description : essai conservé, généralisation différée

- Décision utilisateur 2026-11-12 : conserver l'essai SeedVR2 7B x4 ; reprendre ce traitement
  ultérieurement sur les **976 `item-description`**. Aucun lancement global maintenant.
- Essai local : `batches/item-description-seedvr7b-x4-20261112-v1/` ; assets :
  `CSW1H01`, `CHELM01`, `CAMUL01`, `CPOTN02`.
- Recette exacte : `workflows/four-items.api.json` ; paramètres/sorties : `run.json` ;
  comparaison : `comparison/four-items-comparison.png` (chemins relatifs à l'essai).
- Copie Git de la recette et des métadonnées :
  `../pipeline/recipes/icons-item-description-seedvr7b-x4-20261112-v1/`.
- Modèle `seedvr2_7b_int8_convrot.safetensors`, VAE `seedvr2_ema_vae_fp16.safetensors` ;
  x4 Lanczos, seed `959948902156062`, 1 step, CFG 1, Euler/simple, correction couleur LAB.
- Entrées RGB sur beige `(234,221,190)`, padding droite/bas au multiple de 64 ; crop final
  aux dimensions natives x4. Comparaison RGB ; variante RGBA avec alpha natif nearest x4 séparée.
- Résultats, entrées et workflow conservés localement ; médias ignorés Git. Cette décision
  conserve la piste de traitement ; aucune QA runtime, installation ou release déduite.

## Objets au sol : ReboutCX et lissage renforcé

- Choix utilisateur 2026-11-22 : conserver ReboutCX avec lissage renforcé pour les objets au sol.
- Essai sur `GSW1H01`, `GSACK01`, `GPLAT01`. Masquer l'index cyan 1, inférer le RGB en ×4 avec
  ReboutCX, puis lisser la silhouette par couverture et prolonger les couleurs au bord.
- Lissage : iso-contour du masque à 0,5, couverture à 16 × 16 échantillons par pixel ×4,
  gaussien d'alpha σ 0,62 px natif, transition smoothstep ±0,19 et seuil ajusté à l'aire du
  masque de couverture. RGB pondéré au bord, σ 0,5 px natif. Dériver le ×2 du ×4 lissé
  par moyenne 2 × 2 en alpha prémultiplié.
- Essais locaux : `batches/item-ground-x4-edge-smooth-20261122-v1/` et
  `batches/item-ground-reboutcx-x2-x4-20261122-v1/` (`compare.py`, `planche.png`).
- Choix utilisateur 2026-11-22 : ×2 pour les 67 BAM `item-ground`, contour cyan masqué.
- Production : `python -B pipeline/scripts/build_ground_icon_reboutcx_x2.py item-ground-reboutcx-x2-20261122-v1`.
  Sorties locales : `batches/item-ground-reboutcx-x2-20261122-v1/assets/<RESREF>/reboutcx-lisse-x2.png`
  et `planche.png`. Géométrie et centres dans `geometry.json`, empreintes dans `run.json`.
- Surbrillance ×2 validée visuellement sur les trois objets d'essai : alpha du contour extérieur
  lissé à partir du BAM, calque cyan séparé composé sous le sprite ReboutCX. Les 67 calques et
  aperçus côte à côte sont dans `batches/item-ground-cyan-x2-20261122-v1/`.
- Commande : `python -B pipeline/scripts/build_ground_icon_cyan_x2.py item-ground-reboutcx-x2-20261122-v1 item-ground-cyan-x2-20261122-v1`.
- QA visuelle utilisateur : 67 sprites ×2 avec et sans surbrillance, voir
  `index/qa-decisions/batches/20261122-item-ground-x2-cyan-visual-accepted-v1.json`.
  `qa_state=visual-accepted` porte sur les planches. L'état en jeu reste à évaluer.

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
refuse les identités obsolètes. `icons/index/processing.csv` fait autorité pour ces états.

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
