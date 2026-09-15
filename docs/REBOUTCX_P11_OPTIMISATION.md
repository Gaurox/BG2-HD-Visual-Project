# ReboutCX P11 — mesure 0x5211, 2026-09-15

## Résultat

Famille : `sprite/families/playable-characters/5211-elf-female-mage-low`.
65 composants nouveaux, 65 vérifications indépendantes réussies ; 180 494 frames source,
146 066 frames modèle. Session terminée, code retour 0. Aucun arrêt du PC.

| Version | Durée jusqu'à dernière vérification | Frames modèle/s |
|---|---:|---:|
| P9 historique | 804,981 s | 181,453 |
| P10 | 437,261 s | 334,048 |
| P11 | **329,633 s** | **443,117** |

- P11/P10 : **×1,3265**, débit **+32,65 %**, durée **−24,61 %**, **107,628 s économisées**.
- P11/P9 : **×2,4421**, durée −59,05 % ; P9 utilisait une normalisation RGB différente.
- Estimation antérieure ×1,4–1,8 supplémentaire : non atteinte sur cette famille.
- Comparaison séquentielle unique, sans répétition A/B. Même GPU, 3 composants, 2 workers de
  préparation, 3 de quantification, réservation estimée 4 096 MiB, micro-lot maximal 86.
- `perf_counter` englobe chargement modèle et dernière vérification ; préparation des jobs et
  tri de queue exclus. Chargement unique : P10 8,358 s, P11 3,227 s ; cet écart de 5,131 s
  contribue au gain observé. Ne pas attribuer tout le gain à la seule réduction du padding.

## Architecture mise en place

- `pipeline/scripts/reboutcx_full_p11.py` : jobs/runs `reboutcx-p11-q32-group86-v1` ;
  regroupement des ressources canoniques avant inférence ; publication atomique par composant.
- `pipeline/scripts/reboutcx_runtime_p11.py` : groupes dans l'ordre source, au plus 8 ressources
  et 8 000 000 pixels natifs ; ressource dépassant ce seuil traitée seule. Seuil indépendant de
  la concurrence et de la RAM disponible. Réservation mémoire atomique par groupe, préchargement
  du groupe suivant si le budget le permet, deux lots de post-traitement au maximum.
- Padding : pas **32**, zéro en bas/droite ; entrée float32 `/255` puis fp16 ; recadrage x4
  aux dimensions natives ; BOX float32 vers x2 avant arrondi/quantification.
- Micro-lots géométriques déterministes entre ressources d'un même composant ; retour CPU
  routé par `(resref, frame_index)`, sans collision des numéros de frames.
- `pipeline/scripts/reboutcx_playable_p11.py` et
  `pipeline/scripts/Run-ReboutCX-PlayableCharacters-P11.ps1` : queue explicite, modèle GPU
  persistant, vérification séparée. Wrapper en mode plan par défaut.
- Kernels GPU/CPU P10 réutilisés en lecture seule, SHA épinglés avec les scripts P11 dans les
  manifestes. **Ces fichiers de production sont maintenant figés** : évolution → nouvelle version.
- Runs P8/P9/P10 préservés. Aucun catalogue dérivé, installation, release ou décision QA humaine.

## Cause et limites mesurées

| Indicateur | P10 | P11 |
|---|---:|---:|
| Pixels natifs réellement inférés | 227 852 843 | 227 852 843 |
| Pixels avec padding | 681 148 416 | 403 672 064 (−40,74 %) |
| Surface traitée / surface native | 2,989 | 1,772 |
| Micro-lots | 2 066 | 1 879 |
| Lots pleins de 86 | 1 337 | 1 561 |
| Lots contenant plusieurs ressources | 0 | 721 |
| Temps modèle, événements CUDA | 347,606 s | 236,618 s (−31,93 %) |
| Occupation du worker GPU, toutes phases | 406,498 s | 290,218 s |
| Préparation CPU, somme des durées | 256,135 s | 259,376 s |
| BOX + quantification, somme des durées | 257,360 s | 265,335 s |

