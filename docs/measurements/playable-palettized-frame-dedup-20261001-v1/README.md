# Plan exhaustif de déduplication des Characters palettisés

Livrable : `processing-plan.sqlite` — 576 868 352 octets / 550,14 MiB.
SHA256 : `06b32c785aa4b946a3836275925fea587322b57485163b76bbb79104bd313e25`.
Statut : analyse source complète, contrôlée ; aucune génération, installation ou QA nouvelle.

## Portée

- Source : `sprite/index/{sprite_animations,sprite_families,sprite_resources,extractions}.csv` ; hashes dans `metadata.source_pins`.
- 78 modèles `engine_section=character`, `false_color=1` : 20 clercs, 20 guerriers, 20 voleurs, 16 mages, 2 moines ; les 30 identifiants `LOW` sont inclus.
- 5 142 familles : corps/armures, casques, boucliers, armes ; 4 896 avec ressources, 246 sans BAM natif. Absences conservées dans `absent_families` : 78 casques `YW`, 168 associations de boucliers sans ressource.
- 4 510 BAM V1, 1 564 054 frames déclarées, 168 192 cycles, 3 599 209 slots.
- Exclusions explicites dans `metadata.excluded_scope` : 8 définitions `character_old` (NPC/legacy, dont des modèles non palettisés ou sans BAM), 74 noms de paperdolls statiques d'inventaire. Ce sont des domaines distincts des sprites animés Character.
- Les 25 466 frames non référencées par les cycles et tous les marqueurs/transparents sont conservés. Aucun élagage de frames.

## Volume économisé

| Base de comparaison | Avant | Après | Économie |
|---|---:|---:|---:|
| Toutes occurrences modèle/BAM/frame | 13 677 041 | 563 969 traitements uniques | 13 113 072 / **95,8765 %** |
| Chaque BAM distinct traité une fois | 1 564 054 | 563 969 | 1 000 085 / **63,9418 %** |
| Frames coûteuses après partage des BAM | 894 348 | 563 797 | 330 551 / **36,9600 %** |
| Pixels q32 coûteux après partage des BAM | 2 309 177 344 | 1 655 791 616 | 653 385 728 / **28,2952 %** |
| Chaque modèle déjà dédupliqué en interne : frames coûteuses | 7 182 104 | 563 797 | 6 618 307 / **92,1500 %** |
| Chaque modèle déjà dédupliqué en interne : pixels q32 coûteux | 22 021 695 488 | 1 655 791 616 | 20 365 903 872 / **92,4811 %** |
| Toutes occurrences : pixels q32 coûteux | 31 296 118 784 | 1 655 791 616 | 29 640 327 168 / **94,7093 %** |

- `q32 = ceil(width/32)*32 * ceil(height/32)*32` ; travail neural utile, sans les slots de remplissage fixed86. Les pourcentages mesurent du volume, pas un temps d'exécution observé.
- Q3m K=6 : 68 688 744 cibles neurales sans partage → **3 382 782** avec la queue complète de frames uniques.
- Option à deux étapes : `neural_queue` contient 563 319 entrées, soit **3 379 914** cibles. 478 traitements de guides distincts peuvent réutiliser les mêmes six cibles neurales. Les guides et encodages restent distincts.
- 4 464 BAM sont consommés par plusieurs modèles, jusqu'à 36 modèles/BAM ; 45 680 répétitions de ressources évitées.
- 737 groupes de BAM intégralement identiques sous des resrefs différents : 1 752 ressources, 1 015 copies supplémentaires.
- 144 157 groupes de frames traversent plusieurs BAM ; 558 913 groupes traversent plusieurs modèles, jusqu'à 78 modèles/groupe.
- Comparaison au cache existant, qui inclut toute la palette native : 566 136 clés → 563 969. Ignorer les seules entrées RGB non lues évite **2 167** traitements supplémentaires.

Exemples de traitements communs, équipement compris :

