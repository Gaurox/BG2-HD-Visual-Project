# Interpolation temporelle des animations BAM — procédure LLM

## Objet

Remplacer les répétitions temporelles d'une animation BAM par de vraies images
intermédiaires x4, sans modifier sa taille logique, son ancrage ou les autres
animations du registre global.

Méthode validée : **une image interpolée par position temporelle du cycle BAM**.
Cette méthode conserve l'horloge native et ne demande aucune modification de DLL.

**Les valeurs `27 frames`, `15 FPS`, `1,8 seconde` et `660×520` sont uniquement
l'exemple AM0205E. Ce ne sont jamais des valeurs par défaut.** L'agent doit recalculer
la résolution, le nombre de frames, les FPS et la durée pour chaque resref et chaque cycle.

```text
frames x4 validées -> MP4 x4 au rythme ingame (revue utilisateur)
-> interpolation Topaz à boucle fermée -> audit -> registre -> patch réversible -> QA
```

L'interpolation est automatisée depuis le 2026-08-21 (`interpolate`, Topaz Video AI en
CLI). Elle reste substituable : des PNG interpolés à la main par l'utilisateur entrent
toujours par `ingest-frames`.

**Périmètre.** Cette méthode ne s'applique qu'à un cycle **comportant des répétitions** : elle
remplace les positions qui redessinent la même image par de vraies images intermédiaires, sans
toucher à la DLL. Un cycle où chaque position affiche déjà une image distincte (`N = U`) n'a rien à
y gagner. Pour ajouter de vraies présentations entre ces positions et lire une boucle native
15 fps à 30 fps, la voie runtime est maintenant implémentée séparément :
[`ANIMATION_UPSCALE_30FPS_V2.md`](ANIMATION_UPSCALE_30FPS_V2.md). Les hypothèses abandonnées sont
résumées dans [`../docs/DECISIONS.md`](../docs/DECISIONS.md).

## Règles absolues

1. Travailler d'abord en lecture seule.
2. Ne jamais modifier le BAM source, la map ou ses coordonnées.
3. Ne jamais installer lorsque `Baldur`, `BaldurReal` ou `InfinityLoader` est actif.
4. Ne jamais lancer le jeu à la place de l'utilisateur.
5. Ne jamais remplacer le registre global par un registre contenant seulement la ressource testée.
6. Conserver la taille logique x1 et le centre BAM. Seule la texture physique est x4.
7. Sauvegarder le registre actif et tous les assets remplacés avant la première copie.
8. Vérifier tailles et SHA-256 avant et après installation.
9. Ne valider le CSV qu'après validation visuelle explicite de l'utilisateur.
10. Fournir à l'utilisateur un MP4 source x4 reproduisant la vitesse ingame avant d'interpoler,
    que l'interpolation soit automatisée ou confiée à l'utilisateur.
11. Fermer la boucle avant d'interpoler, et ne jamais étirer une sortie dont la couverture de
    boucle n'est pas établie.

## Données à relever

Pour chaque cycle de la ressource :

- `U` : nombre de frames uniques du BAM source ;
- `N` : nombre de positions temporelles, soit la longueur de `cycles[].frame_indices` ;
- `S` : cadence effective des positions BAM en positions/seconde ;
- `T = N / S` : durée native de la boucle ;
- `R` : répétitions éventuelles d'une même frame dans la table du cycle ;
- taille logique x1 de chaque frame ;
- taille physique attendue x4 ;
- centre/ancrage x1 ;
- zones et occurrences utilisant le resref.

Ne jamais reprendre les paramètres d'une animation déjà traitée. Deux BAM peuvent
avoir des dimensions, un nombre de cycles, une table temporelle et une cadence différents.

Sources :

- manifeste `01_frames_x1/manifest.json` pour `U`, `N`, géométrie, centre et cycles ;
- registre global actif pour la définition runtime courante ;
- logs horodatés du hook pour mesurer `S` si la cadence n'est pas déjà prouvée ;
- `animations/index/occurrences.csv` pour les zones et positions.

Ne pas déduire `S` du nombre de frames uniques. Une frame répétée trois fois dans
le cycle réduit la cadence visuelle unique mais pas la cadence des positions BAM.

## Gate I1 — proposition obligatoire à l'utilisateur

