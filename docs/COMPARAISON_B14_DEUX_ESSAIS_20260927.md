# B1.4 — deux essais AR0900, récupération native et lectures identifiées

**Décision : priorité à la récupération synchrone des données, puis à la règle d'arrêt du préchargement.** Même page A090000 : Demand 83,051 → 8,325 ms, dont CRes::Demand 74,449 → 2,425 ms ; upload CPU quasi constant ~1,1 ms. Animations : la lecture stream explique ~97 % de l'écart de chargement entre les deux essais. Le dézoom conserve des pointes ~234 ms.

## Sources

- Log `config://bg2ee_game_root/InfinityEngine-Enhancer.log` : 5 686 913 octets, 18 688 lignes, SHA-256 `984D447720839942167C2F1FC7B9060EC7E446E7B78C0F811F29F33B07D057F1`.
- Essai 1 : **02:50:29.078 → 02:50:51.717**, L17944–18318, 375 lignes.
- Essai 2 : **02:50:57.706 → 02:51:16.341**, L18319–18688, 370 lignes.
- Même DLL B1.4 et INI ; activation du profilage L17962/L18337. Installation et sauvegardes vérifiées via `backups/renderer/20260927T004837469820Z-68d78d2a/renderer-install-receipt.json`.
- Protocole manuel demandé : même sauvegarde, attente cinq secondes, carte cinq secondes, quitter puis relancer. L'utilisateur déclare les deux essais terminés. Aucun outil de contrôle de l'interface utilisé.
- Premier lancement ≠ cache OS froid garanti ; second lancement ≠ toutes les ressources garanties en cache. Aucune purge ou mesure matérielle des I/O.

## Préchargement A090000 : les phases manquantes

| Mesure | Essai 1 | Essai 2 |
|---|---:|---:|
| Demand natif total | 83,051 ms | 8,325 ms |
| CRes::Demand : récupération de ressource | 74,449 ms | 2,425 ms |
| Dont helper d'ouverture | 0,082 ms | 0,089 ms |
| CRC | 2,044 ms | 0,953 ms |
| Copie du PVR préparé | 4,332 ms | 3,069 ms |
| Création texture | 0,024 ms | 0,029 ms |
| Upload compressé, CPU | 1,126 ms | 1,085 ms |
| Autre coût natif résiduel | 1,076 ms | 0,764 ms |
| Appel avec capture/restauration GL | 83,251 ms | 8,557 ms |
| Pompe complète | 83,286 ms | 8,582 ms |
| Intervalle précédent | 34,041 ms | 23,162 ms |
| Intervalle suivant | 92,362 ms | 30,375 ms |
| Entrées cache occupées avant | 29 | 30 |
| Tentatives / soumissions validées | 1 / 1 | 1 / 1 |

- Sources : L18075/L18094–18095 ; L18462/L18481–18482. `measured=true`, `outcome=consumed`, `residualValid=true`, `validated=true`, génération 7 conservée dans les deux essais.
- CRes::Demand représente **89,6 %** du premier appel ; sa variation de 72,024 ms explique l'essentiel des 74,726 ms d'écart total. Son périmètre comprend récupération/lecture/allocation ; pas de chronomètre ReadFile isolé. L'ouverture elle-même n'est pas dominante.
- Le GPU n'est pas disculpé globalement : seul le coût CPU de soumission est mesuré. En revanche, ces uploads ~1,1 ms n'expliquent pas les 74 ms variables de CRes::Demand.
- Signature compatible avec disponibilité différente des données en cache système et/ou latence de récupération. Les traces ne distinguent pas cache physique, contention, allocation ou attente interne au moteur.
- Compteurs de lecture **processus** : 18 912 266 puis 7 021 509 octets ; le premier inclut potentiellement le worker concurrent. Ne pas les attribuer au seul fichier natif.

## Arrêt trop rigide, mais coût froid réellement dangereux

- Dans les deux essais, `soft-budget-overrun` interrompt le plan après sa première page, parce que la pompe dépasse 8 ms. Aucun échec de validation ni saturation des 128 slots natifs : 29/30 seulement occupés.
- Essai 1 : +83 ms de travail non préemptible ; reprendre automatiquement sans traiter la récupération pourrait répéter des saccades importantes.
- Essai 2 : pompe 8,582 ms, intervalle suivant 30,375 ms. Le seuil coupe définitivement un appel à peine au-dessus de 8 ms, alors que l'image suivante reste sous la cible configurée de 33,33 ms. Cela ne prouve pas que tous les appels suivants seraient aussi courts, ni une cadence constante à 60 FPS.
- Attendre cinq secondes supplémentaires ne réactive pas un plan arrêté. Avant dézoom, les mêmes sept buffers restent retenus : 117 440 876 octets, L18258/L18609.
- Le budget privé reste respecté : pic 125 446 325 octets = 119,63 MiB dans les deux sessions, retour à zéro après expansion. Pas de preuve d'une limite mémoire comme cause première de ces temps natifs.

## Animations : lecture dominante, pas ouverture des 89 fichiers

| Mesure | Essai 1 | Essai 2 |
|---|---:|---:|
| Pack total | 1 165,18 ms | 143,30 ms |
| `frameRead` englobant | 1 164,82 ms | 143,18 ms |
| Ouverture / taille / seek | 7,957 ms | 4,807 ms |
| Allocation / initialisation buffers | 59,073 ms | 34,863 ms |
| Lecture stream | 1 093,915 ms | 102,570 ms |
| Fermeture | 2,897 ms | 0,562 ms |
| LoadArea moteur | 69,54 ms | 23,78 ms |
| Détour LoadArea total | 1 235,13 ms | 167,31 ms |

