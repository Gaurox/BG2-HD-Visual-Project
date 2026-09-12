# Eau — voie 2 : état validé et extension LLM

## 0. Statut et portée

- Implémentation AR0900 jour livrée par `a7397a52` (`feat(engine): add scoped procedural water route`).
- Validation utilisateur le 2026-09-12 : **dosage `1.00` retenu**, jugé nettement plus beau grâce
  au mouvement procédural. Dosages comparés : `0`, `0.15`, `0.30`, `0.50`, `1.00`.
- Portée actuellement codée : **AR0900 jour, overlay1 WTLAKE, page WLAKE00 uniquement**.
- Hors cette identité : dosage forcé à0 ; rendu natif/voie1. Nuit, autres zones, overlays et familles
  non qualifiés.
- Autorité de preuve :
  `engine/InfinityEngine-Enhancer/source-patchee/docs/validation/water-route2-ar0900-20260912.md`.
- Voie1 requise en amont pour les assets défectueux :
  [`WATER_REPAIR_RUNBOOK.md`](WATER_REPAIR_RUNBOOK.md). La voie2 ne corrige ni RGB noircis,
  alpha central erroné, faux contours, padding, ni frames d'overlay non périodiques.
- Aucun rebuild map/overlay, WED/ARE, coordonnées, sauvegarde ou release dans l'implémentation voie2.
- Cette notice documente le résultat et la méthode d'extension. Elle n'autorise ni généralisation,
  installation, tests, projections, packaging ni promotion release.

Lectures minimales avant reprise : `AGENTS.md`, `README.md`, `pipeline/README.md`,
`docs/DECISIONS.md`, `pipeline/PROBLEMES_A_RESOUDRE.md`, notice voie1, puis
`engine/InfinityEngine-Enhancer/source-patchee/{AGENTS.md,README.md}` et les transactions renderer/
shader-suite du moteur.

## 1. Référence AR0900 conservée

| Objet | Valeur validée |
|---|---|
| Zone/variante | AR0900 jour ; WED stock80×60 ;5slots, seuls0/1 renseignés |
| Base | AR0900.TIS,5752tuiles |
| Overlay ciblé | WTLAKE.TIS,6frames ; WLAKE00.PVRZ2048×2048 |
| Build map voie1 | `maps/AR0900/runs/voie1-water-rgb-seams-x4-jour-20260912/05_build/x4-alpha128-water-seams-repaired` |
| Ensemble map | `59DBB058B087D1AD9C1D06A295E7A774D2DF1C6DBA182A2EE8912C467D30E4E8` |
| Reçu map | `backups/maps/AR0900-20260911T235034477666Z-b986b035/install-backup.json` |
| Build overlay | `maps/technical-overlays/WTLAKE/runs/seedvr2-7b-int8-wavelet-periodic-x4/04_build_x4` |
| WTLAKE.TIS | `1743A734B7E94FA60AB927B6615933DBDF7B5BF998019C66428413801BB62EE1` |
| WLAKE00.PVRZ | `BCC99E2E6E2881E9D216687044A661C68EC42D0EEC1A4103C341894BB5E2FA10` |
| Binaire jeu | BG2EE2.7.3.0, `BaldurReal.exe` SHA256 `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57` |
| Commit voie1/doc initiale | `f1cad546`, `9fe13f01` |
| Commit voie2 | `a7397a52` |

Ne jamais restaurer le reçu map ci-dessus pour annuler la voie2 : son état `before` est l'ancien
candidat voie1 avec traits noirs. La voie2 ne modifie aucun fichier map ; restaurer uniquement ses
transactions renderer/shader.

Textures procédurales attendues sous `config://bg2ee_game_root/iee-textures/` :

| Fichier | SHA256 |
|---|---|
| `iee_water_normal.rgba` | `BBEBC635D68084D757176F5522161310AE7C1DDCA330438EB1743D96D8EFE551` |
| `iee_water_dudv.rgba` | `3F9FBF6E982CBECEBE70386F2DF8152A85D61651FD2965D9C17CC70807BBD83E` |
| `iee_water_foam.rgba` | `F9FB4383F83BEDD94A187EC2118FFE91879AEE911C0E96E05CC3C882B309DFF6` |

