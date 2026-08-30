# Problèmes ouverts

Source unique des blocages non résolus. Un problème résolu est retiré de ce fichier et sa décision
durable est ajoutée à [`../docs/DECISIONS.md`](../docs/DECISIONS.md). Les statuts de zones restent
dans `areas.csv`.

## MAP-WATER-001 — rendu de liquide incorrect selon l'état du jeu

- **Périmètre** : eau marron sur AR0900 après nouvelle partie/transition et sur AR1607/AR1800 avec
  WTSWAM ; overlays visibles pendant la pause.
- **Preuves** : statuts et notes des zones dans `areas.csv`, captures/backups locaux.
- **Gate** : reproduction contrôlée nouvelle partie, transition, pause et rechargement ; identifier
  séparément couleur, animation de cycle et couche de composition.

## MAP-WTPOOL-001 — cycle WTPOOL figé

- **Périmètre confirmé** : AR0408 et AR0703.
- **Gate** : vérifier l'index de cycle et les sentinelles avec stock, x2 et x4, sans modifier la map
  dans le même essai.

## MAP-ALPHA-001 — contours de liquide en marches

- **Périmètre** : AR0604/AR0413 et défauts légers signalés sur plusieurs secondaires/eaux.
- **État** : spline périodique `fit 1.0` validée sur AR0413, mais pas solution globale.
- **Gate** : fixture alpha contenant lignes droites, courbes, coins et secondaire ; comparaison
  avant/après sans changement RGB.

## MAP-PERF-001 — gel à la première ouverture de la carte x4

- **Périmètre** : première ouverture/dezoom de la carte ingame sur AR0700N, AR0516, AR0602 et
  AR0900 ; la seconde ouverture déjà chaude n’est pas le défaut principal.
- **Cause mesurée** : 95 à 98 % des frames de pic sont portées par les matérialisations synchrones
  de `CResPVR::Demand`. Les appels GL de création et d’upload restent minoritaires.
- **État** : le mini-lot carte 3 préchauffe progressivement les pages en opt-in. Son candidat ingame
  exact est gelé par le SHA `9FCE57D1…` et se reconstruit avec succès. La campagne chaude A-B-B-A
  est validée sur les quatre zones : les médianes A/B passent à 454,11/6,08 ms sur AR0700N,
  16,21/6,25 ms sur AR0516, 8,09/6,17 ms sur AR0602 et 299,62/6,90 ms sur AR0900. Les parcours B
  comptent zéro matérialisation PVR dans le burst d’ouverture et zéro éviction du préchauffage. Un
  repack zlib niveau 0 exact a ensuite réduit le maximum AR0900 de 43,97 à 12,77 ms et le total de
  746,05 à 228,97 ms, mais il est rejeté : seuil de 8 ms manqué et poids PVRZ ×2,7419 (+264,30 Mio
  pour le seul jour). L’installation d’essai a été intégralement restaurée. L'installateur des
  builds maps est désormais transactionnel et fail-closed : reçu avant copie, inventaire fermé,
  retrait des pages obsolètes, écritures atomiques, rollback automatique et restauration reprenable.
  Une repagination block-exact 2112² a ensuite réduit les 26 pages à 90 pages dans la limite de 96,
  sans réencoder les cellules DXT ni augmenter le payload PVRZ. Ingame, le maximum tombe à 15,22 ms
  et les deux ouvertures restent à 6,33 et 6,63 ms sans matérialisation, mais la gate de 8 ms est
  encore manquée. L'installation d'essai a été restaurée et les 27 fichiers actifs sont de nouveau
  identiques au sous-build antérieur.
