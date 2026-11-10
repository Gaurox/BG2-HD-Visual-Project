# Raccords résiduels —2 observations de couleur seulement

- Quatre familles installées. **Relancer le jeu via InfinityLoader** pour charger la nouvelle DLL. Partie de test,IA du groupe désactivée,ne pas enregistrer après les essais.
- Trace technique temporaire activée. Dépauser etlaisser tourner10–15secondes après chaque commande ;quitter le jeu etInfinityLoader après les2essais pour permettre la lecture du log.
- Aucun retest des images FLMSTRK/Porte dimensionnelle ni des lots déjà acceptés.600contrats natifs passants,208textures inchangées ;palettes/cycles/centres contrôlés automatiquement. Aucun helper/objet spécial à créer ou équiper.

## R4-01 — SHWATER rouge

```lua
C:Eval('ForceSpellRES("SPPR207",Myself)',0)
```

- Observer le halo/impact rouge de Baies magiques sur Player1 :couleur,transparence,pas de rectangle opaque. Le sort crée aussi des baies :effet normal du pilote natif. Attendre quelques secondes.
- Source vérifiée :op141/type26→ID138/SHWATER6 ;aucun opcode de dégâts,téléportation ou retrait de créature.

## R4-02 — SPBOOM doré

Curseur sur un terrain libre à distance du groupe ;créer une cible jetable puis lancer :

```lua
C:CreateCreature("OGRE01")
C:Eval('ForceSpellRES("SPWM110",NearestEnemyOf(Myself))',0)
```

- Observer le petit éclat/impact doré sur l'ogre :couleur,transparence et disparition. Source vérifiée :op170+141 seulement,type32→ID142/MPALETTE67 ;aucun opcode de dégâts,retrait,invocation ou téléportation. Ne pas substituer SPWI980/985/995.
- Les variantes grise/verte etles7palettes SHWATER sont qualifiées automatiquement ;elles ne deviennent pas des commandes à répéter.

## Retour

- «R4-01 bon /R4-02 bon» ou symptôme précis. Si rien n'apparaît,le signaler :le seul lancement de la commande ne vaut pas observation.
- La trace confirmera liaisonHD,palette native réalisée etphases pourles2ressources. Rien n'est encore déclaré accepté visuellement pour ce nouveau contrat ;anciens accords images conservés.
- Après retour :désactiver uniquement la trace ;garder la DLL. Aucun autre lot manuel en attente.
