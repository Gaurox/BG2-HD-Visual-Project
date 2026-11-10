# Lot31 — nouvelle correction01..06 et22/27

- Parent immuable : `../lot31-corrections-preview-20261018-v1/` ; nouvelle recette `pipeline/recipes/effects-lot31-xbr-nativealpha-20261019-v1/`.
-01 ARARROW(11palettes),02 AXE(6),03 BOLT(13),04 DAGGER(2),05 DART(4),06 SPEAR(1) : xBR4X, alpha natif nearest4 +interpolation temporelle inchangée ; aucun Bézier/fondu/flou/retrait. Palettes natives réalisées avant xBR ; RGB source rempli hors alpha, silhouette native seule autoritaire.37contextes.
-22 SPSCHGI et27 SPENTACI : masques lissés précédents conservés, noir/quasi-noir convertis en transparence graduée ; flux lumineux et encodage prémultiplié préservés. Vérification normal/additif sur trois fonds, erreur observée0octet. La source27 contient surtout du quasi-noir, pas une seule couleur noire à supprimer.2contextes.
- Statut exact : `progress.json`, puis `verification.json` et `result.json` à la fin. `results/*.json` lie les données aux parents ; `spatial/*/manifest.json` lie xBR/outil/palette/source ; `native/probe.json` distingue référence statique et flag de mélange non mesuré.
- [Planche animée actualisée](http://127.0.0.1:8794/revisions/xbr-nativealpha-20261019-v1/index.html?v=xbr-native1) :31effets/99palettes/658profils ; sur les huit modifiés,4vues vanilla/SeedVR/dernier essai ReboutCX ou lissé/nouvelle correction.23autres cartes3vues,60contextes conservés ;101canvas au total. Nouveau namespace, anciennes vues et données intactes.
- Géométrie : dimensions/centres/marge20px x4 de l'essai précédent inchangés ; cadence30 et durées rationnelles conservées, base15FPS de compatibilité héritée. Aucune installation ingame/QA/release/autorité de production modifiée.
- [Armes](weapons.png), [transparence22/27 en alpha normal](black.png).
