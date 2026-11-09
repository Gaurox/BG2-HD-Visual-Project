# Derniers raccords — seulement3couleurs à regarder

- **Les3variantes sont maintenant acceptées ;aucun essai à rejouer.** Correction F4-C1 :SPWI985 applique aussi l'opcode168 Remove Creature après2secondes. L'ancienne consigne surPlayer2 était incorrecte ;recharger la sauvegarde d'avant l'essai. Les commandes réellement utilisées sont archivées dans `../final-four-colours-accepted-20261109-v1/CLUA-tested.md`.
- Les4raccords sont installés. Relancer via **InfinityLoader**,partie de test non enregistrée,IA du groupe désactivée ;Player1 etPlayer2 visibles etespacés.
- Seuls les3rendus colorés ci-dessous demandent un regard. Les variantes neutres sont vérifiées comme identiques ;le faisceauSPSCORIC conserve son accord visuel,avec9cycles contrôlés automatiquement. Aucun essai des6raccords précédents à rejouer.
- Pas besoin de juger à nouveau le dessin de base :signaler uniquement une couleur incohérente,un contour opaque ou un placement manifestement faux. Un lancement par commande suffit pour chaque variante.

## F4-C1 — HLYMITE rouge

```lua
C:CreateCreature("OGRE01")
C:Eval('ForceSpellRES("SPWI985",NearestEnemyOf(Myself))',0)
```

- Référence future uniquement :curseur à distance du groupe,créer une créature jetable. SPWI985 retire cette cible après2secondes ;ne jamais cibler un compagnon. Pilier/halo **rouge**,variante native194 RED_HOLY_MIGHT ;aucun retest demandé.

## F4-C2 — SHAIR,palette4

```lua
C:Eval('ForceSpellRES("SPIN835",Player1)',0)
```

- Effet centré sur le lanceur,avec la **palette nativeSHAIR4**,etnon les couleurs du pack neutre. Regarder la cohérence des couleurs et la transparence.

## F4-C3 — SHEARTH,palette6

```lua
C:Eval('ForceSpellRES("SPIN782",Player2)',0)
```

- Variante de l'impact terrestre avec la **palette nativeSHEARTH6** ;même contrôle limité à la couleur/transparence.

La trace temporaire est active :après ces3commandes,dépauser quelques secondes puis fermer le jeu etInfinityLoader. Le contrôle des palettes liées etdu passageHD se fait dans les logs ;il ne constitue pas une autre série de tests à effectuer.
