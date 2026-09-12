# Eau — voie 2 : lancement expérimental LLM

## 0. Mandat, statut, frontières

- Document préparé le 2026-09-12. **Voie 2 non implémentée, non validée.**
- But : conserver art local, ombres/reflets peints, contours et animation native ; ajouter une
  contribution procédurale dosable, homogène entre centre et bords. Aucun nouveau reflet 3D.
- Première cible : **AR0900 JOUR corrigé**, uniquement. Ne pas généraliser la voie 1 au préalable.
- Référence acceptée : voie 1 ; documentation/QA committées dans `f1cad546`.
- Lire cette notice ne vaut pas autorisation d'exécution. Dans la nouvelle tâche, confirmer le
  mandat d'implémentation/installation ; demander séparément le choix des tests avant exécution.
- Aucun rebuild de map, SeedVR, changement WTLAKE, WED/ARE/sauvegarde, autre shader, réglage
  sprites, projection ou release dans le premier essai. Une extension requiert un accord explicite.
- Ne pas promettre « shader seul, toutes les maps, sans rebuild » : c'est une hypothèse à qualifier.
  Un shader ne répare pas des RGB noircis ni une animation générique mal raccordée déjà stockés.
- Tous les chemins sont relatifs au dépôt, sauf les clés `config://...`.

Lectures obligatoires :

1. `AGENTS.md`, `README.md`, `pipeline/README.md`, `docs/DECISIONS.md`,
   `pipeline/PROBLEMES_A_RESOUDRE.md`.
2. [Réparation voie 1](WATER_REPAIR_RUNBOOK.md), surtout §§1–4,10–11 : contrat natif,
   causes résolues, preuve d'installation et limites. Ne pas réexécuter ses producteurs.
3. `engine/InfinityEngine-Enhancer/source-patchee/{AGENTS.md,README.md}`.
4. Sous ce moteur : `docs/{renderer-candidate-transaction,shader-suite-candidate-transaction}.md`.
5. `docs/TEST_SELECTION.md`. Pour de nouveaux formats/offsets : index documentaire BG2EE,
   puis référence nécessaire ; `src/iee/game/build_manifest.*` reste l'autorité binaire.

## 1. État témoin vérifié — ne pas confondre avec les anciens essais

`ENGINE = engine/InfinityEngine-Enhancer/source-patchee` dans les tableaux ci-dessous.
Les hashes suivants sont des repères, **pas** une permission d'écraser un état live divergent.
À la reprise, revalider les fichiers effectifs, les sélections et l'absence d'intervention concurrente.

| Objet | État vérifié |
|---|---|
| Sélection map | `areas.csv`, AR0900 jour, `voie1-water-rgb-seams-x4-jour-20260912`, `validated-installed` |
| Build | `maps/AR0900/runs/voie1-water-rgb-seams-x4-jour-20260912/05_build/x4-alpha128-water-seams-repaired` |
| Preuve map | `backups/maps/AR0900-20260911T235034477666Z-b986b035/install-backup.json` ; 27 fichiers live conformes |
| Ensemble map installé | `59DBB058B087D1AD9C1D06A295E7A774D2DF1C6DBA182A2EE8912C467D30E4E8` |
| Overlay | `maps/technical-overlays/WTLAKE/runs/seedvr2-7b-int8-wavelet-periodic-x4/04_build_x4` ; conforme au live |
| `WTLAKE.TIS` | `1743A734B7E94FA60AB927B6615933DBDF7B5BF998019C66428413801BB62EE1` |
| `WLAKE00.PVRZ` | `BCC99E2E6E2881E9D216687044A661C68EC42D0EEC1A4103C341894BB5E2FA10` |
| `InfinityEngine-Enhancer.dll` live | `8FF3629FEEDB61453B3D316C2C6534F5D109C4390DDE723E39311066A99B9648` |
| `InfinityEngine-Enhancer.ini` live | `93EA39BD9BFDCDBB24A38809964B034FF649AD3FF5A621D169B8721181BCAFFC` |
| Réglages live `[Shaders]` | `EnableWaterEffect=false`, `EnableDebugHotkeys=false` |
| `override/fpSEAM.glsl` live = source ENGINE | `E8D0F51E3A5D0C8E52F0DB03FE792FBCB700ED07951CE7825238B47264D00488` |
| `BaldurReal.exe` 2.7.3.0 | `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57` |
| WED | Pas de `override/AR0900.WED` au contrôle ; WED stock, 80×60 cellules |

