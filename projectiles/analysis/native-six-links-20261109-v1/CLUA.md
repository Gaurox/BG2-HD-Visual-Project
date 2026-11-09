# Six raccords natifs — essais HD après installation

- **DLL installée : `4F63EC61…18469F95`.** Relancer le jeu via **InfinityLoader** pour charger cette version.
- Les six images existaient déjà ;ces essais portent sur leur nouveau passage par le pont HD des cellules natives. Les accords sur leur aspect précédent restent acquis.
- Partie de test non enregistrée ;IA du groupe désactivée. Player1 lanceur,Player2 visible à distance. Un essai à la fois ;recharger entre effets persistants.
- Trace technique temporaire activée (`EnableEffectStreamingTrace=true`). Après chaque essai,dépauser etlaisser tourner15secondes ;après le dernier,quitter le jeu etInfinityLoader pour l'analyse du log etla désactivation ciblée de la trace.

## S6-01 — SKYBOLT / Appel de la foudre

À l'extérieur,sur une cible vivante visible :

```lua
C:Eval('ForceSpellRES("SPPR302",Player2)',0)
```

- Observer l'éclair vertical,son ancrage sur la cible,son contour et sa disparition. Le contrôleur80..83 dépend du niveau ;le nouveau raccord concerne leur enfantSKYBOLT.

## S6-02 — SPBOOM / Tempête de glace

```lua
C:Eval('ForceSpellRES("SPWI404",Player2)',0)
```

- Observer les impacts SPBOOM au milieu des particules et des autres effets de glace. Leurs composants déjà acceptés ne sont pas remis en question.
- Laisser finir la tempête ou recharger avant l'essai suivant.

## S6-03 — SPFDEATH / pilote natif207

Curseur sur terrain libre à distance du groupe ;créer une cible pour ce sort offensif :

```lua
C:CreateCreature("OGRE01")
C:Eval('ForceSpellRES("SENDAIF1",NearestEnemyOf(Myself))',0)
```

- Observer l'effet de mort sur la cible :placement,transparence,animation et disparition. SENDAIF1 est le pilote interne vérifié pour207 ;un simple effet ressemblant de Doigt de mort ne prouverait pas cette route.

## S6-04 — SPGENHLA / Protection contre le plan négatif

```lua
C:Eval('ForceSpellRES("SPPR412",Player2)',0)
```

- Observer le pilier/halo sur la cible :base ancrée,haut conservé,pas de découpe ni de rectangle opaque.

## S6-05 — SPGFLSH1 / Enchevêtrement

```lua
C:Eval('ForceSpellRES("SPPR105",Player2)',0)
```

- Observer le flash/effet SPGFLSH1 associé à la zone,sa transparence et sa disparition. Les éléments persistants déjà acceptés restent distincts.
- Recharger après cet essai pour libérer le groupe avant le suivant.

## S6-06 — SPWRDFLD / Champ de téléportation

```lua
C:Eval('ForceSpellRES("SPWI421",Player2)',0)
```

- Observer l'effet du champ et ses apparitions/disparitions :ancrage,alpha,absence de coupe des contours. Les trois cycles du pack restent ceux du natif.

## Retour et analyse

- Retour par numéro S6-01→S6-06 :aspect correct ou symptôme précis. Si aucun effet n'apparaît,le signaler ;ne pas compter le lancement seul comme une observation réussie.
- La trace permettra de vérifier `EFX_STREAM_ROW` pour SKYBOLT/SPBOOM/SPFDEATH/SPGENHLA/SPGFLSH1/SPWRDFLD :dessin finalHD/masque/phases et éventuel repli natif,par occurrence/cycle.
- Trace seule ≠validation visuelle ;présence catalogue ≠dessin HD. Aucun tauxglobal243 déduit de ce lot.
