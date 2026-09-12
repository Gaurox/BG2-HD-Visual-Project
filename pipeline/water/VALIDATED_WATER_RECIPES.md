# Eau BG2EE — recettes validées et guide de généralisation LLM

## 0. Autorité et portée

- Synthèse opérationnelle des QA utilisateur réalisées le 2026-09-12.
- Les manifests QA restent autorités d'état ; cette notice définit les recettes réutilisables.
- Une validation vaut seulement pour l'identité WED/variante/overlay observée. Ne jamais l'étendre
  automatiquement à une variante nuit, météo, intérieure ou à une autre famille.
- Réglage courant retenu : `q=0.70`. Le test AR0900 à `q=1.00` reste une preuve historique, pas la
  valeur à propager.
- Toute nouvelle inférence SeedVR eau : `color_correction_method=none`. Exceptions figées : map
  AR0900 jour produite en LAB ; overlay WTLAKE périodique produit en wavelet. Préserver, ne pas
  réinférer pour uniformiser.
- Ordre obligatoire : inventaire résolu → audit voie1 → réparation assets → animation overlay/WED →
  registre route2 → candidat → installation transactionnelle → QA séparée → décision.

## 1. Matrice des cas validés

| Famille | Cas probant | Traitement validé | Limite |
|---|---|---|---|
| `lake-wtlake` | AR0900 jour, AR0204, AR1600 | voie1 réparée ; WTLAKE x4 périodique ;36phases/15Hz ; blend30FPS ; matériau eau `id=1` ; q0.70 | identités exactes seulement |
| `lake-wtlake` | AR0046, AR0300, AR1200, AR1700, AR1901, AR2300 | rendu installé q0.70 accepté pendant la session | commande de zone validée ; variante WED exacte non journalisée ; créer un reçu avant promotion formelle |
| `sewage-wtsew` | AR0404 | WTSEW x4 `none`/3×3 ;6→36phases Apollo-8 ;15Hz ; blend30FPS ; matériau égouts `id=4` ; q0.70 | ne couvre aucune autre identité WTSEW |
| `sewage-wtsew` | AR2100 | WED stock + WTSEW partagé ; route2 absente ; q0 natif | n'approuve pas une future route2 AR2100 |
| `swamp-wtswam` | AR1607, AR1800 | bases réparées ; paire sèche/pluie isolée ;36phases/15Hz ; blend30FPS ; matériau marais `id=5` ; q0.70 | deux cartes seulement ; autres WTSWAM restent q0 |

Non validés par ce chantier : AR0512 et AR1604, eaux intérieures ; variantes jour/nuit non observées
séparément ; `WTLAKA-D`, `WTPOOL`, `WTOIL`, `WTLAVA-D`, `WT5000A-D`.

AR2300 : acceptation visuelle de l'eau distincte du problème de crash/incohérence de carte encore
suivi dans `pipeline/PROBLEMES_A_RESOUDRE.md`. Ne pas l'utiliser comme témoin de stabilité globale.

## 2. Contrat commun validé

### 2.1 Composition

```text
U  = RGB overlay natif animé
P  = RGB matériau procédural animé
A  = art local de la base réparée
a  = alpha natif effectif de A
U2 = mix(U, P, q)
C2 = a*A + (1-a)*U2
alpha(U2) = alpha(U)
```

- Modifier uniquement le RGB de l'overlay ciblé ; conserver alpha, `vColor`, tone, blend et ordre.
- Conserver la passe secondaire `WATER_ALPHA` et l'art local : ombres, reflets, objets, transparence.
- `q=0` doit être byte/composition-equivalent au chemin natif.
- Identité absente, divergente, non approuvée ou ressource runtime ambiguë : `q=0`, aucun heuristique.
- `q` effectif : plafond de l'entrée exacte par la configuration ; valeur validée actuelle0.70.
- Réinitialiser le dosage autour de chaque draw ; aucune fuite entre programmes, textures ou zones.

### 2.2 Animation

- Ne pas confondre mouvement procédural et cycle de tuiles.
- Cible validée :6frames source à2.5Hz → Apollo-8 →36phases à15Hz dans le WED/TIS →
  interpolation linéaire renderer à30FPS.
- Le passage36phases corrige la saccade des tuiles ; le blend30FPS corrige la transition entre phases.
- Conserver durée de cycle, indexation primaire/secondaire et vitesse WED ; vérifier les deux frames
  réellement échantillonnées ingame.
- Overlay produit depuis un contexte périodique3×3, sauf WTLAKE wavelet historique déjà validé.

### 2.3 Registre route2

Une entrée doit lier au minimum :

```text
WED + variante + hash WED + base TIS/hash/count + slot overlay + overlay TIS/hash/count
+ page PVRZ/hash/dimensions + matériau + q + variante météo éventuelle
```

- Registre versionné append-only dans un nouveau run ; génération C++ déterministe.
- Matcher les ressources possédées par le tileset et leur nom GL live ; jamais le seul nom, suffixe,
  `textureId`, taille, couleur ou alpha.
