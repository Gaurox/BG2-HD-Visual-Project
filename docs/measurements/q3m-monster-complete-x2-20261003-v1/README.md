# Phase 5 — production complète Monster Q3m K6 x2

- **Terminée** : 39 BAM, 20 925 frames, 2 288 cycles / 41 217 slots ; source/cache/V6 identiques, contrôles natifs passés (**4 090 666 968 pixels**, 37 ressources nouvelles + deux preuves du pilote réutilisées). Reprise complète : **3 190 hits**, aucun processeur/Torch, payloads inchangés.
- Pause historique conservée dans `pause.json` ; reprise séparée sous `work/production-resume-v1/` : Bodhi/MGLC hits uniquement, MBEH **276 hits + 778 nouveaux travaux modèle**, 4 668 cibles. Essai interrompu : 274 résultats modèle MBEH conservés ; nombre exact de cibles non sauvegardées inconnu.
- Périmètre : trois familles figées par les phases 1/2 ; `verification.json` = rapport final. Pack isolé ; aucun catalogue actif, installation, QA ingame ou release écrit.
- Recette acquise : BAM V1 indexé → guides xBR V3 existants → ReboutCX FP16 x4 fixed86/q32 → BOX float32 x2 → encodeur exhaustif OKLab² f64 K6 → I/F/dep → feuilles V6 → catalogue V2 owner `3`, profils `2..7`, règle `2`. Sans B, Q8c ni tramage. Aucun nouveau xBR ni analyse de déduplication.
- Cache commun : `sprite/.work/q3m-monster-pilot-x2-20261003-v1`, namespace `21a989cf5180280bbcc3801296b65e40e2af11f83b63e1a29a3249ecd44bd75c`. Pilote acquis : 272 résultats Q3m réels repris ; aucun résultat ancien xBR/ReboutCX adopté comme Q3m.

Volumes complets produits ; travaux nouveaux = résultats persistants distincts sur l'ensemble des deux essais :

| Cible / CRE | ID / famille / profils | BAM | Frames | Cycles / slots | Travaux modèle nouveaux | Hits acquis / marqueurs nouveaux |
|---|---|---:|---:|---:|---:|---:|
| Bodhi / `BODHI.CRE` | `0x7F30` / `NBOH` / `4,5` | 13 | 8 100 | 765 / 15 561 | 972 | 272 / 0 |
| Golem geôlier AR0602 / `IGOLEM02.CRE` | `0x7F07` / `MGLC` / `6,7` | 13 | 5 994 | 758 / 9 717 | 890 | 0 / 2 |
| Spectateur / `BEHSPE01.CRE` | `0x7F02` / `MBEH` / `2,3` | 13 | 6 831 | 765 / 15 939 | 1 052 | 0 / 2 |
| Total | | **39** | **20 925** | **2 288 / 41 217** | **2 914** | **272 / 4** |

Chaque famille : `G1,G11,G12,G13,G14,G15,G2,G21,G22,G23,G24,G25,G26`. `MGLC` conserve ses 279 frames non référencées par les cycles. Source : 33 payloads BAM distincts pour 39 refs ; déduplication Q3m : 3 190 travaux profil/recette compris, dont 3 184 modèle et six marqueurs. Les partages de sources acquis restent distincts des identités de ressources/runtime.

## Artefacts et contrôles acquis

