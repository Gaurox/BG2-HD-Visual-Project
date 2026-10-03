# Tests couleur Q3m — six frames, 2026-10-03

Statut : diagnostics hors production, QA, installation et release. Archives exactes des cinq essais demandés ; aucun résultat expérimental installé.

## Archives

| Essai | Script / mesures | PNG comparatifs |
|---|---|---|
| Ancien x2 / Q3m x2 installé | [compare.py](../q3m-colour-comparison-20261003-v1/compare.py), [comparison.json](../q3m-colour-comparison-20261003-v1/comparison.json) | [Spectateur](../q3m-colour-comparison-20261003-v1/spectateur-avant-apres.png), [Bodhi](../q3m-colour-comparison-20261003-v1/bodhi-avant-apres.png), [golem](../q3m-colour-comparison-20261003-v1/golem-avant-apres.png) |
| Q3m x4 direct ajouté | [compare_x4.py](../q3m-colour-comparison-x4-20261003-v1/compare_x4.py), [comparison.json](../q3m-colour-comparison-x4-20261003-v1/comparison.json) | [Spectateur](../q3m-colour-comparison-x4-20261003-v1/spectateur-avant-q3m-x2-x4.png), [Bodhi](../q3m-colour-comparison-x4-20261003-v1/bodhi-avant-q3m-x2-x4.png), [golem](../q3m-colour-comparison-x4-20261003-v1/golem-avant-q3m-x2-x4.png) |
| SeedVR2 7B x4, quatrième colonne | [compare_seedvr.py](../seedvr7b-colour-comparison-x4-20261003-v1/compare_seedvr.py), [recette](../seedvr7b-colour-comparison-x4-20261003-v1/recipe.json), [mesures](../seedvr7b-colour-comparison-x4-20261003-v1/comparison.json) | [Spectateur](../seedvr7b-colour-comparison-x4-20261003-v1/spectateur-comparatif-4-traitements.png), [Bodhi](../seedvr7b-colour-comparison-x4-20261003-v1/bodhi-comparatif-4-traitements.png), [golem](../seedvr7b-colour-comparison-x4-20261003-v1/golem-comparatif-4-traitements.png) |
| Q3m x4, 16 niveaux, remplace SeedVR | [compare_16.py](../q3m16-colour-comparison-x4-20261003-v1/compare_16.py), [comparison.json](../q3m16-colour-comparison-x4-20261003-v1/comparison.json) | [Spectateur](../q3m16-colour-comparison-x4-20261003-v1/spectateur-comparatif-q3m-16-niveaux.png), [Bodhi](../q3m16-colour-comparison-x4-20261003-v1/bodhi-comparatif-q3m-16-niveaux.png), [golem](../q3m16-colour-comparison-x4-20261003-v1/golem-comparatif-q3m-16-niveaux.png) |
| Q3m x4, quatre partenaires / huit niveaux, cinquième colonne | [compare_partners.py](compare_partners.py), [comparison.json](comparison.json) | [Spectateur](spectateur-comparatif-5-traitements.png), [Bodhi](bodhi-comparatif-5-traitements.png), [golem](golem-comparatif-5-traitements.png) |

Chaque dossier conserve scripts, JSON et PNG RGBA individuels sans modification. `cache/<namespace>/` conserve recettes, six guides xBR4 et les 18 encodages Q3m x4 / 16 niveaux / quatre partenaires. SeedVR conserve aussi les six entrées, workflows soumis, reçus de jobs et sorties brutes.

Provenance : copie depuis `sprite/.work/<même nom>/`, 113 fichiers issus des essais / 63 PNG / 24 NPZ / 5 scripts / 21 JSON ; 13 660 492 octets copiés. Vérification de copie : égalité de tous les octets, lecture PNG/JSON, compilation syntaxique des scripts sans exécution. `.gitattributes` locaux : aucune normalisation Git des JSON/scripts pour conserver les SHA historiques. Les chemins dans les JSON restent ceux des essais originaux. Les 36 cibles ReboutCX float32 restent dans le cache local ignoré ; leurs SHA sont conservés dans les recettes 16 niveaux et quatre partenaires. Métadonnées de découverte ComfyUI `object-info.json` exclues.

Scripts archivés comme références immuables. Ils dépendent des modules `pipeline/scripts`, du contrat/profils et des ressources/caches locaux aux chemins enregistrés ; ne pas les lancer dans ces archives. Un nouvel essai demande un nouveau dossier de travail et une nouvelle version de résultats.

## Échantillons et paramètres

| Cible / CRE / animation | BAM, frame, cycle, profil |
|---|---|
| Spectateur / `BEHSPE01` / `0x7F02` MBEH | `MBEHG1`, 11, 9, 2 ; `MBEHG2`, 38, 0, 3 |
| Bodhi / `BODHI` / `0x7F30` NBOH | `NBOHG1`, 2, 9, 4 ; `NBOHG2`, 4, 0, 5 |
| Golem geôlier / `IGOLEM02` / `0x7F07` MGLC | `MGLCG1`, 24, 9, 6 ; `MGLCG2`, 3, 0, 7 |

