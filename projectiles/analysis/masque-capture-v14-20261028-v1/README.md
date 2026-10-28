# V14 — canevas natif variable du Projectile magique

- [Installation V14](../../../engine/InfinityEngine-Enhancer/installations/projectiles-mask-canvas-20261028-v14/installation.json), [recette](../../../pipeline/recipes/projectiles-mask-canvas-20261028-v14/install.py), [contrat](geometry-proof.json). Jeu/loader arrêtés avant remplacement ; images/PRO/catalogue/QA visuelles conservés.
- CauseV13 : le moteur dessine ici64×88 ; résoudre seulement le canevas final échoue face au pack64×78 existant. [Observation](../validation-v13-20261028-v1/evidence.json) :source64×64,aucun bindHD,diagnostic64×88.
- Correctif : lookup pack64×78 ; source utile64×64 obtenue par vue mémoire des rangées natives7..70, sans modifier CPUcache/fichiers ; placement natif sur canevas réel. CropTop/Bottom inclus dans clécacheGPU ; bornes/canevas validés ; halo24×16 conservé natif avant lookup. Préfixes composés non compatibles restent natifs. Aucun changement d'algorithme de masque, despositions ou du gameplay.
- [Cinq suites passantes](../../../engine/InfinityEngine-Enhancer/installations/projectiles-mask-canvas-20261028-v14/tests.log),3,56s : surface-owner,occlusion,iee_tests,registry,cacheGPU réel caché. Fixture opaque dans les marges : chaque pixelGPU vérifié pour64×78/y7,64×88/y0,64×88/y12,absence de fuite de marge,source inchangée,crops invalides rejetés,variantescache distinctes. [1048contratschargeur](native-contracts.log),32MiBmetadata,0lectureRGBA.
- [Éclairs et vol Semence acquis en V13](../validation-v13-20261028-v1/README.md), ne pas les rejouer. Validations manuelles conservées ; aucune QAingameV14 inventée.

## Dernier contrôle unique

[Départ logs](log-baseline.json), [commande](next-test.json). Relancer via InfinityLoader ; partie de test non enregistrée, espace dégagé à l'est du personnage,IA du groupe désactivée. Créer une seule cible immobile500PV (ressourceQA déjà installée) :

```lua
C:Eval('CreateCreatureObjectOffset("XQTARG",Player1,[384.0])',0)
```

Après3s dépausées, lancer :

```lua
C:Eval('ForceSpellRES("SPWI112","XQTARG")',0)
```

Attendre15s dépausées puis quitter normalement,sans sauvegarder. Retour : aspect du Projectile magique ; technique : dessin finalHD,masque quand nécessaire,phasesimpaires,sans rejetgéométrie/masque persistant. Un `masked=false` sans coupe native n'est pas à lui seul un défaut.

- Après capture et jeu/loader arrêtés : désactiver uniquement `EnableEffectStreamingTrace`, garderV14. Ne pas restaurer l'INI entière depuisunancienreçu. CiblesQA à supprimer uniquement siSHA conforme au reçuV12 et devenues inutiles.
- Déplacement toujours reportéPROJ-MOTION-001 ;0image retraitée/0release.
