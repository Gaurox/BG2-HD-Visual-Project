# Maps — recherche documentaire et vérifications ingame restantes

État : 2026-10-12. Recherche et suivi uniquement ; aucun asset ni fichier sous `releases/` modifié
par cette tâche. Preuves récupérées : [`qa-documentaire-20261011-v1.json`](qa-documentaire-20261011-v1.json).

## Résultats documentaires

| Question | Résultat vérifiable | Conséquence |
|---|---|---|
| Watcher's Keep : 24 notes sans provenance | Chat `01a072bf-d5ce-7413-b81c-4600c25678f7`, message utilisateur du 2026-09-05 à 21:18:48Z : « ok les 26 maps sont validées. les maps avec eaux devront etre revues pour l'eau comme toutes les autres maps à eau. met a jour le csv et le manifeste » ; commit `dae1d9bc` | QA décor retrouvée pour AR3001, AR3003–AR3027 ; aucun retest décor du lot demandé |
| AR3024 / AR3025 : réserve eau du 5 septembre | AR3024 : QA oil 2026-09-28 ; AR3025 : QA swamp 2026-09-25 ; manifestes `ar3024-temporal-30fps-user-qa-20260928-v1.json` / `ar3025-temporal-30fps-user-qa-20260925-v1.json` | Ancienne obligation de traitement eau levée ; AR3024 reste dans la revue distincte q |
| 30 preuves + 9 racines payload introuvables | 8 runs WTLAKE supprimés avec accord explicite le 2026-09-26 ; commande historique et résultat `REMOVED_TARGETS=36; ALL_GONE=True` retrouvés | Cause établie ; fichiers toujours absents, octets historiques non certifiables ; aucune QA ingame pour retrouver ces fichiers |
| QA WTLAKE ultérieure | `../pipeline/water/manifests/wtlake-family-user-qa-20260926-v1.json`, 14 WED | Traitement courant accepté ; anciennes références conservées comme historique |
| Pluie swamp du 25 septembre | QA du lot indique nuits/pluie contrôlées, sans détail par map ; pluie possible sur AR1100/AR2500/AR2600/AR2700 | Une confirmation nominative des anciens tests peut suffire ; pas de rejet ni défaut établi |

Les 8 runs absents (préfixe `maps/water-batches/runs/`) :

- `ar0204-ar1600-seams-wed-20260912-v1`
- `ar0300n-local-art-alpha208-20260912-v8`
- `ar0300n-native-composition-20260912-v9`
- `ar0300n-reflections-alpha160-20260912-v10`
- `ar0900-night-seams-runtime-20260912-v5`
- `wtlake-remaining-nights-20260912-v6`
- `wtlake-timeline30-q070-20260912-v2`
- `wtlake-timeline30-q070-wed-relocation-20260912-v3`

## Retour ingame du 2026-10-11 : réserves visuelles levées

L'utilisateur a vérifié AR3003, AR5200, AR2101 et AR0604 : tout est OK. Les réserves ci-dessous
sont **closes**. Les 5 premières lignes eau — AR0011, AR0046, AR0046N, AR0204, AR0300 — sont
aussi acceptées visuellement au q courant. Preuve :
[`qa-retour-ingame-20261011-v1.json`](qa-retour-ingame-20261011-v1.json).
Pluie, pause et cycle jour→nuit→jour ne sont pas précisés dans ce retour.

Pour mettre le suivi au propre, **aucune tournée exhaustive supplémentaire demandée**.
Les colonnes météo/cycle/pause ci-dessous restent des observations complémentaires facultatives.
**Dernière passe terminée le 2026-10-12** : AR0900, AR1000, AR0500 et leurs variantes
nocturnes validées en sec, pause/reprise, pluie/retour au sec et cycle jour→nuit→jour.
Preuve : [`../pipeline/water/manifests/water-final-pass-user-qa-20261012-v1.json`](../pipeline/water/manifests/water-final-pass-user-qa-20261012-v1.json).
Aucune nouvelle vérification ingame demandée pour terminer la mise au propre.
Les autres conditions non observées restent explicitement non attestées ; aucune validation
globale de toutes les maps ou autorisation release déduite.

