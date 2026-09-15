# ReboutCX après P11 — recherche 2026-09-15

## Décision

**Pas de plafond établi. Priorité : cache RAM de session partagé entre composants, par
identité de frame, avec suppression des calculs simultanés identiques.** Aucune implémentation
de production P12, aucun nouveau job/run, catalogue, installation ou arrêt du PC.

P10/P11 et mesures de famille commités : `09129723`. Les règles `.gitattributes` ciblées
préservent les octets des scripts/jobs/preuves épinglés par SHA, y compris CRLF ; 146 comparaisons
index Git/fichiers identiques. Le fichier `append-approved-sprites-20260914-v1.json` est hors commit.

## 1. Travail répétitif découvert sur toute la famille 0x5211

Sonde CPU : 630 ressources canoniques, 65 composants, 146 066 frames modèle. Les ressources déjà
réutilisées par P11 sont exclues. Clé suffisante d'identité d'entrée : dimensions, index transparent,
SHA des indices natifs et SHA de la palette RGB de référence. Centres/resref/cycles exclus de la
clé des pixels ; conservés dans les enregistrements individuels. Cette clé peut manquer des RGB
identiques encodés avec des indices différents : c'est une borne basse du nombre de doublons.

| Portée du cache | Frames répétées | Pixels avec padding évitables |
|---|---:|---:|
| Ressource | 4 262 | 9 023 488 |
| Groupe P11 | 7 852 | 17 182 720 |
| Composant | 10 206 | 24 858 624 |
| **Session de famille** | **48 375 / 33,12 %** | **112 139 264 / 27,78 %** |
| Session + même palette native complète + mêmes classes | **48 235 / 33,02 %** | **111 940 608 / 27,73 %** |

La dernière ligne donne une clé plus stricte pour réutiliser aussi le calcul des pixels xBR et la
quantification, pas uniquement le modèle. En P11, `canonical_by_key` dans `reboutcx_full_p11.py`
est local à un composant et porte sur des ressources entières : ces répétitions restent calculées.

Cache d'entrée modèle : 27 632 clés apparaissent plusieurs fois. Conserver seulement leurs cibles
RGB x2 uint8 représente **506,27 MiB de payload**, contre **1,889 GiB** pour toutes les entrées uniques.
Métadonnées, guides, indices quantifiés, futures et buffers de transfert s'ajoutent à ces chiffres.
Ne pas conserver les crops x4 float32 : 16 fois plus volumineux que les cibles x2 RGB uint8.

### Gain estimé, non mesuré en production

Référence P11 : 329,633 s ; latence modèle CUDA 236,618 s. Hypothèse simple : coût modèle
proportionnel aux pixels et autres phases inchangées.

`329,633 − 236,618 × 0,277798 = 263,901 s` → **4 min 24**, débit **×1,249**.

Ce calcul ignore recherche des clés, copies, contention du cache, remplissage des lots et attente
de résultats partagés ; il ignore aussi les économies possibles sur xBR/quantification. Un relevé
préalable séparé ajoute ici environ 4 s. **Cible de prototype : +15 à +30 % de débit**, à confirmer
sur la même famille ; aucune annonce de gain acquis P12.

## 2. Contrat proposé pour un prototype P12

1. Cache éphémère attaché au contrôleur, sans index/catalogue dérivé persistant. Clé : contenu
   source des pixels/indices, dimensions/transparence, palettes native et de référence, classes,
   modèle et contrat complet des transformations/version des outils. Comparaisons de géométrie
   et validation des classes avant réutilisation.
2. Une seule future productrice par clé ; les demandes suivantes réutilisent son résultat.
   Ne jamais bloquer tous les workers/mémoires sur des entrées dont le producteur ne peut démarrer.
   Réserver le budget cache séparément des groupes ; éviction/libération après dernière utilisation.
3. Admission des seules clés répétées ; démarrer avec un budget configurable proche de 1 GiB,
   incluant tous les objets retenus. Les 506 MiB ci-dessus concernent seulement RGB x2.
4. Réutiliser des tableaux de pixels immuables et métriques. Toujours écrire centres, provenance,
   cycles, resref et registre pour chaque frame/composant ; ne jamais cloner un header étranger.