- `Baldur.exe` est ici un lanceur, pas le binaire à utiliser pour les offsets.
- Les huit shaders live correspondent aux sources au contrôle. Ne pas supposer que cela restera vrai.
- Textures procédurales présentes sous `config://bg2ee_game_root/iee-textures/` :

| Fichier | SHA256 |
|---|---|
| `iee_water_normal.rgba` | `BBEBC635D68084D757176F5522161310AE7C1DDCA330438EB1743D96D8EFE551` |
| `iee_water_dudv.rgba` | `3F9FBF6E982CBECEBE70386F2DF8152A85D61651FD2965D9C17CC70807BBD83E` |
| `iee_water_foam.rgba` | `F9FB4383F83BEDD94A187EC2118FFE91879AEE911C0E96E05CC3C882B309DFF6` |

Pas de DDS correspondants au contrôle. Le loader préfère `.dds` à `.rgba` ; un DDS présent mais
invalide bloque le chargement, sans repli RGBA. Ne pas chercher ces textures dans `iee-assets/`.

**Retour arrière :** restaurer l'ancien reçu map ci-dessus remettrait l'essai *antérieur* avec
raccords noirs (`before_set_sha256=9DE7EDB09EBD019B45DA1DC1EB3064A88846C8905561D55A35EEB4FDD86D953B`).
Il sert à vérifier le témoin actuel, pas à annuler la voie 2. La voie 2 doit créer ses propres reçus
à partir de l'état final actuel. Ne pas réutiliser non plus un ancien reçu renderer avant voie 1.

## 2. Diagnostic établi du shader actuel

Source à modifier éventuellement : `ENGINE/assets/override/fpSEAM.glsl`, pas un dump ni un bundle.

| Code actuel | Conséquence |
|---|---|
| `waterMask = (1.0 - texColor.a) * cellSoft`, seulement si `vColor.a > 0.9` | Confond alpha de contour et alpha de mélange central128 |
| `texColor.rgb = ...mix(artLinear, water, waterMask)` | Remplace une partie de l'art local par du procédural |
| `texColor.a = max(texColor.a, waterMask)` | Rend opaque un trou primaire alpha0 ; masque l'overlay animé dessous |
| `alphaScale=0` si cellule liquide et `0.15 < vColor.a < 0.9` | Supprime notamment la passe d'art secondaire `WATER_ALPHA` ; le commentaire « must stay vanilla » plus haut ne décrit pas le résultat final |
| Diagnostic `uIeeEnabled>1.5` | Peut supprimer les passes semi-transparentes et forcer alpha1 ; pas un contrôle d'identité natif |

Activer uniquement `EnableWaterEffect=true`, supprimer uniquement `alphaScale`, ou appliquer le
même alpha final partout **n'est pas une réparation démontrée**.

### Contrat déjà réparé à conserver

- Animation générique WTLAKE : six frames périodiques x4 ; dessin natif conservé.
- Centre sans secondaire : primaire DXT5, alpha texture `128/255`, alpha dessin1.
  Vanilla DXT1 : texture opaque, DrawAlpha `128/255`. Contribution équivalente.
- Cellule avec secondaire : primaire de décor/contour ; art secondaire avec alpha texture
  de couverture et alpha dessin `128/255`. Ne pas lui imposer aussi alpha texture128.
- RGB et alpha des interfaces internes + padding ont été réparés séparément des vraies rives.
- Noir RGB ≠ trou alpha ≠ absence de secondaire. `1-alpha` ne reconstruit plus à lui seul la
  géométrie de l'eau après introduction de l'alpha128 de mélange.
- Les 775 primaires centrales et les 860 cellules avec secondaire doivent avoir une animation
  et des contributions comparables. Garder le décor opaque et les vraies rives intacts.

## 3. Inspection runtime obligatoire avant choix d'implémentation

Fichiers sous ENGINE ; lire les fonctions concernées, pas seulement leurs commentaires :