| Modèles | Frames uniques communes | Dont coûteuses |
|---|---:|---:|
| Humaine clerc `0x6010` / guerrière `0x6110` | 91 277 | 91 197 |
| Humaine guerrière `0x6110` / voleuse `0x6310` | 86 096 | 86 016 |
| Guerrière `0x6110` / alias LOW `0x5110` | 93 948 | 93 868 |
| Guerrière petite race `0x6113` / gnome `0x6114` | 79 724 | 79 653 |

## Identité sûre du traitement

- `input_key` : SHA256 du domaine, largeur/hauteur x1, indice transparent et **tous les indices natifs** dans leur ordre. Aucun recadrage, miroir, rotation, réindexation ni tolérance.
- `work_key` : SHA256 du domaine, `input_key` et triplets RGB natifs des **indices effectivement présents**, y compris le transparent s'il est utilisé.
- Une image RGB identique avec des indices différents conserve des tâches différentes : recoloration, classes sémantiques, ombres et spéciaux restent distincts.
- Les entrées inutilisées de la palette native n'interviennent ni dans le RGBA envoyé à xBR, ni dans sa provenance/map_output. ReboutCX et l'encodeur Q3m utilisent les six palettes de fit communes. La fusion de ces seules différences est donc sûre pour ce contrat.
- Le quatrième octet de palette BAM est conservé dans les ressources ; la production actuelle dérive l'alpha par `index == transparent`, sans lire cet octet.
- Deux guides de palettes natives utilisées différentes ne fusionnent pas ; leurs cibles neurales peuvent partager `input_key` avec les palettes de fit communes.
- Les centres, cycles, resrefs, identités source, couches et modèles ne sont jamais remplacés par ceux du représentant. 2 325 groupes ont effectivement des centres différents.
- Profil figé dans `metadata.profile` : Q3m K6, fractions 0..7, six palettes REF/DEFAULT/LATIN1..4, poids égaux, sans B ni tramage, modèle/kernels/scalepix hashés, fixed86/q32/fp16. Résultats x2 et x4 distincts.
- Ce contrat de calcul n'accorde aucune QA aux autres modèles. Les profils, palettes de fit ou paramètres différents nécessitent un autre namespace de résultats.

## Utilisation du fichier

SQLite standard (`sqlite3` Python), ouverture en lecture seule. Les indices uniques compressés et palettes sont inclus : aucune image intermédiaire ni nouvelle extraction n'est nécessaire pour alimenter le traitement.

| Table/vue | Fonction |
|---|---|
| `processing_queue` | Une seule ligne par traitement de frame complet ; `work_id`, `work_key`, plan indexé zlib, palette native, géométrie, représentant et consommateurs |
| `neural_queue` | Option : cibles neurales partagées par entrée indexée ; six fits par ligne |
| `inputs` / `work_items` | Identités, contenu, liens entre étapes, compteurs et bitset des modèles consommateurs |
| `frame_map` | Toutes les occurrences modèle/famille/couche/resref/frame → résultat unique, avec centres et identités source d'origine |
| `resources` / `frames` | Métadonnées originales, palette BGRA, centres x1, état RLE, référence aux cycles |
| `cycles` | Slots LE uint16, ordre original, lookup_start ; aucun renumérotage des frames |
| `models` / `families` / `family_resources` / `model_resources` | Relations exhaustives de l'inventaire |
| `model_statistics` | Volumes et uniques par modèle |
| `profile_palettes` / `metadata` | Six palettes RGB exactes, contrat, namespace par échelle, hashes, exclusions et statistiques |

```sql
-- Queue complète : les marqueurs et transparents restent présents, needs_model=0.
SELECT * FROM processing_queue ORDER BY padded_height,padded_width,work_id;

-- Reconstruction d'une famille : chaque ligne reprend ses métadonnées natives.
SELECT * FROM frame_map WHERE animation_id='0x6110'
ORDER BY family_id,resref,frame_index;

-- Toutes les réutilisations d'un résultat donné.
SELECT animation_id,family_id,layer,resref,frame_index,center_x,center_y
FROM frame_map WHERE work_id=:work_id;

-- Les identités de palettes/géométrie sont celles des occurrences, pas du représentant.
SELECT * FROM cycles WHERE resource_id=:resource_id ORDER BY cycle_index;
SELECT * FROM absent_families ORDER BY animation_id,family_id;
```

