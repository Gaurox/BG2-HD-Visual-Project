# Éclairs V11 — raccord, contrats et essais prêts

- [V11 installée](../../../engine/InfinityEngine-Enhancer/installations/projectiles-lightning-trails-20261028-v11/installation.json), [recette](../../../pipeline/recipes/projectiles-lightning-trails-20261028-v11/install.py). Delta rendu : SPCHLGT1/3 ajoutés au scope du pont FX/masque ; SPCHLGT2 conservé. 0 image retraitée ; BAM, PRO, catalogue538/62500backings et mouvement inchangés.
- **Trace temporaire active** : seule clé INI modifiée `EnableEffectStreamingTrace=false→true`. `EFX_STREAM_ROW` fournit occurrence/serial, sequence, slot, phase, HD, masked, paused, outcome. Capture destinée à distinguer refus de lookup intermédiaire et dessin final réellement natif ; ne pas désactiver avant lecture de la prochaine session.
- [Contrats natifs](contracts.json), [824 accès chargeur](native-contracts.log), [table](contracts.tsv) : trois BAM, 27cycles natifs0..8, dimensions/centres concordants ; slots/phases30FPS/casse vérifiés,32MiB metadata,0lectureRGBA. [Trois suites passantes](../../../engine/InfinityEngine-Enhancer/installations/projectiles-lightning-trails-20261028-v11/tests.log) : surface-owner/masque, iee_tests, registry ;1,02s.
- Ancienne session10:50 : trois ressources liéesHD sur séquence2 ; pas de preuve masque1/3. Valeur9 déclarée dansLIGHTCHA.PRO, mais9cycles0..8 dansSPCHLGT3 ; aucune séquence9 réellement observée. Ce n'est pas une preuve d'asset absent/crash ; ne pas créer un faux cycle ni modifier le PRO. La prochaine trace révèle les séquences réellement dessinées ; contrat hors parcours observé conservé comme limite.
- [Feu vert accepté](../feu-vert-valide-20261028-v1/acceptance.json) ; 35/37 groupes avec preuve partagée. V11 en attente d'essai, pas de QAingame déduite des tests.

## Deux essais

[Commandes/ressources actives](next-tests.json), [départ logs](log-baseline.json). Partie de test non enregistrée ; jeu lancé via InfinityLoader par l'utilisateur.

1. **Éclairs en chaîne** : désactiver l'IA du groupe, créer trois ogres proches et visibles, lancer avant qu'ils soient tués :

```lua
C:CreateCreature("OGRE01")
C:CreateCreature("OGRE01")
C:CreateCreature("OGRE01")
C:Eval('ForceSpellRES("SPWI615",NearestEnemyOf(Myself))',0)
```

- Observer les branches/rebonds et leur transparence. Dépauser et attendre15s. Cibles ennemies requises par la route native LIGHTCHA ; SPWI615brut213→PROJECTL212.

2. **Semence de feu, vol** : recharger la partie de test ; sélectionner seulement Player1 puis :

```lua
C:CreateItem("FIRESEED",5)
```

- Équiper/sélectionner les Semences comme arme active ; tirer sur une cible vivante à distance. Option après équipement surPlayer1 : `C:Eval('AttackOneRound(Player2)',0)`. Observer le vol ; explosion/dispersion/fumée déjà acceptées, aucune nouvelle appréciation exigée sur ces composants.
- Dépauser et attendre15s après le tir. Le log doit confirmer phases intermédiaires et état HD/masque du vrai dessin final ; ne pas compter la création de l'objet comme un tir.

## Après ces retours

- Examiner les `EFX_STREAM_ROW` par resref/serial/sequence, filtrer pause et chargement froid ; vérifier `traceDropped`, ne pas calculer une cadence globale à partir d'instances entremêlées.
- **Jeu/InfinityLoader arrêtés**, remettre uniquement `EnableEffectStreamingTrace=false` après sauvegarde des logs. Garder DLLV11, reçus et acceptations ; pas de restauration globale V10/INI qui écraserait des réglages ultérieurs.
- SPMAGMIS : incident isolé de masque absent à16:45:47, dessin natif clippé conservé. Ne pas retirer ce garde-fou ni révoquer la QA historique depuis un seul incident ; réexaminer si trace/retour ciblé le justifie.
- Déplacement interpolé toujours reportéPROJ-MOTION-001 ; aucune position intermédiaire ajoutée.
