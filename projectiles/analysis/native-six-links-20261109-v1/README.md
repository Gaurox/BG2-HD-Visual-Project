# Six raccords secondaires installés —2026-11-09

- Scope : SKYBOLT,SPBOOM,SPFDEATH,SPGENHLA,SPGFLSH1,SPWRDFLD ajoutés à `effect_secondary_scope.h`. Classes natives SkyStrike/SpellHit/Fireball→FX29e190/29e260/29df60 déjà prises en charge ;aucun nouveau hook/adresse.
- [CLUA](CLUA.md) :6essais numérotés,sorts natifs déjà vérifiés ;aucun nouvel objet/helper requis. Jeu à relancer viaInfinityLoader.
- `qualification.json` :528backings installés vérifiés SHA ;8cycles natifs sur6BAM,centres/dimensions exacts sur profils base/once ;1624contrats (casse incluse).0image modifiée/inférence.
- `engine-tests.log` :5/5passent (surface-owner/scope,occlusion,iee_tests,registry,GPUcache). `before-install-native-loader.log` et `installed-native-loader.log` :1624contrats chacun,0lectureRGBA par le chargeur metadata.
- DLL installée `4F63EC610B9A4E70CF0A341C521F32F7458508BE055A6EB569A391D018469F95` ;ancienne `009A3457…81E5C60D`. Seule autre écriturejeu :cléINI `EnableEffectStreamingTrace=false→true`.
- Catalogue743ressources/72563backings,registre,images,PRO/carriers,shaders,sprites et autres paramètres conservés. Placement/alpha/préfixes/masques gardent les gardes de repli natif existants ;pas de couleur forcée ni de redimensionnement.
- Reçu/backup : `engine/InfinityEngine-Enhancer/installations/projectiles-native-six-links-20261109-v1/installation.json` ettransaction référencée ;recette `pipeline/recipes/projectiles-native-six-links-20261109-v1/install.py`.
- Suivi :installation/intégration de ces6composants,QAHD en attente ;les accords visuels acquis sont conservés et liés à leur ancienne DLL.0QAingame/release nouvelle déduite.
- Autres raccords ouverts :HLYMITE,SHAIR,SHEARTH(palettes),SPSCORIC(faisceau). Aucun changement de ces4scopes.
- Après essais/logs etfermeturejeu/loader : `python -B pipeline/recipes/projectiles-native-six-links-20261109-v1/install.py disable-trace` ;seule clétrace désactivée,DLL conservée.
