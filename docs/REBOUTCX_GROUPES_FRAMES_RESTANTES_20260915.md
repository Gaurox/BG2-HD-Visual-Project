# ReboutCX — groupes de frames des familles restantes, 2026-09-15

## Décision / résultat

**Partager le calcul des pixels entre familles avant de poursuivre en série avec des caches séparés.**
Sur les **43 familles restantes du lot historique de 76** : **3 338 364 inférences supplémentaires
évitables (85,50 %)** par rapport à un cache P12 indépendant dans chaque famille, supposé sans éviction.
Les écritures, registres et vérifications par composant restent nécessaires.

Analyse de sources, réalisée sans inférence, modèle GPU, job/run de production, catalogue dérivé,
QA humaine, installation ou extinction. Scripts et sorties P8–P12 existants inchangés.
Le suivi reste **33/78 familles produites** ; ce relevé ne produit aucune des familles en attente.

## Périmètre exact

- Référence : `sprite/catalogs/creature-x2-reboutcx/jobs/playable-characters-reboutcx-progress-p12-v1.json`,
  SHA `5BCC6548312A5B086908471F84FDDE67A27D52B4C4F4940FE7A0455CE2006DCD` ; commit de départ `88a8da99`.
- Lot historique : 76 références sous `sprite/families/playable-characters` dans
  `sprite/catalogs/creature-x2-nearest/jobs/append-all-playable-characters-v1.json` ; **43 en attente**.
- Deux références historiques supplémentaires : `0x6102` et `0x6110` ; **45 en attente sur 78**.
  Leur projection utilise explicitement le même contrat que les 43 autres, car leurs jobs de famille
  ReboutCX P8 n'existent pas. Elles n'ajoutent **aucune nouvelle identité de frame** au stock des 43.
- Aucun manifeste de production ReboutCX existant trouvé dans ces 45 familles. Aucun résultat des
  **33 familles déjà produites** n'est utilisé pour réduire les chiffres : gain conservateur sur ce point.
- Les 43 jobs de famille épinglent le même template :
  `sprite/families/playable-characters/6100-human-male-fighter/chmb3/jobs/reboutcx-p8-full-v1.json`,
  SHA `EB1AEEEC069CF77AFE1CCD9F4AA033A18985C660CA090208850BB50279A86774`.

## Volume de travail

« Inférence » = frame non nulle comportant au moins un pixel opaque. Les clones de ressources
entières déjà reconnus par P12 sont retirés avant les calculs ci-dessous.

| Mesure | 43 restantes / lot de 76 | 45 restantes / inventaire de 78 |
|---|---:|---:|
| Composants à assembler/vérifier | 2 657 | 2 787 |
| Frames source à couvrir | 7 453 473 | 7 810 190 |
| Frames modèle logiques, avant cache de frames | 6 128 361 | 6 418 752 |
| Doublons éliminables **dans chaque famille** | 2 224 053 | 2 326 596 |
| Inférences avec caches de famille séparés, sans éviction | 3 904 308 | 4 092 156 |
| **Identités modèle à calculer une seule fois pour l'ensemble** | **565 944** | **565 944** |
| **Inférences supplémentaires évitables entre familles** | **3 338 364** | **3 526 212** |
| **Réduction supplémentaire des inférences** | **85,50 %** | **86,17 %** |
| Pixels d'entrée q32 avec caches séparés | 12 044 839 936 | 12 609 944 576 |
| Pixels d'entrée q32 avec partage global des calculs | 1 658 697 728 | 1 658 697 728 |
| **Pixels q32 supplémentaires évitables** | **10 386 142 208 / 86,23 %** | **10 951 246 848 / 86,85 %** |

q32 = dimensions arrondies individuellement au multiple de 32, comme le regroupement P12.
Ces pixels excluent les places de remplissage des lots GPU de 86 et ne mesurent pas une durée.
Le xBR, la préparation RGB, le passage modèle, BOX et la quantification sont partageables pour ces
identités ; les gains de ces phases ne doivent pas être additionnés à leurs temps concurrents.