**Avant toute interpolation ou intégration, l'agent doit proposer explicitement :**

- un nombre exact de frames à produire ;
- une durée exacte de boucle ;
- une cadence de lecture ;
- la raison technique de ce choix.

Proposition par défaut, sans modification runtime :

```text
frames à produire = N
FPS = S
durée = N / S
une frame interpolée distincte par position BAM
```

Exemple : `N = 27`, `S = 15` donne **27 frames, 15 FPS, 1,8 seconde**.

L'agent doit recommander cette solution si elle reste proche de la cadence demandée.
Il ne doit pas demander arbitrairement à l'utilisateur de choisir les paramètres.

Si l'utilisateur demande une cadence différente :

1. proposer d'abord la cadence native la plus proche ;
2. indiquer l'écart de FPS et de durée ;
3. préciser qu'une cadence arbitraire exige une horloge runtime indépendante ;
4. si une horloge indépendante est retenue, vérifier la cadence d'affichage du jeu.

À 30 FPS d'affichage :

- 15 FPS est régulier : deux images affichées par frame animée ;
- 30 FPS est régulier : une image affichée par frame animée ;
- 20 FPS produit une alternance de maintien sur une puis deux images et peut saccader.

Ne pas développer une horloge indépendante si la méthode native satisfait le besoin.

## Gate I1b — MP4 source obligatoire

Après la proposition frames/FPS/durée et avant la livraison des frames interpolées,
**l'agent doit fabriquer et fournir à l'utilisateur un MP4 de référence**.

Le MP4 doit :

- utiliser les frames RGB x4 actuellement validées ;
- conserver la résolution physique x4 exacte ;
- reproduire la vitesse visuelle et la durée de boucle ingame ;
- contenir les images sources dans leur ordre de lecture ;
- ne pas inclure l'alpha : l'alpha sera réappliqué après interpolation ;
- ne pas ajouter la première frame à la fin dans la version remise pour lecture ;
- être encodé sans perte RGB si l'outil utilisateur accepte `libx264rgb` ;
- être vérifié avec `ffprobe` avant remise.

Ce MP4 est l'artefact de **revue** : il sert à valider vitesse, durée et phase avant
d'engager l'interpolation. Ce n'est pas l'entrée du modèle — `interpolate` repart des PNG
`source_rgb/` et leur ajoute la fermeture de boucle.

Résolution du MP4 :

- géométrie uniforme : utiliser la taille physique x4 de la ressource ;
- géométrie variable : utiliser le canvas commun x4 aligné sur les centres BAM ;
- enregistrer les offsets de chaque frame ; après interpolation, recadrer chaque PNG
  vers sa géométrie runtime native avant de produire les buffers RGBA.

Si chaque frame unique est répétée uniformément `R` fois dans le cycle :

```text
FPS du MP4 source = S / R
frames du MP4 source = U
durée du MP4 source = U / (S / R) = T
```

Exemple uniquement — AM0205E : 9 frames uniques, répétées 3 fois, positions BAM à environ
15 FPS. Le MP4 source doit donc faire **660×520, 9 frames, 5 FPS, 1,8 seconde**.

Ne jamais appliquer ces quatre valeurs à un autre resref sans refaire le préflight.

Commande type :

```powershell
ffmpeg -framerate <fps-source> -i frame_%03d.png -an -c:v libx264rgb -crf 0 -preset slow -pix_fmt rgb24 <RESREF>-x4-source.mp4
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration -of default=noprint_wrappers=1 <RESREF>-x4-source.mp4
```

Si les répétitions ne sont pas uniformes ou si le cycle réordonne les frames :

1. reproduire la table du cycle avec une image par position ;
2. encoder ces `N` positions à `S` FPS ;
3. signaler à l'utilisateur que le MP4 contient des répétitions nécessaires au timing ;
4. proposer une interpolation par segment si l'outil ne traite pas correctement les doublons.

Avec le MP4, l'agent doit remettre une consigne de retour exacte :

```text
Nombre de PNG attendu : <N>
Cadence cible : <S> FPS
Durée cible : <T> seconde(s)
Résolution : <largeur_x4>x<hauteur_x4>
Première frame dupliquée en fin : non
Canal alpha requis : non, sauf demande explicite
```

