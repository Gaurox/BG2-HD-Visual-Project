# Essais Topaz Gigapixel — médaillon central BIGLOGO — x2

Source commune : `BIGLOGO-options-frame-0.png` (346 × 449, RGBA), extraite de `BIGLOGO.BAM`, frame 0. Tous les essais emploient Topaz Gigapixel 8.4.1, facteur x2, PNG RGBA, espace colorimétrique conservé et débruitage/netteté/correction de compression au minimum (`1`).

| Modèle | Dossier | Pixels rouge-dominants | Observation |
| --- | --- | ---: | --- |
| Art & CG | `art-and-cg/x2/` | 1,426 % | Détail marqué, quelques pixels parasites au bord |
| Low Resolution V2 | `low-resolution/x2/` | 0,744 % | Couleurs les plus stables ; meilleur candidat Topaz initial |
| Standard V2 | `standard-2/x2/` | 1,473 % | Aspect plus lissé, davantage de pixels parasites |
| Recover V2, Detail 50 | `recovery-v2-detail-50/x2/` | 0,352 % | **Version retenue et intégrée** pour le médaillon central |

La variante validée possède son atlas DXT5 x2 dans `recovery-v2-detail-50/assets/`. L'overlay installé ne modifie que `iee-assets/BIGLOGO-MOS0017-x2.dxt5` et sa sauvegarde horodatée permet le retour arrière.
