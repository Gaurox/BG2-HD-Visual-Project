# SHAREA — préparation des cinq essais V8

- [V8 installée](../../../engine/InfinityEngine-Enhancer/installations/projectiles-sharea-palettes-20261028-v8/installation.json), moteur seul.22images SHAREA,538ressources,métadonnées,PRO,INI,shaders etpersonnages préservés ;0inférence/0release.
- Défaut identifié : SHAREA absent du scope FXsecondaire ; palettesBMP1..6 changent la teinte entre canauxRGB. Une simple activation aurait figé la palette chaude du pack pour tous les sorts.
- Nouveau transfertRGB à l’upload depuis la palette native réellement réalisée ; cacheGPU séparé par couleur/opacité, points source exacts, couleurs inédites des imagesHD interpolées entre quatre points natifs voisins. Noir neutre ettransparence conservés. SeulSHAREA/Blended opt-in ; palette absente/alpha non uniforme/composition/cas normal conservent le rendu natif.
- [Vérifications](verification.json) :5suites passantesCPU/registre/masques/OpenGL ;1785points natifs exacts,7palettes,RGBA/BGRA,identité,alpha,cachecouleurs/neutre. PasQAingame déduite.
- [Cinq commandes prêtes](tests.json) : SPWI312,Ralentissement ;SPWI116,Sommeil ;SPWI302,Délivrance magie ;SPPR416,Manteau terreur ;SPPR101,Bénédiction. SPL actifs/SHA revérifiés ; champssecondary actifs enregistrés sans déduire une palette depuis le seul numéro historique.
- Relancer BG2 viaInfinityLoader. Partie de test, deux personnages vivants, éloignés ; jouer séparément avec5s entre sorts, observer couleur/fond/expansion/disparition. Ne pas sauvegarder les essais.
- Logs attendus : `EFX_NATIVE_SURFACE resref=SHAREA`, `EFX_PALETTE_BOUND` par fingerprint réellement lié,0x8+0x20 et`EFX_BOUND_PHASE` x4/phases impaires. Comparer les variantes effectivement vues, ne pas valider toute la famille depuis un seul fingerprint.
- `log-baseline.json` distingue les nouveaux essais. Les3variantes précédentes,lesnuages etFIREBAT restent acquis dans leur périmètre ; ne pas les rejouer. Enfant202 sansdriverSPL direct reste distinct.
