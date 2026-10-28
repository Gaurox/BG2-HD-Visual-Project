# V13 — masque SPMAGMIS et capture reproductible

- **[V13 installée](../../../engine/InfinityEngine-Enhancer/installations/projectiles-mask-canvas-20261028-v13/installation.json)** ;4suites passantes,1,11s. [Recette finale](../../../pipeline/recipes/projectiles-mask-canvas-20261028-v13/install.py). Aucun résultat ingame encore déduit.
- DiagnosticV11 : SPMAGMIS hors scopeFX, capture englobante halo24×16 + vol64×78 invalidée ;128dessins natifs `MaskRejected` /36HD non masqués. [Source figée](../validations-manuelles-consolidees-20261028-v1/latest-feedback.json). Un manque de capture ne révoque pas les accords visuels existants.
- Correctif : SPMAGMIS passe dans la capture par FXLock déjà utilisée par FIREBAT ; simulation halo/vol testée pour69×78 et64×78, deux coupes natives accumulées, captures séparées, rejet natif conservé si masque indisponible. Pas d'assouplissement du garde-fou `native_effect_occlusion_fallback_required`.
- [Contrat géométrie vérifié](geometry-proof.json) : BAM natif6frames64×64/centre32,32 ;12backings existants256×312, source contenue ày7 dans64×78/centre32,39. SHA des12backings vérifiés,3,83Mo lus,0écriture. Le pont résout ce pack sur le canevas final, sans appliquer une seconde fois le placement de la source64×64. Préfixe composé incompatible : rendu natif complet conservé. Autres ressources inchangées.
- V12 : candidat intermédiaire scope seul, remplacé parV13 avant demande de test ; reçu historique conservé. **Ne pas tester/réinstaller V12** : il ne prenait pas encore en compte ce pack déjà cadré.
- [1048contrats chargeur](../masque-capture-v12-20261028-v1/native-contracts.log), [table](../masque-capture-v12-20261028-v1/contracts.tsv) : SPMAGMIS/SPFIRSE2/SPCHLGT1/2/3,33cycles, phases30FPS/casse ; même catalogue538/62500backings et registre,32MiBmetadata,0lectureRGBA par chargeur.
- Deux nouvelles ressources isolées [préparées/vérifiées](../masque-capture-v12-20261028-v1/prepare.json) : `XQTARG.cre` = OGRE01,500PV,5scripts vides, variableXQTARG, sans dialogue ; `XQSEED.spl` = SPWI304 dont seuls6mots projectile234→226 changent, mêmeBOLT2 queFIRESEED.ITM. Ressources originales/PRO/images non remplacés ; dégâts ordinaires de Boule de feu conservés pour le pilote de Semence. Pas de production IA/release/mouvement.

## Trois captures prêtes

[Commandes et attentes](next-tests.json), [départ logs](log-baseline.json). Relancer via InfinityLoader ; partie de test non enregistrée, zone dégagée à l'est du personnage principal, IA du groupe désactivée.

Créer trois cibles passives, espacées à distance, puis laisser3s dépausées :

```lua
C:Eval('CreateCreatureObjectOffset("XQTARG",Player1,[320.-80])',0)
C:Eval('CreateCreatureObjectOffset("XQTARG",Player1,[384.0])',0)
C:Eval('CreateCreatureObjectOffset("XQTARG",Player1,[320.80])',0)
```

Soumettre **séparément**,15s de jeu dépausé après chaque tir :

```lua
C:Eval('ForceSpellRES("SPWI112","XQTARG")',0)
```

Projectile magique : vérifier masque/cadrage et absence de régression visuelle. Puis :

```lua
C:Eval('ForceSpellRES("XQSEED","XQTARG")',0)
```

Semence : pilote technique du même PROBOLT2, pas besoin d'équiper l'arme ; ne pas déduire une validation du gameplay de l'arme depuis ce pilote. Puis :

```lua
C:Eval('ForceSpellRES("SPWI615","XQTARG")',0)
```

Éclairs : observer branches/rebonds, séquences natives réellement dessinées. Terminer15s dépausées puis quitter normalement. Si une cible apparaît derrière un mur, choisir un endroit dégagé avant de lancer ; ne pas conclure à une panne graphique si la ligne de vue manque.

## Lecture et nettoyage après capture

- `EFX_STREAM_ROW` par resref/serial/séquence : HD, masque, phases impaires et backings. Séparer pause, chargement froid, rejet masque persistant ; contrôler `traceDropped`. `masked=false` n'est pas en soi un défaut lorsqu'aucune coupe native n'est nécessaire. Aucun déplacement interpolé déduit de phases d'image.
- Trace INI temporaire active : après lecture des nouveaux logs et jeu/loader arrêtés, remettre **seulement** `EnableEffectStreamingTrace=false`, garderV13. QAfiles à retirer uniquement après comparaisonSHA avec leur reçuV12 si devenus inutiles.
- Les28acceptations visuelles et4décisions historiques du [suivi manuel](../../SUIVI_MANUEL.md) restent conservées. Les nouvelles preuves techniques restent en attente ; aucune QA complète243/124 ni release accordée.
- Formats/API : [CRE](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/cre_v1.htm), [création relative de cibles](https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm#252).