5. Résoudre le déterminisme avant production : **11 occurrences P11 ont les mêmes entrées modèle
   et guide mais un hash final différent**. Une seule table de classes est présente dans la famille.
   L'effet numérique du regroupement est une explication possible, non isolée par cette sonde.
   PyTorch ne garantit pas les mêmes bits entre calculs par lots et calculs isolés.
   [Précision numérique, PyTorch 2.7](https://docs.pytorch.org/docs/2.7/notes/numerical_accuracy.html).
6. Une politique à tester : toujours inférer avec N=86 et même géométrie/format mémoire ; compléter
   les fins de lots, distinguer les frames de remplissage, tester cache vide/chaud et ordres de
   livraison différents. Cette politique a un coût : ne pas l'omettre de l'estimation. Autre option :
   un plan de lots canonique rejouable. Une politique « premier résultat arrivé » seule ne suffit pas.
7. Nouveaux jobs/runs/contrats P12 ; P8/P9/P10/P11 restent scellés. Mesure principale = durée jusqu'à
   dernière vérification à couverture identique. Rapporter séparément frames logiques, hits cache,
   frames réellement inférées et remplissage : la suppression de calculs change le dénominateur des img/s GPU.

## 3. Autres pistes examinées

Environnement local : RTX 5090, PyTorch 2.7.0+cu128, cuDNN 90701. Sonde GPU : **6,85 s processus
complet**, deux frames réelles répétées en lots 86, un échauffement et deux mesures par variante.

| Variante | 32×32, modèle/lot | 64×64, modèle/lot | Conclusion |
|---|---:|---:|---|
| P11, référence répétée en fin de sonde | 35,08 ms | 157,82 ms | Référence chaude |
| Poids convolutifs channels-last | 33,06 ms | 156,51 ms | ~6,1 % / ~0,8 % local ; faible priorité |
| Entrée NCHW contiguë | 43,59 ms | 195,97 ms | ~24 % plus lent ; écarter sur ces cas |

L'entrée actuelle est déjà channels-last, malgré ses dimensions NCHW : la transposition NumPy
crée cette disposition, préservée par `.cuda().half()`. Convertir les poids ne révèle pas ici de
gain majeur. L'ordre des essais influe sur les petites durées : la première référence 32×32 valait
43,84 ms, d'où l'usage de la référence répétée. Deux tailles ne prouvent pas un optimum universel.
Sources : [format mémoire](https://docs.pytorch.org/tutorials/intermediate/memory_format_tutorial.html),
[conversion des poids](https://docs.pytorch.org/docs/main/generated/torch.nn.utils.convert_conv2d_weight_memory_format.html).

**BOX + arrondi uint8 sur GPU avant transfert** : cible x2 identique au chemin CPU pour les deux
frames testées. Réduit théoriquement les octets de sortie par 16 à surface égale : x4 float32 →
x2 uint8. Pas de gain global mesuré. La sonde réduit le lot complet mais transfère seulement la
première frame pour comparaison ; ses temps de transfert ne sont pas un benchmark du lot complet.
Risque : ordre des additions/arrondi près des seuils ; comparaison étendue requise avant adoption.

**Buffers de transfert réutilisables** : piste secondaire après cache ; tester l'allocation hors
du chemin critique et les synchronisations explicites. Ajouter `pin_memory()` à chaque lot peut
coûter plus qu'il ne rapporte ; `non_blocking=True` ne rend pas automatiquement sûres les lectures
CPU du résultat. [Guide officiel des transferts](https://docs.pytorch.org/tutorials/intermediate/pinmem_nonblock.html).

## 4. Ce que signifient les plafonds précédents

- 39,415 s hors worker GPU : les supprimer seules donnerait au plus **×1,136**.
- Garder les 236,618 s du descripteur et supprimer tout le reste donnerait **×1,393**.
- Ces bornes conditionnelles ne sont pas des plafonds matériels. Les événements CUDA autour du
  descripteur ne mesurent pas séparément chaque kernel ; les creux entre lancements peuvent être
  inclus. Le cache réduit aussi le nombre de passages du modèle, donc change ces bornes.
- Aucun profilage exhaustif, compilation TensorRT/torch.compile ou production supplémentaire
  n'a été nécessaire à cette conclusion. Un cache de frames est la prochaine expérience prioritaire.

## Preuves et validation effectuée

- Sonde : `pipeline/tests/probe_reboutcx_p12.py`, commandes `duplicates` / `gpu` ; Python configuré
  par `config://chainner_python` ; plafonds externes de processus 12/15 s lors de cette recherche.
- `docs/measurements/reboutcx-p12-20260915/duplicates-v1.json` : relevé complet initial, 3,942 s.
- `duplicates-cache-v2.json` : identité plus stricte, mémoire du cache ; relevé complet, 4,078 s.
- `gpu-layout-box-v1.json` : données brutes GPU ; aucune sortie de production, aucun fichier temporaire.
- `source-check-v1.json` : 630 SHA BAM conformes aux manifestes P11, code P11 inchangé, 0,770 s.

Validation du prochain prototype : tests de collisions de clés, futures/éviction/échec ; cache
froid/chaud et ordres différents ; alpha/classes/indices/représentants/cycles ; petites sondes
chronométrées et nettoyées, puis une famille identique uniquement lors d'une reprise autorisée.
