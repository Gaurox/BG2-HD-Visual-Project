# Piège / Semence — résultat et suite

- [Session figée](runtime-session.log) 2026-10-28 16:38:50–16:39:59 ; [vérification](verification.json). Utilisateur : « ca a l'air ok » ; V10 inchangée, aucune image/installation/release modifiée.
- Semence BOLT2 : FSEEDX, FSEEDA et SPSMPUFF HD0x8 + masque0x20 confirmés ; aspect positif accepté pour ces composants. SPFIRSE2 vol : bindHD0x8 observé, mais cinq tentatives de lookup refusées pour géométrie24×16 et aucune trace0x20 du vol dans cette session. Slots natifs2/0..4 et metadata installée : dimensions/centres concordants. Pas de motif pour retraiter les images ; origine/impact final des tentatives24×16 à examiner techniquement, pas de validation intégrale du vol ni de cadence déduite.
- Piège TRAPBOOM : SPSETSCD vol HD0x8+masque0x20 acquis ; SPSETSH et SPFLAMES absents. Cause du test incomplet : area_flags0x45 = piège visible, déclenchement conditionnel et ennemis seulement. L'instruction précédente visant Player2 ne satisfaisait pas cette condition ; corriger la cible, pas le PRO.
- [Progression](secondary-progress.json) : 31/37 groupes rôle/asset avec preuve partagée ; 6 sans preuve. Deux nouveaux groupes acquis : FSEEDX/FSEEDA ; ne pas compter SPSETSH. Aucun compteur de propriétaires QA déduit.

## Deux essais suivants, V10 déjà installée

Partie de test non enregistrée ; IA du groupe désactivée si elle tue la cible avant l'essai. [Ressources actives/SHA et commandes](next-tests.json), [départ logs](log-baseline.json).

1. **Explosion du piège sur ennemi** : créer un ogre visible et vivant, puis lancer immédiatement avant qu'il soit tué. OGRE01.CRE vérifié EA255 hostile.

```lua
C:CreateCreature("OGRE01")
C:Eval('ForceSpellRES("SPCL911B",NearestEnemyOf(Myself))',0)
```

- Observer explosion/dispersion et transparence ; attendus SPSETSH/SPFLAMES. Le vol SPSETSCD est déjà confirmé, inutile de le rejouer séparément. Dépauser et attendre15s.

2. **Zone de magie sauvage** : recharger la partie de test ; sélectionner uniquement Player1 ; créer la Tunique de Sourdoreille puis utiliser sa capacité depuis l'inventaire par action scriptée.

```lua
C:CreateItem("OHNROBE3")
C:Eval('UseItem("OHNROBE3",Myself)',0)
```

- OHNROBE3 capacité0 vérifiée : cible soi-même5, projectile330→WILDZONE, une charge ; SPGRWHRL déjà produit et dans le scopeFX. UseItem fonctionne depuis l'inventaire sans équipement ; déclenchement effectif à confirmer par le prochain log.
- Observer l'effet tournoyant, la transparence et l'animation ; dépauser, laisser finir (~60s pour10répétitions×100ticks), attendre15s. Si rien ne part, le signaler ; ne pas modifier classe/usabilité ni compter le composant comme testé.

## Restes techniques

- FIREBGRX/FIREBGRR : pilote natif absent des SPL/ITM directs identifiés ; préparer un pilote avant nouveau test.
- LIGHTCHA : SPCHLGT1/SPCHLGT3 hors scopeFX V10 ; cycle9 demandé pour SPCHLGT3 absent de ses9cycles0..8. Contrat natif/repli à résoudre avant essai.
- SPFIRSE2 : distinguer tentative de lookup hors géométrie et véritable dessin final natif ; diagnostic/sonde ciblée à préparer si nécessaire. Aucun déplacement interpolé implémenté ; PROJ-MOTION-001 reste reporté.
- Sources : [PRO/conditions](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/pro_v1.htm), [UseItem](https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm#34).
