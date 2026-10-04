# Q3m x2 — gros sprites découpés en tuiles

## Règle courante (demande utilisateur, 2026-10-04)

Appliquer systématiquement la production contextuelle aux sprites divisés spatialement :
`monster_quadrant`, `multi_new`, tout autre lot déclarant des `multipart_groups` natifs.
Une arme superposée, une orientation E ou deux actions ne sont pas des tuiles voisines.
Producteur : `scripts/q3m_multipart_seams.py`, appelé automatiquement par les commandes
`plan`, `run`, `pack` de `scripts/q3m_family_witnesses.py`. Aucun paramètre de contournement.
Autres familles : résultat inchangé. Installation/release restent des opérations distinctes.

## Contrat validé

| Étape | Décision exacte |
|---|---|
| Assemblage | Original indexé x1 ; ordre natif des parties, coordonnées `(-cx,-cy)`, frame de chaque cycle/slot. Ne pas déduire les groupes du préfixe seul. |
| Contexte | Construire six RGB depuis les palettes K6 ; réunir les masques `index != 0` ; remplir les RGB transparents par voisin le plus proche **après assemblage**. |
| Inférence | ReboutCX x4, fp16, batch6, canvas multiple32 ; BOX float32 vers x2 ; redécouper aux dimensions/centres natifs. |
| Raccord | Distance au bord réellement partagé, limitée à son segment de recouvrement ; poids `clip((4-distance)/3,0,1)` en pixels natifs, évalué aux centres x2. Mélanger anciennes cibles/cibles contextuelles. |
| Encodage | ROI des seules classes du corps (fixe ≥3, rampes ≥4), encodeur Q3m existant ; I/F hors ROI byte-identiques. Guides/classes/partenaires/palettes/cycles/représentants inchangés. |
| Runtime | Conserver les dessins séparés, centres, clips, ombres, dimensions et frames vides authentifiées. Aucun SDF ajouté, aucun changement de shader/DLL requis par cette correction. |
| Cache | Clé = recette/backend/encodeur/sélection + liste ordonnée des clés pixel et géométries de toutes les parties. Checkpoints SHA sous `cache/multipart-seams/<recipe_key>/`. Parents `encoded/targets` en lecture seule pendant la correction. |

Les cibles Q3m par partie servent de base acquise ; leur calcul isolé n'est plus le résultat final
d'un sprite à plusieurs tuiles. Une simple modification du filtre ne répare pas les RGB divergents
produits par des inférences sans voisinage.

## Commandes

```powershell
# Python et outils source : chemins locaux via workspace-paths, aucun chemin machine canonisé.
$spritePython = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
$env:PYTHONPATH = Join-Path (Get-Location) 'sprite/.work/q3m-runtime-tools-20261003-v1'
# Sélection native versionnée : refs, multipart_groups, toutes palettes/actions/orientations utiles.
& $spritePython pipeline/scripts/q3m_family_witnesses.py plan --complete-family monster_quadrant --selection <selection.json> --cache <cache> --output <plan-neuf.json>
& $spritePython pipeline/scripts/q3m_family_witnesses.py run  --complete-family monster_quadrant --selection <selection.json> --cache <cache>
& $spritePython pipeline/scripts/q3m_family_witnesses.py pack --complete-family monster_quadrant --selection <selection.json> --cache <cache> --output <pack-neuf>
```

- `plan` : CPU, nombre exact de contextes et bindings ; ne construit ni modèle ni cibles.
- `run` : produire/reprendre la base, puis seulement les contextes manquants ; encodeur ROI.
- `pack` : relier les checkpoints authentifiés ; aucune inférence, erreur si correction absente.
- Les anciennes productions/QA restent immuables ; archiver la nouvelle recette et la production
  du cache dans un nouveau run. Ne pas relancer `finish.py`/`accept.py` d'un run accepté.
- Palette/profil incompatible ou même frame réutilisée avec des voisinages différents : arrêt
  local explicite ; prévoir des bindings frame/cycle distincts, ne pas choisir arbitrairement un voisinage.
- Vérification locale : I/F hors bande identiques ; guides/classes/géométrie/cycles inchangés ;
  lecture native et assemblage des parties ; comparer frontière, poses voisines, directions symétriques.
  Validation visuelle utilisateur attachée aux feuilles/runtime exacts, séparée de l'installation.

## Référence acquise

- [Analyse](../docs/measurements/q3m-monster-quadrant-seam-analysis-20261004-v1/README.md) :
  barre horizontale du front, raccords verticaux ; inférence/RGB-fill indépendants responsables.
- [Production corrigée](../docs/measurements/q3m-monster-quadrant-seam-fixed-x2-20261004-v1/README.md) :
  deux modèles/sept palettes, 132 feuilles/12 928 frames, 3 144 contextes/18 552 cibles ;
  6 010 622 pixels encodés modifiés, zéro hors bande ; 272 frames non référencées et 65 déclarations0×0 conservées.
- [QA complète acceptée](../sprite/index/qa-decisions/monster_quadrant/2026-10-04-accepted-full-quadrant-contextual-q3m-v7-x2-catmullrom-v1.json).
- Limite de preuve : ingame acquis pour quatre parties Wyverne/Tanar'ri ; groupes9 dragons
  pris en charge par le plan/algorithme, leur production et QA restent propres au futur lot.