- Sources : L18006–18010 et L18380–18384. Mêmes 89 fichiers, 225 615 872 octets (215,16 MiB), 3 BAM / 2 timelines.
- Lecture stream : **93,9 %** du `frameRead` au premier essai. Sa variation 991,345 ms explique **97,0 %** des 1 021,88 ms d'écart du pack. Allocation et nombre d'ouvertures ne sont pas la priorité de ce ralentissement.
- Fichier le plus lent : `AAX4-AM0900DM-frame023.rgba`, 2 737 152 octets / 20,282 ms ; second essai `...frame026.rgba`, 2 857 728 octets / 2,611 ms. Aucun fichier unique ne porte à lui seul toute la seconde de lecture.
- Le second essai retrouve les ~140 ms observées avec B1. Cela affaiblit l'hypothèse d'un surcoût fixe apporté par B1.3/B1.4 ; ne pas transformer cette répétition en preuve d'une cause matérielle unique.
- `streamRead` = appel stream incluant attente OS/cache/copie, pas temps physique disque. Aucun remplacement des assets ou changement de pixels entre essais.

## Dézoom et limites de comparaison

| Fenêtre capturée | Essai 1 | Essai 2 |
|---|---:|---:|
| Trois intervalles d'expansion | 85,38 / 233,20 / 216,71 ms | 132,10 / 234,06 / 84,80 ms |
| Somme | 535,29 ms | 450,96 ms |
| Maximum | 233,20 ms | 234,06 ms |
| Demand matérialisants cumulés | 463,481 ms | 379,764 ms |
| Upload compressé CPU cumulé | 22,930 ms | 22,103 ms |
| Grandes pages uploadées dans la fenêtre | 19 | 18 |
| Moyenne cinq images chaudes | 37,334 ms | 32,926 ms |
| CPU RenderTexture chaud moyen | 9,154 ms | 8,096 ms |

- Sources : L18286–18287 et L18658–18659. Même vue finale 8241×4368, 7 295 tuiles / 7 398 Demand par image. Pas de nouvelle optimisation du rendu chaud.
- **Fenêtres non strictement équivalentes** : première 1031×546 → 1383×733 ; seconde 1202×637 → 2008×1064. Une page supplémentaire est déjà chargée avant la seconde fenêtre ; A090022 apparaît L18633 avant les trois matérialisations du premier échantillon L18635–18637. La somme 450,96 ms n'est donc pas une mesure comparable de toute l'ouverture, ni un gain de 15,8 % attribuable au cache seul.
- Référence B1.3 : 521,75 ms / maximum 231,29 ms ; B1 : 562,73 / 250,64 ms. Les pointes restent du même ordre malgré le second lancement et l'attente préalable.
- Compteurs finaux : essai 1 `prepared=19, hits=11, misses=15, consumed=12` ; essai 2 `prepared=14, hits=10, misses=16, consumed=11`. Une consommation proactive dans chaque total ; préparations cumulatives multigénération, pas nombre de pages uniques. `rejected=0, failures=0` dans les deux sessions.
- Aucun `[error]`. Familles d'avertissements identiques aux essais précédents (EEex reconnu, repli sprites natifs) ; aucune validation visuelle déduite des logs.

## Suite corrective retenue pour l'analyse de code

1. **Priorité carte : supprimer ou anticiper la récupération native restante.** B1 prépare une copie privée décodée, mais le moteur récupère encore sa propre source avant la substitution ; réutiliser les octets privés à une frontière de lecture native validée est une piste à étudier. Préserver allocations, durées de vie, compteurs et cache natifs ; pas d'écriture improvisée dans `CRes::pData`. Inclure tout buffer compressé éventuellement conservé dans les 128 MiB. Repli natif immédiat sur source incompatible ou préparation absente.
2. **Précondition technique : établir le contrat du lecteur avant substitution.** Le plan B1 avait écarté ce branchement faute de preuve d'ownership (`PLAN_IMPLEMENTATION_PAGES_CARTE_B1_20260927.md`, §3). Ne pas remettre simplement le worker sur les fichiers `override` : les copies privées évitent des conflits de partage connus. Les présentes mesures justifient de rouvrir cette étude ; elles ne valident pas encore une implantation.
3. **Ordonnanceur : distinguer erreur de validité et dépassement temporel.** Conserver l'arrêt sur incohérence de source/cache/contexte ; concevoir une suspension/réadmission bornée pour un petit dépassement, avec suivi des intervalles et historique du coût. Ne pas lever globalement le seuil vers 30/80 ms : le premier essai démontre le risque. Réévaluer après sécurisation de l'accès aux données.
4. **Animations : préparer les lectures hors du chemin bloquant lorsque la prochaine zone est connue**, avec mémoire bornée, publication atomique du pack complet et ressources inchangées. Regrouper les fichiers n'est pas le premier correctif justifié par ces mesures : l'ouverture coûte ~8 ms contre ~1 094 ms de lecture. L'anticipation peut améliorer la réactivité sans supprimer le temps réel nécessaire à une lecture froide.
5. Vérification future : pages résidentes avant ouverture, coût natif par phase, maximum des intervalles **avant et pendant** dézoom, mémoire totale et chargement de pack ; ne pas déplacer une longue saccade hors de la fenêtre de télémétrie et l'appeler un gain.

Aucune nouvelle manipulation utilisateur requise pour cette analyse. Code et installation B1.4 conservés ; aucun réglage de budget, asset, payload ou release modifié à partir de ces résultats.