## Groupes identifiés

- **566 120 identités de cache** : 565 944 frames avec modèle + 176 frames transparentes sans modèle.
- **487 956 identités modèle partagées entre familles**, 77 988 propres à une seule famille.
- **54 ensembles de familles consommatrices** dans le périmètre des 43 ; une identité appartient à
  exactement un ensemble. Les ensembles peuvent contenir des familles communes, sans double compter
  leurs identités de frames.
- **230 groupes de composants** ont les mêmes ensembles de sources BAM canoniques et le même contexte
  pixels. Les détails des frames couvrent également les doublons entre fichiers différents.

Les quatre ensembles les plus rentables représentent **2 997 159 inférences évitables**, soit
**89,78 % du gain supplémentaire**. Libellés ci-dessous descriptifs ; les clés de contenu font autorité.

| Ensemble principal | Familles consommatrices | Frames modèle uniques dans cet ensemble | Inférences évitables |
|---|---:|---:|---:|
| `WQS` : armes/casques des petits gabarits | 21 | 69 435 | 1 388 700 |
| `WQM` : équipements des elfes | 8 | 86 721 | 607 047 |
| `WQN` : équipements humains/demi-orcs féminins et moniale | 8 | 82 761 | 579 327 |
| `WQL` : équipements humains/demi-orcs masculins et moine | 6 | 84 417 | 422 085 |

IDs exacts, sans inclure les deux familles historiques supplémentaires :

```text
WQS : 6002 6003 6004 6012 6013 6014 6103 6104 6112 6113 6114
      6202 6204 6212 6214 6302 6303 6304 6312 6313 6314
WQM : 6001 6011 6101 6111 6201 6211 6301 6311
WQN : 6010 6015 6115 6210 6215 6310 6315 6510
WQL : 6005 6105 6205 6300 6305 6500
```

Les boucliers `WQS` forment d'autres ensembles : par exemple **13 968 identités modèle** partagées
par dix familles, soit **125 712 inférences évitables**. Ne pas considérer une classe/race entière
comme identique sur la seule base du préfixe.

### Attribution du calcul à un seul producteur

`family-work-plan.json` attribue chaque identité à sa première famille dans l'ordre croissant des IDs.
Somme des nouvelles inférences : **565 944**. Ce fichier est un plan analytique, pas une file exécutable.

Exemples : `0x6001` = 97 392 nouvelles inférences ; `0x6002` = 93 751 nouvelles + 386 réutilisées ;
`0x6003` = 9 388 nouvelles + 69 575 réutilisées ; `0x6311` = 7 457 nouvelles + 90 057 réutilisées.

**11 familles n'ajoutent aucune nouvelle inférence dans cet ordre** :
`6004 6014 6015 6114 6204 6214 6215 6304 6305 6314 6315`.
Leurs fichiers et contrats doivent néanmoins être assemblés et vérifiés. Le calcul peut être attribué
à un autre producteur sans changer les identités ; ne pas dépendre du premier thread qui termine.

## Identité et provenance

Clé calculée par les fonctions P12 existantes `context_key` et `frame_key`, sans modification :

```text
contrat pixels P12 + configuration/hash modèle + classes + marqueur nul + outil xBR/node
+ dimensions + index transparent + indices natifs + palette native complète + RGBA natif
+ palette RGB de référence réelle
```

- Centres, RESREF, numéro de frame, ID d'animation, nom d'item et couche restent dans les consommateurs.
  Ils ne justifient pas un nouveau calcul des mêmes pixels.
- Les marqueurs nuls sont exclus avec la même règle P12, qui tient compte de leurs centres.
  Les autres frames entièrement transparentes sont distinguées des demandes modèle.
