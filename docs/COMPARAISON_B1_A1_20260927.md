# AR0900 — retour B1 comparé à A1, 2026-09-27

**Résultat : amélioration partielle confirmée dans cette capture ; objectif de fluidité non atteint.** B1 consomme huit pages préparées. Les trois images d'expansion passent de 814,81 à 562,73 ms (−30,94 %) ; le plus grand intervalle de cette expansion passe de 495,58 à 250,64 ms (−49,42 %).

## Sources et comparabilité

- Log : `config://bg2ee_game_root/InfinityEngine-Enhancer.log`, 5 421 921 octets, 17 625 lignes ; SHA256 `E1F842CF46FAAF7E62CE14E3772CA46EC11A611C8CD84CE5FDA6E6C7A719ED46`.
- B1 : dernière session, **01:09:53.093 → 01:10:02.497**, L17297–17625, 329 lignes. Activation explicite L17314 ; dernière statistique worker L17609.
- A1 : **00:35:48.390 → 00:35:57.361** ; [analyse précédente](PVR_DIAGNOSTICS_A1_20260927.md).
- DLL/INI présents : empreintes identiques à [l'installation B1](PAGES_CARTE_B1_INSTALLATION_20260927.md). Aucun processus BG2EE/InfinityLoader observé lors de la lecture.
- Un seul événement wide-view exploitable dans chacune des deux sessions ; cinq images chaudes après expansion. Pas de série de réouvertures ni de garantie de cache OS froid.
- Même AR0900, WED 80×60 / 5 overlays, vue finale 8241×4368, 7 295 tuiles / 7 398 Demand par image finale. Même rafale de 20 grandes pages, distribution **2 / 6 / 12** ; 21 matérialisations en incluant une petite texture.
- Vue intermédiaire légèrement différente : A1 3012×1596 / 2180 tuiles, B1 3070×1627 / 2257 tuiles. Les pourcentages décrivent ces captures, pas une performance garantie.

## Mesures

| Mesure | A1 | B1 | Lecture |
|---|---:|---:|---|
| Image d'expansion 1 | 73,64 ms | 76,28 ms | Pas d'amélioration ici |
| Image d'expansion 2 | 245,59 ms | 250,64 ms | Pas d'amélioration ici |
| Image d'expansion 3, arrivée vue complète | 495,58 ms | 235,81 ms | Gain principal : −259,77 ms |
| Somme des trois intervalles | 814,81 ms | 562,73 ms | −252,08 ms / −30,94 % |
| Demand matérialisants pendant expansion | 755,600 ms | 504,179 ms | −33,27 % |
| Appels upload compressé, CPU | 22,121 ms | 23,018 ms | Quasiment inchangé |
| Résiduel ressource/lecture/décodage/allocation/etc. | 733,196 ms | 480,934 ms | Baisse au bon endroit ; ce n'est pas une mesure isolée de zlib |
| Grandes pages / niveau de base soumis | 20 / 320 MiB | 20 / 320 MiB | Même volume graphique |
| Cinq images chaudes, moyenne | 41,878 ms | 33,742 ms | −19,43 % observés ; échantillon trop court pour attribuer ce gain à B1 |
| CPU RenderTexture sur ces cinq images | 8,662 ms | 8,792 ms | Travail de rendu chaud non réduit |
| Chargement pack animations | 138,07 ms | 139,70 ms | +1,63 ms |
| Détour LoadArea total | 162,16 ms | 164,68 ms | +2,52 ms ; pas de déplacement des ~252 ms gagnées dans ce marqueur |

Preuves : événements A1 L17248–17249 ; B1 L17571–17572 ; chargements A1 L17033/L17036, B1 L17355/L17358. Les sommes des trois intervalles ne mesurent pas une latence entrée utilisateur → carte complète.

Images chaudes B1 : 32,80 / 32,57 / 34,40 / 34,63 / 34,31 ms. La présentation mixte à 39,3 FPS sur cinq secondes (L17580) inclut plusieurs états de vue ; ne pas la présenter comme le FPS de carte complète.

## Ce que B1 a effectivement fait

- L17492, avant événement : `generation=7, prepared=10, hits=0, misses=7, reservedBytes=117440876`.
- L17587 puis L17609 : `prepared=11, hits=8, misses=19, consumed=8, rejected=0, failures=0, reservedBytes=0`.
- Huit substitutions réussies / 27 demandes ciblées observées = 29,6 %. Entre ces deux relevés : huit hits et douze misses, cohérents avec les vingt grandes pages de l'expansion. Les sept demandes initiales avaient toutes manqué la préparation.
- CRC natif : 8,135 ms ; copie : 22,268 ms ; total 30,403 ms pour les huit consommations. Le moteur conserve lecture/allocation/upload.
- `prepared` est cumulatif et peut inclure des générations précédentes ou des résultats retirés : **11 ne signifie pas 11 pages uniques utiles**. Les logs n'identifient pas individuellement les huit substitutions.
- `renderWorkerWaits=0` est une déclaration du chemin sans attente du nouveau code, pas un chronomètre indépendant des blocages du thread principal.

## Ressources et limite d'admission

- Pic comptabilisé des buffers B1 : **125 446 325 octets = 119,63 MiB**, sous le budget 128 MiB. Retour à zéro après la rafale ; ne constitue pas une preuve générale d'absence de fuite.
- Avant expansion : **117 440 876 octets = sept buffers de 16 MiB + en-tête PVR**. Il reste moins de 16 MiB sous le plafond : insuffisant pour admettre une autre page avec entrée compressée + sortie décodée + réserve de travail. Le worker attend donc de la capacité avant d'avancer ; augmenter seulement son parallélisme ne corrigerait pas cette situation.
- Pic brut de mémoire supplémentaire et I/O doublées possibles : B1 est un compromis, pas une réduction démontrée de toutes les ressources. Cache privé disque : 155,59 MiB.
- Fin de chargement du pack : working set A1 652 562 432 octets, B1 726 102 016 ; écart ≈70,13 MiB. Mesure processus entière, comprenant le worker en parallèle ; ne pas imputer cette différence au pack d'animations seul.
- Fin de fenêtre B1 : working set 916 774 912 octets, pic processus 1 010 216 960, private bytes 1 945 300 992 (L17616). Pas de relevé A1 équivalent à la même phase : comparaison globale RAM non concluante.
- Compteurs I/O relevés dans les fenêtres Demand : A1 126 969 832 octets, B1 146 029 730. Ce sont des compteurs **processus** ; B1 y inclut des lectures concurrentes du worker. Ne pas attribuer tout ce volume au lecteur natif ni le comparer à des octets physiques lus sur disque.
- Aucune preuve de saturation VRAM, de swapping ou de limite CPU globale dans ces traces. Les chronos d'upload CPU ne mesurent pas la fin GPU.

## Prochaine étape proposée

1. **B1.3 : consommer progressivement les pages prêtes avant le dézoom**, via Demand natif sur le thread/contexte autorisés, avec admission selon marge disponible et coût observé. Cela libère les buffers CPU et permet au worker de continuer au-delà des sept pages retenues. Aucun Demand spéculatif si la page n'est pas effectivement réservée prête ; un appel natif reste non préemptible.
2. **Priorité spatiale** : préparer d'abord les pages de la vue initiale, puis celles révélées par l'expansion. Aujourd'hui l'ordre TIS prépare des pages qui ne servent qu'à la dernière étape, tandis que les sept premières demandes restent natives.
3. Examiner la réactivation du même WED au chargement : WED AR0900 publié L17352 puis L17359, compteur worker `generation=7`. Le code invalide avant LoadArea ; préserver une préparation compatible lors d'un appel sans changement pourrait éviter du travail perdu. Les logs ne suffisent pas à chiffrer ce gaspillage.
4. Après correction de couverture : traiter séparément le rendu chaud, toujours ~8,8 ms de CPU RenderTexture et 7 398 Demand/image. Ne pas attribuer à B1 une optimisation des soumissions qui n'a pas été codée.

Pas d'augmentation automatique du budget mémoire, pas de dégradation graphique, pas de nouvelle installation pendant cette comparaison. Validation de B1.3 : même sauvegarde, ouvertures immédiates/différées répétées, latence carte et chargement total, coverage avant première demande, mémoire et pics de présentation.