- Valider les slots WED réellement présents : AR0900 stock en possède5, pas2.
- Préserver toutes les entrées antérieures byte-identiques lors de l'ajout d'un lot.

## 3. Voie 1 par type d'asset

### 3.1 Base map TIS/PVRZ

1. Résoudre ARE/WED/TIS/PVRZ depuis KEY/BIF puis override ; ne pas partir du nom supposé.
2. Identifier cellules d'eau, primaires, secondaires, sentinelles, formats et atlas réels.
3. Déduire l'alpha cible de l'ARE/runtime : zéro utilise le défaut128 ; valeur non nulle est native.
   Ne jamais imposer128 globalement. Cas validé : AR1607=100 ; AR1800=128 ; AR0900=128.
4. Pour une primaire pleine eau opaque prouvée : convertir DXT1/PVR7 vers DXT5/PVR11 et remplacer
   seulement l'alpha du cœur256px et du padding atlas4px. Préserver le RGB.
5. Ne pas utiliser `--transparent-full-water-base` pour reconstruire le chemin natif réparé.
6. Ne pas réencoder l'alpha par IA et ne pas binariser une surface alpha100/128 via une spline127.

### 3.2 Raccords internes RGB/alpha

- Distinguer interface interne et vraie rive depuis WED + alpha stock, jamais depuis le RGB noir.
- Donneur RGB : maître secondaire x4 de la même coordonnée WED.
- Paramètres validés : bande8px x4 ; garde vraie rive1px x1 ; poids
  `[1,1,1,1,.75,.5,.25,0]` ; padding4px.
- Encoder en DXT5 puis recopier uniquement les8octets RGB des blocs autorisés ; alpha primaire natif
  inchangé.
- Alpha secondaire : corriger seulement une divergence prouvée ; blocs opaques
  `FF FF 00 00 00 00 00 00`, RGB inchangé. Ne jamais forcer tout le secondaire à255.
- Contrôler RGB/alpha bit-exacts hors masque et idempotence depuis une source scellée.

Cas mesurés validés :

| WED | Alpha central | Greffe RGB |
|---|---:|---:|
| AR0900 | 775 primaires à128 + padding |285tuiles ;94909blocs |
| AR0204 |218 primaires à128 |160tuiles ;45417blocs |
| AR1600 |166 primaires à128 |97tuiles ;31407blocs |
| AR1607 |525 primaires à100 + padding |128tuiles |
| AR1800 |7 primaires déjà128 |7tuiles |

Ces nombres sont des preuves par carte, jamais des constantes de production.

### 3.3 WED

- Toute croissance de table d'animation déplace les offsets absolus suivants.
- Relocaliser toutes les tables ; reparser murs, portes, polygones, sommets et overlays ; vérifier
  reconstruction inverse byte-exacte hors champs autorisés.
- Défauts rencontrés : AR0204 `BRIDGE01` décalé de60octets ; AR1600 douze polygones `DOOR01-06`
  non relocalisés. Le premier chargement peut crasher alors qu'un second semble fonctionner.
- Jour/nuit : produire et valider chaque WED séparément ; ne pas déduire `ARxxxxN` de `ARxxxx`.
- Resref maximum8octets. Choisir une pagination évitant `AxxxxN100+` ;4096 a corrigé les overflows
  nocturnes AR0300N/AR0500N/AR0900N. Ne pas forcer une taille de page sans calcul du préfixe.

### 3.4 Overlay TIS/PVRZ

- WTLAKE : conserver le témoin x4 périodique wavelet existant ; ne pas lancer SeedVR à nouveau si
  ses hashes sont ceux du candidat validé.
- Nouvel overlay : SeedVR2 7B INT8 x4, correction couleur `none`, contexte périodique3×3 ; contrôler
  raccords sur chaque frame avant interpolation.
- Générer TIS/page et padding cohérents ; aucune bordure noire/bleue ; boucle périodique complète.
- Une ressource partagée ne doit être remplacée que si tous ses consommateurs sont compatibles ;
  sinon créer des alias isolés et modifier uniquement les WED autorisés.

### 3.5 Variante météo WTSWAM

- Le sec `WTSWAM` et la pluie `WTSWAMR` sont deux ressources runtime distinctes.
- L'essai shader seul v3 est rejeté : la pluie palette6frames restait non traitée et produisait une
  mosaïque, même si le chemin sec était correct.
- Recette validée AR1607/AR1800 : WED overlay1 `WSWPIL` ; sec `WSWPIL/WWPIL00` ; pluie alternative
  `WSWPILR/WWPILR00` ; x4 `none`/3×3 ;36phases ; ressources globales WTSWAM/R inchangées.
- Le runtime doit inspecter les ressources primaire et alternative (`wrapper+0x20`) et inscrire deux
  identités par carte. Ne pas déduire la pluie par suffixe sans vérifier TIS/page/hash.
- QA obligatoire : sec → pluie → sec. Une capture sèche ne valide pas la paire.

## 4. Matériaux validés