L'utilisateur effectue ensuite l'interpolation avec l'outil de son choix et fournit
le dossier de PNG demandé. L'agent ne lance pas ni ne pilote le logiciel d'interpolation
sauf demande explicite.

## Contrat de livraison des frames

Après remise du MP4 source, demander à l'utilisateur :

- exactement le nombre convenu de PNG ;
- numérotation contiguë et ordre lexical correct ;
- dimensions physiques x4 exactes ;
- canvas et cadrage identiques à l'animation x4 existante ;
- boucle couvrant l'intervalle `[0, T[` ;
- aucune copie volontaire de la première frame ajoutée à la fin ;
- même phase de départ que la source si possible ;
- RGB inchangé après livraison.

Le PNG peut être RGB ou RGBA. L'absence d'alpha n'est pas bloquante si les
masques source validés sont disponibles.

## Gate I2 — audit en lecture seule des frames livrées

Contrôler avant toute écriture :

1. chemin réel du dossier ;
2. nombre exact de PNG ;
3. noms et numérotation contigus ;
4. dimensions identiques et exactes ;
5. mode RGB/RGBA et présence réelle d'un canal alpha ;
6. moyenne d'écart de chaque paire consécutive ;
7. écart dernière frame → première frame ;
8. aperçu visuel du début, du milieu et de la fin ;
9. absence de saut, doublon prolongé, déformation ou changement de cadrage.

La couture doit être du même ordre ou plus faible que les transitions internes.
Un doublon ponctuel peut être acceptable ; plusieurs doublons consécutifs créent une pause.

## Reconstruction alpha

Ordre de préférence :

1. alpha RGBA livré et validé ;
2. masque x4 de la phase source la plus proche ;
3. interpolation contrôlée des masques source ;
4. masque manuel fourni par l'utilisateur.

Pour la sélection par phase :

1. comparer chaque nouvelle RGB aux anciennes RGB x4 ;
2. choisir la phase source ayant le plus faible écart ;
3. appliquer son alpha x4 sans modifier la RGB ;
4. enregistrer `alpha_source_frame` dans le manifeste.

Ne pas générer l'alpha avec le modèle d'upscale. Ne pas appliquer de feather
supplémentaire sans défaut constaté en jeu. Si un rectangle ou un liseré apparaît,
suivre [`ANIMATION_ALPHA_CORRECTIONS.md`](ANIMATION_ALPHA_CORRECTIONS.md) dans un
prototype séparé.

## Interpolation automatisée — Topaz Video AI

Sous-commande `interpolate`. Topaz Video AI livre son propre `ffmpeg.exe` avec le filtre
`tvai_fi` : aucune interaction GUI n'est nécessaire.

### Fermeture de boucle — obligatoire

L'entrée remise au modèle est la séquence source **plus sa première frame recopiée en
fin**. Sans cette fermeture, le modèle n'interpole que les intervalles internes : pour
`U` frames uniques il ne couvre que `U-1` intervalles, la boucle est amputée de son
raccord, et la sortie dure `T×(U-1)/U`.

**Ne pas rattraper cet écart en étirant la vidéo.** L'étirement étale `U-1` intervalles
sur `U`, ce qui ne restitue pas le raccord manquant et décale toutes les phases. C'est
le défaut constaté sur les interpolations antérieures au 2026-08-21 — voir « Défaut
historique » plus bas.

### Paramètres

| Paramètre | Valeur | Raison |
|---|---|---|
| `model` | `apo-8` | Apollo v8. `apf-*` = Apollo Fast, `chr-*`/`chf-*` = Chronos. |
| `rdt` | `-0.01` | **Non négociable.** Le défaut `0.01` fait supprimer par Topaz les frames qu'il juge dupliquées, ce qui casse silencieusement le comptage. Bornes du filtre : `[-0.01, 0.2]` ; toute valeur `<= 0` désactive la suppression. |
| `fps` | `S × oversample` | Cadence demandée au modèle. |
| `--oversample` | `1` | Doit rester **entier** : la cadence Topaz doit être un multiple entier de `S`, sinon la décimation tombe entre deux frames et réintroduit une gigue de phase. |