- Échantillonnage : premiers exemples G1 et G2 de phase 5, eux-mêmes choisis pour une forte présence de F dans des cycles représentatifs. Six frames, aucune conclusion de couverture ou stabilité temporelle complète.
- Ancien : ReboutCX classique x2 pour Spectateur/Bodhi ; **xBR x2 pour le golem**, sans ancien résultat ReboutCX disponible. Sources BAM canoniques et géométrie vérifiées dans les mesures ; payload Q3m x2 identique au leaf installé lors du test.
- Q3m : palettes fixes natives, six ajustements neutral/warm/cold/green/red/dim, classes/indices spéciaux inchangés, alpha 0/127/255, aucun tramage ni B/Q8c. Référence [contrat](../q3m-monster-contract-x2-20261002-v1/contract.json), [profils](../q3m-monster-contract-x2-20261002-v1/profiles.json).
- Q3m x4 : BAM indexé natif → guide xBR4 → 36 cibles ReboutCX x4 direct float32, backend `reboutcx-multipal-float32-p12-fixed86-q32-box-v1`, FP16, canvas fixe 86 / quantum 32, RTX 5090. Aucun BOX de réduction pour ce diagnostic x4 ; l'installation Q3m x2 monde BOX conserve sa recette.
- 16 niveaux : mêmes cibles/guides, CPU seulement ; `((16-F)*P[I]+F*P[succ[I]]+8)>>4`, F=0..15. Ancien espace exactement inclus par F16=2*F8 sur K6.
- Quatre partenaires : mêmes cibles/guides, CPU seulement ; quatre voisins de matière RGB distincts sur K6, distance OKLab f64, égalités départagées par indice. Partenaire 0 = successeur acquis ; F=0..7. 7 337 candidats exhaustifs ; plan `partner` supplémentaire, dépendances recalculées, alpha primaire conservé.
- SeedVR : `seedvr2_7b_int8_convrot.safetensors`, VAE FP16, seed 959948902156062, Euler/simple, un pas, CFG 1, LAB, x4 Lanczos, tiles 512 / overlap 128 ; workflow [7B](../../../pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json) adapté en mémoire. RGB libre ; alpha d'affichage repris de Q3m x4 et RGB des indices spéciaux restauré. Sorties brutes distinctes des PNG comparables.
- Affichage : PNG sans perte, agrandissement nearest-neighbour ; à partir du comparatif x4, même taille physique native×8 (x2×4, x4×2). Détails : même zone native, x2×8 / x4×4. Aucun enrichissement par agrandissement d'affichage.

## Mesures acquises

Nombre de RGB distincts sur pixels alpha=255, avant composition ; ombre et transparence exclues, palette neutre. Plus de couleurs ne mesure pas directement le détail ou la qualité visuelle. SeedVR utilise un espace RGB libre, contrairement aux variantes Q3m.

| Frame | Ancien x2 | Q3m x2 | Q3m x4 | SeedVR x4 | Q3m x4, 16 | Q3m x4, 4 partenaires |
|---|---:|---:|---:|---:|---:|---:|
| MBEHG1 / 11 | 86 | 569 | 760 | 42 586 | 1 109 | 1 742 |
| MBEHG2 / 38 | 85 | 583 | 760 | 42 138 | 1 127 | 1 733 |
| NBOHG1 / 2 | 64 | 428 | 705 | 6 003 | 861 | 1 287 |
| NBOHG2 / 4 | 62 | 423 | 681 | 6 145 | 849 | 1 336 |
| MGLCG1 / 24 | 81 | 342 | 436 | 12 644 | 564 | 1 035 |
| MGLCG2 / 3 | 99 | 402 | 563 | 13 826 | 689 | 1 238 |

Réduction de l'erreur moyenne quadratique OKLab sur K6 et pixels de matière, relative au Q3m x4 à un successeur / huit niveaux :

| Cible | 16 niveaux, G1 / G2 | 4 partenaires, G1 / G2 |
|---|---:|---:|
| Spectateur | 1,54 % / 1,46 % | 20,86 % / 19,15 % |
| Bodhi | 0,41 % / 0,37 % | 3,46 % / 3,31 % |
| Golem | 0,86 % / 1,04 % | 10,17 % / 9,90 % |

Assertions acquises : alpha identique ; indices spéciaux conservés ; anciens candidats inclus exactement ; erreur K6 non croissante à chaque pixel de matière. Quatre partenaires : contrôle indépendant des distances directes sur 32 pixels de matière par frame. Détails et SHA dans les scripts/JSON archivés.

Temps observés dans les sorties des essais : environ 65 s pour les six encodages x4 initiaux, 126 s pour 16 niveaux, 20 s pour quatre partenaires. Le dernier utilise un calcul matriciel optimisé (f64, chunks 256, quatre threads BLAS) ; ces observations ne constituent pas un benchmark du pipeline complet. Les essais 16 niveaux et quatre partenaires réutilisent les 36 cibles sans nouvelle inférence GPU.

## Conclusion / reprise

16 niveaux : gain objectif faible, variation visuelle discrète. Quatre partenaires : gain objectif supérieur sur ces six frames, variation visuelle encore modérée ; piste retenue pour un éventuel prochain essai. SeedVR produit davantage de couleurs et des détails inventés ; aucune validation d'intégration.

Les variantes 16 niveaux et quatre partenaires sont **incompatibles avec le format/lecteur V6 actuel**. Installation éventuelle : essai x2 représentatif, contrat/format et lecteur adaptés, puis traitement complet des trois familles ; conserver les 78 animations Character et paperdolls. Extension à tous les non-jouables dépend des profils moteur, palettes, calques et compositions. Aucun changement de production, QA, installation ou release autorisé par ce commit d'archives.