- **Risques ouverts** : `Demand` reste atomique. La page carrée 2112² est déjà la plus petite unité
  uniforme permettant de placer les 5 752 tuiles sous le plafond de 96 pages : la suivante, 1848²,
  exigerait 118 pages. Une repagination plus petite dépasserait donc le cache préchauffable actuel,
  tandis qu'une page rectangulaire de 60 cellules ne réduirait l'unité que de 6,25 %. La transaction
  locale du renderer gère désormais exactement le DLL et l'INI candidats avec reçu, payload stagé,
  rollback et reprise fail-closed ; les quatre anciens instantanés moteur restent des preuves brutes
  à ne plus utiliser pour une installation. `areas.csv` désigne le sous-build `page4096`, alors que les 27 fichiers
  réellement installés correspondent au sous-build `page4096-spline-fit1.0`. La campagne validée
  mesure un cache OS chaud, pas un démarrage froid. Le préparateur *shadow* 3e-A est maintenant
  implémenté : worker CPU unique, PVRZ d'override uniquement, décompression zlib et validation PVR
  bornées, buffers immuables, invalidation par génération et `Demand` natif inchangé. Les suites
  Debug/Release et 207 tests Python passent ; le préflight Release accepte 26/26 pages AR0900
  (151,73 Mio comprimés, 416,00 Mio décodés, médiane 39,38 ms/page). La gate ingame AR0900 est
  validée : sur 19 pages absentes soumises, 16 (84,21 %) étaient prêtes avant `Demand` et 3 ne
  l'étaient pas, sans échec ni résultat périmé ; le pic terminé reste borné à 4 pages / 64 Mio et le
  rendu est inchangé. Le canari 3e-B1 a ensuite passé sa gate ingame AR0900 : une seule page
  `A090001` a été revendiquée et consommée, avec zéro fallback ou mismatch, puis publication,
  upload et libération natifs ; la carte complète est restée correcte et l'installation initiale a
  été restaurée bit à bit. Cette preuve valide la frontière pour une page. Le candidat 3e-B2 a
  étendu hors ligne la même frontière à quatre revendications prêtes par génération, mais sa gate
  AR0900 a crashé après trois consommations réussies : accès nul `0xC0000005` dans le natif
  `CResPVR::Demand+0x13D` sur `A090010`, avant le quatrième résultat et avant le handoff zlib.
  Le diagnostic 3e-B2a limite ensuite les revendications à trois et journalise l'appel natif
  `CRes::Demand` exact. Il reproduit le crash, mais prouve que `A090010` est en fallback natif sans
  revendication active et que `CRes::Demand` renvoie déjà `false`, `pData=null`, `nSize=0`. Le
  quatrième buffer préparé n'est donc pas le mécanisme immédiat. Les discriminateurs 3e-B2b passent
  ensuite AR0900 avec une puis exactement deux revendications : carte complète correcte, stabilité
  supérieure à 22 secondes, sortie propre et restauration exacte. Avec deux claims, `A090009`,
  `A090010` et les pages suivantes réussissent toutes leur fallback natif. L'échec est donc borné à
  l'effet qui apparaît après la troisième substitution réussie. B2/B2a restent rejetés ; B2b2 est la
  dernière frontière diagnostique prouvée ingame, toujours default-off et non éligible à la release.
  La trace 3e-B2c manifeste ensuite la LRU de 128 pointeurs, sa libération et le helper d'ouverture
  imbriqué. Son contrôle deux claims repasse. Après le troisième claim, `A090010` est connu mais
  non prêt tandis que le worker possède le job en vol ; son ouverture native échoue avec erreur 32
  (`ERROR_SHARING_VIOLATION`), puis `CRes::Demand=false` et le crash. Le cache est seulement à
  36/128, aucune éviction/libération ne survient et la mémoire n'est pas au pic : la collision du
  lecteur fichier est la première divergence prouvée. B2d ajoute alors l'identité en vol et son
   acquittement avant fallback natif. Sa gate trois claims AR0900 passe : `A090000` attend 42,04 ms
   la fermeture shadow puis charge nativement, les trois claims préparés et tous les fallbacks
   suivants réussissent, la carte reste stable plus de 30 secondes et sort proprement. B2e passe
   ensuite quatre claims avec ce handshake, mais sa campagne quatre zones révèle le coût du
   scheduling eager : le worker prépare des dizaines de pages alors que quatre seulement sont
   consommables. B2f passe à un slot JIT, priorité worker inférieure et arrêt à la première expansion.
   Les 16 claims des quatre sauvegardes réussissent sans erreur ; le cumul `totalDemandMs` tombe de
   1 898,48 à 1 782,73 ms contre B2e (-6,1 %) et de 1 945,11 à 1 782,73 ms contre les mesures natives
   historiques (-8,3 %). AR0700N passe de 22,46 ms / deux décompressions sur la frame d'expansion B2e
   à 5,92 ms / zéro décompression. La passe unique reste insuffisante pour une qualification release.
