# AR0900 — B1.3 comparé à B1, session du 27 septembre 2026

**Bilan : gain limité sur l'expansion ; objectif de fluidité non atteint.** Somme des trois intervalles froids : 562,73 → 521,75 ms (−7,28 %). B1.3 précharge une page en 28,926 ms puis s'arrête sur son budget de 8 ms. Chargement de zone beaucoup plus lent dans cette capture : 164,68 → 1 222,95 ms, principalement dans la lecture des animations.

## Sources et installation

- Log lu : `config://bg2ee_game_root/InfinityEngine-Enhancer.log`, 5 495 870 octets, 17 943 lignes ; SHA-256 `CE3A163CC034A3BD6C99902CD04A10612BE1114929C4337F5A3C1B674DEBA3CB`.
- Dernière session B1.3 : **01:39:14.236 → 01:39:24.740**, L17626–17943, 318 lignes. Une seule expansion enregistrée, cinq échantillons chauds ; pas de répétitions comparables immédiat/différé. Dernière ligne = fin de capture, pas preuve d'arrêt propre ni de crash.
- Référence B1 : 01:09:53.093 → 01:10:02.497, L17297–17625 ; `docs/COMPARAISON_B1_A1_20260927.md`.
- Installation B1.3 : **01:34:51 Paris**, reçu `backups/renderer/20260926T233451490314Z-5ba5c9f9/renderer-install-receipt.json`. Vérification installateur réussie à cette analyse : fichiers actifs, candidat sauvegardé et sauvegardes B1 conformes.
- DLL active SHA-256 `C8EAC3B0E6C8EBA27BBABC0B67C7061B745EB998EC6D8A9CB128E2CC951B7ECE` ; INI `0A56C32AADCEAAEDBD9CD52A85A6A3ADDC030C745547333C1423DBBD1C5D2A89`.
- Activation effective L17645 : `Map page B1.3 configured: bindings=27`. Le message générique B1 L17643 « no proactive GPU Demand » décrit seulement B1 ; le module B1.3 ajoute bien un appel proactif dans cette session.
- Candidat/code/test avant installation : `docs/CANDIDAT_B13_PRECHARGEMENT_20260927.md`. Son état « non installé » est historique ; présent document + reçu enregistrent la suite.

## Comparaison de l'expansion

| Mesure | B1 | B1.3 | Écart observé |
|---|---:|---:|---:|
| Image froide 1 | 76,28 ms | 87,36 ms | +11,08 ms |
| Image froide 2 | 250,64 ms | 231,29 ms | −19,35 ms |
| Image froide 3 | 235,81 ms | 203,10 ms | −32,71 ms |
| Somme des trois intervalles | 562,73 ms | 521,75 ms | −40,98 ms / −7,28 % |
| Maximum de cette expansion | 250,64 ms | 231,29 ms | −7,72 % |
| Demand matérialisants pendant expansion | 504,179 ms | 461,353 ms | −8,49 % |
| Upload compressé, durée CPU | 23,018 ms | 21,192 ms | −1,826 ms |
| Résiduel Demand hors création/upload | 480,934 ms | 439,979 ms | −40,955 ms |
| Grandes pages uploadées pendant expansion | 20 / 320 MiB | 19 / 304 MiB | Une page de 16 MiB avancée avant expansion |
| Moyenne cinq images chaudes | 33,742 ms | 32,342 ms | −1,400 ms |
| CPU RenderTexture sur ces cinq images | 8,792 ms | 8,372 ms | −0,420 ms |

- Preuves : B1 L17571–17572 ; B1.3 L17899–17900. Calculs = sommes/moyennes des champs `samples`, offsets 0–2 froids, 3–7 chauds.
- Même AR0900, cinq overlays, WED 80×60 ; vue finale 8241×4368, 7 295 tuiles et 7 398 Demand/image dans les deux sessions. Vue intermédiaire différente : 3070×1627 → 3312×1755 ; répartition des uploads différente : 2/6/12 → 2/7/10. Vingt pages nouvellement dessinées dans les deux expansions ; B1.3 en avait déjà matérialisé une.
- Le coût de 28,926 ms a été payé **avant** la rafale. Ne pas assimiler les −40,98 ms à un gain net bout en bout ; ni soustraire directement durée d'appel et intervalles de présentation, qui ne mesurent pas le même périmètre.
- Un événement par version, cache OS non contrôlé, opportunités worker différentes : pourcentages descriptifs, pas attribution causale complète à B1.3. Le rendu chaud reste essentiellement inchangé.

## Pourquoi le préchargement s'arrête

