# Contours devant l'eau — méthode généralisable proposée

2026-09-23. **Étude puis masque local accepté ; correctif couleur/BC3 installé sur demande utilisateur.**
État courant : [essai installé AR1600](AR1600_CONTOURS_ESSAI_20260923.md), zone bateau uniquement,
validation ingame en attente. Les constats et propositions ci-dessous décrivent l'étude initiale.
Demande : lisser les silhouettes grossières/crénelées visibles sur le bateau de Brynnlaw.
Capture : `E:/Steam/userdata/5536307/760/remote/257350/screenshots/20260923075756_1.jpg`.
Périmètre : objets intégrés au décor et interfaces des surfaces liquides. Les sprites de personnages
ont un autre chemin de rendu ; ils ne doivent pas recevoir cette correction de TIS.

## Décision proposée

Un traitement commun est possible : **reconstruction du contour en coordonnées WED + couverture
antialiasée + RGB propre sur la frontière + composition primaire/secondaire cohérente**.
Le matériau liquide ne détermine pas le lissage. Les adaptations utiles dépendent de la largeur
locale de l'objet, de la topologie et du contrat des passes, pas du nom de la map.

Ne pas appliquer simplement un flou à toute la map ou un rayon gaussien uniforme à tous les alphas.
L'interpolation30 FPS traite le temps ; elle ne corrige ni les silhouettes fixes ni leur RGB.

## Constats vérifiés sur AR1600

Sources : WED/TIS/PVRZ vanilla via `G:/AI/BG2_Vanilla_23534562/chitin.key`, fichiers du jeu
`config://bg2ee_game_root/override`, scripts de production, `fpSEAM.glsl` et capture utilisateur.

| Observation | Preuve | Conséquence |
|---|---|---|
| Masques natifs à basse résolution | 64×64 par cellule ; 587 cellules d'eau, dont421 avec secondaire | L'upscale RGB ne reconstruit pas leur géométrie |
| Alpha déjà adouci dans le HD | Les361 primaires à masque mixte0/255 possèdent toutes des alphas intermédiaires installés | Ce n'est pas simplement un oubli du bilinéaire |
| Ancienne silhouette encore suivie | Exemples cellule `(25,32)`, primaire1817 ; `(26,32)`,1818 | Le bilinéaire adoucit la marche sans redresser la trajectoire |
| Complémentarité native | `alphaP+alphaS=255` sur les1 724 416 pixels des421 paires x1 examinées | Les deux couches doivent partager une même frontière géométrique |
| RGB noir révélé par le masque doux | 451 860 pixels avec alphaHD>0 dans le support transparent du masque natif agrandi nearest ; 262 939 ont RGB=(0,0,0), soit58,2% ; 388 167 ont max(RGB)≤8, soit85,9% | Étendre/adoucir l'alpha seul expose le fond noir ; risque de frange sombre confirmé dans les données |
| Antialiasing global absent | INI : `EnableFullFrameFXAA=false`, `EnableFullFrameSSAA2x=false` | Aucun correctif global ne masque le problème ; l'activer seul ne répare pas les assets |

Mesures ci-dessus : pixels décodés des textures, pas mesure de leur poids final à l'écran.
Le RGB noir sous un alpha nul n'est pas une erreur en soi ; il devient problématique lorsque
l'adoucissement, le filtre ou un déplacement de contour lui donne une contribution visible.
La part exacte du liseré due au RGB, à la géométrie et aux passes reste à comparer dans un essai.

Exemple vérifiable installé : `AR1600.TIS`, primaire1817, `A160037.PVRZ`,
rectangle `(1060,4,256,256)`, celluleWED `(25,32)` en indices0 ; secondaire2767.
Diagnostics de lecture :

- `.tmp/ar1600-contour-study-20260923/rgb-edge-statistics.json`.
- `.tmp/ar1600-contour-study-20260923/decoded-edge-samples.png` : masque natif agrandi,
  alpha installé, RGB installé, composition indicative sur turquoise. Ce n'est pas une capture ingame.

## 1. Séparer géométrie et opacité

Entrées nécessaires : WED/variante, séquences et états, TIS/PVRZ natifs, RGB x4 courant, ARE,
identité runtime et rôles effectifs primaire/secondaire. Résoudre les alias depuis le WED ; ne pas
chercher seulement des noms `WT*`, les overlays de l'essai s'appellent `QALAK0/R`.