- **Gate** : répéter une campagne A/B contrebalancée sur les quatre sauvegardes avec la source B2f
  finale, puis mener séparément une campagne cache OS froid. Toute installation doit passer par la
  transaction DLL/INI exacte désormais disponible. Le premier jalon est le préparateur
  *shadow* 3e-A décrit dans
  [`../engine/InfinityEngine-Enhancer/source-patchee/docs/map-page-offframe-preparation.md`](../engine/InfinityEngine-Enhancer/source-patchee/docs/map-page-offframe-preparation.md) : aucune
  mutation moteur/GL sur le worker, données CPU immuables, queues et mémoire bornées, invalidation
  par génération et `Demand` natif inchangé. Son implémentation et sa gate AR0900 sont terminées.
  3e-B0 a établi cette frontière sur le build manifesté : l'appel `uncompress` à
  `CResPVR::Demand+0x15F` peut recevoir le PVR déjà décodé dans la destination allouée par le moteur,
  tandis que chargement `CRes`, LRU native de 128 entrées, champs PVR, upload et libération restent
  natifs. Les signatures et neuf callsites sont maintenant vérifiés hors ligne. Le canari 3e-B1 est
  implémenté, opt-in et limité à une revendication par génération, avec CRC/taille/source stricts et
  zlib original en fallback. Debug/Release, la DLL x64, 207 tests Python, le validateur du binaire et
  la prévalidation transactionnelle sans écriture passent. Sa gate ingame AR0900 passe également :
  `canaryClaims=1`, `consumed=1`, toutes les familles de fallback à zéro, rendu inchangé, sortie
  stable et restauration exacte. Le candidat 3e-B2 est maintenant implémenté, toujours default-off,
  avec une limite compile-time de quatre revendications prêtes par génération. Les gates
  Debug/Release, la DLL x64, 207 tests Python, le validateur du binaire et la prévalidation
  transactionnelle sans écriture passent, mais l'essai ingame AR0900 échoue : trois pages sont
  consommées, puis `A090010` atteint `Demand+0x13D` avec `pData=null`, `nSize=0` et
  `bLoaded=false`, avant l'allocation et `uncompress`. Le candidat a été restauré exactement et les
  dumps sont archivés. 3e-B2a ajoute une décision par page, borne l'essai à trois revendications et
  observe l'appel `CRes::Demand` à `Demand+0xDC`. Ses gates hors ligne passent, mais AR0900 crashe au
  même endroit après que `A090010` a explicitement choisi le fallback natif, sans revendication
  active ; `CRes::Demand` renvoie `false` et laisse la ressource nulle. La gate suivante était un
  contrôle une revendication avec la même télémétrie, puis un discriminateur deux revendications.
  Les deux passent ingame. La lecture `nCount` ajoutée n'est toutefois pas exploitable : B2b1
  observe des entiers impossibles sur des chargements réussis, tandis que B2b2 observe zéro ; ne pas
  l'interpréter ni l'écrire. 3e-B2c termine la comparaison sans champ deviné : le contrôle deux
  claims passe, tandis que le test trois claims échoue sur l'ouverture native de `A090010` avec
  `ERROR_SHARING_VIOLATION` alors que le job shadow est en vol. La gate suivante est 3e-B2d :
  suivre explicitement l'identité en vol, retirer/annuler la préparation et attendre
  l'acquittement de fermeture avant le fallback natif visant cette même page. Couvrir cette
  concurrence par un test déterministe, puis repasser trois claims sur AR0900. Cette gate est
  maintenant passée : une attente réelle de 42,04 ms précède une ouverture native réussie et les
  trois consommations terminent sans crash. La gate quatre claims 3e-B2e passe à son tour avec le
  handshake inchangé : `A090001`, `A090008`, `A090009` et `A090010` sont consommées, deux fallbacks
  en vol attendent correctement leur acquittement, toutes les demandes natives réussissent et la
  carte reste stable plus de 30 secondes. B2f remplace ensuite la soumission eager par un slot JIT.
  Sa première campagne AR0900/AR0602/AR0516/AR0700N consomme 16/16 claims et améliore le cumul de
  6,1 % contre B2e, sans erreur ni contention compressée sur la première expansion. La prochaine
  gate est une campagne A/B répétée/contrebalancée avec le correctif final de résumé, puis une
  campagne cache OS froid séparée. Si le +1,1 % AR0700N contre la baseline persiste, ajuster le choix
  de page ou la fenêtre d'inactivité avant toute hausse de la limite de quatre claims.