- Pré-déduplication par composant conforme à P12 : même SHA du BAM canonique **et** du payload source ;
  le contexte de rendu est constant à l'intérieur du composant.
- Les contextes de toutes les familles sont compatibles ici. Aucune fusion approximative de pixels,
  de palettes proches ou de classes différentes. L'identité stricte peut manquer d'autres économies.
- **Identité des entrées ne prouve pas une identité binaire avec les anciens rendus** : les regroupements
  GPU peuvent modifier des arrondis. Nouvelle version de runtime/jobs/runs et contrôles ciblés nécessaires
  pour appliquer le partage ; P8–P12 restent immuables.

## Architecture pour exploiter le gain

1. Construire un plan de demandes partagé à partir des clés, avec un producteur stable par clé.
   Conserver la liste des consommateurs `(famille, composant, RESREF, frame)` et les métadonnées propres.
2. Exécuter des blocs bornés par taille de canvas ; lot GPU 86 et contrat numérique explicites.
   Diffuser les pixels calculés à tous les consommateurs ou les stocker dans un cache de pixels versionné.
3. Associer **cache RAM borné + stockage disque de blocs** ou traitement groupé des consommateurs.
   Éviter un démarrage de modèle/cache vide par famille ; ne pas réclamer des résultats dont le producteur
   ne peut pas démarrer faute de mémoire.
4. Réutiliser guide xBR, indices quantifiés, RGB cible et données nécessaires au contrôle. Assembler ensuite
   les registres et manifests **par composant**, avec leurs centres/cycles/palettes/classes d'origine.
5. Conserver la vérification indépendante des fichiers. Aucun catalogue dérivé global nécessaire.

**Capacité mémoire :** les résultats partagés représentent **15,60 Gio** de tableaux denses x2
(`guide uint8 + indices uint8 + RGB uint8`, soit 20 octets/pixel natif). Dans l'ordre actuel des familles,
le pic retenu **entre deux familles** atteindrait déjà **13,17 Gio**. Métriques, représentants, objets Python,
groupes actifs et buffers s'ajoutent : **1 Gio de cache P12 ne garantit pas un calcul unique global**.
Ces tailles ne sont pas un besoin VRAM ni une mesure du RSS. Un cache disque ajoute des lectures/écritures
non mesurées ici ; ordonner les demandes par groupes de consommateurs peut réduire les durées de rétention.

## Estimation de durée — conditionnelle

Calibration : huit familles P12 du lot précédent terminées sans reprise ; 1 414 500 frames source,
2 242,280 s de durée, 1 695,525 s d'occupation du worker GPU, 1 461,050 s d'événements CUDA modèle,
2 248 402 944 pixels q32 utiles. Mesures LOW extrapolées aux familles restantes ; aucun nouveau benchmark.

```text
A = 1695,525 / 2248402944   # secondes worker GPU / pixel q32 utile
C = 1461,050 / 2248402944   # secondes CUDA modèle / pixel q32 utile
R = (2242,280 - 1695,525) / 1414500  # résiduel / frame source
T_actuel = A × pixels_uniques_par_famille + R × frames_source
Gain projeté = [C, A] × pixels_q32_évitables_entre_familles
```

| Périmètre | Caches séparés, projeté | Avec partage, projeté | Durée évitable projetée |
|---|---:|---:|---:|
| 43 familles du lot de 76 | **3 h 19 min** | **1 h 09–1 h 27** | **1 h 52–2 h 11** |
| 45 familles de l'inventaire de 78 | **3 h 29 min** | **1 h 11–1 h 30** | **1 h 59–2 h 18** |

**Ce ne sont pas des performances acquises.** Hypothèses : mêmes coûts GPU par pixel et même ratio
de remplissage que le lot mesuré ; résiduel hors worker GPU conservé ; seuls les calculs du modèle ou
du worker GPU sont soustraits selon le scénario. Les nouveaux coûts du plan/cache disque/sérialisation,
les changements de recouvrement CPU/GPU et les interruptions Windows restent à mesurer. Les économies
CPU pourraient compenser une partie de ces coûts. Retenir **environ deux heures de calcul/attente évitables
dans ce modèle**, puis mesurer le temps réel avant d'annoncer un facteur de débit global.

