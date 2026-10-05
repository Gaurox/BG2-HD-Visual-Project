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
- Limite de preuve : ingame acquis pour quatre parties Wyverne/Tanar'ri. MultiNew complet :
  [run](../docs/measurements/q3m-multi-new-full-x2-20261005-v1/README.md), QA ingame en attente.

## MultiNew / MonsterMulti : deux conventions natives

- Inventaire `multi_new`, owner5 : `1200..1208` = MonsterMulti/9 parties ; `1300` = MultiNew/4 parties.
- Dragons : `prefix + bank[1..5] + part[1..9] + chunk + direction`, 8 caractères ;
  groupe `ref[:5]+ref[6:]`, partie `ref[5]`. Sept variantes MDR1 partagent exactement la géométrie.
- Démogorgon : `MDEM + G + bank[1..2] + part[1..4] + chunk optionnel`, 7/8 caractères ;
  groupe `ref[:6]+ref[7:]`, partie `ref[6]`. Préserver tous les noms/cycles même si un BAM est identique.
- `general.new_palette=MDR1_GR` etc. désigne un **préfixe** : ressources BMP natives `prefix1..5`.
  Sélection `palette_overrides_by_bank` : cinq `{resref,sha256}` ; palette choisie par `ref[4]`.
  Ne pas chercher/fabriquer un BMP sans suffixe ; vérifier SHA et K6 avant traitement.
- Source_plan conserve les clés BAM originales, puis les clés RGB/palettes effectives. Union après
  contrats : 42 772 travaux pour 519 867 frames liées ; coûts par variante non additionnables.
- `Q3M_GUIDE_WORKERS=8` : processus indépendants, mêmes guides/namespace ; publication atomique par
  le parent seul. Défaut1 ; script appelant protégé par `if __name__=='__main__'` sous Windows.
  Garder `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OMP_NUM_THREADS=1` pour éviter la surallocation CPU.
- `Q3M_ENCODE_WORKERS=8` : clés encodées indépendantes en threads ; défaut2, intervalle1..16.
  Calcul du codec/namespace inchangé ; test SHA des fichiers serial/parallèle. Reprise par clés complètes
  existantes ; ne jamais réencoder un hit ni multiplier les threads BLAS par les workers.
  MultiNew sur CPU24 threads : mesure `encode-scheduling.json`, 24 clés synthétiques,
  guides 80×96/96×128/160×192 ;
  workers1/8/12/16 = 12,54/3,29/3,22/2,98s, SHA identiques. Production16 ; gain réel dépend des frames.
- `Q3M_TARGET_IO_WORKERS=8` : réduction BOX/compression NPZ en threads CPU ; batch CUDA fixé86
  inchangé, aucune cible supplémentaire. Tests SHA serial/parallèle sur sorties float32 jusqu'à
  `256×224` source. Reprise depuis fichiers complets atomiques ; `.part` ignorés, aucune réécriture des hits.
- Windows/WDDM : `Q3M_TRIM_CUDA_CACHE=1` libère les allocations CUDA inactives après chaque batch,
  réduit la mémoire partagée/éviction VRAM. N86/FP16/canvases restent identiques ; premier batch
  répété avant/après libération, comparaison exacte des sorties. Ne pas quitter les apps utilisateur.
- Même option pour les contextes : batchK6/canvas/BOX inchangés, première prédictionK6 comparée
  avant/après purge puis allocations inactives purgées entre contextes. `Q3M_CONTEXT_ENCODE_WORKERS=8`
  encode les cellules indépendantes, ordre natif conservé ; défaut1, intervalle1..16. Test neuf parties,
  profils initialement froids : SHA serial/parallèle identiques, I/F hors bande et spéciaux conservés.
  Nouveau SHA du producteur = nouvelle recette ; aucune production/QA acquise réécrite.
- Runtime : MonsterMulti rend neuf cellules séparées (`FrameTextureLayout::Unbordered`) ; MultiNew
  rend quatre cellules. Le compositor Character/équipement limité à huit couches n'est pas cette voie.
  Vérification hors jeu : décodages natifs des cellules, centres/cycles, puis assemblage ordonné4/9 ;
  DLL/INI/shaders acquis conservés. Ne jamais déduire QA ingame de ce contrôle.

## Encodage palette accéléré, option mesurée

- `Q3M_PALETTE_ENCODER=gpu-grouped-guarded-v1` : `scripts/q3m_guarded_gpu_encode.py` ;
  défaut `cpu`. Cibles K6, modèle/FP16/BOX et fichier `palette_q3m_partners.py` inchangés.
- Candidats strictement identiques (`features+norm`) regroupés, premier indice natif conservé ;
  classement CUDA FP64, blocs4096. Écart entre deux choix distincts ≤ garde numérique :
  recalcul du bloc CPU original256, ordre/dimensions d'origine. Zéros : argmin CPU des normes.
- Verrou unique GPU ; jusqu'à16 workers chargent/compressent les NPZ. Import Torch uniquement
  pour un encodage manquant ; reprise entièrement acquise sans Torch. Aucun hit réécrit.
- MultiNew : `acceleration-benchmark.json` (30 frames, dix variantes/quatre modèles),
  `acceleration-concurrent.json` (CPU16/GPU16 avec charge concomitante),
  `acceleration-validation.json` (696 frames/31 profils, 13 855 901 pixels avec ROIs, zéro écart,
  39 blocs CPU ambigus). Source SHA/compteurs dans `production.json` ; recette contextuelle
  inclut SHA de l'accélérateur/mode. Les mesures d'un microbenchmark ne donnent pas l'ETA globale.
- Essais ciblés : `test_q3m_guarded_gpu_encode.py` (couleurs dupliquées, choix exacts/proches,
  pixels spéciaux, ROIs, mode CPU paresseux). Exécuter après les tests Multipart qui prouvent
  l'absence d'import Torch, ou dans un processus distinct.
- `CUBLAS_WORKSPACE_CONFIG=:4096:8` avant création CUDA ; conserver purge entre inférences
  contextuelles. Ne pas toucher ComfyUI/autres processus utilisateur pour accélérer ce travail.