- Extraire le masque de présence de l'objet depuis l'alpha **natif** et son rôle WED.
- Garder séparée l'opacité de l'art marin : `a`, ARE0→128 par défaut, mais100/160 existent.
- Ne jamais binariser l'alpha HD entier à127 : une centrale d'eau à128 deviendrait un objet opaque.
- Ne pas utiliser le noir RGB comme segmentation : il contient aussi ombres et détails légitimes.
- Reconstituer les contours dans l'espace de la map, avec tous les trous, îlots et états utiles.
  Une frontière d'atlas ou de tuile n'est pas une frontière d'objet.
- Les overlays animés et leur timeline restent inchangés pour cette correction spatiale.

## 2. Reconstruire une trajectoire, puis rasteriser sa couverture

Approche privilégiée à évaluer : vectorisation du masque natif, segments droits/courbes de Bézier
avec coins conservés, puis rastérisation suréchantillonnée à la résolution x4. Potrace est une
brique locale existante ; une spline contrainte reste une alternative. Une spline périodique sans
contraintes peut arrondir les angles de ponts et déformer les pointes de voiles.

Contraintes communes :

- Préserver composantes connexes, ouvertures et voisinages ; aucune suppression de « petite tache »
  automatique : il peut s'agir d'un cordage ou d'un trou entre deux pièces de gréement.
- Borner le déplacement de la frontière ; la tolérance d'un ajustement spline n'est pas, à elle
  seule, une borne maximale de déplacement.
- Autoriser de petits déplacements des deux côtés dans cette bande. Une intersection systématique
  avec le masque d'origine conserverait ses encoches et amincirait les diagonales.
- Conserver les coins réels ; éviter de transformer les pentes faibles en succession d'arrondis.
- Générer un alpha de **couverture** par aire sous-pixel ; ne pas rebinariser après réduction.
- Calculer depuis le contour entier, puis découper en blocs de travail avec halo ; ne pas
  vectoriser chaque tuile indépendamment. À14336×12032, un suréchantillonnage intégral serait coûteux.

Réglages de départ de l'étude ; application locale décrite dans l'essai en fin de document :

| Paramètre | Première plage à comparer |
|---|---|
| Déplacement maximal, objets larges | 0,25–0,5px x1 =1–2px x4 |
| Suréchantillonnage de rasterisation | 4× par axe relativement au x4 final, par blocs avec halo |
| Largeur antialiasée | Couverture sous-pixel ; éventuel adoucissement supplémentaire limité à1–2px x4 |
| Trait fin | Déplacement plafonné par sa largeur locale ; pas d'érosion systématique |

La contrainte topologique décide du repli local si un réglage efface une corde, fusionne deux
objets ou ferme un trou. Ce repli est automatique par caractéristique, sans recette spécifique ARxxxx.

## 3. Réparer le RGB de bord avec la même géométrie

Objectif : les nouveaux pixels partiellement couverts doivent porter la couleur de l'objet,
pas le noir de détourage ni la couleur de l'eau située de l'autre côté.

1. Définir une bande de travail étroite autour de la frontière, avec les pixels nouvellement
   couverts et la portée du filtre. Le cœur texturé reste inchangé.
2. Extrapoler les couleurs depuis l'intérieur **du même objet**, sans traverser un trou, une corde
   voisine, une ombre séparée ou une frontière de matériau. Moyenne pondérée/orientée locale ;
   éviter la copie brute du pixel le plus proche, qui peut étirer les textures.
3. Pour une corde sans cœur assez épais : réduire la profondeur du donneur, préserver les couleurs
   de son axe et la largeur ; signaler le cas sans donneur fiable au lieu de l'effacer.
4. Ne pas supprimer tous les traits sombres : distinguer le bord noir de détourage d'une ombre ou
   d'un trait appartenant réellement au dessin. La statistique de noir n'est pas un masque de suppression.
5. Faire les opérations de rééchantillonnage RGBA en prémultiplié en interne si nécessaire,
   puis exporter selon le contrat runtime existant, ici RGB droit + alpha. Ne pas prémultiplier
   les textures une seconde fois lors du mélange `SRC_ALPHA`.

La génération SeedVR n'est pas nécessaire pour cette étape. Les couleurs validées à l'intérieur
des objets et de l'eau sont conservées. Un remplissage RGB borné peut être nécessaire même avec
un alpha parfait : l'upscale RGB a parfois dessiné le liseré lui-même.

## 4. Apparier les couches et respecter l'ordre des passes

