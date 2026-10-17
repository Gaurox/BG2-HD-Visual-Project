# Nuages : alpha palette natif pour les VVC normaux — 2026-10-17

- **Installé/vérifié hors jeu ; QA visuelle en attente.** Demande : « applique un correctif » après diagnostic `effects/research/black-cloud-backgrounds-20261017-v1/REPORT.md`.
- Autorités : [`installation.json`](installation.json), [`transaction.json`](transaction.json), [`verification.json`](verification.json). Manifest runtime actif SHA256 `0471FAEDCAA40E3D682A7EA2AC733CBEE085C703A08507FC82645B7E91A43E8F`.
- Les4commandes restent identiques : Z580269/278/290/300. Leurs références BAM ciblent désormais X58WFOG/CLK/CLS/DFOG. Les46contrôleurs normaux de ces4BAM sont routés de la même manière ; SPHORWIA/SPHORWIL inchangés.

| Production native | Alias normal corrigé | Run dérivé sous `effects/ressources/<BAM>/runs/` | Phases vérifiées |
|---|---|---|---:|
| BDWOFOGA |X58WFOG|`bdwofoga-palettealpha-normal-x4-30fps-20261017-v1`|1360|
| SPCLOUDK |X58CLK|`spcloudk-palettealpha-normal-x4-30fps-20261017-v1`|568|
| SPCLOUDS |X58CLS|`spclouds-palettealpha-normal-x4-30fps-20261017-v1`|568|
| SPDFOGA |X58DFOG|`spdfoga-palettealpha-normal-x4-30fps-20261017-v1`|568|

## Traitement / preuves

- Alpha : palette native A1..254 ; A0/255 = opaque par compatibilité, index transparent0 =0. Alignement aux centres natifs ; nearest x4 ; mêmes sources temporelles gauche/droite/fractions que les runs Apollo existants ; feather interne12 sur la silhouette binaire originale.
- **3064/3064 RGB byte-identiques** aux companions straight existants SeedVR7B/Apollo30/gauss1.2 ; aucune nouvelle inférence. Alpha changé sur3048phases ;16phases vides conservées. Reconstruction de l'ancien masque avant correction : erreur maximale0 sur toutes les phases, contrôlant l'alignement et le feather.
- Chaque run nouveau contient `run.json` scellé, `02-interpolation/manifest.json`, `verification.json` et aperçus avant à gauche/après à droite sous `verification/`. Géométrie, centres, cycles/modes, doublons condensés et durée natives issus du run parent ; tous profils conservés.
- Runtime :2750nouveaux backings dédupliqués,4carriers alias dont les octets sont identiques aux carriers originaux ;225RESREF runtime /30229backings ;219productions initiales conservées.
- Les221anciens descripteurs de ressource,27479descripteurs de frame et anciens enregistrements binaires du registre restent identiques. SHA256 des4carriers BAM originaux revérifiés. Les noms BAM/SPL/PRO originaux des vrais sorts sont conservés ; aucun changement de leur chemin pour compenser l'alpha.
- DLL/INI/exécutable/shaders/catalogue personnages identiques par hash. Métadonnées16351068octets <16Mio ; CPU768Mio, GPU288Mio/64slots inchangés.
- `candidate-native-loader.log` et `installed-native-loader.log` : **65392contrats natifs/30FPS passent**,225ressources ; zéro lectureRGBA en mode catalogue. Inclut les59264contrats originaux et6128nouveaux contrats alias.
- Copie delta : chaque source vérifiée, sauvegarde des seules références/catalogue remplacés, copie atomique/hash temporaire puis hashes des2802cibles gérées vérifiés avant statut installé. Rollback automatique si erreur. Aucun rehash/copie des14,6Go d'anciennes images.
- CLI export amélioré : `pipeline/scripts/export_bam_frames.py --alpha-policy native-palette`, opt-in explicite ; défaut `binary-index` conservé pour anciens consommateurs. `pipeline/scripts/bam_export.py::native_palette_alpha` réutilisé par le correctif. Fixture CLI réelle `checks/palette-fixture.bam` : alpha binaire `[0,255,255,255]`, alpha palette `[0,255,64,255]`, RGB identiques ; sorties/contrôle dans `verification.json`.

## Reprise / retrait

- Recette : `pipeline/recipes/effects-cloud-palettealpha-20261017-v1/repair.py` ; `produce`, `prepare`, `install` exécutés. Les sorties/runs historiques sont conservés ; ne pas écraser leurs manifestes.
- `candidate/` est un **delta**, pas un pack autonome : nouveaux alias + catalogue complet + références VVC corrigées. Le catalogue référence aussi les anciennes images déjà installées ; base liée par SHA du manifest dans `before.json`/`plan.json`. Liens physiques vers les nouvelles productions scellées pour le candidat ; ne pas modifier ces fichiers en place.
- Sauvegardes des références/catalogue remplacés sous `before/` ; transaction sur la cible `config://bg2ee_game_root`, jeu et InfinityLoader fermés. Retrait enlève les seuls nouveaux alias et rétablit références/catalogue initiaux.

```powershell
python -B pipeline/recipes/effects-cloud-palettealpha-20261017-v1/repair.py restore
```

Relancer le jeu HD, puis les mêmes4CLUA Z58. Aucun lancement/QA ingame, acceptation des58 ou changement release déduit de cette installation.
