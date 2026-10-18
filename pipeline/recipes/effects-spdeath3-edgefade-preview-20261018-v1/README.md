# SPDEATH3 — fondu gaussien du contour Bézier validé

```powershell
python -B pipeline/recipes/effects-spdeath3-edgefade-preview-20261018-v1/preview.py
```

- Demande2026-10-18 : « super ! validé ! peux tu ajouter un flou gaussien / fondu transparance sur les contours pour que ca s'integre mieux aux décors ». Validation visuelle limitée au comparatif Bézier précédent ; enregistrée dans `accepted-base.json`, aucune QA ingame/acceptation du lot33 déduite.
- Base exacte : `effects/batches/spdeath3-bezier-continuous-alpha-preview-20261018-v1/`, compagnons droit/prémultiplié hashés. Aucun retracé Bézier ni nouvelle inférence/interpolation.
- Formule locale réemployée : `am3000e-contour-soft-20261011-v1/build.py:soften`, seulement calcul raster ; aucun format runtime/padding de ce précédent transféré. Filtre Gaussian RGBA prémultiplié, pas de seconde prémultiplication. `w=1-smoothstep((distance-2sigma)/(2sigma))` ; `R=(1-w)*source+w*Gaussian(source,sigma)`, noyau exact si distance≥4sigma.
- `soft2` : sigma2x4, plein filtre dans4px intérieurs, cœur exact au-delà8. `soft4` : sigma4x4, plein filtre dans8px, cœur exact au-delà16. Tronqué4sigma, marge d'aperçu supplémentaire16px x4 commune aux trois vues. Fondu des deux côtés du contour, aucune érosion imposée.
-124phases/2profils62phases/31/15s conservés. Vérifications par variante : cœur RGBA prémultiplié et droit exact, RGB≤A, RGB nuls siA0, reconversion droit→prémultiplié erreur≤1, aucune phase vide, bords de canevas transparents. MasseA99.976–100.297% (soft2) /100.007–100.657% (soft4) ; variation maximale de flux RGB prémultiplié1.264%/1.525%.
- Sortie `effects/batches/spdeath3-bezier-edgefade-preview-20261018-v1/{accepted-base,summary,result}.json`, galerie3vues synchronisées Bézier/doux/diffus, masque seul, phases, fonds et détail. Dimensions d'aperçu256×416 ; les marges sont communes et conservent les ancrages relatifs.
- Version installée/indices/QA/release inchangés ; hash du manifest actif contrôlé avant/après. Si installation demandée, créer un dérivé runtime avec dimensions/centres/carriers cohérents ; ces raws d'aperçu ne se substituent pas directement aux anciens fichiers.
