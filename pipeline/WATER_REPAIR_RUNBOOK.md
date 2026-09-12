# Réparation complète de l'eau — reprise LLM

Pour expérimenter la voie 2 avant une généralisation :
[`WATER_ROUTE2_EXPERIMENT_RUNBOOK.md`](WATER_ROUTE2_EXPERIMENT_RUNBOOK.md).
Elle conserve AR0900 corrigé comme témoin ; elle ne remplace pas cette recette native validée.

## 0. Mandat et limites

- Référence : AR0900 **jour**, correctif complet accepté ingame par l'utilisateur le 2026-09-12.
- Finalité : porter la réparation aux maps d'eau du jeu patché, dans une nouvelle tâche.
- Destinataire : LLM de la prochaine tâche, modèle demandé par l'utilisateur : 5.6 Terra.
- Cette notice ne vaut ni exécution du lot, ni QA des autres maps/nuit, ni autorisation release.
- Voie retenue : composition native + assets corrigés. Pas de nouvelle eau procédurale, de
  retouche globale du shader, de modification des coordonnées WED/ARE ou des sauvegardes.
- Unités : `x1 = monde/source`, `x4 = texture`. Tuile monde64 ; tuile x4=256 ; marge atlas4px x4.
- Tous les chemins ci-dessous sont relatifs au dépôt, sauf `config://bg2ee_game_root`.
- Lire `AGENTS.md`, `README.md`, `pipeline/README.md`, `docs/DECISIONS.md`,
  `pipeline/PROBLEMES_A_RESOUDRE.md`, `docs/UPSCALING_WORK_PREFLIGHT.md` avant exécution.
- Ne pas relancer les producteurs AR0900 figés tels quels : ils ont des chemins, hashes,
  populations, dimensions et assertions propres au témoin. En dériver un producteur paramétré.
- Ne pas réécrire les runs historiques. La QA courante des maps appartient à `areas.csv` ; les
  manifests de build restent dans leur état historique `built-pending-qa`.

## 1. Causes établies et ordre des corrections

| Symptôme | Cause établie | Réparation |
|---|---|---|
| Eau plate ; disparition des ombres/reflets locaux | `fpSEAM` remplace l'eau par un matériau procédural et annule la passe secondaire d'art local lorsque l'effet est actif | `EnableWaterEffect=false`, conserver le rendu xN et la composition native |
| Carreaux/raccords bleus sur l'animation générique | Frames WTLAKE upscalées avec un mauvais contexte spatial ; changer LAB en wavelet seul ne suffit pas | Contexte périodique3×3 avant inférence, récupérer uniquement la copie centrale |
| Centre bleu uniforme, différent des bords | Ancien `--transparent-full-water-base` impose alpha0 et supprime l'art local central | Restaurer le mélange effectif natif, pas une transparence totale |
| Centre contrasté mais immobile après restauration alpha255 | DXT1 natif reçoit DrawAlpha128 ; DXT5 central saute cet appel | Alpha texture128 sur les seules primaires opaques DXT1 converties en DXT5, eau sans secondaire |
| Très fins traits noirs aux frontières centre/secondaire | RGB primaire déjà noirci avant assemblage/compression ; halo au voisinage du noir technique | Bande RGB issue du maître secondaire continu, puis marges atlas cohérentes |
| Raccord alpha secondaire résiduel | Spline secondaire calculée sur fond noir aux cellules sans secondaire ; faux contour interne | Restaurer alpha255 uniquement sur les bandes internes prouvées eau ; préserver les vraies rives |

Ordre opérationnel : **inventaire → configuration native → overlay périodique si nécessaire →
base x4/masques → alpha128 central → raccords RGB/alpha + marges → contrôles → installation → QA**.
Les étapes déjà prouvées correctes sont conservées, pas régénérées.

## 2. Contrat de composition natif

L'art propre à la map contient les ombres/reflets/variations locales. L'overlay partagé apporte
l'animation. Ce n'est pas un besoin de calculer de nouveaux reflets 3D.

| Population | Format / alpha texture | Alpha de dessin | Contribution effective |
|---|---|---|---|
| Primaire eau sans secondaire, vanilla AR0900 | DXT1 / 255 | 128 | Art local semi-transparent au-dessus de l'animation |
| Même population, ancien x4 | DXT5 / 0 | 255 | Animation générique seule ; art perdu |
| Essai rejeté, restauration brute | DXT5 / 255 | 255 | Art local opaque ; animation masquée |
| Réparation retenue | DXT5 / 128 | 255 | Mélange équivalent au vanilla |
| Eau avec secondaire | Primaire : masque de décor ; secondaire : alpha source | Passe secondaire : 128, y compris DXT5 | Ne pas appliquer une seconde atténuation128 à la texture secondaire |

- Avec `SRC_ALPHA / ONE_MINUS_SRC_ALPHA`, opacité effective normalisée =
  `(alpha_texture/255) * (alpha_dessin/255)`.
  Ne jamais cumuler texture128 et DrawAlpha128 sur le même art : environ25% au lieu de50%.