Le code/documentation locale décrit, pour ce chemin : **overlayU → primaireP → secondaireS**,
avec le secondaire modulé par l'alpha marin `a`. Voir
`engine/InfinityEngine-Enhancer/source-patchee/docs/validation/phase0-gates.md`, verdictv15,
et `assets/override/fpSEAM.glsl`, commentaire de la passe secondaire après la base.

Avec un masque binaire, les frontières complémentaires fonctionnent. Avec un masque fractionnaire,
deux mélanges successifs ne sont pas équivalents à une unique couverture : adoucir P et S
indépendamment peut ajouter une frange, même si leurs alphas somment à1.

Modèle simplifié, hors teinte/fondu : `F`=objet, `A`=art de l'eau, `U`=overlay animé,
`M`=couverture géométrique de l'objet ; `a`∈[0,1]=opacité effective du secondaire.

```text
C_voulu = M*F + (1-M) * (a*A + (1-a)*U)
C_passes = a*S*A + (1-a*S) * (P*F + (1-P)*U)

Si S = 1-M et P = M :
coefficient de F = M * (1-a*(1-M)), différent de M dans la transition.
Exemple M=0,5 ; a=0,5 : coefficient de F=0,375 au lieu de0,5.

Compensation possible pour cet ordre et ce contrat précis :
S = 1-M
P = M / (1-a*(1-M))
```

La dernière formule redonne le modèle voulu algébriquement. **Appliquée au témoin AR1600,
elle n'est pas encore validée ingame.** Cas a=1,M=0 : définir P=0 plutôt que diviser0/0. Elle exige des RGB de couches
propres, les mêmes coordonnées de masque et l'ordre/mode de mélange qualifiés. Le résultat est
ensuite perturbé par quantification/compression ; mesurer après décodage.

- Géométrie commune : M. Alphas de texture exportés : adaptés au rôle et au contrat, donc pas
  nécessairement complémentaires après compensation.
- Option assets si `a` est constant dans les passes qualifiées ; option shader ciblée si la
  modulation varie réellement au runtime. Ne pas modifier globalement le mélange moteur.
- Sans secondaire : conserver l'opacité du fond marin ; ne pas appliquer la formule de paire.
- Une porte, un état alternatif, un fondu, la météo ou une autre passe ne peuvent pas hériter
  aveuglément de cette formule. Prévoir une classification du contrat et un repli conservateur.

## 5. Exporter sans recréer de coutures

- Reprojeter le résultat du canvas monde vers les TIS, sans déplacement de géométrieWED.
- Conserver le layout des pages ; régénérer les marges d'atlas concernées, souvent4px x4.
- Respecter les sentinelles et texels réservés au comportement de `seamSample` : pas de
  remplissage RGB global de toutes les zones noires/transparentes.
- BC3/DXT5 : encoder uniquement les blocs nécessaires ; conserver les blocs hors périmètre
  byte-exacts. Le demi-bloc RGB peut rester intact quand seul l'alpha change.
- Comparer le résultat décodé, y compris les éléments fins et les frontières de cellules.
  Un ré-encodage de page entière ne garantit pas un RGB identique.
- Une même tuile utilisée dans plusieurs contextes reçoit une correction commune seulement si
  elle convient à tous. Sinon : isoler ce cas lors d'une production explicitement autorisée.
- Si une identité route2 référence les pages modifiées, recalculer son registre ; ne pas laisser
  la correction de contours désactiver silencieusement l'interpolation30 FPS.

## Briques présentes : réemploi et limites

| Fichier | Partie utile | Limite à traiter |
|---|---|---|
| `pipeline/scripts/build_upscaled_area.py` | Rôles WED, restauration de l'alpha, export | Alpha bilinéaire par tuile ; trajectoire x1 et RGB noir restent possibles |
| `pipeline/scripts/build_spline_map_alpha.py` | Canvas WED, multi-contours, trous/îlots | Seuil>127 confond l'eau128 avec un solide ; couches indépendantes ; ne met pas à jour les marges ; ré-encode les pages entières |
| `pipeline/scripts/build_water_contour_feather.py` | Assemblage du canvas | Rayon5px x4 par défaut trop uniforme pour cordages ; mêmes risques de marges/recompression ; pas de correction RGB |
| `pipeline/scripts/build_spatial_spline_alpha.py` | `potrace_alpha`, `fill_edge_rgb` : vectorisation bornée et couleur de bord | Domaine animations ; travail utilisateur en cours, lu seulement ; adaptation WED nécessaire, aucune exécution/modification |
| `pipeline/scripts/build_liquid_base_x4_trial.py` | Masques par rôle, modifications BC3 bornées, préservation hors blocs | Répare les raccords de tuiles, pas la silhouette de chaque objet |

