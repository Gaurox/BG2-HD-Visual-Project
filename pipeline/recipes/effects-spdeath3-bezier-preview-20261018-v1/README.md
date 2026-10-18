# SPDEATH3 — courbes Bézier avant interpolation alpha

```powershell
python -B pipeline/recipes/effects-spdeath3-bezier-preview-20261018-v1/preview.py
```

- Retour utilisateur : phases encore entièrement pixelisées après SDF Ankheg ; autre méthode demandée. Périmètre SPDEATH3 seul, aperçu, aucune installation/inférence/réinscription.
- Limites de l'essai précédent : champ SDF borné et pondéré près des coeurs pour protéger les parties fines ; opacité temporelle issue d'une enveloppe nearest. Une silhouette légèrement lissée ne suffit pas à reconstruire les marches de cette enveloppe.
- Variante : vectoriser les30masques natifs alignés x1 par Potrace, alphamax1.334 (tous angles transformés en courbes), opttolerance0.1, turdsize0 ; rasterisation x4 SS8/BOX. Réemploi `build_spatial_spline_alpha.py:potrace_alpha` et port local `.tools/potracer`. Bande10000 = aucun clamp par l'ancien masque nearest.
- **Tracer avant interpolation** : pour chaque phase `(left,right,fraction)`, `Anew=round((1-f)*Acurve[left]+f*Acurve[right])`. Reconstruction des124alphas d'origine avec les30masques nearest démontrée exacte ; fraction/durée/cadence/phase RGB inchangées. Aucun nearest alpha réinjecté, aucune multiplication par l'ancien support.
- RGB visibles déjà présents exacts ; nouveaux bords extrudés du premier plan voisin, distance≤4x4. RGB nuls siA0, compagnons droit/prémultiplié vérifiés. Marge d'aperçu commune4x4, runtime/carrier inchangés ; une installation future doit adapter sa géométrie.
- Résultat `effects/batches/spdeath3-bezier-continuous-alpha-preview-20261018-v1/` :124phases,206pixels alpha gradués minimum/phase, aucune composante native entièrement perdue (mesure de masse sur chaque composante source ; pas une garantie de topologie à tout seuil). MasseA93.22–100.05% : arrondi plus marqué pouvant modifier les détails, aucun inset imposé. Ne pas présenter cette variante comme une copie de la silhouette d'origine.
- Galerie synchronisée installé/SDF/Bézier,2profils de62phases/31/15s, alpha seul/détail. Exemple phase19 : angle vertical conservé par le SDF, reconstruit par Bézier. Ancien comparatif8790 conservé.
- Documentation primaire : [manuel Potrace](https://potrace.sourceforge.net/potrace.1.html), alphamax>4/3 supprime les coins ; opttolerance pilote la fusion des segments Bézier. Pas de changement global de politique alpha.