- `RGB=(0,0,0)` n'est **pas** un détecteur d'alpha. Séparer noir de décor, RGB caché sous alpha0,
  tuile sentinelle et absence de secondaire. Lire les données natives.
- `secondary=0xFFFF` signifie absence de secondaire, pas absence d'art primaire.
- `page=0xFFFFFFFF` dans le TIS est une sentinelle distincte ; pas un slot texture éditable.
- Ne pas généraliser alpha128 aux tuiles terrestres, aux secondaires, aux overlays génériques,
  aux sources DXT5 ou aux sources partiellement transparentes sans preuve du chemin de mélange.

### Preuve moteur de référence

- BG2EE2.7.3.0, **BaldurReal.exe**, SHA256
  `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`.
  `Baldur.exe` local est un lanceur ; ne pas utiliser son hash pour ces offsets.
- `CInfTileSet::Render` RVA `0x2A4570`, image base `0x140000000`.
- `0x2A46D7` lit le format PVR ; branche contrôlant7/24 ; `0x2A46FC` saute DrawAlpha pour DXT5.
- `0x2A4700` contrôle l'absence de secondaire ; `0x2A4706..0F` applique128 depuis `0x65B4E4`.
- Passe secondaire `0x2A47DE..E7` : même128 sans cette exclusion DXT5.
- Hook xN : `engine/InfinityEngine-Enhancer/source-patchee/src/iee/features/tile_render.cpp`.
  Il conserve l'alpha hérité pour une texture normale ; quads monde64, UV étendus selon TIS.
- Ce128 est le défaut lu dans le binaire, pas une mesure mémoire universelle. Nouveau moteur,
  hook de blend ou réglage natif différent : requalifier ; ne pas patcher des RVA en dur.

## 3. Inventaire préalable du lot

1. `git status --short` ; préserver le worktree hors tâche.
2. Lire `areas.csv`. Pour chaque zone/variante, relever run/build **sélectionnés**, QA et dépendances.
   Les répertoires et index générés ne choisissent jamais le build.
3. Inventorier les WED référencés réellement ; jour/nuit séparés, sans repli nuit→jour. Recouper
   l'inventaire des ressources avec `areas.csv` pour signaler les zones absentes du catalogue.
4. Résoudre le TIS de l'overlay0 depuis le WED, pas depuis une hypothèse `TIS == nom ARE`.
5. Pour chaque overlay `i>0`, relever resref et bit `1<<i`. Classifier les liquides ; prendre en compte
   les familles reconnues par les outils (`WTWAVE`, `WTRIV`, `WTPOOL`, `WTLAK`, `WTFALL`, `WTURN`,
   `YSPOOL`, `YSRIV`, `YSWAVE`, `WTSWAM`, `WTSEW`, `WTOIL`, `WTLAV`). Inconnu : signaler, ne pas ignorer.
6. Lire **tous** les indices du lookup primaire (`range(start,start+count)`), pas uniquement la frame0.
   Enregistrer : cellule, overlay(s), primaire(s), secondaire, réutilisations et sentinelles.
7. Séparer les couches d'entrée :

   - stock : `bg2lib.load_key/resolve_resource/resolve_tileset_resource`, KEY+BIF, sans override ;
   - installée : TIS/PVRZ/WED effectifs d'override, sinon fallback stock ;
   - production : build sélectionné et maîtres x1/x4 de provenance vérifiée.
8. Si un WED override existe, comparer au stock avant traitement. Les utilitaires stock ne le
   chargent pas automatiquement. Ne jamais l'écraser pour rendre un audit conforme.
9. Geler un manifeste de lot puis une requête par map/variante : sources/hashes, recette, sélection
   des tuiles/interfaces, format et layout, sorties, exclusions, QA et installation séparées.

Repères binaires utilisés par les producteurs (little-endian) :

- WED : nombre d'overlays à0x08, offset table overlays à0x10,24octets/overlay ; largeur/hauteur
  uint16 à+0/+2, resref TIS8octets à+4, offsets tilemap/lookup uint32 à+16/+20.
- Cellule tilemap :10octets, `<HHHB3x>` = start lookup, nombre de frames, secondaire, flags.
  Lookup : indices uint16. Types KEY : WED `0x03E9`, TIS `0x03EB`, PVRZ `0x0404`.
- TIS standalone : `TIS V1  ` puis `<4I>` à+8 = count, entrySize, headerSize, tileDimension ;
  entrée PVRZ `<3I>` = page,x,y à `headerSize + index*entrySize`.
- `resolve_tileset_resource` renvoie les **entrées seules** du TIS en BIF, plus count/entrySize ;
  ne pas appliquer le décalage24 d'un fichier standalone à ce buffer.
- Examiner la sentinelle avant décodage : `area_decode.decode_tis_tiles` la représente en noir
  opaque, ce qui ne permet pas de la distinguer d'une vraie tuile par l'alpha seul.

### Classification obligatoire

