# Overlays techniques TIS

Ces ressources liquides partagées ne sont pas des maps autonomes. Leur sélection release est
définie uniquement par `releases/BG2-HD-Upscale/manifests/overlay-sources.json`; la présence d'un
fichier sous ce dossier, dans un run ou dans un backup ne prouve aucun statut.

## Organisation et outils actifs

| Besoin | Emplacement / commande |
|---|---|
| Runs et builds par resref | `<RESREF>/runs/<run-id>/` ; ne pas réécrire un run historique |
| Extraction d'un TIS palette ancien | `pipeline/scripts/extract_legacy_tis_frames.py` |
| Reconstruction TIS/PVRZ depuis les frames traitées | `pipeline/scripts/build_upscaled_legacy_tis.py` |
| Diagnostic de couverture liquide WED | `pipeline/scripts/render_liquid_overlay_mask.py` |
| Diagnostic primaire/secondaire/vide | `pipeline/scripts/render_tile_classes.py` |
| Variante locale de contour alpha | `pipeline/scripts/build_water_contour_feather.py` |

Les sources extraites restent immuables. Une installation utilise les scripts transactionnels et
la politique `overlay-sources.json`; elle ne modifie pas cette politique par déduction.