| Mode | Famille | Paramètres spécifiques | q validé |
|---:|---|---|---:|
|1|WTLAKE|matériau lac existant, teinte issue de l'art, écume0.75, spéculaire1.00|0.70|
|4|WTSEW|deep `(0.10,0.075,0.03)` ; shallow `(0.24,0.19,0.075)` ; foam `(0.34,0.29,0.12)` ; foam0.18 ; spec0.08|0.70 AR0404|
|5|WTSWAM|deep `(0.055,0.12,0.10)` ; shallow `(0.30,0.48,0.37)` ; foam `(0.30,0.40,0.31)` ; foam0.25 ; spec0.40|0.70 AR1607/AR1800|

- Valeurs RGB converties sRGB→linéaire dans `fpSEAM.glsl`.
- Ne pas appliquer le mode1 aux égouts/marais ; ne pas réutiliser4/5 pour huile, goo ou lave.
- Lave : alpha128 eau interdit ; branche émissive et composition dédiées requises.
- Intérieur : AR0512/AR1604 reportées. Classer comme sous-famille/environnement distinct avant QA ;
  AR0204 prouve seulement qu'un cas sombre peut être validé à0.70 après réparation de l'art local.

## 5. Procédure pour une carte restante

1. Créer une ligne par `WED × variante × slot × overlay × météo` depuis les ressources résolues.
2. Classer famille et environnement ; famille inconnue = bloquée, q0.
3. Comparer à un cas probant : format, alpha ARE, populations WED, overlay, météo, art local.
4. Auditer alpha central/padding, RGB internes, alpha secondaire, vraie rive et périodicité.
5. Créer un run neuf voie1 ; réparer uniquement les divergences prouvées.
6. Produire/réutiliser l'overlay selon §3.4 ; inclure toutes les alternatives météo.
7. Étendre WED à36phases/15Hz avec relocation complète ; renderer30FPS.
8. Ajouter les identités exactes au registre ; conserver q0 pour tout écart.
9. Assembler candidat et manifests ; aucune réécriture de run, reçu ou preuve antérieure.
10. Préparer les tests ciblés selon `AGENTS.md`; exécuter seulement après choix utilisateur.
11. Installer jeu et InfinityLoader fermés, par lot transactionnel, après autorisation.
12. QA ingame séparée ; état final explicite : `validated-installed`, `candidate-installable-pending-qa`,
    `already-conform` ou `blocked` avec cause et correctif.

## 6. QA minimale par identité

```lua
C:MoveToArea("ARxxxx")
```

- Démarrage frais via InfinityLoader ; sauvegarde n'ayant jamais visité la zone si nécessaire.
- Pause puis mouvement ; zoom/pan ; cycle complet ; chargement/rechargement et sortie/retour.
- Art local, ombres, profondeur, transparence, teinte familiale, raccords, padding, bords noirs/bleus.
- Fluidité du mouvement procédural et des tuiles : deux validations distinctes.
- Jour/nuit séparés ; sec/pluie/sec pour météo ; portes/bridges/objets après WED relocalisé.
- Diagnostic temporaire : identité exacte, `overlay=true`, `q=0.7`, `temporal=true`, bonne page et
  `weather=true` pour pluie. Désactiver les diagnostics dans la configuration finale.
- Une capture fixe, un hash, une compilation ou un log ne prouvent pas seuls la QA visuelle.

## 7. Échecs à ne pas reproduire

| Échec | Cause | Règle |
|---|---|---|
| art local disparu / centre immobile | alpha0/255 ou passe secondaire supprimée | restaurer alpha natif avant route2 |
| traits noirs/bleus | RGB primaire contaminé ou padding incohérent | greffe bornée depuis secondaire même coordonnée |
| tuiles encore saccadées | seul mouvement procédural fluide |36phases15Hz + blend30FPS |
| mosaïque au début de pluie | seule ressource sèche traitée | produire et router la ressource alternative |
| route2 invisible | identité WED/TIS/page/GL non reconnue | diagnostiquer le matcher ; ne pas augmenter q |
| crash intermittent | offsets WED ou resref>8 | relocation structurelle + pagination bornée |
| autre carte modifiée par effet de bord | overlay partagé remplacé globalement | alias isolé + WED/registre exacts |
| eau intérieure artificielle | recette lac propagée sans qualification | branche environnementale et QA dédiée |

## 8. Références courantes

- Suivi vers release : `release-tracking-v1.json` ; procédure : `WATER_RELEASE_TRACKING.md`.
- Lac : `manifests/ar0204-ar1600-validated-installed-20260912-v1.json`.
- Égouts : `manifests/wtsew-ar0404-ar2100-validated-20260912-v1.json`.
- Marais sec/pluie : `manifests/wtswam-ar1607-ar1800-validated-20260912-v1.json`.
- Installation marais v4 : `manifests/wtswam-rain-installed-20260912-v4.json`.
- Politique familles : `family-policy-v1.json` ; voie1 : `route1-policy-v1.json`.
- Inventaire : `manifests/liquid-target-matrix-v1.json`.
- Détails voie1 : `../WATER_REPAIR_RUNBOOK.md` ; moteur : `../WATER_ROUTE2_EXPERIMENT_RUNBOOK.md`.
