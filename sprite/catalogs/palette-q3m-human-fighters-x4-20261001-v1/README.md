# Guerriers humains 0x6100 + 0x6110 — test ingame Q3m K6 x4

- Catalogue x4 rétabli le 2026-10-01 à 17:52 UTC après comparaison x2 ; DLL corrigée et INI inchangés, 1 312 shards installés vérifiés. Preuve : [restoration-verification.json](../palette-q3m-human-fighters-x2-20261001-v1/restoration-verification.json). Le pack x2 reste disponible pour réinstallation ; les preuves initiales ci-dessous restent historiques.
- Runtime courant : [correctif Character à froid](../../../pipeline/runtime/fixes/character-cold-resolve-20261001-v1/README.md), installé le 2026-10-01 ; catalogue/INI inchangés, nouvelle DLL et reçu actif mis à jour. Les preuves d'installation initiale ci-dessous restent historiques.
- État : `installation-verification.json` = `installed-pending-manual-qa` ; reçu courant `ingame-installation/active-test.json`.
- Catalogue V2 x4 actif : 2 animations Character, 1 312 composants/shards V6, 1 312 routes ; 358 697 frames stockées.
- Par modèle : 656 BAM, 4 corps/armures, 18 casques, 12 boucliers, 31 armes ; absences natives conservées.
- Recette des deux sources : Q3m K6, six palettes P1, F=0..7 en octets, XPRESS/raw, sans B/tramage ; géométrie, centres, cycles et représentants conservés.

| Animation | Source finale, relative à `sprite/families/playable-characters/` | Frames |
|---|---|---:|
| `0x6100` masculin | `6100-human-male-fighter/research/palette-q3m-series-20261001-v1/x4-verification.json` | 180 337 |
| `0x6110` féminin | `6110-human-female-fighter/research/palette-q3m-p3-20261001-v5-full-x4-6110/verification.json` | 178 360 |

## Assemblage et preuves

- `prepare_catalog.py` : fusion des tables, contrôle SHA/taille/entête V6 de chaque source ; liens physiques vers les fichiers existants, aucun calcul neural ni réencodage.
- `verification.json` : sources et preuves liées par SHA ; toutes les routes `(animation, resref, digest composant, SHA shard, ordinal)` identiques aux deux catalogues sources.
- Preuves natives complètes des deux sources acquises sur 18 palettes ; octets V6 inchangés, preuves historiques conservées.
- Contrôle supplémentaire sur le catalogue commun : pour chaque modèle, première frame des 656 BAM puis retour au premier ; 657 frames × 18 palettes, composition des quatre couches réelles, plafonds I/F et métadonnées de 128 Mio respectés.
- Limite I+F requise déclarée : borne conservative `2 × max(index_bytes par shard)` ; runtime x4 capable de 1 Gio. Valeur exacte dans `generation/build-manifest.json`.
- `generation/build-manifest.json`, `current-generation.json`, `x4-q3m-k6.job.json` : identité scellée du catalogue installable. Payload local ignoré sous `generation/iee-assets/creature-sprites/` ; vue native courte `sprite/.work/q3m-human-fighters-x4-20261001-v1/`.

## Installation initiale — 2026-10-01

- Jeu : `config://bg2ee_game_root` ; jeu et InfinityLoader fermés avant remplacement.
- Catalogue actif : `iee-assets/creature-sprites/CreatureSprites-XN.catalog`, SHA `637DBC809EAD7A9AD2A771BB760F5C0042109C5A4B6A19BE68A75CC41D50E0B8`.
- Pack actif : 1 105 771 164 octets (1,106 Go décimaux) ; 656 shards masculins copiés, 656 féminins déjà présents et vérifiés. Anciens shards hors catalogue conservés.
- Runtime Q3m x4 existant : SHA DLL `250BCF9219152BB70358CF8687DAA14351878B2C57B116582460810FB0938FE3`, octets inchangés.
- Nearest ; filtrage linéaire désactivé ; `ShaderSuite.fpSprite/fpSELECT.Enabled=false`, trace palette désactivée. INI identique à la baseline.
- `installation-baseline.json`, `installation-verification.json` : catalogue précédent féminin seul, INI, sauvegardes exactes, vérification des 1 312 shards réellement installés et possibilité de restauration.
- Reçu courant `ingame-installation/active-test.json` et sauvegardes : locaux ignorés selon la convention du dépôt ; preuves finales d'installation versionnées.
- `install_and_verify.ps1` : première installation, preuve finale immutable ; ne pas réexécuter ce script dans le run historique.
- Autres animations : comportement BAM natif conservé ; aucune modification de production globale, QA acceptée ou release.
- Limites : alpha d'oracle synthétique ; effets vivants, rendu GL et qualité visuelle restent à contrôler ingame. Régression REF P1 x4 +11,59 % conservée avec la recette.

Depuis la racine du workspace :

```powershell
$q3mRun = 'sprite/catalogs/palette-q3m-human-fighters-x4-20261001-v1'
$q3mRuntime = 'pipeline/runtime/manifests/iee-character-cold-resolve-20261001-v1.json'
# Vérifier catalogue, DLL, configuration et tous les shards actifs ; lecture seule.
& pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 -JobFile "$q3mRun/x4-q3m-k6.job.json" -RuntimeManifest $q3mRuntime -CreatureSpriteFilter Nearest -VerifyOnly
# Restauration catalogue + ancienne DLL : commandes dans
# pipeline/runtime/fixes/character-cold-resolve-20261001-v1/README.md.
```

- Contrôle manuel attendu : chaque sexe, quatre armures, casques/boucliers/armes, directions, repos/marche/attaque, couleurs, effets pulsés et ombres/transparence. Aucun lancement ni contrôle du jeu effectué par l'installateur.