| Fichier | Vérification |
|---|---|
| `src/iee/features/tile_render.cpp` | Identité tileset/tuile/page, flags, UV xN, DrawColor/DrawAlpha hérités ; aucune sémantique explicite primaire/secondaire envoyée au shader actuellement |
| `src/iee/shader_probe.cpp` | Programme réellement lié, classification `vpDraw/fpSEAM` slot8 ; détection `uIee*`, feed et horloge `on_frame_tick` |
| `src/iee/shader_uniform_bridge.{h,cpp}` | Locations, invalidation/cache par révision, samplers, uniforms ; aucune uniform actuelle de dosage ou d'identité de passe eau |
| `src/iee/area_state.cpp` | WED réellement chargé, génération/changement de zone, teinte, upload masque |
| `src/iee/game/area_texture.cpp` | Masque R8 par cellule64, première couche liquide WED gagne ; pas un masque de contour au pixel |
| `src/iee/game/tile_liquid.{h,cpp}` | Modes0 aucun,1 eau,2 lave,3 goo,4 égouts,5 marais,6 huile ; classification resref |
| `src/iee/water_textures.cpp`, `src/iee/dll_main.cpp` | Chargement `iee-textures`, DDS prioritaire, erreurs/upload/bind |
| `src/iee/core/config.{h,cpp}`, `src/iee/hooks.cpp` | Activation et replis en cas d'échec des hooks |

Exiger une preuve du chemin réel pour au moins : centre sans secondaire, eau avec secondaire,
rive partiellement couverte, terre non liquide ; ajouter un fade et un changement de zone.
La trace minimale associe : resref zone/WED/tileset, cellule, ID tuile, rôle, programme lié,
format, alpha texture pertinent, alpha dessin, blend factors, ordre des passes et nombre d'applications.
Si une instrumentation est nécessaire, bornée et désactivée par défaut ; demander les tests avant
exécution et ne pas modifier le jeu durant ce diagnostic sans mandat d'installation.

Points bloquants à lever :

- `vColor.a≈0.5` ne prouve pas « secondaire » ; `vColor.a≈1` ne prouve pas « primaire ».
- Une page PVRZ contient plusieurs rôles possibles ; ne pas classifier l'eau par simple textureId.
- Le masque WED actuel ne fournit ni le rôle du draw, ni le contour exact, ni toutes les couches
  liquides superposées. Sa couverture élargie peut déborder vers une cellule voisine non marquée.
- Les textures x1 peuvent être déléguées au renderer natif par le hook xN : un mécanisme placé
  uniquement dans son chemin xN ne couvrira pas automatiquement WTSEW/WTSWAM/WTOIL stock.
- Un nouveau signal par draw ne doit pas être bloqué par `lastAppliedRevision` inchangée ;
  réinitialiser/restaurer le contexte entre draws, zones et contextes GL pour éviter toute fuite.
- `EnableWaterEffect` est global ; il n'existe pas ici de clé INI confirmée « AR0900 seulement ».
  Prévoir un opt-in explicite testé si le candidat doit être strictement borné à cette zone.
  Sinon annoncer sa portée globale et obtenir l'accord avant installation ; ne pas inventer une clé.

## 4. Cible de composition — contrat, pas patch prêt à copier

Notations simplifiées pour une zone entièrement eau : `U` animation générique native, `A` art local,
`a` son opacité effective, `P` contribution procédurale, `q` dosage choisi dans `[0,1]`.

```text
Témoin : C0 = a*A + (1-a)*U
Cible  : U2 = (1-q)*U + q*P
         C2 = a*A + (1-a)*U2
Invariants : q=0 => C2=C0 ; EnableWaterEffect=false => chemin témoin inchangé.
```

La formule décrit les contributions ; implémenter dans l'espace colorimétrique réel du framebuffer
et du blend, à vérifier. Ne pas introduire une conversion sRGB/linéaire supplémentaire dans le
chemin neutre. Le fragment actuel est en alpha droit ; vérifier les facteurs GL avant toute formule.

Ordre de préférence à évaluer après la trace :

1. Appliquer `q` **une seule fois à la couche animée sous-jacente identifiée**, laisser l'art
   primaire/secondaire et leurs alphas natifs inchangés. Ce modèle conserve naturellement la même
   contribution de l'art au centre et au bord. L'identification et le programme de cet overlay sont
   à prouver ; ne pas affirmer que `fpSEAM` actuel dispose déjà des signaux nécessaires.
