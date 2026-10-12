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
| QA eau référencée + anciennes sélections | `pipeline/water/release-tracking-v1.json` ; portée dans `defaults.tracking_scope` |
| Réserves / incertitudes courantes | `maps/SUIVI.md` |
| Recherche documentaire / vérifications ingame restantes | `maps/qa-documentaire-20261011-v1.json`, `maps/VERIFICATIONS_INGAME.md` |
| Recettes | `pipeline/water/VALIDATED_WATER_RECIPES.md` |
| Registre runtime legacy | preuve indiquée par `runtime.registry_evidence_id` |
| Registre runtime courant | `pipeline/water/route2-registry-current.json` |
| Sélections release locale courantes | `releases/BG2-HD-Upscale/manifests/map-release-candidates.csv`, `map-release-assemblies.json` |
| Paquet / statut public | `releases/BG2-HD-Upscale/manifests/release.json` ; local buildable ≠ publié |

Finalisation maps du 2026-10-12 : 399 variantes, 63 WED liquides, 188 identités runtime
jour/pluie ; sources finales figées, QA acquises conservées. Recette :
`pipeline/recipes/maps-release-finalization-20261012-v1/README.md`.
`release-tracking-v1.json` reste une photographie legacy ; ses artefacts manquants et anciennes
sélections ne sont pas réutilisés comme sources du paquet courant.

## Structure du JSON

`ingame-map-tracking-v1.json` :

- `inventory` : matrice source hashée, 67 WED, 98 overlays et liste explicite des 7 nuits.
- `workflow.active_map_id` : au plus une carte active ; `null` entre deux sessions.
- `maps[]` : une entrée par WED/variante ; tous ses slots liquides restent groupés.
- `work_state` : `queued`, `active`, `blocked` ou `done`.
- `preparation_state`, `qa_state`, `installation_state` : états séparés, jamais déduits l'un de
  l'autre.
- `overlays[].candidate_state` et `route2_strength` : photographie source de la matrice
  d'inventaire, pas statut QA courant. `release_target_ids` relie les anciennes sélections ;
  `qa_evidence_ids` référence les décisions finales du traitement.

`release-tracking-v1.json` :

- `evidence[]` : références/hashes historiques et décisions finales existantes ; celles absentes
  localement sont explicitement listées dans `defaults.tracking_scope.missing_legacy_evidence_ids`.
- `artifact_sets[]`, paramètres overlay/q des `targets[]`, fichiers du `runtime` : photographie
  legacy du 2026-09-12 ; ne pas l'utiliser pour certifier les octets actuellement installés.
- `targets[].qa_state/qa_evidence_id` : dernière acceptation du **traitement** pour la WED ;
  ne revalide pas les payloads legacy. Périmètre exact dans le manifeste référencé.
- `defaults.tracking_scope` : contrat de lecture, pointeurs courants et racines legacy absentes.
- `release_state`, `release_boundary` : anciens états d'intégration conservés ; aucune
  promotion, annulation ni approbation release déduite de la réconciliation QA.

## États QA

| État | Sens |
|---|---|
| `validated-ingame` | identité exacte acceptée ingame |
| `validated-current-fallback` | rendu courant q0 accepté |
| `session-accepted-variant-unresolved` | retour positif sans variante exacte identifiée |
| `pending-ingame` | candidat sans verdict ingame final |
| `blocked-family-qa` | famille ou environnement non qualifié |

## Réconciliation au 2026-10-12

- 63 WED à liquide actif : traitement accepté ; 4 sans liquide actif : baseline conservée.
  Les 63 WED ont des références QA dans `ingame-map-tracking-v1.json`.
- Lot WTLAKE : 14 WED explicitement acceptées 2026-09-26 ; AR0046/AR0300/AR0900/AR0512/AR1604/AR2300
  ne sont plus ambiguës ou bloquées pour le traitement eau. Preuve :
  `manifests/wtlake-family-user-qa-20260926-v1.json` ; réserve esthétique acceptée AR1604.
- AR3000 : runtime/raccords RGB acceptés 2026-10-11 ; météo non spécifiée.
- Revue distincte : q **46 validés / 17 pending**, pluie **7 validés / 17 pending**,
  nuit **3 validés / 3 pending**. Les acceptations génériques ne clôturent pas météo/cycle jour→nuit→jour.
- Passe finale AR0900/AR1000/AR0500 du 2026-10-12 : sec, pause, pluie et cycle jour→nuit→jour
  acceptés sur les 6 WED ; preuve `pipeline/water/manifests/water-final-pass-user-qa-20261012-v1.json`.
  AR1000N pluie attestée ; AR1000/AR2000 pluie discrète conservée. Compléments restants facultatifs.
- Anciennes sélections : **30 preuves + 9 racines payload dans 8 runs WTLAKE** supprimés lors du
  ménage autorisé du 2026-09-26 ; provenance retrouvée dans
  `maps/qa-documentaire-20261011-v1.json`. Fichiers toujours absents ; cause établie, octets
  historiques non certifiables. Aucune QA ingame à refaire pour ces lacunes.
- Réserves ouvertes et réserves esthétiques acceptées : [`../../maps/SUIVI.md`](../../maps/SUIVI.md).

## Audit facultatif

```powershell
python -B pipeline/scripts/audit_water_ingame_tracking.py --json
python -B pipeline/scripts/audit_water_release_tracking.py --json
```

Le premier vérifie l'inventaire liquide, les références et les états de revue. Le second contrôle
les fichiers historiques référencés ; il continue de signaler les **39 lacunes locales déclarées**.
Ne pas supprimer ces références ni inventer des hashes pour obtenir un résultat vert. Aucun audit
n'est nécessaire pour chercher ou produire une correction locale.

## Enregistrement final, si utile

Pour conserver une décision finale : référencer le manifeste QA exact, mettre à jour la cible
correspondante et garder jour/nuit/météo séparés seulement lorsqu'ils ont réellement été observés.
Cela ne touche ni payload, staging, `content.json`, TP2, archive ou manifests de release.