- **Preuve et protocole** :
  [`../docs/AUDIT_PERFORMANCES_CARTES_X4_SUIVI.md`](../docs/AUDIT_PERFORMANCES_CARTES_X4_SUIVI.md).
- **Règle** : prototype non éligible à la release ; aucune promotion de contenu ou de manifeste
  avant validation ingame concluante et accord explicite.

## MAP-QA-001 — zones installées non validées

- **Périmètre actuel** : lire `areas.csv`; au moment de l'assainissement, AR1607 et AR1800 étaient
  `installed-pending-qa` après refus sur l'eau.
- **Gate** : correction, vérification SHA de l'installation puis nouvelle QA utilisateur.
- **Règle** : ne jamais transformer ce statut en `validated-installed` depuis un log de batch.

## ENGINE-UI-001 — tooltips UI instables avec les FPS EEex déplafonnés

- **Périmètre** : BG2EE 2.7.3 avec EEex 1.2.0 et le renderer local ; les bulles contextuelles des
  boutons apparaissent immédiatement et clignotent à chaque mouvement de souris lorsque la cadence
  de présentation atteint environ 154 à 165 FPS.
- **Preuve A/B** : `Tooltips=15` et `Maximum Frame Rate=30` sont restés inchangés. Déconnecter le
  préchauffage PVR du callback post-`SwapBuffers` n'a produit aucun changement ingame ; ce candidat
  a été restauré exactement. Avec le renderer antérieur restauré, les seuls réglages EEex
  `Uncap FPS Limit Enabled=1` et `Uncap FPS Limit=30` suppriment le défaut.
- **État** : contournement local conservé à 30 FPS. Le rendu des cartes x4 ne dépend pas du
  déplafonnement. Le préchauffage reste fonctionnel, mais ses paramètres exprimés en frames
  progressent plus lentement en temps réel : un délai de 30 frames vaut environ 1 s à 30 FPS contre
  0,18 s à 165 FPS.
- **Gate** : avant de rétablir le déplafonnement, vérifier le chemin EEex
  `EEex::Override_uiDrawMenuStack`, puis mener un A/B à 30 FPS et à la fréquence de l'écran avec
  délai et stabilité des tooltips. Ne pas compenser en modifiant `Tooltips=15`.
- **Preuve détaillée** :
  [`../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/eeex-tooltip-uncapped-fps.md`](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/eeex-tooltip-uncapped-fps.md).

## ENGINE-OCCLUSION-001 — validation ingame du bridge structurel xN

- **Périmètre** : animations de zone v1/v2/v3 non masquées, Monster, MonsterIcewind et Character
  remplacés ; premier plan WED, dither partiel, flag ARE `No Wall`, transitions et resize.
- **État** : jalon Phase 1 validé ingame sur AR0516 pour une animation de zone `CGameStatic` x4
  et une créature `Character` xN. Le bridge générique réapplique correctement l'occlusion WED au
  backing xN, sans règle par map. Le défaut résiduel du `SPHINCT` inférieur d'AR0516 a été prouvé
  indépendant du bridge : géométrie `Cover animations` absente du WED vanilla. Un polygone local
  `0x09` a été validé ingame le 2026-08-27 ; cette exception n'élargit pas le périmètre moteur.
  Installation QA locale seulement ; promotion release interdite.
- **Preuve** :
  `engine/InfinityEngine-Enhancer/source-patchee/docs/validation/native-occlusion-phase1-validation.md`
  et `engine/InfinityEngine-Enhancer/source-patchee/docs/validation/native-occlusion-ar0516-wed-correction.md`.
- **Gate restante** : matrice A/B de
  `engine/InfinityEngine-Enhancer/source-patchee/docs/native-occlusion-phase1.md`, stabilité GL et
  mémoire, Monster/MonsterIcewind, effets/classes non modélisés, transitions et compatibilité packs
  v1/v2/v3 sans modification de leurs hashes.