- Feuilles : `sprite/.work/q3m-monster-complete-x2-leaves-20261003-v1/{RESREF}.registry` + `leaves.json`.
- Pack isolé : `sprite/.work/q3m-monster-complete-x2-pack-20261003-v1/`, 39 composants/shards, trois IDs ; `iee-assets/creature-sprites/CreatureSprites-XN.catalog`, `pack.json`, `oracles/`, `previews/`.
- Source → cache → feuille : toutes les frames, dimensions/centres/transparence x1, représentants, cycles/slots, indices/profil/palette, I/F/dep. Assemblage sans réencodage. `NBOHG1/NBOHG2` : feuilles et oracles identiques au pilote.
- Lecteur/compositeur natif : exécutable de phase 4 inchangé, 37 nouvelles ressources ; deux preuves natives du pilote réutilisées sur identité feuille/oracle/lecteur. Neuf palettes × trois encodages : six fits, transparence 128/ombre 64, ombre opaque, RGB arbitraire avec alpha matière uniforme ; toutes les frames, y compris non référencées, tous les slots et centres. Hors contexte GL/jeu.
- Reprise persistante : `verify_resume.py` impose 3 190 hits, aucun processeur/Torch, mêmes SHA des payloads avant/après. Aucun modèle réexécuté pour cette vérification.
- Runtime candidat de phase 3 conservé : `.work/q3m-monster-phase3-20261003-v1/candidate/InfinityEngine-Enhancer.dll`, SHA `ade49a32a4685e490e773843519fd5f221b79aaffda10cbac02b56d94d4f6759`. Sources runtime inchangées ; aucune compilation.
- Planches : trois cycles non nuls par groupe de base `G1/G2` ; source NN x2 / guide / Q3m neutre-chaud-froid, centres alignés, cadre adapté aux grandes frames. Comparaison statique ; aucune acceptation QA.
- Rapports intermédiaires locaux sous `work/` et `production.log`, ignorés. Résumé final, SHA et mesures : `verification.json`. Les preuves historiques des phases 1–4 ne sont pas réécrites.

## Commandes / reprise

```powershell
$monsterPython = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
# Reprise de l'arrêt : nouvelles traces, même cache ; Bodhi/MGLC hits uniquement,
# MBEH : 276 hits + 778 travaux modèle attendus. Ne pas réécrire work/production/.
& $monsterPython -B docs/measurements/q3m-monster-complete-x2-20261003-v1/produce.py --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --output docs/measurements/q3m-monster-complete-x2-20261003-v1/work/production-resume-v1
# Nouvelle destination de rapport ; cache commun existant. Production : Bodhi → MGLC → MBEH.
& $monsterPython -B docs/measurements/q3m-monster-complete-x2-20261003-v1/produce.py --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --output <nouveau-rapport>
# Après production complète : nouvelles destinations ; ne pas remplacer les preuves finales.
& $monsterPython -B pipeline/scripts/palette_monster.py pack --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --output <nouvelles-feuilles>
& $monsterPython -B docs/measurements/q3m-monster-complete-x2-20261003-v1/assemble.py --leaves <nouvelles-feuilles> --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --output <nouveau-pack>
& $monsterPython -B docs/measurements/q3m-monster-complete-x2-20261003-v1/verify_native.py --pack <nouveau-pack> --executable .work/q3m-monster-phase4-20261003-v1/build/Release/iee_palette_monster_tests.exe --output <nouvelle-preuve-native>
& $monsterPython -B docs/measurements/q3m-monster-complete-x2-20261003-v1/verify_resume.py --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --output <nouvelle-preuve-cache.json>
# record.py scelle uniquement le rapport final de cette version ; ne pas rejouer après scellement.
```

`record.py --production <rapports-de-reprise>` agrège les rapports originaux, `pause.json` et la reprise ; distingue les hits de phase 4 des résultats de l'essai interrompu. Les éventuelles cibles calculées mais non sauvegardées avant interruption ne sont pas comptabilisées comme résultats.

## Suite autorisée séparément

- **Phase 6** : nouveau catalogue candidat intégrant ces 39 BAM aux **78 animations Character** acquises ; conserver octets/membres Character, **81 paperdolls**, shaders/UI Nearest et BOX monde. Pas de réencodage ni de QA globale des acquisitions.
- **Phase 7** : installation ciblée après fermeture du jeu/InfinityLoader, puis test ingame des trois créatures. Aucun état QA ingame ou release déduit des contrôles de phase 5.
