# SPDEATH3 — aperçu masque SDF Ankheg

```powershell
python -B pipeline/recipes/effects-spdeath3-sdf-preview-20261018-v1/preview.py
```

- Demande2026-10-18 : retravailler uniquement33SPDEATH3, commencer par lisser le masque avec la méthode Ankheg. Aperçu hors jeu, pas de nouvelle inférence ni installation implicite.
- Réemploi direct `effects-lot8-sdf-ankheg-preview-20261017-v1/preview.py:smooth_rgba` et référence `docs/measurements/q3m-ankheg-sdf-offline-x2-20261004-v1/sdf_trial.py`. SDF sigma2/biais±1 sur grillex2, équivalents4/±2x4 ; quantification1/16x2, couverture8×8, FG8/BG4 du champ protégés. Aucun inset.
- Source `spdeath3-apollo30-native-retimed-20261017-v1`,124phases/2profils once+loop62phases/31/15s chacun. Alpha nearest x4 réduit exactement versx2 ; enveloppe d'opacité temporelle conservée. RGB visibles existants exacts ; extension des nouveaux bords depuis le premier plan voisin, RGB nuls siA0, prémultiplication contrôlée.
- Calcul sur canevas aligné avec marge transparente4x4 identique avant/après : les crops source touchent le bord ; cette marge évite de tronquer l'expansion SDF. Aucun carrier/centre/runtime modifié ; une future dérivation installable devra encoder cette marge en géométrie cohérente, pas recopier les raws avec les anciennes dimensions.
- Sortie immuable `effects/batches/spdeath3-sdf-ankheg-preview-20261018-v1/{result,summary}.json`, `review/index.html` ;33masques distincts/124phases,107208pixels d'alpha changés, extension maximale2x4, masseA96.82–99.95% de la source. Aucun effacement de phase visible ; pas de retrait systématique (lissage peut modifier l'aire).
- Galerie : PNG à phase commune, lecture synchronisée/cycle/curseur, alpha seul, fond, clic pour déplacer le détail. Les deux vues ont la même marge et les mêmes ancrages ; durée/cadence nominale inchangées. `review/frames/` contient les compagnons droit/prémultiplié pour réutilisation exacte ultérieure, hashes dans `result.json`.
- Installation active hashée avant/après et identique ; index de production/QA/install/release inchangés. QA Ankheg acquise citée comme provenance, aucune validation de SPDEATH3 déduite.