| Cas | Action |
|---|---|
| DXT1 source opaque → DXT5, primaire exclusivement eau sans secondaire | Éligible alpha128 si même contrat moteur |
| Source DXT1 → sortie DXT1 | Pas d'alpha128 texture : le natif fournit déjà l'alpha de dessin |
| Source alpha partiel, DXT5 natif, palette de base ou format autre | Audit du mélange requis ; pas de conversion automatique |
| Primaire partagé avec terre/secondaire/autre rôle | Refuser la modification de l'ID partagé ; traitement dédié |
| ID utilisé à plusieurs coordonnées | Alpha possible seulement si tous les usages sont compatibles ; RGB seulement si toutes les corrections requises sont identiques |
| `count>1` primaire | Inventorier toutes les frames ; les producteurs AR0900 exigent count1 et ne suffisent pas |
| Plusieurs overlays/liquides superposés | Contrôler le chemin et la famille de chaque cellule ; pas de masque universel |
| Sentinelle / slot partagé / layout sans padding / source manquante | Rapport bloquant par cible ; aucun contournement silencieux |

`audit_water_area.py` et `audit_area_preflight.py` sont utiles à l'inventaire, **pas décideurs** :
leur recommandation `--transparent-full-water-base` est invalidée pour le contrat ci-dessus.
`audit_water_area.py` ne parcourt que la première frame primaire et sa politique lave est obsolète.

## 4. Configuration : conserver la composition native

Dans `config://bg2ee_game_root/InfinityEngine-Enhancer.ini` :

```ini
[Shaders]
EnableWaterEffect = false
```

- Désactiver l'effet, **pas** le hook de tuiles xN ni toute la suite shader.
- Shader concerné : `engine/InfinityEngine-Enhancer/source-patchee/assets/override/fpSEAM.glsl`.
  Quand actif : `texColor.a=max(texColor.a,waterMask)` recouvre l'overlay ; la passe secondaire
  est annulée par `alphaScale=0` pour `0.15<vColor.a<0.9`. Quand désactivé : cette substitution
  et cette annulation ne s'appliquent plus.
- `EnableDebugHotkeys=false` sur le témoin ; éviter une bascule involontaire F10 pendant QA.
- AR0900 n'a requis aucune recompilation DLL pour cette réparation. Si la configuration change,
  suivre la transaction renderer documentée, DLL existante inchangée + nouvelle INI, jeu fermé.
- Portée globale du commutateur : contrôler aussi les familles lave/égouts/marais/huile auparavant
  dépendantes du matériau procédural. Leur rendu n'est pas qualifié par la seule QA de WTLAKE.
- **Divergence release au 2026-09-12** :
  `releases/BG2-HD-Upscale/manifests/runtime-compatibility.json`,
  `owned_ini_keys.core-steam.Shaders.EnableWaterEffect` vaut encore `true` ; les INI sample aussi.
  Prévoir une décision Core/release distincte pour éviter qu'une installation réactive le défaut.
  Ne pas reconstruire payload/staging/content/archive ni modifier un bundle scellé implicitement.

## 5. Overlay animé : supprimer les coutures de répétition

### Réutilisation prioritaire

- Autorité : `releases/BG2-HD-Upscale/manifests/overlay-sources.json`, à relire au lancement du lot.
- WTLAKE déjà réparé :
  `maps/technical-overlays/WTLAKE/runs/seedvr2-7b-int8-wavelet-periodic-x4/04_build_x4`.
  Réutiliser les octets de cette version, pas une nouvelle inférence par map.
- État au 2026-09-12 : WTLAKE x4 périodique ; WTPOOL et WTLAKA/B/C/D x2 ; WTSWAM/WTSEW/WTOIL
  stock ; WTLAVA/B/C/D x4 selon manifeste. Cette sélection n'est pas une QA de leur combinaison
  avec la présente réparation. Le x4 WTPOOL a un antécédent de cycle figé.
- Pas d'override pour une famille déclarée stock. Ne pas utiliser WTLAKE comme substitut d'un autre
  resref. Une réparation d'overlay partagé se réalise une seule fois, avec sa propre QA/transaction.

### Recette WTLAKE exécutée et validée

1. Extraire les6 frames natives64×64, indices0..5 inchangés. Source palette TIS dans
   `data/ARMisc.bif`, via KEY. `extract_legacy_tis_frames.py` gère ces entrées5120octets :
   palette256×4 BGRA + indices64×64 ; octet3 de palette **non alpha**. WTLAKE : alpha255.
2. Séparer RGB et alpha. Pour chaque frame, créer un canvas192×192 contenant **9 copies de cette
   même frame**, disposition3×3, sans intervalle. Répéter également l'alpha. Ne pas concaténer les
   six instants d'animation comme contexte spatial.
3. Inférence RGB seule avec `upscale_animation_frames.py`, paramètres ci-dessous ; alpha source
   agrandi nearest, jamais généré par SeedVR. **`--pad 0`**, sinon réintroduction d'un cadre artificiel.