- L17691 à 01:39:19.932 : génération 7, début du plan.
- L17755 à 01:39:20.356 : `reason=soft-budget-overrun, attempts=1, submitted=1, budgetSkips=2, notReady=0, unresolved=0, totalMs=28.926`.
- `submitted=1` implique les contrôles du code réussis sur cet appel : substitution consommée, texture résidente, génération/contexte/zone stables, entrées du cache conservées. Ce n'est pas un échec de CRC, de résolution de tuile ou de cache.
- Budget 8 ms dépassé de ~3,6×. Demand non préemptible : arrêt des tentatives suivantes pour ce plan, conformément à `MapPagePreloadPolicy::completed`. Attendre davantage dans la même génération ne relancera donc pas B1.3.
- L17868, avant expansion : `prepared=15, hits=0, misses=7, consumed=1, reservedBytes=117440876`. Sept grands buffers restent retenus ; le préchargement interrompu n'a pas supprimé la limite de capacité.
- L17921, après expansion : `prepared=19, hits=11, misses=15, consumed=12, rejected=0, failures=0, reservedBytes=0`. B1 seul : `prepared=11, hits=8, misses=19, consumed=8`.
- B1.3 : une consommation proactive + onze naturelles ; B1 : huit naturelles. Les 19 préparations sont cumulatives sur plusieurs générations, **pas 19 pages uniques utiles**. Les compteurs `hits/misses` ne comptent pas la réservation proactive.
- Avant expansion, CRC 0,949 ms + copie 3,139 ms pour la seule consommation : ~4,088 ms sur l'appel à 28,926 ms. Le reste (~24,838 ms) n'est pas ventilé ici : ressource/lecture/allocation/upload/état GL/diagnostics. Ne pas l'attribuer exclusivement au disque ou au GPU. La page proactive et son découpage natif ne sont pas nommés par cette trace.

## Chargements et ressources

| Mesure | B1 | B1.3 |
|---|---:|---:|
| LoadArea moteur | 24,70 ms | 68,29 ms |
| Détour LoadArea total | 164,68 ms | 1 222,95 ms |
| Pack d'animations total | 139,70 ms | 1 153,33 ms |
| `frameRead` pack | 139,56 ms | 1 152,19 ms |
| Données pack | 89 fichiers / 225 615 872 octets | identique |
| Pic des buffers privés B1 | 125 446 325 octets | identique (119,63 MiB) |
| Working set fin de chargement pack | 726 102 016 octets | 771 325 952 octets |

- Sources B1 L17355–17358 ; B1.3 L17685–17688. +1 058,27 ms sur LoadArea, dont +1 013,63 ms sur pack (~8,26×).
- Le chronomètre `frameRead` englobe `read_file` et son buffer de sortie (`area_animation_x4_registry.cpp:788`) ; ce n'est pas une mesure matérielle du débit disque. Cache OS, latence stockage et concurrence I/O possibles, causes non isolées.
- Le pack finit à 01:39:19.804 ; début B1.3 à 19.932, appel proactif fini à 20.356. **Ce Demand proactif n'explique pas directement le ralentissement antérieur du pack.** Le worker B1, lui, préparait déjà en parallèle (L17683) ; aucune preuve permettant de quantifier une contention.
- L17918 : pic présentation 1 528,08 ms, moyenne mixte 39,83 ms sur cinq secondes. Fenêtre incluant chargement et changement de vue : ne pas présenter ce maximum comme une image de dézoom, ni 25,1 FPS comme le FPS carte stabilisée.
- Pendant les Demand de l'expansion, compteurs I/O processus : 146 029 730 → 165 644 549 octets. Comprend le worker concurrent ; pas une mesure de lecture native seule ni de volume disque physique.
- Aucun relevé périodique mémoire B1.3 après expansion comparable à L17616 de B1 : pas de conclusion sur le pic global RAM/VRAM ou une fuite. Retour des buffers privés à zéro observé.
- Aucun `[error]` dans les deux sessions. Les six avertissements B1.3 ont les mêmes familles que B1 (détour EEex reconnu et repli sprites natifs). Ils ne démontrent ni nouvelle régression B1.3 ni validation visuelle générale.

## Décision enregistrée / suite recommandée

- Committer B1.3 comme étape expérimentale mesurée : transport du buffer prêt → moteur fonctionnel sur un appel, stratégie 8 ms insuffisante pour vider progressivement la file sur cette machine. **Ne pas qualifier l'objectif de fluidité de résolu.**
- Prochaine analyse corrective : instrumenter séparément le Demand proactif (page, lecture/ressource, CRC, copie, upload CPU, intervalle avant/après), puis déterminer quelle partie restante peut être préparée hors thread principal ou fractionnée. Porter simplement le plafond à 30 ms autoriserait des appels longs répétés ; ce n'est pas une preuve de fluidification.
- Autre axe : priorité spatiale des préparations et suppression des invalidations sans changement du WED, après contrôle de compatibilité. Sept demandes initiales restent des misses ; publication AR0900 deux fois L17681/L17689, sans quantification du travail perdu.
- Chargements généraux : comparer le pack à froid/à chaud sur plusieurs sessions, puis examiner lecture anticipée ou stockage groupé des 89 frames sans changer leurs pixels. Garder cet axe séparé du Demand de carte.
- Cette analyse ne modifie aucun code, réglage installé ou asset ; conserve les limites du candidat testé. Tests préexistants passants (DLL Release, suite C++ et huit tests Python), `git diff --check` et reçu actif vérifiés avant commit.