Les sommes concurrentes ne s'additionnent pas au temps de session. Les attentes de préparation
comptées par ressource augmentent avec les groupes : elles incluent préchargement et recouvrement,
pas une mesure isolée de sérialisation ou de coût CPU.

P11 : modèle = 71,78 % du temps total ; worker GPU = 88,04 %. Dans ce worker : packing 21,363 s,
soumission H2D 16,643 s, attente modèle/conversion/D2H 243,535 s, crop 8,677 s.
`model_wait_and_d2h_seconds` inclut le modèle ; ce n'est pas du transfert seul.
Hors worker GPU : 39,415 s. COMPS39 vérifié à 145,1 s environ contre 142,3 s en P10 :
le gain de famille vient surtout des autres composants, pas d'une accélération uniforme.

## Validation courte et différences de pixels

- `pipeline/tests/test_reboutcx_p11.py` : 5 tests, **0,480 s**. Routage entre ressources,
  frames nulles, limites de groupes, échec de préparation/libération mémoire, publication/clone,
  vérification, refus d'écrasement, tokens entre processus Windows. Répertoires temporaires nettoyés.
- `pipeline/tests/check_reboutcx_p11_gpu.py <famille>` : **7,433 s**, 6 frames réelles,
  formes représentant 116 495 frames de la famille, micro-lots 86 ; pas 64/32/16 ; aucun run
  ni fichier temporaire. Mesure indicative courte, pas une preuve d'optimalité universelle.
  Deux petites formes sont plus lentes au pas 16 qu'au pas 32 ; 16 modifie davantage de pixels.
- Après production : contrôle des 130 SHA de manifestes P9/P10 et des helpers historiques ;
  correspondance de tous les inventaires, sources, modèles, palettes, classes, couvertures et
  hashes des guides P10/P11 ; SHA des 65 manifestes P11 égaux aux événements de vérification.
- Comparaison supplémentaire : **1,857 s**, 1 008 frames / 126 ressources / 639 953 pixels
  visibles. Transparence, classes, géométrie et représentants source identiques sur cet échantillon.
  **1 497 indices visibles changent, soit 0,2339 %** ; ce taux concerne seulement l'échantillon.
- Sur l'ensemble des manifestes, 43 871 frames ont un hash d'indices différent. La réduction du
  padding et le changement de composition des lots ne garantissent pas les mêmes pixels.
  Les sorties restent `completed-pending-human-review`, non installables.

## Priorités suivantes — proposées, non exécutées

1. Réduire allocations et copies dans le worker GPU : buffers réutilisables, transport CPU des
   crops sans copies redondantes ; mesurer packing/H2D/crop séparément. Risques : durée de vie
   des buffers, réutilisation pendant transfert, consommation mémoire et déterminisme.
2. Soumettre un lot prédéfini dès que ses ressources sont préparées, sans attendre tout le
   groupe. Conserver un plan déterministe et les réservations bornées. Réduire seulement le
   temps hors worker GPU donne un plafond idéal de **×1,136**, pas ×2.
3. Pour dépasser nettement ce plafond : accélérer aussi le modèle ou sélectionner les géométries
   au pas 16 après mesures par forme. Risques : petites formes moins efficaces et différences de
   pixels. Même la suppression idéale de tout coût hors modèle serait limitée à **×1,393**.

Protocole d'une prochaine variante : nouveaux jobs/runs ; tests CPU temporaires < 2 s ; sonde GPU
bornée à quelques secondes avec mesure des phases et comparaison classes/alpha/indices ; puis
une même famille seulement après autorisation, chronométrée jusqu'à dernière vérification.

## Artefacts vérifiables

Préfixe : `sprite/families/playable-characters/5211-elf-female-mage-low/family-runs/complete-reboutcx-p11-v1/`

- `jobs/elf-female-mage-low-p11-throughput-v1.json` : queue de 65 jobs, aucun catalogue.
- `measurements/padding-probe-v1.json` : mesures GPU et différences ciblées.
- `measurements/baseline-before-p11-v1.json` : SHA antérieurs et référence P10.
- `measurements/throughput-p11-v1.json` : mesures finales, invariants, échantillon, SHA et membres.
- Log : `sprite/.work/reboutcx-p11-production/session-1789455145335925500.jsonl`.
