# Phase 1 — contrat Q3m Monster fixe x2

État : **contrat spécifié et vérifié CPU** ; producteur/lecteur Monster V6 à implémenter.
Périmètre écrit : ce dossier uniquement. Aucun GPU, cache Q3m, registre, QA, build,
assemblage, installation, configuration, release ou commit.

## Artefacts

- `contract.json` : classes, K6, encodeur/décodeur, identités, portée et adaptations.
- `profiles.json` : six palettes sources BGRA, six tables de successeurs u8, 36 palettes
  de fit RGBA ; hex = octets dans l'ordre des indices `0..255`, digest SHA256.
- `verification.json` : vérifications ciblées de ce contrat ; **pas une QA ingame**.
- `build_contract.py` : reproduction CPU vers une nouvelle destination ; refuse l'écrasement.

## Identité / profils réservés

| Cible / CRE | Animation / famille | Profil palette G1 / G2 | BAM / frames natives |
|---|---|---|---|
| Spectateur / `BEHSPE01` | `0x7F02`, `MBEH` | `2 / 3` | `13 / 6 831` |
| Bodhi / `BODHI` | `0x7F30`, `NBOH` | `4 / 5` | `13 / 8 100` |
| Golem geôlier / `IGOLEM02` | `0x7F07`, `MGLC` | `6 / 7` | `13 / 5 994` |

- Identités reprises de l'analyse native CRE/ARE et des index acquis ; le golem est
  l'acteur `Clay Golem` d'`AR0602` à `(2944,2853)`, CRE `IGOLEM02`, dialogue `igolem2`.
- Source de familles : `sprite/index/sprite_families.csv` ; BAM des trois manifests
  `sprite/families/monsters/7fxx/{7f02-mbeh-beholder,7f30-nboh-bodhi,7f07-mglc-golem-clay}/source/stock/manifest.json`.
- Tous : `monster-bg2ee-2.7.3.0`, owner `3`, `false_color=0`, body simple.
- G1 = `G1,G11,G12,G13,G14,G15` ; G2 = `G2,G21,G22,G23,G24,G25,G26`.
- Deux palettes distinctes par famille ; palettes égales au sein de chaque groupe.
- IDs `2..7` et règle `2` **réservés par ce contrat, non activés dans le runtime**.
  Character conserve profil `1`, règle `1`, owner `1`.
- Un remplacement de famille affectera ses autres consommateurs : usages stock indexés
  `MBEH=27 CRE`, `NBOH=11`, `MGLC=36` ; pas d'isolation par nom de créature.

## Classes / successeurs / alpha

- Classes : `0=transparent`, `1=shadow_black`, `2=null_frame_marker`, `3..255=material`.
  Classes fixes historiques MBEH/NBOH reprises ; aucune rampe Character transposée.
  Cette classe material ne prétend pas identifier peau, métal ou vêtements.
- Successeurs : spéciaux vers eux-mêmes ; matière vers la couleur matière distincte
  la plus proche en moyenne de distance OKLab² f64 sur K6, égalité → indice minimum.
  Table calculée une fois puis figée par profil ; jamais `i+1` ni tri runtime.
- Pour guide spécial : `I=guide`, `F=0`. Pour matière : `I=3..255`, `F=0..7`.
  Pas de mélange vers `0/1/2`, tramage, B ou Q8c.
- RGB : `((8-F)*P[I].rgb + F*P[succ[I]].rgb + 4) >> 3` ; alpha : **`P[I].alpha` live**.
  Indice transparent `0` forcé à alpha zéro ; les octets réservés source ne sont pas l'alpha.
- Oracle natif fixe sélectionné : `CVidPalette::Realize` `0x421430`, type `0` → `0x42d350`.
  Flags `5` : alpha `0/127/255/255` pour indices `0/1/2/3`.
  Flags `7`, transparence `128` : alpha `0/64/128/128` ; flags `1` : ombre opaque.
  Ces valeurs correspondent aux paramètres de l'oracle, **pas à une capture du jeu**.
- Le lecteur utilisera les couleurs/alphas réalisés à chaque appel, sans figer l'ombre à 127.
  Dépendances = union des `I` et `succ[I]` si `F>0`, 32 octets ; alpha primaire participe
  à l'invalidation. Exiger l'égalité d'alpha des paires matière positives, sinon repli natif.