| Map / console | Ancienne réserve | État courant |
|---|---|---|
| AR3003 — `C:MoveToArea("AR3003")` | Liseré cyan / blocs BC1 des portails | Vérifié, accepté ; réserve levée |
| AR5200 — `C:MoveToArea("AR5200")` | Portion eau hors lave | Vérifié, accepté ; réserve levée |
| AR2101 — `C:MoveToArea("AR2101")` | Contours à retoucher dans Photoshop | Vérifié, accepté ; réserve levée |
| AR0604 — `C:MoveToArea("AR0604")` | Contours du décor signalés le 19 septembre | Vérifié, accepté ; réserve levée |

## Inventaire complémentaire facultatif : q, pluie, nuit, pause

Source : `../pipeline/water/ingame-map-tracking-v1.json` ; **17 q + 17 pluie + 3 cycles nuit**
non attestés séparément. La table initiale est conservée pour retrouver les entrées et regrouper
les visites éventuelles ; les contrôles déjà vérifiés sont marqués OK. Elle inclut variantes nocturnes
et recoupements : ce n'est pas une demande de revisiter 42 maps. Les états `pending` n'annulent
aucune QA déjà acquise et ne prouvent pas un défaut actuel.

| Code | Contrôle limité |
|---|---|
| Q | Observer l'aspect **sec au q courant indiqué**, confirmer le choix ; regarder texture, mouvement et bordures. q0 = composante procédurale désactivée ; l'upscale et l'interpolation restent des états distincts. Aucun réglage ni installation nécessaires pour observer |
| P | Jour/nuit selon la WED : `C:SetWeather(1)`, jeu non en pause, ~10 s ; contrôler flaques/texture, absence de mosaïque, opacité et raccords ; retour au sec avec `C:SetWeather(0)`. q pluie courant = 0 pour toutes les lignes |
| N | Sur l'ARE **sans suffixe N**, effectuer jour→nuit→jour par repos/attente ; contrôler chargement de la WED nuit, teinte, opacité, raccords puis retour au jour. Une QA de l'image nocturne seule ne prouve pas ce cycle |
| Pause | Pause→reprise devant l'eau, vérifier les anciennes marques/tuiles. 12 zones encore sans clôture spécifique ; AR0900 clos le 12/10, traitement ultérieur accepté |

Pour une ligne nocturne, la commande téléporte dans l'ARE de base : attendre la nuit avant Q/P.
Regrouper les contrôles d'une même zone ; conserver un verdict par WED/condition réellement
observée. Le q est une valeur du registre, pas un réglage à modifier via l'INI.

