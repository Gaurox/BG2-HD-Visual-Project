# ReboutCX P12 — dix nouvelles familles, 2026-09-15

## Résultat

- Autorisation : dix nouvelles familles ; suivi + commit. Extinction annulée par la dernière consigne utilisateur.
- **10/10 familles, 638 composants, 1 775 174 frames source produits et vérifiés**.
- Lot : **3 188,068 s = 53 min 08 s**, processus et interruptions/reprises inclus ; préparation séparée **17,621 s**.
- Huit familles sans incident : médiane **281,875 s = 4 min 42 s** ; plage 259,376–298,658 s.
- Inférences logiques : **1 492 601** ; calculées : **936 526** ; évitées par cache : **556 075 (37,26 %)**.
- Gain comparatif P11→P12 déjà mesuré sur `0x5211` : **+10,63 % de débit**, 329,633→297,950 s ;
  voir [REBOUTCX_P12_MESURE.md](REBOUTCX_P12_MESURE.md). Le lot courant ne constitue pas un nouveau comparatif P11.
- Suivi : **33/78 complètes, 45 restantes, 2 109 composants** ; production uniquement.

| Animation | Composants | Temps famille, reprises incluses (s) | Sessions |
|---|---:|---:|---:|
| 0x5212 | 65 | 285,838 | 1 |
| 0x5300 | 65 | 473,912 | 2 |
| 0x5301 | 65 | 281,904 | 1 |
| 0x5302 | 65 | 275,381 | 1 |
| 0x5303 | 53 | 259,376 | 1 |
| 0x5310 | 65 | 298,658 | 1 |
| 0x5311 | 65 | 281,845 | 1 |
| 0x5312 | 65 | 275,194 | 1 |
| 0x5313 | 65 | 284,084 | 1 |
| 0x6000 | 65 | 461,828 | 2 |

## Exécution et preuves

- Plan : `docs/measurements/reboutcx-p12-next10-20260915-v1/plan.json` ; dix premiers IDs en attente du P9-v1.
- Résultats : `batch-summary.json`, `production-report.json` dans ce même dossier.
- Par famille : `family-runs/complete-reboutcx-p12-v1/measurements/production-p12-v1.json`.
- Jobs : `*/jobs/reboutcx-p12-cache86-v1.json` ; runs : `*/runs/reboutcx-p12-cache86-v1/`.
- Sessions/journal : `sprite/.work/reboutcx-p12-production/` ; journal append-only
  `reboutcx-p12-next10-20260915-v1-batch/families.jsonl`.
- Runtime P12 existant : trois composants, deux préparateurs, trois post-traitements, mémoire 4 096 MiB,
  cache 1 024 MiB, micro-lot GPU 86. Une session/cache indépendant par famille ; familles séquentielles.
- Préparation directe depuis les sources xBR scellées : `pipeline/scripts/reboutcx_prepare_sources_p12.py`.
  Provenance native et SHA épinglés ; contrat P8 réutilisé ; aucune fabrication de hash de référence GPU,
  aucune écriture P8. Association des composants par ensembles RESREF exacts.
- Orchestration bornée : `pipeline/scripts/reboutcx_run_family_set_p12.py <plan> [--resume]`.
  Reprise = vérification des sorties déjà présentes ; calcul des seules sorties manquantes.
- Finalisation : `pipeline/scripts/reboutcx_finish_family_set_p12.py <plan>` ; contrôle **17,838 s**,
  638 manifests/événements de vérification concordants, **1 471 manifests antérieurs inchangés**,
  **1 297 références code/entrées inchangées**, aucun répertoire temporaire de run restant.
- Nouveau snapshot : `sprite/catalogs/creature-x2-reboutcx/jobs/playable-characters-reboutcx-progress-p12-v1.json`.
  P9-v1 conservé ; pilote `0x5211` associé aux manifests P12 déjà mesurés.
- Scripts runtime P8–P12 et runs préexistants inchangés. Aucun catalogue global construit,
  aucune QA humaine acceptée, installation ou release.

## Deux interruptions Windows

`PermissionError [WinError 5]` au renommage final d'un répertoire temporaire complet :

| Famille/composant | Temporaire | SHA-256 du manifeste récupéré |
|---|---|---|
| `0x5300/helm13-wqlj5` | `.reboutcx-p12-cache86-v1.tmp-11712` | `C3FE7832813649762EF2AED7DEE2576607F12A6828A7587617724727AD99DC57` |
| `0x6000/dwsw1h01-wqlsc` | `.reboutcx-p12-cache86-v1.tmp-15712` | `C46FD28971F84A2FDB69EB163CFCB666014463E57E3E987589A8FD68ACAC96BB` |

- Après arrêt des workers : chemins résolus dans le workspace, destination absente, manifeste complet ;
  renommage natif PowerShell puis `reboutcx_full_p12.py verify`. Vérifications ciblées <1 s chacune.
- Aucun octet de sprite modifié pour récupérer ces deux sorties. À la reprise : respectivement
  15 et 44 composants existants revérifiés ; reste produit normalement.
- Les temps famille ci-dessus incluent les deux tentatives et l'attente de reprise. Les pics de cache
  des rapports désignent la dernière session ; les sommes par phase se chevauchent entre workers.
- Cause précise du verrou Windows non établie. Amélioration future : retry borné du renommage final
  dans une **nouvelle version** du runtime ; ne pas modifier P12 dont les SHA sont maintenant scellés.

## Pourquoi 76 / 78 familles ?

Une famille décrit un avatar par ID d'animation : race/gabarit, sexe, apparence de classe et variante.
Plusieurs personnages nommés peuvent utiliser la même famille ; ses ~65 composants décrivent les
corps/armures et couches d'équipement (armes, casques, boucliers), pas des personnages supplémentaires.

| Groupe d'IDs | Clerc | Guerrier | Mage | Voleur | Moine | Total |
|---|---:|---:|---:|---:|---:|---:|
| LOW, 0x5xxx | 8 | 8 | 6 | 8 | 0 | 30 |
| Ordinaires, 0x60xx–0x63xx | 12 | 12 | 10 | 12 | 0 | 46 |
| 0x6500 / 0x6510 | 0 | 0 | 0 | 0 | 2 | 2 |
| **Total** | **20** | **20** | **16** | **20** | **2** | **78** |

Source : jobs `*/family-runs/complete-xn-xbr2x/jobs/*.json` et inventaire du snapshot P9-v1.
Le job historique `sprite/catalogs/creature-x2-nearest/jobs/append-all-playable-characters-v1.json`
référence **76** familles sous `sprite/families/playable-characters`, plus deux références historiques
sous `sprite/jobs` : guerrier nain masculin `0x6102`, guerrière humaine `0x6110`. Total : **78**.
Ce décompte décrit l'inventaire des animations ; il ne mesure pas le nombre de compagnons recrutables.
