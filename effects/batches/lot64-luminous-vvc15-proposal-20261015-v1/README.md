# Lot64 — proposition lumineuse VVC15, 2026-10-15

- `batch.json` : 64 BAM distincts, non commencés, consommateurs VVC connus ; sources SHA256 vérifiées, zéro doublon canonique entre eux ou avec les effets acceptés. Mode Blended, 15 FPS, aucune palette externe.
- Temporalité : 37 ponctuels, 24 boucles, 3 mixtes ; conserver séparément cycles/directions/phases, durée native et raccord de boucle. La recette mono-cycle du lot33 ne se rejoue pas sans adaptation temporelle.
- 4097 frames sources ; 226 cycles BAM, 4961 slots bruts cumulés (pas une durée globale : directions/cycles peuvent être alternatifs).
- `preview/lot64-native-{1,2,3,4}.png` : une frame source par BAM, même numérotation que le manifeste ; pose de flux RGB maximal parmi les frames utilisées, palette et alpha sources conservés, fond noir, zoom NEAREST par case. Aperçus recadrés pour lecture ; aucune échelle ingame déduite des vignettes. PNG natifs RGB/RGBA sous `preview/native/`.
- Ressources partagées déjà acceptées côté animations écartées : BDFORCEW, OHDLPORT, OHHNECR, OHRSGATE, SPDIMNDR ; aucun traitement/contrat de map réutilisé implicitement. Personnages/objets physiques détaillés et ressources sans contrôleur identifié hors lot.
- Proposition uniquement : aucun upscale, interpolation ou changement installé/index/QA/release.
