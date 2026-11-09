# RESTDUNG — analyse et six propositions Topaz

État : six propositions produites ; contrôles techniques réussis, QA visuelle utilisateur en attente. Comparateur committé séparément : `d3104f90`.

## Évidence locale

- Source : `video/restdung/restdung.wbm`, VP8 1280×720, 15 fps, 91 frames, PTS 0..6 s ; vidéo ≈6,067 s, conteneur/audio ≈7,053 s. Pas de trou temporel (deltas 66/67 ms).
- Analyse : `video/restdung/analysis/treatment-proposals-20261109-v1/` ; `analyze.py`, `metrics.json`, `source-timestamps.json`, `source-timeline.jpg`, `pierre.jpg`, `bois.jpg`, `sol.jpg`, `lumiere.jpg`.
- 7 séquences × 91 frames décodées : source, masters A/B/N1-A/N2-A, nettoyages N1/N2 seuls. Alignement par index ; entrées 720p agrandies Lanczos à 1080p pour mesures/crops.
- Mesures centrales frames 33..63 = 2,2..4,2 s ; crops à 1,2 / 2,8 / 4,2 s. Le premier crop documente aussi le fade-in. Boucle recommandée : 2,2..4,2 s.
- Plan presque fixe ; animation localisée et éclairage fluctuant. Ce plan ne suffit pas à valider une recette d'interpolation pour les travellings du jeu.
- Bandes noires natives conservées. Mesures hors bandes ; pas de changement de cadrage.

## Résultat

| Variante | Pierre HP RMS | Bois HP RMS | Zone éclairée HP RMS | Observation visuelle |
|---|---:|---:|---:|---|
| Source Lanczos | 1,004 | 0,994 | 1,405 | doux, détails peu séparés |
| A Proteus direct | 0,949 | 0,988 | 1,447 | amélioration discrète, aucun gain global net mesuré |
| B Gaia CG direct | 0,951 | 0,925 | 1,307 | traitement conservateur, zone éclairée plus douce |
| N1 nettoyage Proteus seul | 1,170 | 1,337 | 2,365 | joints/planches mieux séparés ; aplats noirs, textures durcies dans la lumière |
| N1 puis A | 1,214 | 1,466 | 3,250 | effet N1 accentué, forte dureté locale |
| N2 Nyx seul | 1,025 | 1,034 | 1,360 | modification plus discrète |
| N2 puis A | 0,998 | 1,010 | 1,493 | proche de A, gain de netteté limité |

HP RMS = énergie du résidu gris − flou gaussien sigma1,2 ; proxy d'activité spatiale, PAS score de fidélité. La Laplacienne augmente aussi fortement sur N1, mais amplifie les aplats/contours artificiels.

- Netteté appréciée par l'utilisateur : N1 à explorer, sans considérer toute énergie haute fréquence comme du détail récupéré.
- Les différences temporelles des régions presque fixes augmentent aussi après traitement ; ces mesures non compensées en mouvement ne prouvent ni scintillement ni stabilité perçue. Évaluer en lecture native et ralentie.
- Assombrissement décodé observé : pierre moyenne source25,29 → A24,22 → N1-A23,04 /255. Cause NON isolée : modèle et conversions couleur possibles. N1 FFV1 annonce `tv/bt470bg`, masters ProRes non étiquetés ; homogénéiser les conversions avant la comparaison finale. Ne pas corriger l'exposition à l'aveugle.
- MCP : faux visages dans les pierres ; son estimation105 frames était erronée. Aucun fondement pour prioriser Iris.
- Nyx reste témoin utile, moins prioritaire pour le gain recherché. Pas d'indice justifiant un débruitage fort ou une récupération de visages.

## Briques et paramètres de départ

Valeurs CLI `tvai_up`, pas pourcentages GUI. `grain=0`, `estimate=0`, réglages manuels fixes, `preblur=-0.03`.

| Brique | Modèle | noise | details | halo | blur | compression | blend |
|---|---|---:|---:|---:|---:|---:|---:|
| C : nettoyage N1 existant, 720p x1 | prob-4 | .02 | 0 | .03 | 0 | .20 | .25 |
| C doux : limiter aplats/contours, 720p x1 | prob-4 | .01 | 0 | .03 | 0 | .12 | .45 |
| U : upscale A existant | prob-4 | 0 | .12 | .05 | .06 | .15 | .20 |

- G : `gcg-5`, x2 natif 2560×1440 → Lanczos 1920×1080 ; pas de curseurs Proteus appliqués à Gaia.
- U : x2 natif puis Lanczos 1080p, comme A. Conserver cet ordre pour isoler l'effet du nettoyage.
- L : Lanczos 720p→1080p, aucune seconde inférence spatiale.
- I : `apo-8`, 15→30 fps, sans ralenti, `rdt=-0.01` ; contrat de référence `pipeline/topaz/recipes/Video-Interpolation-Apollo8-30fps-v1.json`.
- J : `aion-1`, 15→30 fps sans ralenti ; schéma CLI/poids à vérifier avant rendu, présence du JSON local seule ne garantit pas que les poids sont en cache.