Avec `oversample = k`, le modèle rend `N×k + 1` frames ; le pipeline en garde une sur `k`
et jette la frame de fermeture. Apollo échantillonnant le flux optique à un `t` arbitraire,
`k = 1` produit les mêmes phases que `k > 1` décimé, pour un `k`-ième du temps GPU. Le
réglage n'existe que pour un A/B éventuel.

Le transit se fait en **PNG rgb24 de bout en bout** : pas de sous-échantillonnage chroma,
pas de génération lossy intermédiaire.

### Montage ffmpeg — repli conditionnel

Quand le modèle rend exactement `N×k + 1` frames (ou `N×k`), chaque position est une frame
existante choisie par index : **aucun rééchantillonnage, aucun montage**. Vérifié sur
AM0205B : le montage appliqué à une séquence déjà exacte est une identité au pixel près.

`--retime` pilote le repli :

- `auto` (défaut) — montage seulement si le compte n'est pas exact ; **s'arrête** si le
  compte est irrégulier, car la couverture de boucle devient incertaine ;
- `always` — force le montage ffmpeg, qui **suppose une boucle complète** ;
- `never` — exige le compte exact.

Le montage ne peut que dupliquer ou jeter des frames : il ne répare jamais une couverture
incomplète. `auto` refuse donc de masquer un problème de modèle ou de cadence.

### Phase alpha déterministe

La position temporelle de chaque frame étant connue par construction, `build-patch` lit
l'alpha dans `alpha_phase_map` au lieu de le deviner par comparaison d'images : la position
`j` retient la phase source `round(j×U/N)` modulo `U`, le modulo couvrant les positions qui
interpolent le raccord. Le résultat de la recherche par image reste enregistré dans
`alpha_nearest_rgb_frame` comme diagnostic. Sans rapport d'interpolation, la recherche par
image reste le mécanisme de sélection.

### Défaut historique — antérieur au 2026-08-21

`AM0205E`, `AM0205A` et `AM0205B` ont été interpolés avec une boucle ouverte puis un
étirement. Mesuré sur AM0205B : Topaz avait rendu `57 = 8×7+1` frames sur 1,629 s, le
raccord `frame 8 → frame 0` n'était pas interpolé, et l'étirement vers 1,8 s a décalé
toutes les phases — la position 24 tombait sur la source 7 au lieu de la 8, et **5 des 27
positions ont reçu le mauvais masque alpha**. Les trois sont validés en jeu et ne sont pas
urgents à reprendre ; ils sont régénérables à faible coût avec `interpolate`.

### Limite constatée — contenu à morphologie marquée (AM0205E)

`AM0205E` a été reconstruit avec `interpolate` (modèle `apo-8`) le 2026-08-21 : couverture
Topaz exacte, 9/9 ancrages alignés, couture au 19ᵉ percentile — toutes les métriques
automatiques au vert. **Rejeté après QA en jeu** : le rendu de l'orifice qui s'ouvre puis se
referme est mauvais visuellement, alors que les métriques MAE ne le signalaient pas. C'est
précisément ce qui avait motivé un traitement manuel différent à l'origine pour ce resref.

Contrairement aux pods `AM0205A`-`AM0205D` (texture seule, transitions internes MAE ~3-10),
`AM0205E` a des transitions source brutes jusqu'à MAE 36,8 (changement de forme, pas
seulement de texture). Les métriques automatiques (couverture, alignement de phase, MAE de
couture) valident la **mécanique** de l'interpolation, pas la **qualité perçue** du morphing
sur un sujet qui change de forme — une QA visuelle en jeu reste nécessaire avant d'adopter
`interpolate` sur un contenu similaire, même si toutes les métriques sont bonnes. La version
manuelle d'`AM0205E` reste active ; voir
`proto/AM0205E-orifice/interpolation-27f-15fps-x4-pipeline-v2/README.md` pour l'essai
conservé comme trace.

## Pipeline automatisé v1

Script : `pipeline/scripts/run_animation_interpolation.py`.

Le pipeline v1 traite **un resref ayant un seul cycle BAM**. Une ressource à
plusieurs cycles s'arrête avant toute écriture : ne pas fabriquer une table
temporelle approximative. Ajouter une spécification par cycle avant d'étendre le code.

Séquence :

