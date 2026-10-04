# Monster_quadrant — raccords Q3m : diagnostic et prototype

- Demande : analyser lignes horizontales/verticales, proposer correction. **Prototype local seulement ; production courante, cache global et installation inchangés.**
- Capture : `E:/Steam/userdata/5536307/760/remote/257350/screenshots/20261004215948_1.jpg` ; pose reproduite `MWYVG21..24`, séquence0/slot2, ID1000. Ne pas déduire une identité exacte de frame depuis l'horodatage seul.
- Parent : `../q3m-monster-quadrant-full-x2-20261004-v1/current-generation.json` ; Q3m K6 V7 x2, palettes améliorées, sans SDF, ingame QA encore en attente.

## Cause / vérification

| Hypothèse | Résultat |
|---|---|
| Marge transparente ajoutée autour des textures | Écartée : session21:59:40, `MWYVG21`65×75 → texture130×150 **unbordered**, concordance dimensions BAM/texture exacte. |
| Erreur de placement/centre des parties | Aucun décalage ajouté : séparation native commune x=0/y=-40, géométrie/cycles de production vérifiés. |
| Filtrage indépendant | Reproduit : CatmullRom16 taps +GL_NEAREST/CLAMP_TO_EDGE sur chaque texture. Le filtre ne connaît pas ses voisins. Assemblage avant filtrage modifie les raccords, mais laisse la ligne de tête inscrite dans les pixels. |
| Traitement neuronal indépendant des quadrants | Cause principale du raccord montré : les bords reçoivent des contextes différents pendant remplissage RGB/inférence. Q3m sur le sprite assemblé supprime la barre horizontale dans le prototype. |

- `analysis.json`, `filter-comparison.png`, `poses.png` :10 poses MWYVG2/seq0 ; comparaison source, filtrage séparé et assemblé. Mesures de discontinuité RGB ne doivent pas être interprétées seules comme défauts : l'art natif contient aussi des transitions légitimes.
- Configuration observée : Stored, Sharpen0, Gamma1, Contrast1, Brightness0, Saturation1, CatmullRom, contour Native. Simulation = couleur/alpha/filtre ; contour natif, éclairage, occlusion et GPU du jeu non rejoués.

## Correction recommandée

1. Reconstituer le sprite original sous chacune des six palettes K6 avec les centres/cycles réels des quatre parties ; remplir le transparent **après assemblage**.
2. Inférer Q3m sur le contexte assemblé, réduire x4→x2 par Box, redécouper aux dimensions natives.
3. Réutiliser guides, profils/partenaires, anciennes cibles RGB et anciens encodages. Reprendre seulement une bande de **quatre pixels natifs** à chaque frontière réellement partagée ; force1 près du raccord, transition progressive vers0 au bord de la bande.
4. Encoder les pixels de cette bande ; conserver I/F bit à bit hors bande, recalculer dépendances. Masques/classes, ombres, palettes, centres, cycles, déclarations0×0 restent identiques.
5. Publier une nouvelle génération immuable des seules feuilles modifiées. Garder les quatre dessins/UV/clips natifs et le lecteur actuel ; QA ingame des différentes directions/zooms nécessaire avant acceptation.

- **Six cas /36 nouvelles cibles expérimentales** :1000 seq0 slots1/2/3 +seq4 slot2 ;1004 seq0 slot2 ;1100 seq0 slot2. `context-probe.json`, `probe_context.py`.
- Essai neuronal batch6 fp16 ; production parent batch86. Ne pas réutiliser l'identité de cache du parent pour ce nouveau contexte/backend.
- `native-draw-analysis.json`, `preview_native_draws.py` : même simulation de quatre dessins séparés après correction, résultat visuel favorable ; le filtrage assemblé n'est pas requis pour éliminer la barre montrée.
- Pose1000/seq0/slot2 :2 048/61 060 pixels I/F modifiés (**3,35%**), **zéro modification hors bande**. La même conservation hors bande est contrôlée dans les six cas.
- `seam-closeup.png` : actuel/quatre dessins → correction/quatre dessins → correction/filtre assemblé. `native-draw-comparison.png` : sprite complet actuel/correction.

## Étendue du futur lot

- `context-inventory.json` :3×308 contextes MWYV +4×555 MTAN =**3 144 contextes distincts**, soit18 864 cibles K6 avant déduplication supplémentaire.
- 17 768 slots natifs synchronisés ;12 576 frames référencées,352 déclarées non référencées. Les352 restent dans les feuilles avec leur encodage acquis ; ne pas supprimer les frames ni normaliser les cycles.
- **Aucun index de frame natif non vide réutilisé sous plusieurs voisinages** dans les cycles disponibles : une réparation par frame peut conserver le contrat de résolution actuel.
- Encodeur bande : découper `guide` et cibles sur ROI puis appeler `Profile.encode` en forme1×N ; recopier uniquement ROI dans les I/F acquis. Évite d'encoder tout le sprite une seconde fois.
- Les33 BAM hors constructeur, MWDR1101/1105 absents, autres familles/DLL/shaders/INI ne font pas partie de la correction proposée.

## État

- Analyse/prototype terminés. **Pas de traitement complet du correctif, pas d'installation, pas de validation ingame, pas de commit/release déduits.**
- Scripts/prototypes dans ce run ; tableaux NPZ sous `work/`, non autoritaires pour production.
