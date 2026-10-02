# Traitement des sprites — chemin court

Processus Q3m x2 courant, cache/dédup, assemblage parallèle, installation et extension monstres/PNJ : [`../pipeline/SPRITES_PRODUCTION_Q3M_X2.md`](../pipeline/SPRITES_PRODUCTION_Q3M_X2.md). Les commandes xBR/ReboutCX ci-dessous ne remplacent pas ce catalogue actuel de 78 Character.

## Autorités indépendantes

| État | Source |
|---|---|
| identité/éligibilité | `index/sprite_*.csv`, `index/manifest.json` |
| production xBR | `catalogs/creature-x2-nearest/**/current-generation.json` |
| production ReboutCX | `catalogs/creature-x2-reboutcx/**/current-generation.json` |
| production Q3m Character x2 | `../docs/measurements/playable-q3m-x2-ingame-20261002-v1/current-generation.json` |
| QA ingame | décision immuable sous `index/qa-decisions/` |
| installation locale | reçu actif du run effectivement installé ; pour le Q3m complet : `../docs/measurements/playable-q3m-x2-ingame-20261002-v1/ingame-installation/active-test.json` |
| release | `sprite-release-candidates.json`, puis `content.json` |

Une installation ne vaut pas QA ; une QA ne vaut pas intégration release.

## Modes raster

| Mode | Usage | Sortie |
|---|---|---|
| xBR | nouvelle famille/animation ; repli sûr | catalogue canonique cumulatif |
| ReboutCX | améliorer des composants xBR existants | catalogue dérivé complet : ReboutCX ciblé + xBR ailleurs |
| Q3m K6 Character | traitement de série des personnages palettisés ; 78 IDs x2 produits/installés | queue unique + cache partagé I/F, catalogue V6 ; x4 séparé |

xBR et ReboutCX conservent BAM, cycles, centres, palettes dynamiques et registre x2. ReboutCX n'est
pas un second runtime et ne se sélectionne pas par instance ingame.

## Préparer les sources

La famille doit avoir `runtime_supported=yes`, `pipeline_ready=yes`, aucun `blocker` ni
`override_collision`, et des ressources non vides.

```powershell
python pipeline/scripts/extract_sprite_sources.py --family-id <family_id> --run
python pipeline/scripts/materialize_sprite_sources.py --job <job-xbr> --run
```

## Produire

### Q3m — Characters palettisés

Entrée de série : `pipeline/scripts/palette_playable.py`. Le plan actif
[`index/palette-work-plan.json`](index/palette-work-plan.json) est consommé systématiquement ;
résultats communs persistés entre modèles, source/centres/cycles propres à chaque occurrence.
Commandes `plan` (CPU), `run` (GPU demandé explicitement), `pack` (assemblage expérimental) et
reconstruction du SQLite : [`../pipeline/PALETTE_PLAYABLE.md`](../pipeline/PALETTE_PLAYABLE.md).
Cette voie ne change aucun état installation/QA/release.
L'installation complète a été réalisée séparément : [run et vérification](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/README.md), aucun manquant. Monstres/anciens PNJ hors Character : lire le [contrat d'extension](../pipeline/SPRITES_PRODUCTION_Q3M_X2.md), pas de commande Q3m générale disponible.

### xBR

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job <job-xbr>
```

Publier ensuite l'ajout canonique selon [`FAMILY_APPEND.md`](FAMILY_APPEND.md).

### ReboutCX

Précondition : le composant complet existe dans le catalogue xBR parent et le job ReboutCX épingle
un profil palette/classes déjà démontré pour ce type de calque. Toute inférence GPU doit être
annoncée à l'utilisateur avant lancement.

```powershell
python pipeline/scripts/reboutcx_full.py run <job-reboutcx>
python pipeline/scripts/reboutcx_full.py verify <job-reboutcx>
python pipeline/scripts/reboutcx_catalog.py build <job-catalogue-reboutcx>
python pipeline/scripts/reboutcx_catalog.py verify <job-catalogue-reboutcx>
```

`run` produit un composant complet ; `verify` reprend un run existant. Un changement de source,
recette ou sélection crée un nouveau job/run. Le job de catalogue est cumulatif : il redéclare les
remplacements ReboutCX antérieurs à conserver.

Profils de référence :

- Monster sans false-color :
  `sprite/families/monsters/7fxx/7f02-mbeh-beholder/jobs/reboutcx-p2-mbeh-v2.json` ; réutiliser ses
  classes seulement si la palette du nouveau cas est compatible.
- Character false-color : `sprite/families/playable-characters/6100-human-male-fighter/chmb3/jobs/reboutcx-p8-full-v1.json` ; palette réalisée RANGES12 et
  classes Character obligatoires pour body/arme/bouclier/casque.

Détails raster : [`../docs/REBOUTCX_PIPELINE_BG2_CODEX.md`](../docs/REBOUTCX_PIPELINE_BG2_CODEX.md).

## Installer et accepter

Utiliser les commandes du mode choisi dans [`FAMILY_APPEND.md`](FAMILY_APPEND.md). Jeu et
InfinityLoader doivent être fermés avant install/restore. Tester seulement le delta utile, puis
enregistrer la décision QA exacte. Compilation globale et release restent différées.