Chargement d'une entrée :

```python
i = np.frombuffer(zlib.decompress(row['indices_zlib']), np.uint8).reshape(row['height'], row['width'])
native_rgb = np.frombuffer(row['palette_bgra'], np.uint8).reshape(256, 4)[:, [2, 1, 0]].copy()
# alpha = np.where(i == row['transparent_index'], 0, 255)
# fitting palettes = profile_palettes.rgb_u8_256x3 ; ne pas remplacer par native_rgb.
```

Contrat du futur consommateur :

1. Parcourir `processing_queue` une fois pour un profil/une échelle ; regrouper les tâches par canvas en préservant fixed86/q32/fp16.
2. Persister les résultats encodés `I/F/dep_mask` sous `(namespace_by_scale[scale], work_key)` dans un cache de résultats séparé du plan immutable. Reprise et éviction mémoire relisent ce résultat ; elles ne relancent pas le calcul.
3. Pour chaque famille, rematérialiser depuis `frame_map`, `frames`, `resources`, `cycles`. Les centres x1, resrefs, source SHA, dimensions et cycles restent ceux de chaque occurrence. Représentatives calculées depuis son plan indexé natif, identique dans le groupe.
4. Partager seulement le résultat indexé. Réalisation des palettes par acteur/couche, LUT, effets et caches de pixels colorés restent propres au runtime.

Les producteurs existants ne consultent pas automatiquement cette base. Le livrable est le plan exhaustif destiné à leur future consommation ; aucune modification de génération n'est faite dans cette analyse. La queue décrit tout le corpus, y compris `0x6110` déjà produit : l'adoption future peut importer ses résultats existants après vérification du profil et des données, sans présumer qu'un ancien x4 Q0/ReboutCX serait du Q3m.

## Preuves

- `verification.json` : second parcours avec `bam_export.decode_bam`, indépendant de `palette_oracle.read_bam_p8` ; **4 510 BAM, 1 564 054 frames, 1 268 986 342 pixels natifs, 3 599 209 slots** comparés ; indices, RGB utilisés, alpha contractuel, géométrie, centres et cycles identiques.
- À chaque réutilisation du scan : comparaison réelle des plans décompressés et des RGB utilisés ; pas une simple égalité de hash.
- `coverage-verification.json` : **563 969** groupes contrôlés depuis les relations de la base ; compteurs, bitsets des modèles, centres différents, absence de groupe orphelin et existence des représentants.
- Chaque groupe a ses clés de contenu recalculées ; SQLite integrity/FK OK ; hashes de tous les BAM source/canoniques contrôlés.
- 9 tests de contre-exemples : RGB identique/indices différents, dimensions, transparence, palette utilisée/inutilisée, pixel modifié, transformations, spéciaux, conservation des centres et couches.
- Contre-vérification `0x6110` : **178 360 frames / 94 099 clés du cache historique**, identiques aux comptes du run Q3m x4 terminé. Le contrat minimal ramène cette famille à 93 948 tâches, dont 93 868 coûteuses.
- 70 frames stock à dernier run transparent RLE débordant : même troncature native que les deux lecteurs ; données originales conservées par leurs identités source.
- Ces preuves portent sur l'identité des entrées et la conservation des métadonnées ; aucune nouvelle inférence, preuve de qualité de tous les futurs résultats, validation native/ingame ou intégration release n'est déduite.

Reproduction (Python configuré, sans inférence) :

```powershell
$dedupPython = (Get-Content -LiteralPath 'config/workspace-paths.local.json' -Raw | ConvertFrom-Json).paths.chainner_python
& $dedupPython -B -m unittest discover -s pipeline/tests -p test_playable_frame_dedup.py -v
& $dedupPython -u -B pipeline/scripts/analyze_playable_frame_dedup.py verify docs/measurements/playable-palettized-frame-dedup-20261001-v1/processing-plan.sqlite
# Nouveau scan seulement vers un répertoire inexistant :
& $dedupPython -u -B pipeline/scripts/analyze_playable_frame_dedup.py scan docs/measurements/playable-palettized-frame-dedup-20261001-v2
```