2. Composition équivalente dans le chemin primaire : acceptable seulement si la dérivation prend
   en compte l'art central dans la primaire, l'art de bord dans une passe ultérieure, la couverture
   des rives et les fades. Ne pas simplement interpoler RGB puis relever alpha : cela n'est pas
   équivalent au modèle ci-dessus. Fournir les équations par population et leur vérification.
3. Si les entrées GLSL ne suffisent pas, ajouter le minimum de contexte runtime explicite et
   documenté ; ne pas remplacer les signaux absents par des seuils alpha/couleur universels.
   Présenter cette extension et obtenir accord avant de dépasser le périmètre initial.

Pour les trois cas :

- Ne plus annuler `WATER_ALPHA` dans la voie 2 ; ne pas exécuter l'ancien remplacement en plus du nouveau.
- Conserver les assets voie 1 et alpha128 pour le premier essai. Si un nouveau contrat exige de
  changer cet alpha, le démontrer puis créer un candidat assets séparé après accord ; jamais écraser
  le témoin ni double-atténuer à128×128.
- Décorréler couverture eau, opacité de l'art et dosage procédural. Garder les vraies rives.
- `q` est un paramètre conceptuel **à implémenter**, pas une option INI existante. Commencer à0.
  À dosage nul, contourner réellement le calcul procédural et ses modifications alpha/RGB.
- Valeurs exploratoires après identité validée : 0.15 puis0.30 ; aucune valeur n'est validée d'avance.
- Hors zone/famille/rôle autorisé, identité manquante, masque invalide, texture indisponible ou
  build inconnu : rendu natif, sans réutiliser un état de la zone/draw précédent.
- Le mode3/5/6 n'a pas actuellement une branche visuelle dédiée comme la lave/les égouts.
  Leur simple classification ne vaut pas prise en charge graphique correcte.

## 5. Candidats, tests et jalons

1. `git status --short`. Ne pas embarquer les travaux animations ou autres changements concurrents.
2. Revalider §1. Si drift : expliquer, arrêter l'installation, ne rien restaurer automatiquement.
3. Geler un nouveau dossier d'expérience versionné, par exemple
   `ENGINE/docs/validation/water-route2-ar0900-<id>/`, avec requête, hashes d'entrée, hypothèses,
   portée, équations, fichiers modifiés, contrôles, références des candidats/reçus et QA distinctes.
   Les grosses copies binaires restent dans les répertoires locaux de candidats, pas dans Git.
4. Snapshot exact du live (shaders, DLL, INI, dépendances) avant modification. Conserver le témoin.
5. Implémenter un premier candidat **neutre** (`q=0`) et sa sélection de passe ; ne pas régler
   simultanément palette, vagues, écume, cadence et transparence.
6. Préparer uniquement le plan des fichiers modifiés, sans lancer les tests :

```powershell
python pipeline/scripts/test_changed.py --targeted --path engine/InfinityEngine-Enhancer/source-patchee/assets/override/fpSEAM.glsl
```

Ajouter les `--path` réels de tout C++/test modifié. Demander explicitement **tests ciblés / tous /
aucun**. Reprendre exactement le plan accepté avec `--run`, sans escalade globale. Ajouter des tests
de composition et de sélection/fallback ; le shader compile réellement dans le contexte du jeu.
Un succès CTest ou un contrôle textuel ne prouve ni le link GL ni la QA visuelle.

7. Si nouvelle DLL nécessaire : build ciblé après accord selon le README moteur, cible CMake
   `InfinityEngine-Enhancer` dans un nouveau dossier de build ; aucun `release_bundle`, packaging
   ou `cmake --install` dans le jeu. Si GLSL seul : DLL live inchangée.
8. Installer transactionnellement (§6) après autorisation. Vérifier hashes et link réel.
9. Gate A : effet OFF identique au témoin. Gate B : effet ON, `q=0`, identique au témoin.
   Comparer à même scène/zoom/phase native ; une capture non synchronisée n'est pas une diff fiable.
10. Seulement après A+B : nouveau candidat versionné avec `q>0`, validation utilisateur AR0900 jour.
11. Échec : arrêter le réglage esthétique ; tracer contribution/ordre/alpha par population, ou
    restaurer le témoin (§6). Ne pas lancer un nouvel upscale pour masquer une erreur de composition.

## 6. Installation et retour arrière exacts

