# Eau — repères de suivi

Ce document explique où se trouve l'état final lorsqu'il faut le consulter ou l'actualiser. Il
n'impose aucune mise à jour à chaque essai, aucun audit, aucune reconstruction et aucune transaction
release. Les tentatives locales peuvent rester hors du suivi ; une sélection finale utile peut être
enregistrée une seule fois.

## Autorités disponibles

| Objet | Emplacement |
|---|---|
| État général d'une map | `areas.csv` |
| File exhaustive de QA ingame par WED/variante | `pipeline/water/ingame-map-tracking-v1.json` |
| Décision QA eau exacte | `pipeline/water/manifests/*validated*.json` |
| Sélection eau courante | `pipeline/water/release-tracking-v1.json` |
| Recettes | `pipeline/water/VALIDATED_WATER_RECIPES.md` |
| Registre runtime | preuve indiquée par `runtime.registry_evidence_id` |
| Release publiée | `releases/BG2-HD-Upscale/manifests/`, séparée de ce suivi |

## Structure du JSON

`ingame-map-tracking-v1.json` :

- `inventory` : matrice source hashée, 67 WED, 98 overlays et liste explicite des 7 nuits.
- `workflow.active_map_id` : au plus une carte active ; `null` entre deux sessions.
- `maps[]` : une entrée par WED/variante ; tous ses slots liquides restent groupés.
- `work_state` : `queued`, `active`, `blocked` ou `done`.
- `preparation_state`, `qa_state`, `installation_state` : états séparés, jamais déduits l'un de
  l'autre.
- `overlays[].candidate_state` et `route2_strength` : photographie de la matrice d'inventaire ; la
  sélection courante reste référencée par `release_target_ids`.

`release-tracking-v1.json` :

- `evidence[]` : références et hashes des preuves retenues.
- `artifact_sets[]` : groupes d'artefacts candidats.
- `runtime` : commit, registre, DLL, INI, shaders et éventuels bloqueurs connus.
- `targets[]` : WED/variante, famille, overlay, matériau, q, QA et installation.
- `release_state` : état d'intégration ; aucune valeur n'est déduite de la seule QA.

## États QA

| État | Sens |
|---|---|
| `validated-ingame` | identité exacte acceptée ingame |
| `validated-current-fallback` | rendu courant q0 accepté |
| `session-accepted-variant-unresolved` | retour positif sans variante exacte identifiée |
| `pending-ingame` | candidat sans verdict ingame final |
| `blocked-family-qa` | famille ou environnement non qualifié |

## État utile au 2026-09-12

- Validés ingame : AR0046N, AR0204, AR0300N, AR0900N, AR1000 jour, AR1000N sec, AR1200, AR1600, AR1700,
  AR1901, AR0404, AR1607, AR1800.
- Fallback q0 validé : AR2100.
- En attente ou historiquement ambiguës : AR0300 jour, AR0900 jour, AR2300, AR0046 historique.
- Eaux intérieures non qualifiées : AR0512, AR1604.
- AR1000 jour courant : v5 q0.70, 36 phases/15 Hz, blend 30 FPS, validé ingame.
- AR1000N courant : WSWPIL sec q0.70, 36 phases/15 Hz, blend 30 FPS, validé ingame ; animation
  discrète acceptée. WSWPILR pluie est installé mais non observé séparément.

L'autorité machine reste `release-tracking-v1.json` si cette synthèse devient obsolète.

## Audit facultatif

```powershell
python -B pipeline/scripts/audit_water_ingame_tracking.py --json
python -B pipeline/scripts/audit_water_release_tracking.py --json
```

Le premier audit exige l'égalité exacte avec la matrice liquide, vérifie les variantes nuit et les
overlays multi-slots, calcule les compteurs et impose l'unicité de la carte active. Le second contrôle les sélections
finales. Ils ne sont pas nécessaires pour chercher ou produire une correction locale.

## Enregistrement final, si utile

Pour conserver une décision finale : référencer le manifeste QA exact, mettre à jour la cible
correspondante et garder jour/nuit/météo séparés seulement lorsqu'ils ont réellement été observés.
Cela ne touche ni payload, staging, `content.json`, TP2, archive ou manifests de release.