## Six candidats (1080p30)

| ID | Chaîne | Passes IA | Question isolée | Risque |
|---|---|---:|---|---|
| T1 | C720 → U1080 → I1080 | 3 | référence nette déjà appréciée + fluidité | durcissement cumulé, aplats noirs |
| T2 | C720 → G1080 → I1080 | 3 | Gaia préserve-t-il mieux le nettoyage que Proteus ? | douceur résiduelle ou textures amplifiées |
| T3 | C doux720 → G1080 → I1080 | 3 | garder la lisibilité N1 avec davantage de matière d'origine | moins de piqué apparent |
| T4 | C720 → L1080 → I1080 | 2 | le nettoyage suffit-il, sans seconde reconstruction IA ? | agrandissement moins riche |
| T5 | C720 → I720 → G1080 | 3 | interpoler avant l'upscale réduit-il les défauts temporels ? | moins d'information pour Apollo, upscale des intermédiaires |
| T6 | C720 → G1080 → J1080 | 3 | contrôle strict T2 : Aion plutôt qu'Apollo | coût, déformations locales toujours possibles |

Priorité de jugement : T2/T3/T4 pour le spatial ; T1 comme témoin de préférence ; T5/T6 pour l'ordre et le modèle temporel. Réutiliser les étapes identiques ; garder leurs sorties15 fps pour attribuer les défauts.

## Comparaison à produire après accord

- Six nouvelles versions dans des runs distincts ; conserver tous les essais précédents. Ajouter les sorties au comparateur seulement une fois présentes.
- Même cible1080p, codec de preview/CRF, cadrage et traitement couleur ; aucun grain, HDR, stabilisation ni renforcement global de contraste.
- Référence source décodée : fixer explicitement plage/matrice et vérifier des pixels/témoins avant empilement. Intermédiaires lossless ou ProRes10bit avec couleur déclarée ; cette mise au propre peut imposer de recalculer C/U pour tous les candidats. Pas de réécriture des runs historiques.
- Interpolation réelle `tvai_fi`, jamais simple `-r30`/duplication. Contrôler PTS, nombre d'images, intermédiaires mobiles et durée ; référence Apollo `2N−1` (=181 pour91) avant gestion des doublons. Pas de suppression automatique des maintiens source ni raccourcissement implicite de l'audio.
- Audio source autoritaire ; le conteneur est ≈0,99 s plus long que la piste vidéo. Définir explicitement la fin/noir et le mux de preview communs, sans étirer le mouvement pour atteindre7,05 s. Encodage/install/release jeu hors périmètre.
- Boucle2,2..4,2 : pierres, cercles du tonneau, fibres du bois, petits débris ; observer surfaces qui bouillent et contours qui collent. Vérifier ensuite les fondus0..2,2 et4,2..6,067 séparément.
- L'image éclairée est volontairement fluctuante : préserver la lumière d'origine ; distinguer cette animation des variations créées par les modèles.

Références Topaz : [enhancement](https://docs.topazlabs.com/video-ai/filters/enhancement), [interpolation](https://docs.topazlabs.com/video-ai/filters/frame-interpolation). Ces familles documentées orientent l'essai, pas l'acceptation de RESTDUNG.


## Production T1–T6 (2026-11-09)

- Producteur : `produce.py` ; vérification temporelle : `verify.py` ; menus : `add_to_comparator.py`.
- Étapes communes : `video/restdung/runs/restdung-topaz-six-shared-20261109-v1/production.json`.
- Chaque sortie : `video/restdung/runs/restdung-T<n>-20261109-v1/T<n>-RESTDUNG-<chaine>-1080p30.mp4` ; paramètres exacts/parents dans `run.json` ; aucun état QA accepté.
- Intermédiaires FFV1 RGB16 sans perte ; référence source : interprétation limitée BT.601 (décodage historique), conversion RGB plein domaine, primaires BT.709 / transfert sRGB ; MP4 final limité BT.709. Pas de YUV intermédiaire entre passes IA.
- Contrôle RGB référence à2,8s : différence moyenne0,871/255 face au décodage direct FFmpeg RGB8 (conversion haute précision / chroma différente) ; ce contrôle ne prouve pas une identité pixel à pixel.
- Encodeur MP4 FFmpeg standard `libx264`, CRF16/slow, AAC192k ; inférence exclusivement FFmpeg Topaz. Le binaire Topaz ne contient pas `libx264`.
- Interpolation : 181 frames et derniers PTS6s ; audio source conservé jusqu'à≈7,05s. Le noir terminal reste affiché pendant la queue audio ; aucun étirement du mouvement.
- Les étapes partagées restent techniques. Pour l'inspection dans le navigateur, utiliser les six MP4 finaux ; aucune intégration patch/release.

- Vérification temporelle réussie sur les6 branches :30/30 intermédiaires centraux distincts de leurs deux voisins ; résultats dans `interpolation-verification.json`. FPS/dimensions/181frames contrôlés sur chaque MP4. Cela ne valide pas la qualité perceptive.
