# Feu vert — pilote ingame isolé

- **Prêt à tester** : [installation](installation.json), [préparation vérifiée](prepare.json), [`candidate/XPGREEN.spl`](candidate/XPGREEN.spl), [recette](../../../pipeline/recipes/projectiles-green-test-driver-20261028-v1/prepare_install.py).
- Un nouveau fichier `config://bg2ee_game_root/override/XPGREEN.spl` (978octets), aucun fichier existant remplacé. Processus BG2/InfinityLoader vérifiés arrêtés avant installation ; création exclusive et SHA relu après écriture. RendererV10/DLL et registry inchangés.
- Base : SPWI304 actif ; six capacités conservées, seuls leurs six mots projectile passent de234 à104 (`PROJECTL.IDS 103 FIREBLGR +1`). Contrôle : six octets différents, tous dans ces mots ; signature/taille/tableaux/payload d'origine conservés. **Dégâts ordinaires de Boule de feu conservés** : partie de test, cible vivante.
- Pas d'édition de FIREBLGR.PRO, de ses BAM, de PROJECTL.IDS, du catalogue ni d'une release. FBFLAMGR sans entrée IDS directe n'est pas validé par ce pilote ; images partagées seulement.

## Essai unique

Relancer BG2 via InfinityLoader, charger une partie de test, espacer deux personnages vivants :

```lua
C:Eval('ForceSpellRES("XPGREEN",Player2)',0)
```

- Observer vol, explosion et anneau verts, fumée, transparence/bords ; dépauser puis attendre15s avant de quitter/recharger.
- Attendus : FIREBGRT, FIREBGRX, FIREBGRR et fumée native déclarée ; confirmer les ressources réellement créées depuis les logs, sans compter un test simplement lancé comme validation.
- Deux groupes nouveaux visés : explosion-animation/FIREBGRX, ring-animation/FIREBGRR. État QA : en attente, aucune acceptation ingame inventée.
- Après résultat : LIGHTCHA/SPCHLGT1+3 exige examen du dispatch/scope/cycle9 avant un essai utile ; réserves SPFIRSE2 et SPMAGMIS conservées séparément.
- Nettoyage futur : jeu et InfinityLoader arrêtés, supprimer uniquement ce nouveau XPGREEN.spl après correspondance SHA avec `installation.json`. Aucun autre fichier à restaurer ; pas de suppression faite à ce stade.
- Format : [SPL/offsets capacités et projectile](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/spl_v1.htm).