Ces commandes sont des **gabarits futurs**, à exécuter seulement après mandat, gates et jeu fermé.
`<...>` désigne un chemin réel à résoudre, jamais une valeur à copier littéralement.
Depuis la racine du dépôt :

```powershell
$taskGame = python -B -c "import sys; sys.path.insert(0,'pipeline/scripts'); from workspace_paths import get_path; print(get_path('bg2ee_game_root'))"
$taskEngine = 'engine/InfinityEngine-Enhancer/source-patchee'
```

Préparation hors jeu :

- Fermer BG2EE/BaldurReal et InfinityLoader avant installation/restauration ; ne pas tuer de processus
  ou abandonner une sauvegarde sans accord. Ne pas installer une moitié de candidat pendant le jeu.
- La transaction shaders impose **huit fichiers**, pas un sous-ensemble : `fpSprite.glsl`,
  `fpSELECT.glsl`, `fpDraw.glsl`, `fpTone.glsl`, `fpFONT.glsl`, `fpSEAM.glsl`, `fpYUV.glsl`, `fpYUVGRY.glsl`.
- `<baseline-eight>` : copie exacte des huit shaders live au snapshot, et rien d'autre.
  `<source-eight>` : mêmes sept shaders inchangés + `fpSEAM` candidat. Ne pas passer le dossier
  `override` complet du jeu ; l'inventaire strict le refuserait. Ne pas partir d'une vieille suite D2/D3.
- Vérifier source/live des sept shaders avant et après préparation. Ne pas régénérer la suite
  sprites : `build_shader_suite.py` ne produit pas `fpSEAM`.
- Le candidat GLSL conserve `// fpSEAM.glsl`, `void main`, l'interface native et
  `uIeeShaderSuiteEnabled` ; pas de `#version` ajouté (préambule moteur).
- `<renderer-candidate>` contient exactement `InfinityEngine-Enhancer.dll` et
  `InfinityEngine-Enhancer.ini` ; copie DLL live si inchangée, INI dérivée du live.
  Modifier uniquement les clés de cette expérience. Aucun pack effets optionnel.

```powershell
python "$taskEngine/tools/install_shader_suite_candidate.py" prepare <source-eight> <new-shader-candidate> --baseline-override <baseline-eight>
python "$taskEngine/tools/install_shader_suite_candidate.py" install <new-shader-candidate> --game-root "$taskGame" --verify-only
python "$taskEngine/tools/install_renderer_candidate.py" install <renderer-candidate> --game-root "$taskGame" --verify-only
```

`prepare` écrit le candidat ; `install/restore --verify-only` contrôlent sans installer/restaurer.
Ces installateurs n'ont pas d'option `--run` : **sans `--verify-only`, install/restore écrivent**.
Comparer encore le snapshot runtime juste avant installation : les deux outils ne constituent pas
une transaction atomique commune.

```powershell
python "$taskEngine/tools/install_shader_suite_candidate.py" install <new-shader-candidate> --game-root "$taskGame"
python "$taskEngine/tools/install_renderer_candidate.py" install <renderer-candidate> --game-root "$taskGame"
python "$taskEngine/tools/install_shader_suite_candidate.py" verify <new-shader-receipt> --game-root "$taskGame"
python "$taskEngine/tools/install_renderer_candidate.py" verify <new-renderer-receipt> --game-root "$taskGame"
```

- Enregistrer les deux reçus exacts retournés (`backups/shader-suite/`, `backups/renderer/`).
- Si la seconde installation échoue, inspecter son résultat/rollback puis restaurer la première ;
  ne jamais démarrer le jeu dans un état mixte. Dérive tierce : arrêter, pas de copie forcée.
- Redémarrer le jeu pour charger DLL/INI/GLSL. Le hash disque ne prouve pas le programme déjà lié.
- Contrôler les logs : `Water shader override is active in engine program`, absence d'erreur
  compile/link, masque liquide AR0900 chargé/uploadé, textures choisies/bindées, uniforms et temps.
  Le message « active » détecte l'interface `uIee*`, pas à lui seul l'identité de notre candidat :
  associer hash installé, démarrage frais et preuve de branche/dosage via diagnostics bornés.
- `feed()` peut forcer `uIeeEnabled=0` si masque ou textures ne se bindent pas : un rendu identique
  à `q=0` sans preuve d'activation serait un faux succès. Garder F10 désactivé pour la QA finale.