Le loader préfère `.dds` à `.rgba`. Un DDS présent mais invalide bloque le chargement sans repli
RGBA : inventorier les deux extensions avant diagnostic.

## 2. Configuration retenue

Réglage visuel validé pour AR0900 jour :

```ini
[Shaders]
EnableWaterEffect = true
EnableWaterOverlayRoute2 = true
WaterOverlayStrength = 1.00
EnableDebugHotkeys = false
```

- `WaterOverlayStrength=1.00` : RGB de l'underlay WTLAKE remplacé entièrement par le matériau
  procédural animé. L'art local de la map reste composé au-dessus avec ses alphas natifs réparés.
- `EnableWaterEffect=true` est nécessaire à la production de `P`; route2 empêche l'ancien effet
  destructif de s'appliquer aux draws non ciblés.
- Valeurs source par défaut : route2`false`, strength`0`. Valeur non finie/hors `[0,1]` →0.
- `EnableTilePageDiagnostics=true` a servi aux essais. Réglage retenu hors diagnostic :
  `EnableTilePageDiagnostics=false` pour éviter les logs. L'activer temporairement uniquement pour
  prouver un nouveau ciblage.
- Ne pas activer F10 pendant la QA ; le hash d'une INI de QA avec diagnosticsON n'est pas le hash de
  l'INI finale diagnosticsOFF.

Historique de décision :

| q | Résultat |
|---:|---|
|0|Identique voie1 après correction du routage ; gate neutre validée|
|0.15|Différence légère ; peut-être meilleure|
|0.30|Mouvement plus perceptible ; gain statique faible|
|0.50|Diagnostic intermédiaire, non retenu|
|1.00|Préférence utilisateur nette ; **valeur retenue AR0900 jour**|

## 3. Contrat de composition

```text
U = RGB overlay natif animé WTLAKE
P = RGB matériau procédural animé
A = art local map réparé par voie1
a = alpha effectif natif de A
U2 = mix(U, P, q)
C2 = a*A + (1-a)*U2
alpha(U2) = alpha(U)
q=0 => C2 identique voie1
q=1 => U2=P ; A, a et ordre des passes inchangés
```

Invariants obligatoires :

- modifier uniquement le RGB de l'overlay animé identifié ; jamais son alpha ;
- conserver `vColor`, tone, facteurs de blend et ordre natifs ;
- ne pas relever `texColor.a` en route2 ;
- ne pas annuler la passe secondaire `WATER_ALPHA` en route2 ;
- ne pas exécuter l'ancien remplacement procédural en plus de route2 ;
- dosage par draw, initialisé/remis à0 autour de chaque `glDrawArrays` ; aucune fuite de programme,
  texture, zone ou contexte GL ;
- non-éligible/erreur/identité inconnue → dosage0 et rendu natif ; aucun fallback heuristique.

Trace AR0900 : blend actif `SRC_ALPHA(770) / ONE_MINUS_SRC_ALPHA(771)`, framebuffer sRGB0.
Le matériau `P` est calculé en linéaire puis encodé ; `mix(U,P,q)` est réalisé en RGB stocké avant
les tone/blend existants. Le chemin q0 contourne le calcul et toute conversion colorimétrique.

## 4. Implémentation livrée

| Fichier | Rôle |
|---|---|
| `ENGINE/assets/override/fpSEAM.glsl` | Uniforms route2/strength ; calcul `P` ; mix RGB seulement ; conservation alpha/WATER_ALPHA |
| `ENGINE/src/iee/core/config.{h,cpp}` | Clés INI, sérialisation, validation `[0,1]`, defaults fail-closed |
| `ENGINE/src/iee/core/water_overlay_policy.h` | Identité AR0900/WTLAKE stricte et layout WED |
| `ENGINE/src/iee/shader_uniform_bridge.{h,cpp}` | Uniform global `uIeeWaterRoute2` |
| `ENGINE/src/iee/shader_probe.cpp` | Détection draw `vpDraw/fpSEAM`, sampler réel, uniform strength par draw, reset RAII, logs bornés |
| `ENGINE/src/iee/area_state.{h,cpp}` | Revalidation WED/base/overlay/page live et correspondance texture moteur→GL |
| `ENGINE/src/iee/hooks.{h,cpp}` | Table textures native manifestée, validation signatures/mémoire, pont de sélection |
| `ENGINE/tests/iee_tests.cpp` | Policy/layout/dosage/defaults/INI |
| `pipeline/tests/test_water_route2_shader_contract.py` | Gardes source ; ne remplace pas compilation GLSL/QA ingame |

