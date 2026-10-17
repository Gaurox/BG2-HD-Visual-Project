# Nuages Z58 : fonds noirs HD, vanilla correct — 2026-10-17

## Cause établie

**Perte de l'alpha gradué des palettes BAM lors de l'export source HD.**
Les4ressources BDWOFOGA/SPCLOUDK/SPCLOUDS/SPDFOGA possèdent des palettes BGRA avec A variable, presque transparent sur les couleurs sombres. L'export HD utilise seulement l'index transparent et rend tous les autres pixels opaques. Le traitement spatial/temporel conserve ce masque binaire, avec un feather de contour ; la variante RGB straight conserve le même mauvais alpha. Le rendu normal des VVC expose les zones sombres opaques vues sur les captures utilisateur.

| BAM / VVC | Cycle testé | A palette hors index transparent | A médian natif de l'échantillon | A médian après export binaire | Pixels affectés de l'échantillon |
|---|---|---|---:|---:|---:|
| BDWOFOGA /Z580269 |4loop|1..253|40|255|18564/18564|
| SPCLOUDK /Z580278 |2once|12..187|54|255|18024/18024|
| SPCLOUDS /Z580290 |2once|4..213|67|255|18024/18024|
| SPDFOGA /Z580300 |1once|3..248|77|255|9155/9155|

Échantillons : slot médian de chaque cycle natif ; aucune prétention de correspondance exacte à la phase des captures. A=54 signifie~21% d'opacité, remplacée par100% avant traitements.

## Chaîne vérifiée

- Captures HD originales référencées et SHA256 : `evidence.json`, fichiers Steam `20261017154631_1.jpg`, `20261017154637_1.jpg`, `20261017154645_1.jpg`, `20261017154652_1.jpg`. Vanilla correct et vrais sorts corrects : témoignage utilisateur.
- VVC runtime HD/vanilla **identiques octet pour octet**, display flags0/non-Blended ; références BAM/cycles15FPS conformes. Donc aucun écart de contrôleur entre les2copies.
- BAM source projet = SHA des BAM extraits du BIF officiel vanilla dans le reçu `effects/installations/vanilla-cloud-tests-20261017-v2/installation.json`. Palettes des carriers BAM HD identiques aux sources.
- `pipeline/scripts/bam_export.py:39` : lecture BGRA puis `rgb = palette[:, [2,1,0]]` ; 4ecomposante perdue pour l'API du décodeur.
- `pipeline/scripts/export_bam_frames.py:130` : `alpha = (indices != frame_transparent) *255`. Source immédiate du défaut.
- `pipeline/recipes/effects-lot58-seedvr7b-apollo30-20261016-v1/temporal.py:310` : interpolation des alphas spatiaux déjà binarisés, puis premultiplication/feather. `:324` : companion straight obtenu en modifiant RGB seulement ; alpha inchangé. Même logique dans `repair_temporal.py`.
- `pipeline/recipes/effects-lot58-install-20261017-v1/install.py:49` : sélection des companions straight pour ces4BAM via `STRAIGHT` ; `:91` indique `rgb_encoding=straight`. Le choix straight/premultiplied ne rétablit pas A.
- Textures RGBA installées contrôlées par SHA et reliées aux phases natives dans `evidence.json` : beaucoup de pixels alpha255, alors que toutes les entrées non transparentes de ces4palettes ont A<255.
- Logs15:46 : `session-1546-effects.log`, diagnostics propriétaire0x80, frame résolue0x1, phase0x4, texture HD liée0x8. Sur SPCLOUDS,0x20 = transfert occlusion à certaines phases ; le problème alpha existe aussi sans ce transfert.

## Interprétation native de A : preuve sur l'exécutable exact

Recherche statique uniquement, aucun code du jeu exécuté. PE BG2EE SHA256 `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57` ; RVAs sans image base :

- `VidPaletteRealize`421430 choisit palette de ressource ->42D350.
- `PaletteResource.asm:42D84A` lit explicitement `palette[index].A` dans EBX.
- `42D9F7..42DA36` : test `(A-1) <=253` sur8bits ; A1..254 -> alphaA, A0/255 -> alpha par défaut/global. `42DA1C..42DA22` place A dans les8bits de poids fort du pixel réalisé. Index vert transparent traité séparément à42DA59..42DA82.
- Les4palettes concernées utilisent A1..253 /12..187 /4..213 /3..248 hors index0 : **le chemin gradué s'applique à toutes leurs couleurs visibles**, pour la réalisation normale sans autre effet de palette.
- La description générale IESDP BAM limite historiquement la prise en compte d'A à l'UI ; ne pas en déduire que ce PE ignore A dans cette branche de réalisation. Ne pas activer aveuglément la même politique sur tous les anciens BAM : leurs A0 doivent garder la compatibilité opaque.

## Pourquoi les vrais sorts peuvent rester corrects

Établi : les vrais sorts utilisent leurs SPL/PRO et un contexte de rendu différent des VVC isolés ; le moteur distingue ces owners (`hooks.cpp`, `detour_vvc_vid_cell_render` /scope ProjectileBAM). Leur réussite visuelle rapportée ne valide donc pas ce test normal/non-Blended.

**Non établi par cette recherche :** état de mélange exact et présence effective de la substitution HD pour chaque puff des vrais sorts dans la session comparée. Les diagnostics disponibles ne tracent pas ces états par draw. Ne pas affirmer sans trace qu'il s'agit forcément d'un mélange additif ; un rendu natif/fallback est aussi à distinguer. Aucun changement des sorts n'est nécessaire pour expliquer le défaut des VVC : le mauvais alpha des textures de ces4BAM est déjà démontré.

## Correction ciblée à produire ensuite

- Normal/VVC : reconstruire l'alpha depuis la palette et les index des frames natives (A1..254, A0/255 compatibilité opaque, index transparent0), puis appliquer agrandissement/interpolation/feather avec géométrie et durée conservées.
- Réutiliser RGB SeedVR7B/Apollo existants ; aucune nouvelle inférence RGB n'est justifiée pour réparer cet alpha.
- Nouveaux runs/pack/installation ; conserver les productions et reçus actuels. Contrôler séparément le contrat PRO avant remplacement d'une ressource partagée ; alias normal si nécessaire pour conserver le chemin de sort validé visuellement par utilisateur.
- Ne pas masquer l'erreur en passant les VVC en Blended : la référence demandée est leur affichage normal vanilla avec alpha natif.
- Recherche seulement : aucun asset, VVC, DLL ou fichier installé modifié. Aucune QA globale des58 déduite.

Reproduction : `python -B effects/research/black-cloud-backgrounds-20261017-v1/pe_probe.py` ; `alpha_probe.py` a produit le reçu immuable `evidence.json` (ouvrir un nouveau dossier pour une nouvelle mesure).
