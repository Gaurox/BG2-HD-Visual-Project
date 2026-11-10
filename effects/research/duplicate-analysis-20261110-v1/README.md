# Doublons effets — analyse complète, 2026-11-10

## Autorités / périmètre

- Entrées : `effects/index/bam-assets.csv` (497), sélections courantes ; release alpha.8 `content.json`, pack `accepted-20261110-v1`.
- Sources vanilla : 495 BAM V1 physiquement hashés/décodés ; 2 absents conservés absents. 19 508 frames examinées.
- Livraison : 72 756 fichiers effets physiquement rehashés ; chaque membre des groupes doublons comparé octet par octet à sa référence, dans la source release **et** le staging.
- Lecture seule : aucun asset, QA, fichier moteur, installation ou manifeste release modifié. Sans rognage ni inférence.

## Résultats sources vanilla

| Identité examinée | Groupes | Membres |
|---|---:|---:|
| BAM fichier strict | 13 | 26 BAM |
| BAM décompressé strict | 13 | 27 BAM |
| BAM sémantique : indices, palette BGRA complète, transparence, dimensions/centres et cycles | 14 | 29 BAM |
| Images natives : indices + palette complète + transparence + dimensions | 1 410 | 3 868 frames |
| Même identité, partagée entre plusieurs BAM | 1 090 | voir inventaire |

- Identité native volontairement stricte : pas d'assimilation perceptuelle, palette différente ou simple aperçu RGB ressemblant. Inclut les entrées de palette inutilisées ; des dessins rendus équivalents peuvent donc rester distincts.
- `native-whole-source-reuse-candidates.json` : les groupes de BAM complets ayant plusieurs sélections HD n'ont pas de divergence de ces sorties sélectionnées ; réemplois historiques déjà présents, notamment COLDH/SPICEIMP, FIREH/SPFIRIMP, OHNVIS1/SPARMOUR et SPPRISM2/3/T.
- `native-frame-runtime-reuse-candidates.json` : 698 groupes inter-BAM rapprochés ; **112 ont plusieurs sorties HD**. Divergence toutes causes confondues : ne prouve pas à elle seule une variation SeedVR (palettes propriétaires, normal/additif, alpha, recettes, géométrie et voisins d'interpolation peuvent différer).
- Rapprochement analytique : 699/733 ressources runtime, 3 059 ancres natives répétées ; 33 contrats demandent un adaptateur de provenance spécifique, COW vient du domaine sprite. Détail : `native-runtime-anchor-coverage.json`. Ce reliquat ne concerne pas l'inventaire complet des doublons livrés, qui est vérifié intégralement.
- Synthèse du rapprochement : **`native-runtime-anchor-summary-v2.json`** remplace le compte d'ancres erroné du premier résumé ; inventaires et groupes inchangés.
- Une image native identique ne suffit pas à mutualiser des images HD différentes ni leurs phases interpolées. Aucun gain garanti ajouté pour ces candidats ; choix de référence et qualification avant harmonisation.

## Gain confirmé sur les fichiers actuels

| Classe | Groupes stricts | Copies redondantes | Octets supprimables |
|---|---:|---:|---:|
| RGBA | 5 826 | 6 122 | **2 588 515 136 = 2,41074 Gio** |
| BAM de support | 176 | 318 | **59 921 928 = 57,146 Mio** |
| Total | 6 002 | 6 440 | **2 648 437 064 = 2,46655 Gio** |

- Images : 71 971 références logiques → **65 849 blocs physiques** ; 34,78866 → **32,37791 Gio**.
- Prototype d'index u32 : 287 884 octets ; économie images après ce seul index = **2 588 227 252 octets**. En-tête/version et éventuelles métadonnées finales à déduire.
- 0 groupe image avec dimensions divergentes ; 22 groupes entièrement nuls. Garder les identités logiques, centres, cycles, palettes et caches GPU distincts.
- 72 756 identités de fichiers physiques distinctes dans les sources release : les copies redondantes ne sont pas déjà des liens physiques dans ce pack.
- DEFLATE6 : charge utile dupliquée mesurée = **553 755 685 octets images (~528,10 Mio)**, plus **12 912 499 octets BAM**. Gain ZIP complet à confirmer après prise en compte des index/en-têtes ; les 2,47 Gio bruts ne sont pas le gain du téléchargement compressé.
- Chiffres de contenu apparent, pas mesure de clusters NTFS ni gain global de tout le dépôt. Sources historiques/QA restent conservées.

## Livrables pour implémentation

- `final-file-to-blob-map.csv` : **tous les 72 756 fichiers**, destination, référence canonique, SHA, dimensions et action proposée.
- `final-identical-byte-groups.json` : groupes stricts et membres complets ; vérification binaire source/staging, alpha nul, encodages, économie et DEFLATE6.
- `final-savings-by-resource.csv` : gains par resref ; attribution déterministe à la référence conservée, pas classement qualité.
- `native-*-groups.json`, `native_pixel_key-groups.json`, `native_geometry_key-groups.json` : inventaires natifs exhaustifs.
- `native-frame-to-runtime-anchor-map.csv` : liens prouvés source/cycle → ancre HD et contexte de génération.
- `proposed-storage-map.u32le` : prototype complet des 71 971 identifiants ; ordre du registre vérifié, références canoniques sans chaînes, SHA et tailles égaux. **Donnée d'analyse non installée ; en-tête de production encore requis.**
- `implementation-plan.json` : contrat/prototype, fichiers moteur/producteurs concernés et qualifications ciblées.
- `summary.json` : synthèse chiffrée du contrôle natif et des doublons livrés.

## Décision technique proposée

1. Mutualiser les RGBA **déjà strictement identiques**, sans changement de pixels ni sélection QA ; conserver le registre logique v3 et ajouter une indirection de stockage optionnelle compacte (~0,275 Mio).
2. Adapter les **deux** lecteurs : préchargement et streaming (`effect_animation_x4_registry.cpp`). Ils construisent actuellement le nom depuis `resref + frame` et exigent la taille RGBA complète.
3. Produire un nouveau pack versionné, adapter inventaire/candidats/compilateur/staging et vérifier les 71 971 résolutions logiques ; préserver les sources/QA existantes. Un retrait brut de fichiers échouerait avec le lecteur actuel.
4. BAM natifs : réemploi de source dans le package, puis copies distinctes aux destinations WeiDU natives. Le moteur stock doit toujours trouver tous ses noms ; économie installée supplémentaire seulement avec une stratégie de liens physiques qualifiée.
5. Qualifier résolution des sources, bornes/index corrompu, normal/additif/palettes, masquage, pause/timings et streaming. Rejouer les contrats techniques existants ; contrôle ingame borné au nouveau contrat de stockage, pas campagne PRO par PRO.
6. Traiter séparément les 112 groupes de sorties divergentes ; aucun remplacement automatique de la version acceptée. Le rognage fera l'objet d'une phase distincte.

Scripts : `pipeline/recipes/effects-duplicate-analysis-20261110-v1/{analyze,link_native_anchors}.py`. Nouveau dossier/version pour toute nouvelle passe scellée.
