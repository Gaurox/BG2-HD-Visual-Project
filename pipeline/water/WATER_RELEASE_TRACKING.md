# Eau — repères de suivi

Ce document explique où se trouve l'état final lorsqu'il faut le consulter ou l'actualiser. Il
n'impose aucune mise à jour à chaque essai, aucun audit, aucune reconstruction et aucune transaction
release. Les tentatives locales peuvent rester hors du suivi ; une sélection finale utile peut être
enregistrée une seule fois.

## Autorités disponibles

| Objet | Emplacement |
|---|---|
| État général d'une map | `areas.csv` |
| Décision QA eau exacte | `pipeline/water/manifests/*validated*.json` |
| Sélection eau courante | `pipeline/water/release-tracking-v1.json` |
| Recettes | `pipeline/water/VALIDATED_WATER_RECIPES.md` |
| Registre runtime | preuve indiquée par `runtime.registry_evidence_id` |
| Release publiée | `releases/BG2-HD-Upscale/manifests/`, séparée de ce suivi |

## Structure du JSON

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

- Validés ingame : AR0046N, AR0204, AR0300N, AR0900N, AR1000 jour, AR1200, AR1600, AR1700,
  AR1901, AR0404, AR1607, AR1800.
- Fallback q0 validé : AR2100.
- En attente ou historiquement ambiguës : AR0300 jour, AR0900 jour, AR2300, AR0046 historique.
- Eaux intérieures non qualifiées : AR0512, AR1604.
- AR1000 jour courant : v5 q0.70, 36 phases/15 Hz, blend 30 FPS, validé ingame.
- AR1000N : hors périmètre et sans état déduit du jour.

L'autorité machine reste `release-tracking-v1.json` si cette synthèse devient obsolète.

## Audit facultatif

```powershell
python -B pipeline/scripts/audit_water_release_tracking.py --json
```

Cet audit est utile avant une intégration ou pour diagnostiquer une incohérence du suivi. Il n'est
pas nécessaire pour chercher, produire ou installer une correction locale.

## Enregistrement final, si utile

Pour conserver une décision finale : référencer le manifeste QA exact, mettre à jour la cible
correspondante et garder jour/nuit/météo séparés seulement lorsqu'ils ont réellement été observés.
Cela ne touche ni payload, staging, `content.json`, TP2, archive ou manifests de release.
