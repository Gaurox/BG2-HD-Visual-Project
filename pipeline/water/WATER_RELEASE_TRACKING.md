# Eau — suivi des correctifs vers release

## Autorités

| Objet | Autorité |
|---|---|
| État map jour/nuit, run/build retenu | `areas.csv` |
| Décision QA exacte | `pipeline/water/manifests/*validated*.json` immuable |
| Sélection eau courante | `pipeline/water/release-tracking-v1.json` |
| Recettes | `pipeline/water/VALIDATED_WATER_RECIPES.md` |
| Registre runtime | evidence désignée par `runtime.registry_evidence_id` du suivi ; préserver toutes ses identités |
| Release publiée | `releases/BG2-HD-Upscale/manifests/*`, hors périmètre avant autorisation distincte |

`release-tracking-v1.json` prépare la release ; il ne l'approuve pas. Il référence par SHA-256 les
manifests, runs et candidats sans recopier leurs inventaires. `content.json`, payload, staging,
TP2, archives et manifests release restent inchangés.

## Structure

- `evidence[]` : fichier immuable + rôle + SHA-256.
- `artifact_sets[]` : racines de payload candidates et preuves associées.
- `runtime` : commit moteur, registre final, DLL, INI, shaders, textures et bloqueurs release.
- `targets[]` : une entrée par WED/variante ; famille, environnement, overlay, matériau, q,
  artefacts, QA, installation, bloqueurs.
- `release_state` reste `not-evaluated` jusqu'à la transaction release explicitement autorisée.
- Le suivi courant contient18 identités :14 WTLAKE,2 WTSEW,2 WTSWAM.

## Audit lecture seule

```powershell
python -B pipeline/scripts/audit_water_release_tracking.py
python -B pipeline/scripts/audit_water_release_tracking.py --json
python -B pipeline/scripts/audit_water_release_tracking.py --release-gate
```

- Audit normal : structure, références, hashes, racines candidates, commit moteur, cohérence
  `areas.csv`, famille/matériau/q. Les bloqueurs attendus n'échouent pas l'intégrité.
- `--release-gate` : code non nul tant qu'une QA, un correctif ou le runtime final manque. Un succès
  prouve seulement la préparation technique ; il ne donne aucune autorisation release. Aucun écrit.

## Mise à jour après chaque lot

1. Créer run, candidat, manifeste d'installation et reçu neufs ; ne jamais réécrire l'historique.
2. Après QA explicite, créer un manifeste QA immuable par carte/variante/famille.
3. Mettre `areas.csv` à `validated-installed` uniquement pour la variante effectivement validée.
4. Ajouter dans `evidence[]` les nouveaux manifests avec leur SHA-256.
5. Ajouter/mettre à jour un `artifact_set`; remplacer la sélection courante, conserver la preuve
   supersédée référencée par les anciens manifests.
6. Ajouter/mettre à jour chaque `target`; aucune propagation jour→nuit, sec→pluie ou famille→famille.
   Toute map jour examinée inclut sa nuit ou une preuve d'absence ; checklist §0.1 du
   `../WATER_REPAIR_RUNBOOK.md`. Une validation nuit ne prouve pas le cycle jour→nuit→jour.
7. À chaque nouveau build moteur, remplacer atomiquement `runtime.source_commit`, registre, DLL,
   INI et shaders. Nouveau runtime sans QA : `installed-pending-ingame-qa`. Ne pas hériter de la QA
   de sa DLL parente. Commit non créé : préciser baseline et snapshot source hashé dans les preuves.
   Ajouter un bloqueur si diagnostics actifs ou tests absents.
8. Exécuter l'audit normal ; préparer les tests ciblés selon `AGENTS.md`, sans les lancer sans choix.

Commande SHA-256 :

```powershell
Get-FileHash -Algorithm SHA256 <manifest-ou-candidat>
```

Règles : chemin relatif workspace ; SHA uppercase64 ; ID stable ; aucun chemin `override` live comme
source release ; aucune preuve déduite d'un fichier présent.

## États QA utilisables

| État | Sens | Éligible futur |
|---|---|---|
| `validated-ingame` | identité exacte validée, preuve QA référencée | oui après autres gates |
| `validated-current-fallback` | état q0 observé ; aucune route2 approuvée | seulement comme fallback |
| `session-accepted-variant-unresolved` | retour positif sans WED jour/nuit identifié | non ; reçu spécifique requis |
| `pending-ingame` | candidat installé/non validé | non |
| `blocked-family-qa` | matériau/environnement non qualifié | non |

