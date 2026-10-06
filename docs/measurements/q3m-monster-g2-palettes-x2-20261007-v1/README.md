# Monster — derniers correctifs G2 traités/installés

- Autorisation : « ok finalise les derniers correctifs. je veux terminer les sprites ». Scope7312 ELEMENTAL_FIRE_PURPLE/MFIE,7313 ELEMENTAL_FIRE_SMALL_PURPLE/MFIS. **Production, vérifications natives et installation terminées** ; seuls deux retests ingame des nouvelles attaques restent ouverts.
- Parent : `../q3m-mfie-native-palettes-x2-20261007-v3/current-generation.json` ; MFIE7314 accepté conservé. [Défaut initial/plan](../q3m-monster-final-checks-x2-20261007-v1/README.md) : G2 utilisait la palette G1,0/5 292 frames acceptées par la DLL avec palette2 native.

## Correction

- G1→palette1 inchangé ; **G2→palette2 natif** :7312 MFIEG2B/256,7313 MFISG2B/256. INV7312 propre conservé ;7313 sans INV. Q3m V7 K6/quatre partenaires/huit niveaux/x2/Nearest sans SDF, monolithique ;aucun raccord spatial requis.
-14 feuilles nouvelles : MFIEG2/21–26 et MFISG2/21–26.13 G1/INV identiques au parent. [Production](production.json)/[encodage](encoding.json) :27 ressources/11 774 frames,1 842 encodages uniques ;1 084 hits acquis +756 nouveaux ordinaires +2 spéciaux sans GPU ;4 536 cibles K6.
- [Reprise vérifiable](production-resume-evidence.json) : premier lancement arrêté après inférence par nom de mode palette invalide ;2 spéciaux déjà publiés. Reprise mode `gpu-grouped-guarded-v1`,1 086 hits SHA vérifiés,4 536 cibles réutilisées,aucune nouvelle inférence. Contrat fixed86/q32/fp16 acquis conservé ;trim CUDA avec répétition byte-exacte du premier lot. Journaux locaux ignorés,cache exclusif et anciennes feuilles conservés.
- **DLL/shaders/INI/77 CRE inchangés**. Aucun élargissement de tolérance palette ni compilation runtime. DLL `c8690b4edd978d28eafabd1e6aafbd2533820c0bfbc0ea88192ea161850e5697`.

## Vérification et installation

- [Natif](verification.json), objets du build v3 installé : **5 292/5 292 G2 acceptent palette2**,0 accepte palette1 erronée ;6 480/6 480 G1 acceptent palette1.11 772 frames monde portent la palette BMP exacte ;cycles BAM natifs/SHA source conservés.
-1 531 cycles,33 682 lectures Loop/Clamp/signed slots passent. **11 774 frames K6×3 formats,1 133 696 160 pixels décodés**,19 479 slots natifs,0 erreur. [Sonde](palette_probe.cpp),[script](verify.py).
- [Catalogue](catalog-proof.json) : **329 autres IDs/63 002 routes/digests identiques**, MFIE QA inclus ;331 IDs/14 330 feuilles/2 791 737 frames actives. Catalogue SHA `2ad7838cb4157b3b3226dbf3635d59ed17ce028e209f33615499a7e1700b289c`.
- `install.ps1 -DryRun` puis installation autorisée,jeu/InfinityLoader fermés :14 nouvelles feuilles +catalogue ;**1 126 fichiers préservés SHA vérifiés**,DLL conservée. [Preuve d'installation](installation-verification.json),[contre-vérification](installed-verification.json).
- [Génération active](current-generation.json),[production composite](production-generation.json) ;reçu actif `ingame-installation/active-test.json`. [Résumé](summary.json) et suivi index actualisés,ancienne QA immuable.
- [Sélection complète courante77](full-selection.json) :74 témoins inchangés +palettes natives corrigées7312/7313/7314 ;[provenance/validation](full-selection-provenance.json),composition CPU seule. Les compteurs historiques de travail du lot complet initial restent identifiés comme tels ;coût des corrections enregistré séparément,aucune addition de clés globales supposée.
- Restauration : `restore.ps1 -DryRun`,puis `restore.ps1` jeu fermé ;catalogue parent exact restauré,uniquement14 nouvelles feuilles identifiées retirées ;réconcilier les pointeurs actifs si utilisé.
- Travail local : `sprite/.work/q3m-monster-g2-palettes-x2-20261007-v1/{isolated,combined}` ;runtime parent réutilisé. Scripts :produce.py→prepare_install.py→verify.py→install.ps1→finish.py. Sorties finales scellées,ne pas écraser un run acquis.

## Dernière QA ingame

- **331 IDs/15 familles installés ;329 contrats actifs acceptés,2 nouveaux contrats à retester.** Aucun traitement/correctif sprite connu restant. QA historique77 Monster conservée ;QA nouvelle non déduite de vérifications natives. Release non modifiée.
- CRE neutres sans AI scripts,script names exacts et actions présentes dans le jeu contrôlés : [CLUA-proof.json](CLUA-proof.json). [Commandes copiables](CLUA.txt),à saisir **une ligne à la fois**.

Grand élémentaire violet :

```lua
C:CreateCreature("QMON7312")
```

```lua
C:Eval('ActionOverride("QMON7312",AttackOneRound(Player1))')
```

Petit élémentaire violet :

```lua
C:CreateCreature("QMON7313")
```

```lua
C:Eval('ActionOverride("QMON7313",AttackOneRound(Player1))')
```

- Après création,puis Eval,dépauser : observer une attaque G2 et retour G1 ;aucune silhouette/couleur vanilla temporaire attendue. Ces commandes n'ont pas été exécutées par l'agent ;confirmation visuelle utilisateur requise.
- Syntaxe console : [Beamdog,C:Eval](https://forums.beamdog.com/discussion/8317/general-bgee-customization-pre-v2-0/p11). Sémantique : [IESDP BGEE,ActionOverride/AttackOneRound](https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm),actions1/105 du `ACTION.IDS` installé ;attaque limitée à un round.