```powershell
# 1. Lecture seule : proposition à soumettre à l'utilisateur.
python pipeline/scripts/run_animation_interpolation.py plan `
  --resref <RESREF> `
  --frames-manifest <01_frames_x1/manifest.json> `
  --upscale-manifest <02_upscale_x4/manifest.json> `
  --base-pack <pack-runtime-global-actif> `
  --slot-fps <cadence-mesuree> `
  --interpolation-patch <patch-deja-actif>

# 2. Après accord : MP4 x4 et contrat de retour.
python pipeline/scripts/run_animation_interpolation.py prepare-video `
  --resref <RESREF> `
  --frames-manifest <01_frames_x1/manifest.json> `
  --upscale-manifest <02_upscale_x4/manifest.json> `
  --base-pack <pack-runtime-global-actif> `
  --slot-fps <cadence-mesuree> `
  --interpolation-patch <patch-deja-actif> `
  --output <work-root>

# 3. Interpolation Topaz, boucle fermée. Ne modifie pas le jeu.
#    Omettre cette étape si l'utilisateur fournit lui-même les PNG.
python pipeline/scripts/run_animation_interpolation.py interpolate `
  --work-root <work-root>

# 4. Audit des PNG, sans modifier le jeu.
python pipeline/scripts/run_animation_interpolation.py ingest-frames `
  --work-root <work-root> `
  --input-frames <work-root>/interpolation/frames

# 5. Construire le patch différentiel hors jeu.
python pipeline/scripts/run_animation_interpolation.py build-patch `
  --work-root <work-root> `
  --output <work-root/runtime-patch>

# 6. Jeu fermé : installation puis restauration éventuelle.
.\pipeline\scripts\Install-AreaAnimation-Interpolation-Patch.ps1 `
  -PatchRoot <work-root/runtime-patch>
.\pipeline\scripts\Restore-AreaAnimation-Interpolation-Patch.ps1 `
  -BackupPath <sauvegarde>
```

`plan` ne crée aucun fichier. `prepare-video` crée un MP4, les PNG RGB source et
`handoff.json`. `interpolate` crée `interpolation/` (entrée à boucle fermée, sortie brute
Topaz, frames finales et `interpolation.json`) et ne touche à rien d'autre.
`ingest-frames` crée `intake.json`. `build-patch` crée uniquement
le registre reconstruit, les buffers du resref et `manifest.json`. Aucun sous-programme
ne lance le jeu, ne copie la DLL ou l'INI, ni n'installe implicitement le patch.

Si un ou plusieurs patches d'interpolation sont déjà actifs dans le jeu, passer chacun
avec `--interpolation-patch`, dans l'ordre de leur installation. Le pipeline contrôle la
chaîne de SHA-256 des registres puis conserve leurs ressources dans le nouveau registre.
Omettre un patch actif ferait régresser sa ressource : le pipeline ne doit jamais construire
ni installer un tel registre.

## Construction runtime — méthode native

Précondition v1 : un seul cycle BAM.

Pour un cycle de `N` positions :

1. convertir chaque PNG en RGBA8 brut, lignes haut vers bas ;
2. exiger `bytes = largeur_x4 × hauteur_x4 × 4` ;
3. nommer les assets `AAX4-<RESREF>-frame000.rgba` à `frameNNN.rgba` ;
4. porter `frame_count` runtime de `U` à `N` ;
5. conserver pour chaque frame `logical_size_x1`, `physical_size_x4` et `centre_x1` ;
6. remplacer le lookup du cycle par `[0, 1, ..., N-1]` ;
7. reconstruire le registre avec toutes les autres ressources inchangées ;
8. comparer les ressources non ciblées au pack de base par SHA-256.

Le moteur continue de fournir `currentFrame = 0..N-1`. Le registre retourne la
nouvelle frame portant le même index. Aucun calcul temporel supplémentaire n'est requis.

Pour plusieurs cycles, le pipeline s'arrête. Documenter la cadence et les frames
de chaque cycle avant de développer une extension dédiée ; ne pas contourner ce garde-fou.

## Manifeste minimal du patch

Enregistrer au minimum :

```json
{
  "schema": "bg2-upscale-area-animation-frame-expansion-test-v1",
  "status": "completed",
  "resref": "AM0205E",
  "scale": 4,
  "frame_count": 27,
  "native_cycle_slots": 27,
  "playback_fps": 15,
  "loop_duration_seconds": 1.8,
  "base_registry_sha256": "...",
  "target_registry_sha256": "...",
  "base_resource": {},
  "resource": {},
  "frames": []
}
```