## État courant — audit du 2026-09-12

| État eau exact | Identités |
|---|---|
| `validated-ingame` | AR0046N, AR0204, AR0300N, AR0900N, AR1200, AR1600, AR1700, AR1901, AR0404, AR1607, AR1800 |
| `validated-current-fallback` | AR2100 (`q=0`, aucune route2 approuvée) |
| `pending-ingame` | AR0300 jour, AR0900 jour, AR2300 |
| `session-accepted-variant-unresolved` | AR0046 jour ou nuit observé historiquement ; AR0046N possède désormais sa QA exacte séparée |
| `blocked-family-qa` | AR0512, AR1604 (eaux intérieures) |

Total :18identités suivies ;11validées route2,1fallback validé,3en attente,1non résolue,
2bloquées. Toutes sont installées ; installation ≠ QA. Autorité machine :
`release-tracking-v1.json`. `areas.csv` garde la QA générale des maps ; le présent suivi reste plus
strict pour chaque traitement eau/WED après modification. Aucun état release n'est déduit.
Runtime installé v10 : source exacte commit `98cba84fa59e8647c9b4a816ca69e47dbaa3cfa8`, registre
`ar0300n-reflections-alpha160-registry-v10`, DLL SHA256 `250A5BC2872CD91DBFD4DEFDBC898CFAFAB010AC3033E27820209F354447AD59`.

## État initial enregistré — historique

- Formalisés : AR0204, AR0900 jour, AR1600, AR0404, AR1607, AR1800.
- Fallback formalisé : AR2100 q0.
- Retours positifs à préciser : AR0046 et AR0300, variante observée inconnue.
- Retours positifs uniques : AR1200, AR1700, AR1901 ; AR2300 garde un blocage map indépendant.
- En attente nuit à l'ouverture du chantier : AR0046N, AR0300N, AR0900N ; toutes trois sont
  maintenant validées sur leurs candidats exacts, sans validation implicite des cycles/météos.
- Bloqués eaux intérieures : AR0512, AR1604.
- Runtime développement validé ingame : commit `d37c7899`, registre19, q0.70. Non prêt release :
  diagnostics INI actifs, bundle final non reconstruit, tests/lifecycle non autorisés.

## Transaction release future

Mise à jour 2026-09-12 : AR0900N v5 et AR0046N v7 validés ingame. AR0300N v8 alpha208 est rejeté :
rupture de composition avec les secondaires128. V9 installé restaure l'alpha natif128 et conserve
l'art original nuit, conformément au choix utilisateur ; l'ombre solaire attendue est absente de
la source nuit, son reflet nocturne est présent. Preuve :
`manifests/ar0300n-native-composition-installed-20260912-v9.json` (repli conservé).
Courant : v10 validé installé sur AR0300N, opacité160 appariée aux892 centres et374 secondaires,
RGB nuit et q0.70 inchangés. QA : `manifests/ar0300n-reflections-alpha160-validated-20260912-v10.json`.
Cycle jour→nuit→jour, météo et autres maps avec cette DLL non attestés ; aucun état propagé.
Le registre compilé et les reçus d'installation gardent leur état historique ; la QA courante est
portée par ce nouveau manifeste. Les états initiaux ci-dessus restent historiques.

Après autorisation release distincte seulement :

1. Exiger audit normal valide puis fermer les bloqueurs techniques de `--release-gate`.
2. Convertir les cibles `validated-ingame` en sources map du générateur, cohérentes avec `areas.csv`.
3. Reporter les overlays/alias sélectionnés dans `release/.../overlay-sources.json` avec hashes.
4. Construire un unique bundle renderer final depuis le commit/registre sélectionnés, diagnosticsOFF ;
   aligner `renderer-bundle.json` et `runtime-compatibility.json`.
5. Allouer les composants permanents et dépendances map→overlay→core.
6. Régénérer le tier manifest uniquement : `content.json`, composants, métadonnées, TP2.
7. Tests, staging, packaging et archive restent des accords séparés selon le workflow release.

Le suivi eau est une source d'intégration à adapter au générateur ; il ne doit jamais être copié
tel quel dans `content.json` ni remplacer `overlay-sources.json`.
