# ReboutCX P12 — mesure d'une famille, 2026-09-15

## Résultat retenu

**65/65 composants produits et vérifiés ; débit +10,63 % face à P11, temps −9,61 %.**
Une seule exécution autorisée : famille `0x5211`, `5211-elf-female-mage-low`.
Implémentation commitée avant lancement : `37701d48cc5832eafe4975e26b22e5d95a38a66f`.
Production terminée, code de sortie 0 ; aucun catalogue global, installation, release ni extinction.

| Mesure | P11 | P12 |
|---|---:|---:|
| Temps jusqu'à dernière vérification | 329,633 s | **297,950 s** |
| Temps lisible | 5 min 29,63 | **4 min 57,95** |
| Débit de frames modèle logiques | 443,12/s | **490,24/s** |
| Frames source | 180 494 | 180 494 |
| Frames modèle logiques | 146 066 | 146 066 |
| Frames effectivement inférées | 146 066 | **97 831** |
| Lots GPU | 1 879 | 1 273 |
| Temps des événements CUDA autour du modèle | 236,618 s | 202,040 s |
| Occupation du worker GPU, transferts inclus | 290,218 s | 232,382 s |
| Somme préparation CPU | 259,376 s | 200,175 s |
| Somme quantification CPU | 235,764 s | 165,280 s |

- **31,683 s économisées** ; facteur de débit `329,632947 / 297,9501576 = 1,10633587`.
- Cache : **48 235 inférences évitées / 33,02 %**, zéro éviction, pic comptabilisé **650,35 MiB**
  pour un budget de 1 024 MiB. Cache et comptes d'admission vides à la fin ; aucune future pendante.
- Admission : **10,211 s incluses dans les 297,950 s**. 146 780 demandes éligibles au cache,
  dont 714 frames sans RGB opaque contournant le modèle ; d'où 48 888 hits cache mais
  48 235 inférences évitées. Les 30 204 marqueurs nuls restent hors cache.
- GPU : 109 478 slots, **11 647 places vides** ; 338 606 080 pixels avec padding/remplissage.
  Paramètres : composants 3, préparation 2, postprocesseurs 3, q32, N=86 constant,
  budget estimé groupes 4 096 MiB, cache 1 024 MiB ; un modèle chargé en 3,182 s.

## Pourquoi le gain global reste inférieur aux calculs évités

Le worker GPU économise 57,836 s, mais le temps hors de ce worker passe de 39,415 à 65,568 s
(+26,153 s). Le précomptage en explique directement 10,211 s. Le reste inclut les changements
de recouvrement CPU/GPU, écritures et synchronisations ; cette exécution ne les isole pas.
Les attentes de cache totalisent 25,958 s **sur des composants concurrents** : ne pas les
additionner au temps total ni les attribuer entièrement au chemin critique.

Les lots complétés à 86 et ces surcoûts expliquent l'écart avec les 33 % d'inférences supprimées.
L'estimation ajustée de +13 % était proche ; **retenir désormais +10,63 % mesurés** sur cette famille.
Aucun plafond matériel établi. Piste suivante éventuelle : assembler les demandes de même canvas
de plusieurs composants au niveau du propriétaire GPU pour réduire le remplissage ; mesure séparée.

## Contrats et différences de pixels

- Les 65 vérifications indépendantes sont terminées. Sources, modèle, palettes, classes,
  couverture et **tous les guides xBR** correspondent à P11 ; 195 manifestes antérieurs inchangés.
- **31 occurrences de frames ont un hash d'indices différent**, sur 180 494 frames source.
  Contrôle ciblé exhaustif de ces différences : 23 ressources, 167 144 pixels, **77 indices visibles
  modifiés** ; alpha, classes, géométrie, centres, cycles et représentants source identiques.
- Échantillon transversal supplémentaire : 126 ressources / 1 008 frames / 5 004 716 pixels,
  dont 639 953 visibles ; 1 indice visible différent, mêmes contrats.
- Conclusion : équivalence des contrats vérifiés ; **pas d'identité pixel à pixel complète avec P11**.
  La forme fixe du lot et sa composition peuvent modifier les arrondis numériques. Ces contrôles
  techniques n'attribuent aucune validation humaine ou ingame.
- Comparaison à une mesure historique unique P11, sans répétition A/B. Horloge `perf_counter`
  jusqu'à dernière vérification ; préparation de jobs/tri de file exclus dans les deux versions,
  admission P12 incluse. Les sommes de phases concurrentes ne sont pas additives.

## Artefacts et reproduction du relevé

Racine famille : `sprite/families/playable-characters/5211-elf-female-mage-low/`.

- 65 jobs : `*/jobs/reboutcx-p12-cache86-v1.json` ; runs scellés : `*/runs/reboutcx-p12-cache86-v1/`.
- File : `family-runs/complete-reboutcx-p12-v1/jobs/elf-female-mage-low-p12-v1.json`.
- Mesures : `family-runs/complete-reboutcx-p12-v1/measurements/` :
  `baseline-before-p12-v1.json`, `throughput-p12-v1.json`, `changed-frames-contract-v1.json`.
- Log : `sprite/.work/reboutcx-p12-production/session-1789459882943484900.jsonl`, SHA
  `5C978D914F8A535696D35F5AD308113392E95CB538FCEC7CA9B8796B241D0C87`.
- Sonde : `pipeline/tests/measure_reboutcx_p12_family.py <famille> <session>` : relevé 1,814 s,
  processus 2,082 s ; `--changed-frames` : 1,005 s, processus 1,291 s. Aucune production,
  aucun temporaire ; écritures exclusives de mesures nouvelles, refus d'écrasement.
- Aucun script P8–P12 utilisé par les runs n'a été modifié après leur publication. Préserver leurs
  octets et ceux des jobs épinglés ; toute évolution de production ultérieure doit être versionnée.