Chaque frame doit enregistrer source, SHA-256 source, phase alpha, dimensions,
nom runtime, octets et SHA-256 runtime.

## Patch réversible

Le patch différentiel contient uniquement :

- le registre global reconstruit ;
- les nouveaux assets du resref ;
- le manifeste ;
- un installateur ;
- un restaurateur.

### Installation

L'installateur doit :

1. refuser si le jeu ou InfinityLoader est actif ;
2. vérifier le hash du registre actif contre `base_registry_sha256` ;
3. vérifier le manifeste, chaque taille et chaque SHA-256 source ;
4. vérifier les anciens assets attendus ;
5. refuser tout nouvel asset déjà présent et ambigu ;
6. sauvegarder le registre actif et les assets remplacés ;
7. enregistrer la présence/absence initiale de chaque asset ;
8. copier le nouveau registre et les nouveaux assets ;
9. revérifier tous les SHA-256 ;
10. restaurer automatiquement l'état initial si une étape échoue ;
11. laisser le jeu fermé.

Ne pas recopier la DLL ou l'INI pour la méthode native.

### Restauration

Le restaurateur doit :

1. refuser si le jeu ou InfinityLoader est actif ;
2. vérifier que le registre et les assets actifs correspondent encore au test ;
3. restaurer le registre sauvegardé ;
4. restaurer les assets anciennement présents ;
5. supprimer uniquement les assets absents avant le test ;
6. revérifier les SHA-256 restaurés ;
7. refuser d'écraser un fichier modifié depuis l'installation.

## Gate I3 — QA utilisateur

Donner à l'utilisateur la zone et la position de l'élément. Lui demander de contrôler :

- fluidité réelle ;
- durée et vitesse perçues ;
- raccord dernière → première frame ;
- pauses ou doublons ;
- artefacts d'interpolation ;
- alpha, rectangle, halo ou liseré ;
- taille à l'écran et ancrage ;
- absence de régression sur les autres animations.

L'agent ne lance pas le jeu et ne prend pas le contrôle du PC.

## Validation et registres

Après validation explicite :

1. passer l'entrée unique du resref à `validé-x4` dans
   `animations/index/animation_upscale_registry.csv` ;
2. mettre dans `correction_id` un identifiant stable incluant interpolation,
   nombre de frames et FPS ;
3. noter frames runtime, FPS, durée, date, zone et caractère réversible ;
4. conserver la colonne technique `frames` au nombre de frames du BAM source ;
5. exécuter :

```powershell
python pipeline/scripts/sync_animation_upscale_registry.py --check
```

6. mettre le README du prototype à `validé en jeu` ;
7. ne modifier `animation_alpha_corrections.csv` que si un correctif alpha a été retenu.

## Référence validée — AM0205E, exemple non réutilisable tel quel

```text
resref                 AM0205E
zone                   AR0205
position monde         1661,1387
frames BAM uniques     9
positions du cycle     27
table source           000,111,222,333,444,555,666,777,888
cadence des positions  environ 15 FPS
MP4 source             9 frames RGB x4 à 5 FPS
sortie interpolée      27 frames
durée                   environ 1,8 seconde
taille logique x1      165x130
taille physique x4     660x520
centre x1              83,130
validation             2026-08-21
```

Prototype :
`proto/AM0205E-orifice/interpolation-27f-15fps-x4/`.

Commandes AM0205E utilisées pour le test du pipeline :

```powershell
python pipeline/scripts/run_animation_interpolation.py plan `
  --resref AM0205E `
  --frames-manifest proto/AM0205E-orifice/02_frames_x1/manifest.json `
  --upscale-manifest proto/AM0205E-orifice/x4/manifest.json `
  --base-pack animations/runs/ar0205-a-d-seedvr7b-lab-x4/04_ingame_test/03_runtime_pack-a-e `
  --slot-fps 15