| WED à observer | Console ARE | Q courant si à confirmer | P | N | Pause |
|---|---|---|---|---|---|
| AR0011 | `C:MoveToArea("AR0011")` | 0 — OK 11/10 | — | — | — |
| AR0046 | `C:MoveToArea("AR0046")` | 0 — OK 11/10 | — | — | ✓ |
| AR0046N | `C:MoveToArea("AR0046")` | 0 — OK 11/10 | — | ✓ | — |
| AR0204 | `C:MoveToArea("AR0204")` | 0 — OK 11/10 | — | — | ✓ |
| AR0300 | `C:MoveToArea("AR0300")` | 0 — OK 11/10 | ✓ | — | ✓ |
| AR0300N | `C:MoveToArea("AR0300")` | — | ✓ | ✓ | — |
| AR0404 | `C:MoveToArea("AR0404")` | 0 | — | — | — |
| AR0500 | `C:MoveToArea("AR0500")` | 0.4 — OK 12/10 | OK 12/10 | — | OK 12/10 |
| AR0500N | `C:MoveToArea("AR0500")` | 0.4 — OK 12/10 | OK 12/10 | OK 12/10 | OK 12/10 |
| AR0503 | `C:MoveToArea("AR0503")` | 0 | — | — | — |
| AR0512 | `C:MoveToArea("AR0512")` | 0 | — | — | — |
| AR0603 | `C:MoveToArea("AR0603")` | 0 | — | — | — |
| AR0900 | `C:MoveToArea("AR0900")` | 0 — OK 12/10 | OK 12/10 | — | OK 12/10 |
| AR0900N | `C:MoveToArea("AR0900")` | 0 — OK 12/10 | OK 12/10 | OK 12/10 | OK 12/10 |
| AR1000N | `C:MoveToArea("AR1000")` | 0.4 — OK 12/10 | OK 12/10 | OK 12/10 | OK 12/10 |
| AR1100 | `C:MoveToArea("AR1100")` | — | ✓ | — | ✓ |
| AR1200 | `C:MoveToArea("AR1200")` | 0 | ✓ | — | ✓ |
| AR1201 | `C:MoveToArea("AR1201")` | — | — | — | ✓ |
| AR1203 | `C:MoveToArea("AR1203")` | 0 | — | — | — |
| AR1403 | `C:MoveToArea("AR1403")` | — | — | — | ✓ |
| AR1600 | `C:MoveToArea("AR1600")` | 0 | ✓ | — | — |
| AR1604 | `C:MoveToArea("AR1604")` | 0 | — | — | — |
| AR1607 | `C:MoveToArea("AR1607")` | 0.4 | ✓ | — | ✓ |
| AR1700 | `C:MoveToArea("AR1700")` | 0 | ✓ | — | ✓ |
| AR1800 | `C:MoveToArea("AR1800")` | 0.4 | ✓ | — | ✓ |
| AR1901 | `C:MoveToArea("AR1901")` | 0 | — | — | ✓ |
| AR2000N | `C:MoveToArea("AR2000")` | — | ✓ | ✓ | — |
| AR2100 | `C:MoveToArea("AR2100")` | 0 | — | — | — |
| AR2102 | `C:MoveToArea("AR2102")` | 0 | — | — | — |
| AR2300 | `C:MoveToArea("AR2300")` | 0 | — | — | — |
| AR2500 | `C:MoveToArea("AR2500")` | — | ✓ | — | — |
| AR2600 | `C:MoveToArea("AR2600")` | — | ✓ | — | — |
| AR2700 | `C:MoveToArea("AR2700")` | — | ✓ | — | ✓ |
| AR3000 | `C:MoveToArea("AR3000")` | — | ✓ | — | — |
| AR3024 | `C:MoveToArea("AR3024")` | 0 | — | — | — |
| AR5000 | `C:MoveToArea("AR5000")` | 0 | ✓ | — | — |
| AR5200 | `C:MoveToArea("AR5200")` | — | ✓ | — | — |
| AR5203 | `C:MoveToArea("AR5203")` | — | ✓ | — | — |
| AR6300 | `C:MoveToArea("AR6300")` | — | ✓ | — | — |

### Compléments facultatifs non attestés

- Watcher's Keep : rien à demander ; validation des 26 décors retrouvée.
- Pluie AR1100/AR2500/AR2600/AR2700 : confirmer que ces quatre maps ont bien été vues sous pluie
  lors du lot swamp du 25 septembre suffit si tu t'en souviens ; sinon contrôle P ciblé.
- Anciens symptômes pause : confirmer les zones effectivement revues en pause après le dernier
  traitement permet de les clore ; sinon contrôle Pause de la liste, sans réinstaller.
- q : un verdict explicite sur les paramètres courants peut clore la revue distincte ; les
  validations générales ne sont pas remplacées par une nouvelle QA complète du décor.

### Acceptations conservées ; aucune nouvelle vérification nécessaire sans symptôme

AR3000 runtime/raccords RGB (11 octobre), AR2300 crash corrigé, AR1000N noms PVRZ corrigés,
OH6460 via tileset OH8100 ; réserves esthétiques acceptées AR1604, AR1600, AR0506/AR1003/AR1004,
AR1000/AR2000 pluie discrète, AR2100 matte courant. Détails : [`SUIVI.md`](SUIVI.md).

Classification préflight WT5000/WTLAVA-D : recherche technique/documentaire côté agent.
Performance renderer : campagne distincte, à définir seulement si demandée ; aucun nombre
supplémentaire de visites ingame imposé ici.

Retour exploitable : `WED — condition(s) réellement observée(s) — OK / réserve — emplacement`.
Exemple : `AR0900N — q0 sec, pluie, jour→nuit→jour, pause — OK`.