## Artefacts complets et reproduction

Racine : `docs/measurements/reboutcx-pending-frame-groups-20260915-v1/`.

| Fichier | Contenu |
|---|---|
| `summary.json` | Totaux des deux périmètres, temps, SHA des trois artefacts principaux |
| `source-inventory.json` | Familles, composants, 3 495 templates BAM, consommateurs, sources et code épinglés |
| `frame-groups.jsonl.gz` | **566 120 groupes**, une ligne par clé ; frame représentative et toutes les références |
| `sharing-cohorts.json` | Regroupement exact par ensemble de familles consommatrices |
| `group-details.json` | Répartition par couches, exemples et 230 groupes de composants partageant leurs sources |
| `family-work-plan.json` | Travail nouveau/réutilisé par famille dans l'ordre croissant des IDs |
| `work-estimate.json` | Formules, coefficients, mesures de calibration et projections |
| `validation.json` | Contrôles des références, totaux et comparaisons natives ciblées |

Interpréter une ligne de `frame-groups.jsonl.gz` : `key` = SHA de l'identité P12 ; `size` = `[largeur,hauteur]` ;
`model` = besoin d'inférence ; `families` = indices dans `source-inventory.families` ; `representative`
et `references` = `[resource_id, frame_index]`. Chaque ressource donne ses `canonical_consumers`
`[component_id, RESREF]`. Chaque composant donne sa famille et tous les alias de ressource,
via `canonical_resref`. Cette factorisation identifie toutes les utilisations sans recopier des millions
de chemins. Les entrées transparentes non nulles sont incluses avec `model=false`.

```powershell
$taskPython = python -B -c "import sys; sys.path.insert(0,'pipeline/scripts'); from workspace_paths import get_path; print(get_path('chainner_python',required=True))"
# Choisir un nouveau dossier/version ; ne pas réécrire v1.
& $taskPython -B pipeline/scripts/reboutcx_inventory_pending_frame_groups.py docs/measurements/reboutcx-pending-frame-groups-20260915-v2
& $taskPython -B pipeline/scripts/reboutcx_summarize_pending_frame_groups.py docs/measurements/reboutcx-pending-frame-groups-20260915-v2
```

Relevé réussi : **124,837 s** (lecture/empreintes 58,336 s ; décodage/clés 52,227 s ; export/contrôles restants).
**57 043 fichiers de payload vérifiés par SHA**, code et métadonnées sources revérifiés à la fin.
Contrôle des **566 120 groupes et références : 3,999 s** ; reconstruction indépendante de
**12 paires de frames natives : 0,170 s**, égalité des clés/indices/palettes/RGBA.
Aucune image générée ; aucun temporaire de production ni catalogue construit.

## Validation courte avant application éventuelle

- Petit lot borné de deux composants pris dans un groupe fortement partagé ; limiter explicitement
  aux mêmes quelques dizaines de frames, incluant changement de canvas, transparence et classes.
- Vérifier qu'une clé provoque exactement un calcul même avec deux consommateurs concurrents ; tester
  aussi échec du producteur, éviction/relecture, reprise et ordre inversé.
- Comparer alpha, indices autorisés/classes, palettes, représentants, centres et cycles ; mesurer les
  différences éventuelles d'indices dues au regroupement numérique, pas seulement les hashes globaux.
- Mesurer séparément clé/plan, modèle CUDA, CPU, I/O du cache et écritures/vérification. Chronométrer le
  même ensemble jusqu'à la dernière vérification ; ne pas assimiler les 85,50 % de calcul évitable au débit.
- Créer une nouvelle version de contrat et de runs si l'application est autorisée ; conserver ce relevé.
