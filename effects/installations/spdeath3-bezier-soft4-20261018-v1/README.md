# SPDEATH3 — Bézier et fondu sigma4 installés2026-10-18

Acceptation ultérieure : [33effets validés ingame, SPDEATH3 final inclus](../../batches/lot33-impacts-accepted-20261018-v1/README.md). Le reçu ci-dessous conserve l'état de la transaction avant QA.

- [`installation.json`](installation.json), [`transaction.json`](transaction.json), [`scope-verification.json`](scope-verification.json). **Installé pour test**, pas de QA ingame acquise. Autorisation : utilisateur choisit sigma4 et demande installation de SPDEATH3 uniquement.
-124phases exactes du comparatif soft4 ;2profils once/loop62phases/2.066667s. Même ancrage monde, native15FPS de compatibilité→30FPS nominal ; cadence réelle non mesurée ici. Run `spdeath3-bezier-soft4-20261018-v2`, pack autonome correspondant.
- Géométrie réelle64×104x1/centre33,60, textures256×416 ; marge de fondu non tronquée, source BAM conservée en indices/palette/cycles/lookup et position monde. Variante normaleX33N33 et primaireSPDEATH3 mis à jour ensemble.
-250cibles transactionnelles :244backings remplacés +2nouveaux,2carriers +registre/manifest.322RESREF/43357backings cumulés ;320autres ressources/43111backings et tous contrôleursVVC identiques. Métadonnées20564362octets sous32Mio,92632contrats natifs passent candidat+installé.
- DLL/INI/shaders/profil personnages/exécutable inchangés ; jeu/InfinityLoader fermés pendant copie. Installation de la seule ligne SPDEATH3 mise à jour après sa dérivation ; QA/release conservées. Sauvegarde ciblée `before/`, restauration via recette, jeu fermé.
- [CLUA](CLUA.md), inchangée :

```lua
-- SPDEATH3 / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T33",Player1)',0)
-- Boucle de test bornée
C:Eval('CreateVisualEffectObject("Z33P0182",Player1)',0)
```

- Relancer via InfinityLoader. Ces testsVVC utilisent un owner déjà pris en charge ; les chemins natifs directs des vrais sorts restent un contrat distinct non observé. [Recette](../../../pipeline/recipes/effects-spdeath3-soft4-install-20261018-v1/README.md).

```text
manifest DCE23D121BBA6060B023A8A72A6EBF6A2C055C33B936538DB00917FEE4C86F1C
DLL      FEA4B2B153653461D465B67EB9CC5A762CC97785E511EEBBF5C776348268C246
```