`ENGINE = engine/InfinityEngine-Enhancer/source-patchee`.

### Sélection exacte actuelle

À chaque draw `vpDraw/fpSEAM` :

1. lire le sampler `uTex` et la texture2D liée ; restaurer l'unité active ;
2. exiger zone active stable, WED/runtime `AR0900`, base80×60 ;
3. accepter2–5slots WED, base`AR0900`, overlay1`WTLAKE`, slots2+ sans resref ni couverture ;
4. exiger base runtime5752tuiles, overlay runtime6tuiles ; refuser base`AR0900N` ;
5. valider chaque wrapper WTLAKE : index TIS, entrée, page `WLAKE00`, dimensions2048² ;
6. `CResPVR::texture` est un **slot moteur**, pas un nomGL. Résoudre le nomGL live depuis la table
   manifestée :512descripteurs, stride0x28, nom+0, largeur+4, hauteur+8, deletePending+0x0D ;
7. comparer ce nomGL au sampler courant ; recontrôler zone/WED avant succès ;
8. exiger `cellMode=1` dans le fragment ; appliquer q configuré ; sinon q0.

Validation table native indépendante des options sprites/occlusion : section et mémoireRW non
exécutables, trois signatures/référencesRIP, sélecteur secondaire+0x24. Échec → route2 inactive.
Ne pas appeler `DrawBindTexture` pendant le draw et ne pas conserver un nomGL en cache.

### Deux erreurs corrigées pendant q0

| Erreur | Symptôme | Correction |
|---|---|---|
| `overlays.size()!=2` | AR0900 stock possède5slots ; aucun draw reconnu | Accepter2–5, exiger slots2+ vides/sans couverture |
| `CResPVR::texture == GL name` | Slot moteur22, nomGL25 ; `overlay=false` | Résolution live par descripteur natif validé |

Ne jamais réintroduire ces simplifications dans une généralisation.

## 5. Preuve et candidat retenu

Gate q0-r2 observée :

```text
WATER_ROUTE2 native texture table validated=true
WATER_ROUTE2 identity slots=5 baseTiles=5752 overlayTiles=6 page=WLAKE00 engineSlot=22 glName=25
WATER_ROUTE2 draw program=24 texture=25 size=2048x2048 overlay=true q=0 blend=1/770/771 srgb=0
```

Les pages map4096² ont été tracées `overlay=false q=0`. Neutralité q0 confirmée ingame.
À15%, trace `overlay=true q=0.15`; à100%, validation visuelle utilisateur retenue.

| Objet | Valeur |
|---|---|
| Candidat q1 local | `build/water-route2-ar0900-20260912-q100/renderer/` |
| DLL | `5AA0C41F9B1ED75FD170A15668A56908AA77153EC1939DADE4C139AE510B84D9` |
| INI q1 diagnosticsON | `7860F28D78DF284CD402CC89F2CCA440FF93C44F18FE5956443521BFE4FCD4B0` |
| fpSEAM | `CDE3FF62046DAB3F9DDE1C85E9C5C57EB51FE7F229074F4B15339D3C4425B00D` |
| Reçu renderer q1 | `backups/renderer/20260912T010634675930Z-92bbee1b/renderer-install-receipt.json` |
| Reçu shaders initial | `backups/shader-suite/20260912T003316103827Z-b4481933/shader-install-receipt.json` |
| Build DLL | `build/iee-water-route2-ar0900-20260912-vs2019`, Release, VS2019, BUILD_TESTING=OFF |

- Le dossier `build/` et les reçus sont locaux/ignorés : vérifier leur présence ; la preuve Git
  durable est le document de validation.
- Aucun unittest/CTest n'a été exécuté : choix utilisateur « aucun test ». La DLL Release a compilé ;
  installation/preflight/verify et QA ingame ont réussi. Ne pas transformer cela en succès de tests.
- Les27fichiers AR0900, WTLAKE.TIS, WLAKE00.PVRZ, BaldurReal et les sept autres shaders sont restés
  inchangés pendant les essais.