Retour au témoin, runtime fermé, **ordre inverse** :

```powershell
python "$taskEngine/tools/install_renderer_candidate.py" restore <new-renderer-receipt> --game-root "$taskGame" --verify-only
python "$taskEngine/tools/install_renderer_candidate.py" restore <new-renderer-receipt> --game-root "$taskGame"
python "$taskEngine/tools/install_shader_suite_candidate.py" restore <new-shader-receipt> --game-root "$taskGame" --verify-only
python "$taskEngine/tools/install_shader_suite_candidate.py" restore <new-shader-receipt> --game-root "$taskGame"
python "$taskEngine/tools/install_renderer_candidate.py" verify <new-renderer-receipt> --game-root "$taskGame"
python "$taskEngine/tools/install_shader_suite_candidate.py" verify <new-shader-receipt> --game-root "$taskGame"
```

Recontrôler les hashes §1, INI effetOFF, les 27 fichiers map et WTLAKE. Avec plusieurs essais,
restaurer les transactions dans l'ordre inverse complet jusqu'au témoin, pas seulement le dernier.
Ne toucher ni aux reçus historiques ni à la sélection AR0900 pour enregistrer un essai non validé.

## 7. QA et décision de généralisation

### AR0900 jour — gates minimales

- Comparaisons témoin/ON-q0/ON-q>0 à même scène et zoom ; captures + courte vidéo pour l'animation.
- Centre, bords, sous pont, zone claire/sombre, orbe/effets proches : art et profondeur conservés.
- Absence de carreaux bleus, centre statique, traits noirs, double contour, différence centre/bord.
- Continuité spatiale des vagues et des marges, plusieurs zooms/pans ; pas d'eau sur le décor.
- Pause/reprise, changement de zone/retour, jour/nuit : vérifier l'horloge et les resets, ne pas
  supposer que `uIeeTime` suit l'horloge native d'animation. Nuit = QA séparée, pas acquise.
- Texte, UI, sprites, objets au sol et scènes sèches inchangés ; temps de frame comparables à froid/chaud.
- Arrêter sur crash, GL invalide, mauvaise identité, mélange non compris ou rollback non vérifié.

### Après accord utilisateur seulement — matrice multi-familles

| Cas | Risque à qualifier |
|---|---|
| Lac WTLAKE et eau lac/mer WTLAKA–D | Teinte locale, ombres/reflets, frames, centre/bords ; maps et formats distincts |
| Piscine WTPOOL | Petite surface, animation native, échelle x2, couverture des rives |
| Rivière/cascade et familles YS | Courant/animation orientés ; aucun remplacement universel par vagues de lac |
| Marais WTSWAM | Overlay stock ; couleur sombre, pas de bleu/écume imposés |
| Égouts WTSEW | Overlay stock ; palette sale, transparence et débit spécifiques |
| Huile WTOIL / goo WTGOO* si présents | Viscosité/aspect distincts ; pas de transparence d'eau imposée |
| Lave WTLAVA–D | Émissivité/opacité spécifiques ; ne pas lui appliquer automatiquement alpha128 d'eau |
| Carte sèche, multi-overlay, WED moddé, format x1/x2/x4, jour/nuit | Fallback sûr, identité, ordre des couches, absence de fuite d'état |

Choisir les zones réelles à partir des WED/sélections, pas de noms supposés. Réconcilier d'abord
`overlay-sources.json` avec les audits : ceux-ci classent encore WTLAVA–D stock alors que le
manifeste sélectionne x4. Les réglages release/sample imposent encore `EnableWaterEffect=true` :
ce n'est ni la preuve de validation de la voie 2 ni l'autorisation de modifier la release.

Livrables de la tâche d'exécution : sources et tests ciblés, équations/trace de composition,
manifeste candidat/hashes/reçus, résultat QA utilisateur par zone/variante/famille, rollback vérifié,
liste des limites. Commit explicite du seul lot. Si accepté ingame, demander séparément
l'intégration release ; aucun payload/staging/content/archive reconstruit implicitement.

**Décision finale :** shader/runtime global seulement si la matrice prouve la compatibilité des
assets existants. Sinon recette hybride : runtime commun + réparations d'assets ciblées selon le
runbook voie 1. Ne jamais déclarer toutes les maps réparées depuis le seul témoin AR0900.