- MGLC : audit nouveau strictement nécessaire aux spéciaux, `5 994` frames ; `4 970`
  utilisent l'indice `2`, exclusivement en `1×1`, centre `(0,0)`, zéro anomalie.
  NBOH : audit historique du job `reboutcx-p2-sample-v1.json` repris.
  MBEH : classes et résultats historiques repris ; toute optimisation de bypass null
  doit appliquer le prédicat `1×1/(0,0)/pixel=2`. Son exclusivité globale reste à établir
  en phase 2 si les témoins existants ne la démontrent pas ; le chemin général conserve
  de toute façon l'indice 2 et sa géométrie.

## Six fits

| Fit | Flags natifs | Tint RGB |
|---|---|---|
| neutral | `0x00005` | `255,255,255` (tint désactivée) |
| warm | `0x20005` | `255,192,128` |
| cold | `0x20005` | `128,192,255` |
| green | `0x20005` | `128,255,160` |
| red | `0x20005` | `255,128,160` |
| dim | `0x20005` | `128,128,128` |

- Poids égaux ; transparence `255` ; conditions statiques conçues pour couvrir neutre,
  teintes divergentes et obscurcissement, pas six conditions mesurées dans AR0602/Bodhi.
- Palettes issues de l'exécution CPU émulée de la branche native, comparées à une
  traduction scalaire indépendante : tint matière `RGB*tint >> 8`, **pas `/255`**.
- Oracle : PE local pinné `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`,
  Unicorn `2.1.4`, état vidéo explicite ; requête de teinte de zone blanche inutilisée
  par ces flags, contrôle `/GS` neutralisé dans l'émulation, aucun appel OS/jeu.
- Non couverts : gamma/luminosité, effets animés, tint de zone, add/light et autres flags.
  La palette live restera l'autorité de décodage. Capturer le profil réellement utilisé
  et juger K6/successeurs dans le pilote ; nouvelle version si le contrat doit changer.
- `REF/DEFAULT/LATIN1..4` Character exclus : ils ne définissent pas ces palettes fixes.

## Briques conservées / adaptation de phase 3

- BAM V1/P8 natif ; guide xBR2X avec provenance ; remplissage RGB nearest opaque sous
  transparent ; ReboutCX x4 FP16, batch `86`, canvas quantum `32` ; BOX float32 x4→x2
  avant encodage ; K6 exhaustif OKLab² f64, égalité `I` puis `F`.
- Format V6 I/F/dep proposé inchangé ; conservation de toutes les frames, centres signés,
  cycles/lookup et marqueurs. Aucun V6 Monster généré ici.
- Adapter encodeur/validation aux classes et successeurs fixes, plan/work keys,
  producteur, writer catalogue owner 3, dispatch/décodeur/LUT natifs, manifeste de capacités.
  Vérifier type de palette réellement capturé pour Monster ; ne pas seulement retirer
  le garde-fou Character. Profil inconnu/corrompu → rejet et repli natif.
- Nouveau namespace de cache : profil/règle, palette source, successeurs, K6, classes,
  alpha/guide, modèle, kernel et scale. Aucun résultat Character I/F/dep réutilisable
  par identité d'image seule. Les anciens candidats xBR/Q0 n'établissent pas du Q3m.
- Installation future : extension du catalogue actif des `78` Character, conservation
  des `81` paperdolls et shaders/UI, BOX global monde. Références acquises :
  `docs/measurements/playable-q3m-x2-ingame-20261002-v1/current-generation.json` et
  `pipeline/SPRITES_PRODUCTION_Q3M_X2.md`. Aucun contrôle Character acquis répété.

## Vérification et reprise

- `39` en-têtes palettes comparés, `6` profils ; `54` réalisations natives / `13 824`
  entrées RGBA comparées ; `72 972` reconstructions RGB scalaires/vectorielles ; zéro écart.
- Aucune mesure de qualité ReboutCX, QA visuelle, validation runtime ou déduplication
  frame inter-familles/Character effectuée ici.
- Reproduction depuis le dépôt, avec Python `config://chainner_python`, numpy et Unicorn
  `2.1.4` disponibles dans cet interpréteur ou un dossier de dépendances temporaire :

```powershell
& $spritePython -B docs/measurements/q3m-monster-contract-x2-20261002-v1/build_contract.py `
  --output <nouveau-dossier> --unicorn-path <dossier-dependances-temporaire>
```

Prochaine action : **phase 2 CPU**, plan de travail limité aux trois familles, comparaison
avec le plan/cache Character et les témoins historiques ; comptage exact des tâches
compatibles réutilisables et manquantes, sans inférence ni modification des suivis existants.