- Le candidat q1 est validé localement, pas intégré à `areas.csv` ni au manifeste release.

## 6. Procédure d'extension à d'autres eaux

### 6.1 Précondition assets — voie1 d'abord si nécessaire

Pour chaque zone/variante :

1. résoudre WED/base/overlays effectifs, sources stock/installées/build sélectionné ; jour/nuit séparés ;
2. appliquer l'audit voie1 : art local, populations primaire/secondaire, formats, alpha effectif,
   RGB des interfaces, padding, périodicité et animation de l'overlay ;
3. réparer les défauts d'assets selon la notice voie1 avant route2. Ne pas utiliser le shader pour
   masquer alpha0, alpha255 central, coutures bleues/noires ou frames immobiles ;
4. conserver un témoin voie1 installé et un reçu propre par zone/overlay.

Route2 dépend donc de voie1 quand les assets ont le défaut AR0900. Une zone dont les assets natifs/
xN sont déjà corrects peut passer directement au routage q0 après preuve du même contrat de blend.

### 6.2 Ne pas élargir la condition AR0900 à l'aveugle

Remplacer la policy codée en dur par une allowlist/registre validé, versionné et fail-closed. Une
entrée minimale par cible contient :

```text
areaVariant, wedResref, baseTisResref, baseWidth, baseHeight, baseTileCount,
overlaySlot, overlayTisResref, overlayTileCount,
allowedPvrzPages[{resref,width,height}], liquidMode,
source/build hashes, approvedStrength, qaStatus
```

Règles :

- aucun match sur seul nom de zone, taille, alpha, couleur, textureId, GL name ou `vColor.a` ;
- inventorier toutes les pages d'un overlay et tous leurs usages ; une page mixte/inconnue est refusée ;
- résoudre slot moteur→nomGL à chaque draw via la table validée ; pas de cache persistant ;
- revalider activeArea/WED avant/après résolution ; reset q0 après draw et transition ;
- accepter x1/x2/x4 seulement avec dimensions/pages explicitement manifestées ;
- overlay stock délégué au renderer natif : prouver le même chemin `vpDraw/fpSEAM`; ne pas supposer
  que le hook xN l'intercepte ;
- WED moddé, overlay supplémentaire, population/dimension/hash divergents → q0 + diagnostic borné ;
- chaque entrée a un dosage approuvé séparé. **Ne pas propager `1.00` depuis WTLAKE**.

### 6.3 Qualification par famille

| Famille | Risque |
|---|---|
| WTLAKE, WTLAKA–D | Teinte, vitesse, mer/lac, nombre de pages/frames, centre/bords |
| WTPOOL | Petite surface ; cycle x4 historiquement figé ; source x2 courante |
| WTRIV/WTWAVE/WTFALL/WTURN, YS* | Direction du courant ; shader lac non interchangeable |
| WTSWAM | Stock ; eau sombre/brune ; éviter bleu/écume propre |
| WTSEW | Stock ; branche matériau égouts existante mais route2 non qualifiée |
| WTOIL, WTGOO* | Viscosité/opacité ; matériau d'eau non adapté par défaut |
| WTLAVA–D | Émissivité/opacité ; branche lave existante mais alpha128 eau interdit |
| Multi-overlay/jour-nuit/WED moddé | Ordre, collisions, reset, identité et fallback |

Le shader possède des branches visuelles historiques lave et égouts ; leur présence ne constitue ni
un routage route2 ni une QA. Modes marais/huile/goo n'ont pas de matériau dédié validé.

### 6.4 Gates obligatoires par nouvelle entrée/famille

1. Créer candidat/manifest/snapshot neufs ; ne pas réécrire runs, reçus ou candidats AR0900.
2. Ajouter tests policy/config/sélection/fallback et garde GLSL. Selon `AGENTS.md`, préparer
   `test_changed.py --targeted --path ...`, puis demander **ciblés / tous / aucun** avant exécution.
3. Compiler uniquement `InfinityEngine-Enhancer`; aucun release_bundle/package/staging.
4. Installer transactionnellement, jeu et InfinityLoader fermés ; préflight puis install puis verify.
5. Gate q0 : `overlay=true q=0` sur chaque page autorisée, `overlay=false q=0` partout ailleurs ;
   rendu strictement identique au témoin voie1. Une image identique sans trace positive est un échec.