## Petit nombre de comportements, même pipeline

| Cas détecté automatiquement | Traitement |
|---|---|
| Pont, voile, rive large, architecture | Reconstruction de contour avec coins conservés ; AA étroit ; RGB de bord |
| Corde, filet, brindille, ouverture étroite | Même méthode, tolérance et donneur RGB bornés par la largeur ; connectivité conservée |
| Alpha intrinsèquement doux / art marin translucide | Préserver l'opacité ; pas de conversion binaire ; séparation explicite de la couverture et de la transparence |

Ces comportements traversent toutes les familles de liquides. La variante jour/nuit et le matériau
déterminent les données et l'opacité, pas un jeu arbitraire de paramètres propres à chaque map.

## Validation couleur/ingame proposée, non réalisée

Premier témoin : AR1600, trois régions du bateau : grande diagonale de voile, cordages/filets,
angle du pont et frontière traversant une tuile. Comparer séparément :

1. correction RGB de bord sur la couverture actuelle ;
2. nouvelle géométrie + RGB propre, même contrat de composition ;
3. compensation de paire si les passes observées confirment le modèle ci-dessus.

Cela permettra d'attribuer le gain et de ne pas masquer une mauvaise compensation par davantage
de flou. Contrôle futur : zoom normal/fort, pan, eau en mouvement, normales/pluie, largeur des cordes,
trous des filets, couleurs, frontières de tuiles, absence de nouvelle frange claire/sombre.

Après ce témoin, une rive naturelle et un bassin architectural suffisent pour éprouver la
généralisation initiale ; les portes/états et alphas doux restent des contrats distincts à qualifier.
FXAA/SSAA peuvent ensuite aider le rééchantillonnage à l'écran, mais ne constituent pas la réparation
principale des silhouettes et des couleurs de bord contenues dans les textures.

## Essai de masque AR1600 — 2026-09-23

- Producteur : `pipeline/scripts/preview_water_contours.py` ; lecture vanilla + installation, sorties locales uniquement.
- Résultat retenu pour présentation : `maps/water-batches/runs/ar1600-contour-mask-preview-20260923-v2/`.
- Zone bateau : rectangle WED x1 `(1856,2048,384,320)`, contexte64px ; masque final1536×1280.
- Avant : alpha HD installé aux frontières ; cellules entièrement eau normalisées à0 pour séparer géométrie et opacité marine.
- Après : masque natif vectorisé Potrace, `turdsize=0`, `alphamax=0.8`, `opttolerance=0.1`, `TURNPOLICY_BLACK` ; rastérisation16× native puis réduction par aire à4×.
- Modification bornée à une bande de rayon2px x4 autour des bords natifs ; hors bande byte-exact.118163pixels modifiés, soit6,0101% de la zone.
- Contrôle après seuillage128 : natif et résultat ont1composante de décor (connexité8),110composantes d'eau dont99fermées (connexité4). Égalité des comptes, pas une preuve exhaustive de conservation de chaque détail/épaisseur.
- Le HD actuel a11composantes de décor et104composantes d'eau dont93fermées. La référence géométrique est le natif ; ses différences avec le HD ne sont pas attribuées au nouvel essai.
- Variante `v1` non retenue : politique de jonction par défaut,95composantes d'eau dont84fermées ; `v2` traite les jonctions diagonales selon la connexité native. Ne pas réutiliser `v1`.
- Comparatifs : `comparison.png` (zone complète), `comparison-detail.png` (crop x4 `(400,256,720,512)`, affichage2×). Masques pleine définition : `mask-before.png`, `mask-after.png` ; entrées/hashes/mesures dans `report.json`.
- Limites : masque géométrique uniquement ; RGB inchangé, aucune compensation des passes, aucune compressionBC3, aucune installation. La correction des franges RGB et la composition restent à traiter avant un candidat ingame.

Reproduction (Python avec NumPy/Pillow ; Potrace local `.tools/potracer`) ; choisir une **nouvelle** sortie :

```powershell
python -B pipeline/scripts/preview_water_contours.py --vanilla-root G:/AI/BG2_Vanilla_23534562 --rect-x1 1856 2048 384 320 --output maps/water-batches/runs/ar1600-contour-mask-preview-NOUVELLE-VERSION
```
