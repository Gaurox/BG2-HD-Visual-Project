# Suite — explosion de piège et Semence de feu

- État : deux essais à jouer, version V10 déjà installée ; aucune écriture jeu/image/release. [Série précédente acceptée](../mur-brouillard-v10-valide-20261028-v1/acceptance.json).
- [Progression](secondary-progress.json) : 29/37 groupes rôle/asset ont une preuve partagée, 8 restent sans preuve ; ces deux essais en ciblent 3. Ce compteur ne valide ni tous les propriétaires ni leurs palettes/positions ; 100 chaînes statiquement vérifiées conservées.
- [Ressources actives, SHA et commandes](tests.json), [point de départ logs](log-baseline.json). Sources KEY/override lues ; SPCL911B projectile brut269→TRAPBOOM ; FIRESEED capacité à distance, brut226→BOLT2, restrictions de classe0.

## 1 — Explosion de piège

```lua
C:Eval('ForceSpellRES("SPCL911B",Player2)',0)
```

- Deux personnages vivants, partie de test. Observer explosion/dispersion, bords et transparence.
- Attendus : SPSETSCD, SPSETSH (nouveau groupe), SPFLAMES. SPCL911B est un pilote technique sans nom : pas un test de pose/déclenchement du piège.
- Attendre 10 s avant rechargement ; restaurer la cible si nécessaire.

## 2 — Semence de feu comme arme de jet

```lua
C:CreateItem("FIRESEED",5)
```

- Sélectionner seulement Player1 avant création ; équiper les Semences de feu dans un emplacement d'arme et les sélectionner comme arme active.
- À distance, attaquer une cible vivante. Option dans la partie de test, après équipement sur Player1 :

```lua
C:Eval('AttackOneRound(Player2)',0)
```

- Observer vol, explosion orange/rouge, dispersion et fumée ; un tir manqué peut nécessiter un second essai. Créer l'objet seul ne teste pas le rendu.
- Attendus : SPFIRSE2, FSEEDX/FSEEDA (deux nouveaux groupes), SPSMPUFF. Attendre 10 s après le tir.
- Retour utilisateur attendu : aspect 1/2, notamment transparence ; ensuite examiner les binds HD0x8/masque0x20, distinguer chargement transitoire et repli durable. Pas de validation avant ces observations.

## Restes après ces essais si concluants

- FIREBGRX/FIREBGRR : pilote natif à déterminer.
- SPGRWHRL/WILDZONE : pilote OHNROBE3 à préparer selon contrat actif.
- SPCHLGT1/SPCHLGT3 : vérifier le contrat cycle9 avant de demander un nouvel essai.
- Déplacement reporté [PROJ-MOTION-001](../../../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001).
- Syntaxe : [console BG2](https://gibberlings3.github.io/iesdp/appendices/clua/bg2.htm), [actions BGEE](https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm).