4. Sortie768×768 ; extraire `(left,top,right,bottom)=(256,256,512,512)`, donc le centre256×256.
   Même recadrage RGB/alpha ; conserver ordre et nombre de frames. Renommer pour le builder
   `frame-000.png`..`frame-005.png` (l'upscaler utilise `frame_000.png`).
5. `build_upscaled_legacy_tis.py` : TIS12octets/entrée, header24, dimension256, DXT5/PVR11,
   atlas2048×2048, padding RGBA répliqué4px,6 entrées ; sorties WTLAKE.TIS + WLAKE00.PVRZ.
6. Vérifier répétition3×3 de chaque résultat, cycle complet, alpha et hashes installés.
   Ne modifier ni vitesse, ni table de frames, ni géométrie WED.

| Paramètre SeedVR | Valeur validée |
|---|---|
| Workflow | `pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json` |
| SHA256 workflow | `30DEC619A4C1A3ECDE076C0926A5ED8EE29D5F2CA8B4EB89A75D3B5F7811B61E` |
| Modèle / VAE | `seedvr2_7b_int8_convrot.safetensors` / `seedvr2_ema_vae_fp16.safetensors` |
| dtype / scale / resize | `default` / 4 / Lanczos |
| seed / steps / CFG | `959948902156062` / 1 / 1 |
| sampler / scheduler / denoise | Euler / simple / 1 |
| couleur overlay | **wavelet** ; la recette map reste LAB |
| VAE encode et decode | tile512, overlap128, temporal4096, temporal overlap8 |
| padding du runner | 0 ; géométrie uniforme192×192 |

Invocation historique équivalente, **écrit des sorties** ; appeler uniquement depuis l'exécution
autorisée du lot, pas comme préflight :

```powershell
python -B pipeline/scripts/upscale_animation_frames.py <rgb-periodique> <alpha-periodique> <nouveau-upscale> --scale 4 --pad 0 --color-correction-method wavelet --workflow pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json
python -B pipeline/scripts/build_upscaled_legacy_tis.py WTLAKE <frames-centre-x4> <nouveau-build>
```

Mesure : `seam_x=mean(abs(RGB[:,-1]-RGB[:,0]))`, divisée par la différence moyenne entre colonnes
adjacentes intérieures ; idemY, calcul en float. Moyennes6frames : LAB x4 `12.822/17.914` ;
wavelet non périodique `25.775/30.313` ; wavelet périodique `1.166/0.948`.
Ce sont des témoins, pas des seuils universels. **Wavelet seul et padding atlas seul ne corrigent
pas un contexte d'inférence non périodique.**

## 6. Base de map et vrais masques de rive

1. Réutiliser le build x4 sélectionné si son RGB et ses vrais contours sont corrects. Conserver
   ses paramètres/page-layout ; ne pas refaire toute la map pour modifier l'alpha central.
2. Vérifier les maîtres x1 primaire/secondaire et les maîtres x4 associés par hash et dimensions.
   `render_secondary.py` conserve le primaire dans les cellules sans secondaire ; ailleurs il
   substitue le secondaire. Ce maître contient donc une eau continue utile comme donneur RGB.
3. Si un nouveau build est nécessaire : RGB x4 de chaque état à sa propre position WED,
   alpha natif restauré séparément, dimensions exactes, aucun upscale de l'alpha par IA.
   Le builder courant adoucit bilinéairement les masques non opaques.
4. Conserver DXT5 pour les contours graduels. Ne pas forcer DXT1 pour contourner la différence de
   blend ; cela détruirait les graduations d'alpha.
5. **Ne pas utiliser `--transparent-full-water-base` pour le chemin natif réparé.** Si son alpha0
   existe déjà, corriger directement vers128 sur la population éligible (§7). L'essai255 rejeté
   n'est pas une étape intermédiaire à reproduire.
6. La base AR0900 retenue comporte une spline : `fit_error_x4=1.0`, `sample_spacing_x4=1.5`,
   `supersample=2`, contours du canvas WED complet primaire/secondaire. Unités réellement x4
   dans `build_spline_map_alpha.py`, malgré l'ambiguïté du guide général.
7. Ne pas rajouter de spline à un build déjà traité, ni de feather5.0 (variante non retenue ici).
   Ne pas repasser les surfaces alpha128 dans une spline binaire à seuil127 : séparer le masque
   géométrique de l'opacité de mélange. Si une spline est requise : géométrie avant alpha128.
8. Le script spline historique réencode les pages et ne refait que l'intérieur des tuiles, pas
   leurs marges. Il n'offre pas une garantie générale de RGB bit-exact. Pour une implémentation
   nouvelle, remplacer uniquement les blocs alpha nécessaires, puis traiter §8 les faux contours
   et leurs marges. Préserver la spline des **vraies** rives/trous/îlots.

Pas de redécoupe par tuile isolée pour l'upscale de la map. Recette maîtres AR0900 : SeedVR7B/LAB,
x4, grille2×5, marge interne128px x1 puis retrait512px x4 ; réutiliser ces maîtres existants.
La découpe des autres maps suit leur propre recette, pas systématiquement2×5.

## 7. Alpha central : patch DXT5 sans réencoder le RGB

### Sélection

Pour chaque ID primaire, agréger **tous** ses usages. Éligible seulement si :

- tous les usages sont des cellules d'eau reconnues, sans secondaire (`0xFFFF`) ;
- aucun usage secondaire ni usage hors eau ;
- source non sentinelle, DXT1/PVR7, alpha255 sur toute la tuile native ;
- destination DXT5/PVR11 ; contrat natif du §2 confirmé.

AR0900 :775IDs éligibles,775cellules ;860autres cellules d'eau avec secondaire. Ces nombres ne
sont des assertions que pour AR0900 jour, pas des constantes du lot.

### Écriture exacte

- PVRZ = taille décompressée uint32 LE puis flux zlib. PVRv3 : header52octets + metadata.
- `pixelFormat` uint64 à offset8 ; height/width offsets24/28 ; metadataSize offset48.
  Données DXT à `52+metadataSize` ; conserver intégralement header et metadata.
- Bloc DXT5 de4×4px =16octets : `[0:8]` alpha ; `[8:16]` RGB.
- Remplacer seulement l'alpha par `80 80 00 00 00 00 00 00` hex : endpoints128, indices0.
- Inclure intérieur **et marges atlas**. AR0900 : UV(x,y), zone
  `[x-4,x+256+4) × [y-4,y+256+4)` =264×264 =66×66blocs.
- Adresse d'un bloc : `dataOffset + ((py//4)*(width//4) + px//4)*16`.
- Rejeter tout chevauchement avec un autre slot ou débordement ; la marge4 ne se déduit pas
  universellement du TIS. Prouver le layout du build avant d'écrire autour d'une tuile.
- Préserver tous les octets RGB et tout alpha hors sélection ; re-zlib niveau9, relire/décompresser.
- Ne pas toucher aux TIS, WED, secondaires ni à l'alpha de l'overlay animé.

Référence de code figée :
`maps/AR0900/runs/voie1-native-blend-alpha128-x4-jour-20260912/build-candidate.py`.
Le script original attend un préflight temporaire voisin aujourd'hui non livré sous ce nom dans
le run ; le snapshot conservé s'appelle `water-audit.json`. Adapter les entrées, ne pas le lancer
aveuglément. Pour le lot, produire directement cette correction depuis le build sélectionné.

## 8. Raccords internes : RGB contaminé et faux alpha secondaire

### 8.1 Diagnostic à reproduire par cible

- Comparer même cellule/bord dans : source native, morceau x4 brut, maître primaire assemblé,
  maître secondaire assemblé, PVRZ avant/après traitement. Distinguer l'origine RGB de l'alpha.
- AR0900 primaire1958 : bord RGB x1 `(115.40,119.97,102.32)` ; maître primaire x4
  `(37.03,34.13,24.27)` ; pixel intérieur voisin trop clair `(136.29,143.95,124.65)`.
  PVRZ avant/après spline identique sur ce bord `(30.35,29.01,18.02)`.
- Le morceau brut porte déjà le défaut : origine dans la chaîne d'upscale au contact du noir,
  avant assemblage/DXT ; la responsabilité fine Lanczos/modèle/LAB n'a pas été isolée.
- Donneur secondaire x4 à **la même cellule** : bord `(116.76,120.83,104.28)`, sans creux noir.
- Secondaire5020 côté voisin : alpha255 avant spline ; après spline bord moyen190.46,
  20pixels0/240,93pixels255/240 ; intérieur à4px≈255. Faux contour dû aux cellules sans secondaire
  laissées noires dans `assemble_mask`, pas une rive réelle.

### 8.2 Masque de sélection exécuté sur AR0900

Notations : `P` = primaire, `S` = secondaire, `aP/aS` = alpha **stock décodé x1**.

1. Canvas booléen eau x1, taille `(wedHeight*64,wedWidth*64)` :

   - hors cellules d'eau : faux ;
   - eau sans S, P éligible au §7 : vrai sur toute la cellule ;
   - eau avec S : vrai seulement où `(aP==0) & (aS==255)`.
2. `safe = binary_erosion(water, structure=ones((3,3)), border_value=0)` : garde1px x1 autour
   des vrais bords. Ne pas construire ce masque depuis le RGB noir ni l'alpha x4 déjà corrigé.
3. Énumérer uniquement les interfaces cardinales d'une cellule éligible sans S vers une cellule
   voisine d'eau **avec** S, de famille compatible. Ni interfaces terre/eau, ni centre/centre.
4. À chaque position le long de l'interface, exiger les2pixels x1 adjacents à la frontière
   `safe=true` de chaque côté. Exemple bord droit de P :

   ```python
   valid_rows = own_safe[:, -2:].all(axis=1) & neighbor_safe[:, :2].all(axis=1)
   along_x4 = np.repeat(valid_rows, 4)
   ```

   Transposer pour haut/bas, inverser pour gauche. Aucun `valid` : interface ignorée et comptée.
5. Bande de8px x4 vers l'intérieur de chaque tuile, limitée aux positions valides. Le masque
   augmenté aux blocs4×4 doit rester entièrement dans `safe` ; sinon refuser/resserrer, pas déborder.
6. Vérifier les réutilisations d'IDs et de slots. Le script témoin exige des IDs uniques par cellule,
   ensembles primaire/secondaire disjoints et `count==1`. Ne pas supprimer ces garde-fous sans
   prendre en charge explicitement les usages multiples.

### 8.3 RGB primaire : greffe bornée

- Donneur = maître secondaire x4, **même coordonnée WED que le primaire à réparer**, pas le RGB
  de la tuile secondaire voisine. `render_secondary.py` y a conservé l'art primaire, mais avec
  contexte d'eau continu. Vérifier cet invariant et la continuité du donneur avant greffe.
- Crop donneur : `(col*256,row*256,(col+1)*256,(row+1)*256)`.
- Distance intérieure au bord `d=0..7`, poids donneur : `[1,1,1,1,0.75,0.5,0.25,0]`.
- `fixedRGB = round(currentDecodedRGB*(1-w) + donorRGB*w)`, float32, clamp0..255 → uint8.
  Si plusieurs côtés se croisent, fusionner les poids par `maximum`, pas addition.
- Alpha primaire128 conservé intégralement. Répliquer RGBA du bord réparé sur4px de padding.
- Encoder la tuile264×264 en DXT5 ; recopier **seulement les8octets RGB des blocs sélectionnés**
  dans le flux original de la page. Ne pas réencoder toute la page ; les autres blocs restent exacts.
- La 8e ligne/colonne a un poids0 mais appartient à un bloc sélectionné : sa quantification DXT
  peut évoluer. La garantie d'identité hors masque se mesure au niveau des blocs4×4.

### 8.4 Alpha secondaire : enlever seulement le faux contour

- Sur la bande voisine sélectionnée en8.2, restaurer255 (sa valeur stock prouvée), sans feather.
- Inclure les marges correspondantes en étendant le masque par réplication4px.
- Blocs alpha DXT5 : `FF FF 00 00 00 00 00 00`. Conserver leurs8octets RGB d'origine.
- Ne pas forcer tout le secondaire à255 ; conserver les vrais contours et tous les autres alpha.
- Le DrawAlpha128 natif du secondaire reste chargé de son mélange avec l'animation.

### Référence et résultat

- Producteur complet :
  `maps/AR0900/runs/voie1-water-rgb-seams-x4-jour-20260912/build-candidate.py`.
- Requête : `request.json` ; sélection exhaustive des502interfaces, positions éligibles, hashes.
- Contrôles : `repair-report.json` ;285tuiles RGB primaires,358tuiles alpha secondaires,
  94909blocs RGB modifiés,97794blocs alpha secondaires modifiés,0horsmasque ; TIS inchangé.
- Ce patch suppose x4, atlas4096, slots264 et count1. Le lot doit lire les dimensions effectives,
  conserver les layouts2048 valides et traiter/refuser explicitement les autres cas.
- Ne pas généraliser la greffe si le donneur n'est pas propre/équivalent : signaler la cible et
  produire un essai local justifié. Aucun remplacement par une texture d'une autre map.

## 9. Contrôles avant installation

Pour chaque map/variante :

- TIS : signature, dimensions, nombre d'entrées et indices ; layout inchangé pour un post-patch.
- Reconstruction depuis maîtres : `0 resampled` ; tout fallback vers une tuile native redimensionnée
  doit bloquer la cible ou faire l'objet d'une exception documentée, jamais être masqué.
- Pages : inventaire exact, format attendu, dimensions, single-surface/single-mip ou rejet explicite,
  taille décompressée correcte, metadata conservée,0OOB, resrefs≤8caractères.
- Ne pas forcer atlas4096 partout. AR0900 historique :26pages4096 ; le jour pourrait tenir sur
  davantage de pages2048, la nuit a un namespace plus court. Conserver le layout existant.
- Alpha128 exact dans toutes les primaires centrales sélectionnées **et leurs marges**.
- Alpha255 exact uniquement dans les bandes secondaires internes validées.
- RGB bit-exact hors blocs de greffe ; alpha bit-exact hors masques explicitement prévus.
- Masques de greffe et expansion DXT disjoints du décor/des vraies rives.
- Aucun changement des géométries ARE/WED, cycles, cadence, overlays exclus ou autre variante.
- Relecture des fichiers écrits, pas uniquement assertions sur buffers mémoire ; hashes des
  sorties, de leurs sources et du producteur. Hash d'ensemble : `inject_build.aggregate_hash`.
- Contrôler visuellement des raccords horizontaux/verticaux, angles, rives et îlots, plusieurs frames
  d'overlay. Une moyenne de bord correcte ne prouve pas à elle seule l'absence de couture.

`verify_upscaled.py` ne valide que le rendu RGB statique primaire et écrit toujours une miniature
dans le build : **ne pas le lancer sur un run déjà scellé**. Utiliser un espace de vérification
séparé/un validateur en lecture seule ; ajouter des contrôles RGBA et secondaires au producteur.
PSNR seul n'établit ni le blend, ni l'animation, ni la QA.

## 10. Installation, QA et généralisation

1. Construire un nouveau candidat complet dans un nouveau run ; pas de modification en place.
2. Fermer BG2EE/BaldurReal et InfinityLoader avant toute installation/restauration.
3. Vérifier que l'état live correspond encore au snapshot initial ; sinon arrêter cette transaction.
4. Prévalidation puis installation via `inject_build.py`, avec sauvegarde et reçu. Ce script legacy
   écrit à l'appel `install` ; réserver l'appel à l'exécution explicitement autorisée du lot.

   - `install <TIS-resref> <nouveau-build> --verify-only` ; vérifier aussi les fichiers à retirer ;
   - `install <TIS-resref> <nouveau-build>` ;
   - `verify <backup-dir>` ; comparaison live/build + sauvegarde ;
   - `restore <backup-dir>` pour retour arrière, jeu fermé.
5. Overlays partagés et renderer : transactions séparées, dédupliquées ; pas de wildcard jour
   englobant la nuit (`A0900*.PVRZ` attrape aussi `A0900N...`). Utiliser l'inventaire TIS exact.
6. QA utilisateur par cible : ombres/reflets, centre animé, raccord centre/bords, absence de carrés
   bleus et traits noirs ; plusieurs zooms, déplacement caméra, pause/reprise, rechargement,
   entrée/sortie de zone, automap. Nuit séparée si présente.
7. Avant déploiement global : échantillons de plusieurs structures/familles. Audits antérieurs
   DXT1→DXT5 : AR0300(892sansS/374avecS), AR0204(218/443), AR0046(18/30),
   AR1200(154/491), AR1100(48/495). **Preuves structurelles seulement**, pas QA ingame.
8. Traiter toutes les cibles éligibles ; rendre une liste explicite des réussites, exclusions,
   échecs et besoins QA. Ne jamais annoncer « tout le jeu corrigé » avec des familles non couvertes.
9. Après validation explicite : sélectionner le run/build exact dans `areas.csv`, variante correcte,
   avec reçu/hash et QA. Aucun `animation_workflow.py finalize` pour les maps : ce workflow concerne
   les animations, pas cette autorité.
10. Demander séparément l'intégration release. WTLAKE périodique figure déjà dans son manifeste ;
    le correctif map AR0900 et la configuration native ne sont pas automatiquement intégrés.

### Travail à réaliser par la prochaine tâche

- Créer un orchestrateur de réparation paramétré, **plan-only par défaut**, exécution `--run`,
  reprise par requête/source hashée et refus d'écraser. Unité : map + variante, overlay dédupliqué.
- Traiter les pages une par une, réutiliser le décodage stock/masques et ne recomprimer que les pages
  touchées. Borne mémoire par map ; éviter les canvas RGB float64 complets pendant le batch.
- Réutiliser les producteurs figés comme référence d'algorithme ; ne pas généraliser leurs IDs,
  offsets de page, hashes, chemins temporaires ni leurs suppositions d'unicité.
- Corriger les recommandations des audits et raccorder la recette au builder pour éviter qu'un
  futur rebuild réintroduise alpha0, alpha255 central ou faux raccords. Garder le mode natif explicite.
- Idempotence : fixer l'alpha cible, ne pas le multiplier à chaque passe ; repartir d'une source
  scellée connue et ne pas appliquer une seconde greffe sur une sortie déjà réparée.
- Pas de nouvelle inférence globale si les RGB existants conviennent. Donneur absent ou corrompu :
  restaurer la provenance ou créer une nouvelle production autorisée ; aucun fallback Lanczos caché.
- Code modifié : préparer uniquement `test_changed.py --targeted --path <fichiers-du-lot>`, puis
  demander ciblés/tous/aucun. Tests à prévoir : sélection multi-usages/multi-frames, sentinelles,
  masque vraie rive/interface interne, padding, DXT bit-exact, jour/nuit, refus formats inconnus,
  périodicité/frame-order des overlays, transaction/reprise sans double application.
- Aucune exécution automatique de tests. Projections : seulement au jalon convenu, plan séparé,
  accord scopes ciblés/toutes/aucune. Aucun packaging implicite.

## 11. Référence AR0900 : chemins, empreintes et résultat accepté

Racine `R = maps/AR0900/runs/` ; `M = seedvr2-7b-int8-lab-grid-2x5-x4-jour`.

| Étape historique | Run/build sous R | Rôle |
|---|---|---|
| Base avec contour spline | `M/05_build/x4-water-alpha-antialias-page4096-spline-fit1.0` | RGB conservé ; ancien alpha0 central erroné |
| Essai255 rejeté | `voie1-source-alpha-x4-jour-20260912/05_build/x4-source-alpha-preserved-spline-fit1.0` | Art revenu mais centre statique ; ne pas reproduire |
| Mélange natif | `voie1-native-blend-alpha128-x4-jour-20260912/05_build/x4-native-alpha128-spline-fit1.0` | Centre animé/reflets, fins traits noirs encore présents |
| **Final validé** | `voie1-water-rgb-seams-x4-jour-20260912/05_build/x4-alpha128-water-seams-repaired` | Eau entièrement corrigée selon retour utilisateur |

- Stock AR0900/AR0900N : `data/AREA0900.bif` du jeu configuré, résolution via KEY.
- Maîtres x1 :
  `maps/AR0900/rendus-x1/tuiles-principales/AR0900-tuiles-principales-x1.png` ;
  `maps/AR0900/rendus-x1/tuiles-secondaires/AR0900-tuiles-secondaires-x1.png`.
- Maîtres x4 sous `R/M/` :
  `tuiles-principales/03_assemble/AR0900-tuiles-principales-x4-seedvr2-7b-int8-lab-overlap.png` ;
  `tuiles-secondaires/03_assemble/AR0900-tuiles-secondaires-x4-seedvr2-7b-int8-lab-overlap.png`.
- Dimensions5120×3840x1 /20480×15360x4 ; WED80×60 ; TIS5752tuiles ;27fichiers finaux.
- Les vieux manifests mentionnent `maps/maps-principales/AR0900/...` ; le chemin canonique actuel
  est `maps/AR0900/...`. Résolution admise seulement après vérification du hash, sans réécriture.
- Reçu final : `backups/maps/AR0900-20260911T235034477666Z-b986b035/install-backup.json`.
  Sauvegarde = candidat alpha128 précédent ;0fichier retiré ; live revérifié le 2026-09-12.
- Capture de localisation **avant** dernier correctif : `20260912012622_1.jpg`. Ne pas la présenter
  comme preuve visuelle du résultat final ; QA finale = retour explicite utilisateur de cette tâche.

| Objet | SHA256 |
|---|---|
| Maître primaire x1 | `4217E730B637B1262E45437E902ABBBB34AFB2F5F06167452451E3EEB529EBA4` |
| Maître secondaire x1 | `DD446926F8F201DA882F95EDBF9F46C9B6378C22DE1F6189A1860ADA33603002` |
| Maître primaire x4 | `6D650626C0201CF2A1E2259223199B2BF3197E07F7D4B007F113BE130F4779DF` |
| Donneur secondaire x4 | `8C0BEDC4C440994857ABFD26EA4F450A78053A6DAC1E88B3D522E420687AA764` |
| WED stock | `471B1A2A5FBF4D78DDDF44851E8A95F18CDA6883B6C048D3382BC84AEE67092A` |
| TIS x4 inchangé | `4671AE969FDAC1AF919D1D4B887E8581BC4DC6513A727CD73775A1D1E14696F8` |
| Ensemble essai255 | `C7862BBA6C8501271983F62D2244B2318C137677DA938BCD273146A168A55860` |
| Ensemble alpha128 | `9DE7EDB09EBD019B45DA1DC1EB3064A88846C8905561D55A35EEB4FDD86D953B` |
| **Ensemble final installé** | `59DBB058B087D1AD9C1D06A295E7A774D2DF1C6DBA182A2EE8912C467D30E4E8` |
| Producteur alpha128 | `984E1F34F393298F34647CB077C5D2DA70617307D741221573391C591ED2E789` |
| Producteur raccords | `E54B013FA868D176118D2F0CDDA1D836E0382118CCBB49EDE89F5B71B01F5228` |
| WTLAKE.TIS périodique x4,96octets | `1743A734B7E94FA60AB927B6615933DBDF7B5BF998019C66428413801BB62EE1` |
| WLAKE00.PVRZ,166525octets | `BCC99E2E6E2881E9D216687044A661C68EC42D0EEC1A4103C341894BB5E2FA10` |
| DLL témoin | `8FF3629FEEDB61453B3D316C2C6534F5D109C4390DDE723E39311066A99B9648` |
| INI témoin, effet désactivé | `93EA39BD9BFDCDBB24A38809964B034FF649AD3FF5A621D169B8721181BCAFFC` |

Témoins zéro-based pour contrôle de non-régression :

| Primaire / cellule | Côté | Secondaire voisin / cellule | RGB moyen bord après patch |
|---|---|---|---|
| 1958 / (38,24) | droit | 5020 / (39,24) | (116.70,121.08,103.79) |
| 2039 / (39,25) | droit | 5042 / (40,25) | (83.22,96.10,83.23) |
| 2121 / (41,26) | droit | 5067 / (42,26) | (79.26,92.60,80.94) |
| 2036 / (36,25) | bas | 5066 / (36,26) | (52.91,67.11,64.47) |

Mesures sur240pixels de bord, coins8px exclus. Atlas/UV exacts dans `repair-report.json`.
Les hashes du témoin servent à vérifier les références, pas à imposer les mêmes ressources aux
autres maps. Les artefacts lourds sont locaux/ignorés ; cette notice contient la recette même si
les scripts temporaires du premier diagnostic ont disparu.