6. Gate q>0 : commencer par une valeur visible mais prudente selon la famille. Pour WTLAKE AR0900,
   q1 est déjà retenu ; pour toute autre cible, q1 reste une hypothèse à tester.
7. QA : animation, art local, ombres/reflets, transparence, rives, centre/bords, zoom/pan,
   pause/reprise, transition/retour, nuit, carte sèche, UI/sprites, coût de frame.
8. Enregistrer logs bornés, captures/vidéo, hashes, reçus, décision utilisateur par zone/variante.
9. Échec : q0/fallback ou restore du nouveau reçu ; ne pas modifier les assets pour compenser sans
   retourner à l'audit voie1.

Logs attendus avec diagnosticsON :

```text
WATER_ROUTE2 native texture table validated=true
WATER_ROUTE2 identity ... page=<PVRZ> engineSlot=<id> glName=<name>
WATER_ROUTE2 draw ... overlay=true q=<requested> blend=1/770/771 srgb=0
WATER_ROUTE2 draw ... overlay=false q=0 ...
```

`Water shader override is active` prouve l'interface, pas le ciblage. `feed()` peut forcer l'effet
à0 si masque/textures manquent. Toujours exiger la trace `overlay=true` et le q attendu.

## 7. Installation et rollback

Outils :

```powershell
$taskGame = python -B -c "import sys; sys.path.insert(0,'pipeline/scripts'); from workspace_paths import get_path; print(get_path('bg2ee_game_root'))"
$taskEngine = 'engine/InfinityEngine-Enhancer/source-patchee'
python "$taskEngine/tools/install_shader_suite_candidate.py" install <shader-candidate> --game-root "$taskGame" --verify-only
python "$taskEngine/tools/install_renderer_candidate.py" install <renderer-candidate> --game-root "$taskGame" --verify-only
python "$taskEngine/tools/install_shader_suite_candidate.py" install <shader-candidate> --game-root "$taskGame"
python "$taskEngine/tools/install_renderer_candidate.py" install <renderer-candidate> --game-root "$taskGame"
python "$taskEngine/tools/install_shader_suite_candidate.py" verify <shader-receipt> --game-root "$taskGame"
python "$taskEngine/tools/install_renderer_candidate.py" verify <renderer-receipt> --game-root "$taskGame"
```

- Shader candidate : exactement huit shaders ; sept inchangés + fpSEAM. Renderer candidate :
  exactement DLL+INI. Comparer le live au snapshot juste avant écriture.
- Les deux transactions ne sont pas atomiques ensemble. Installer shader puis renderer ; échec du
  second → inspecter rollback puis restaurer le premier. Dérive tierce → arrêter.
- Redémarrage frais obligatoire après installation. Hash disque seul ≠ programme lié.
- Rollback, runtime fermé, ordre inverse : renderer puis shader, chaque restore précédé de
  `--verify-only`, puis verify du reçu. Avec plusieurs essais, dérouler les reçus dans l'ordre inverse.
- Ne jamais restaurer un reçu antérieur au témoin voie1 et ne jamais restaurer le reçu map AR0900.

## 8. Release et décision globale

- AR0900 q1 n'autorise aucune autre zone/famille ni variante nuit.
- Le runtime peut devenir commun seulement après matrice multi-familles ; les entrées d'allowlist et
  dosages restent spécifiques aux assets/variantes approuvés.
- Si une cible échoue route2 mais réussit voie1 : conserver la voie1 pour cette cible. Architecture
  finale possible : runtime commun fail-closed + allowlist partielle + réparations assets voie1.
- Après validation ingame, demander séparément l'intégration aux manifests Core/release.
  Ne modifier ni payload, staging, `content.json`, archive ou projection sans accord.
- Réconcilier avant release `runtime-compatibility.json`, INI samples et réglages Core :
  `EnableWaterEffect=true`, route2 explicite, dosage par politique/allowlist ; diagnosticsOFF.
- Livrables d'une généralisation : source, tests choisis, registre/version, candidats, hashes/reçus,
  preuves q0/q>0, QA par cible, exclusions, rollback, coût/performance et commit isolé.

Ne jamais annoncer « toutes les eaux réparées » tant qu'une famille, variante ou structure WED reste
non auditée ou non validée ingame.
