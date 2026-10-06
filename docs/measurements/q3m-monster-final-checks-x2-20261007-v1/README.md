# Monster — MFIE accepté, vérification native7312/7313

- Demande : « validé. fais les dernières vérif dont tu parles ». MFIE7314 natif-palettes-v3 accepté par l'utilisateur ; vérifications7312/7313 réalisées sur fichiers installés et code natif. **Deux défauts techniques G2 confirmés ; correction préparée**.
- Génération active : `../q3m-mfie-native-palettes-x2-20261007-v3/current-generation.json`. DLL `c8690b4e…`, catalogue `d013ac44…` ; octets installés vérifiés. Source de vérité : [checks.json](checks.json).

## Résultats

- Dernière session `2026-10-07 01:27…` : MFIE `MFIE_PALETTE accepted=true` +composition HD x2. [Trace](session-evidence.txt). Aucun7312/7313 observé dans cette session ; aucun échec visuel sur eux inféré du journal.
- IDs officiels : **7312 ELEMENTAL_FIRE_PURPLE** (MFIE), **7313 ELEMENTAL_FIRE_SMALL_PURPLE** (MFIS), `sprite/index/sprite_animations.csv`. Le libellé BLUE_FIRE du README parent était erroné ; l'identité numérique/les ressources d'audit étaient correctes.
- Moteur Monster SetSequence : G1→INI `monster.palette1`, G2→`monster.palette2` ; preuve native parent `native-bank-selection.txt`. 7312 : MFIEG1B/MFIEG2B,236 différences RGB ;7313 : MFISG1B/MFISG2B,253 différences. Chaque BMP256 entrées (`biClrUsed=0` =256 lorsque présent).
- Ressources installées G2 portent la palette G1. Garde de la **même DLL native installée**, appel exact `frame_accepts_fixed_monster_palette` sur toutes les frames : **0/5 292 acceptées avec palette2**, **5 292/5 292 acceptées avec palette1 erronée**. Ce chemin refuse donc la capture HD lorsqu'une attaque soumet la palette native G2 ; le fallback vanilla reste possible.
- G1 : **6 480/6 480 frames** acceptées avec palette1 correcte. Cycles installés/sourceplan/BAM natifs exacts ; Loop/Clamp/signed slots : **33 682 contrôles**, **1 531 cycles**,27 ressources/11 774 frames ; zéro désaccord de lecture native.
- [Sonde](check_banks.cpp) : liée aux objets du build v3, aucun changement runtime. [Script](check.py) : lecture des assets/BAM/BMP, émulation CPU des palettes K6, contrôle des clés cache ; aucune inférence GPU ni écriture de fichiers du jeu.

## Correction prête

- [Sélection27 bindings/2 IDs](correction-selection.json), [plan scellé](correction-plan.json) : **1 842 encodages uniques**, **1 084 hits acquis**, **758 manquants**. 14 ressources G2 changent ;13 ressources G1/INV réutilisables.
- MFIEG2/21–26 pour7312 →MFIEG2B ; MFISG2/21–26 pour7313 →MFISG2B. G1 garde ses palettes actuelles. INV7312 propre inchangé ; aucun INV7313.
- Q3m K6/quatre partenaires/huit niveaux/x2/Nearest sans SDF ; sprites monolithiques, pas de raccord spatial requis. **DLL/shaders/INI compatibles à conserver** : palettes256 strictes, aucune exception ni adaptation DLL nécessaire. Déduplication par clé encodage/palette ; aucun recalcul des1 084 hits.
- Après production autorisée : nouvelle génération immuable, remplacement des deux IDs dans catalogue actif, preuve329 autres IDs identiques (MFIE validé compris), installation jeu/InfinityLoader fermés, retest uniquement des nouvelles ressources G2. Les historiques et les anciennes décisions QA restent acquis pour leurs octets.

## QA et suivi

- [Décision MFIE v3](../../../sprite/index/qa-decisions/monsters/2026-10-07-accepted-MFIE-native-palettes-q3m-v7-x2-nearest-v3.json), autorité utilisateur. 14 feuilles/5 888 frames ; contrat DLL/catalogue exact et [inventaire](MFIE-accepted-assets.csv). Actions ingame détaillées non précisées par utilisateur.
- Union77 IDs :73 QA initiale +3 retests stabilité-v1 +MFIE1 v3 ; [résumé](acceptance-summary.json). Vérification1 037 feuilles Monster +1 119 fichiers préservés, [inventaire complet actif](monster-current-assets.csv). Aucune QA d'un futur correctif G2 déduite.
- QA acquise : **14 familles améliorées/253 IDs** ; Character V6 inclus **15 familles/331 IDs**. Deux anomalies techniques7312/7313 suivies séparément ; preuves QA historiques immuables.
- Reçu actif v3 avancé `installed-MFIE-user-accepted` ; preuve `installation-verification.json` v3 reste l'instantané historique de l'installation avant QA. Production/source/release inchangées. Aucun commit demandé dans cette reprise.

```lua
C:CreateCreature("QMON7312") -- élémentaire de feu violet, grand
C:CreateCreature("QMON7313") -- élémentaire de feu violet, petit
```

- Test visuel utile : provoquer une attaque G2, puis revenir à G1 ; actuellement le défaut est prouvé au niveau du contrat natif, sans observation ingame spécifique7312/7313.