```

Résultat validé : registre global de 18 ressources conservé, AM0205E étendu de
9 à 27 assets runtime, DLL et INI inchangés, 255 assets des autres animations
confirmés identiques.

## Référence validée complémentaire — AM0205A

`AM0205A` (`AR0205`, premier pod) confirme la chaîne de patches : son patch
27 frames / 15 FPS / 1,8 s a été construit au-dessus de l'interpolation active
de `AM0205E`, sans la régresser. La validation en jeu est datée du 2026-08-21.
Le fade de canvas retenu après QA appartient au prototype alpha séparé
`proto/AM0205A-pod-canvas-feather-x4/`; voir
`pipeline/ANIMATION_ALPHA_CORRECTIONS.md`.

## Référence validée complémentaire — AM0205B

`AM0205B` (`AR0205`, pod en position 2027,401) reprend la même cadence native
de 15 FPS que `AM0205A`/`AM0205E` (même famille de pods, même zone), sans
nouvelle mesure indépendante de `S`. Patch 27 frames / 15 FPS / 1,8 s construit
dans l'archive locale externe
`G:\AI\BG2_Upscale-data\archive-pre-cleanup-20260827\temp-snapshots\interpolation-am0205b-20260821\runtime-patch\` au-dessus de la
chaîne `AM0205E` puis `AM0205A`, sans les régresser. Validation en jeu datée du
2026-08-21. Le fade de canvas 32 px x4 retenu après QA appartient au prototype
alpha séparé `proto/AM0205B-pod-canvas-feather-x4/`; voir
`pipeline/ANIMATION_ALPHA_CORRECTIONS.md`.

## Référence validée complémentaire — AM0205C

`AM0205C` (`AR0205`, pod en position 3076,1586) est le premier resref traité
avec la sous-commande `interpolate` automatisée (Topaz Video AI, boucle
fermée) — voir « Interpolation automatisée — Topaz Video AI » ci-dessus.
Résultat : couverture Topaz exacte (28 frames brutes, aucun montage requis),
9/9 ancrages alignés sur leur source, couture de boucle au 23ᵉ percentile des
transitions internes (contre le 100ᵉ pour `AM0205B` avec l'ancien process), et
phase alpha déterministe. Patch conservé dans l'archive locale externe
`G:\AI\BG2_Upscale-data\archive-pre-cleanup-20260827\temp-snapshots\interpolation-am0205c-v2-20260821\runtime-patch\` au-dessus de la chaîne
`AM0205E` → `AM0205A` → `AM0205B`, sans les régresser. Validation en jeu datée
du 2026-08-21. Le fade de canvas 32 px x4 retenu après QA appartient au
prototype alpha séparé `proto/AM0205C-pod-canvas-feather-x4/`; voir
`pipeline/ANIMATION_ALPHA_CORRECTIONS.md`.

## Référence validée complémentaire — AM0205D

`AM0205D` (`AR0205`, pod en position 1295,2360) ferme la série AM0205 (A à E
toutes validées). Traité comme `AM0205C` avec `interpolate` : couverture
Topaz exacte, 9/9 ancrages alignés, couture au 27ᵉ percentile des transitions
internes, phase alpha déterministe. Patch conservé dans l'archive locale externe
`G:\AI\BG2_Upscale-data\archive-pre-cleanup-20260827\temp-snapshots\interpolation-am0205d-v2-20260821\runtime-patch\` au-dessus de la chaîne
`AM0205E` → `AM0205A` → `AM0205B` → `AM0205C`, sans les régresser. Validation
en jeu datée du 2026-08-21. Le fade de canvas 32 px x4 retenu après QA
appartient au prototype alpha séparé `proto/AM0205D-pod-canvas-feather-x4/`;
voir `pipeline/ANIMATION_ALPHA_CORRECTIONS.md`.

## Conditions d'arrêt

Arrêter sans intégrer si :

- nombre, dimensions ou ordre des frames incorrect ;
- cadence `S` non établie ;
- proposition frames/FPS/durée non faite ;
- MP4 source x4 non fourni ou non vérifié ;
- raccord de boucle manifestement mauvais ;
- nombre de frames rendu par le modèle hors des valeurs exactes attendues ;
- cadence Topaz qui n'est pas un multiple entier de `S` ;
- répétitions non uniformes dans la table du cycle ;
- registre actif différent du pack de base attendu ;
- jeu non fermé ;
- sauvegarde ou restauration non déterministe ;
- une ressource non ciblée changerait.
