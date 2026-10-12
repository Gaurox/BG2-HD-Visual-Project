# Release maps — 2026-10-12 v1

- Autorisation : finalisation release/installeur demandée dans ce chat ; ZIP sans compression
  jusqu'à la version finale. Aucune publication ni écriture dans le jeu installé.
- Sélection : `releases/BG2-HD-Upscale/manifests/map-release-candidates.csv` = 399 variantes,
  IDs permanents conservés. Ancien bootstrap PowerShell migré en données.
- Autorité exacte : `selection-manifest-v3.json` → miroir courant
  `releases/BG2-HD-Upscale/manifests/map-release-assemblies.json`.
- Catalogue : 400 QA acquises ; OH6460 partage OH8100, sans payload autonome dupliqué.
- Assemblages figés : 64 variantes, 2 579 fichiers, 3 628 031 638 octets copiés depuis sources
  conservées ; `maps/<BASE>/runs/release-maps-20261012-v1/<VARIANT>/05_build`.
- Eau : 63 WED ; décor final + contours + TIS/WED + 188 identités overlay jour/pluie dans leur
  composant map. Gardes WED/base TIS/pages comparées au registre courant ; aucune couche legacy
  manquante du 12 septembre réutilisée.
- QA : 144 preuves immuables reliées ; aucune nouvelle décision ingame. Deux preuves historiques
  existent en CRLF local/LF Git : deux empreintes exactes épinglées, sans normaliser les assets.
- AR3003 : patch réellement installé le 2026-09-06 retrouvé sous
  `output/map-patch-compositor/ar3003-four-portals-20260906/05_build/x4-four-portals-patched-test` ;
  quatre pages changées exactes au reçu historique et au rendu accepté le 2026-10-11.
- AR0413 : 22 fichiers de `ar0413-final-user-qa-20260928-v1.json` ; opacité64/64,
  YFGPKI/YFGPKIR, 30 FPS, q0,25 sec/q0 pluie. Ancien contrat août 17 fichiers remplacé.
- AR0516 : WED détenu par le contrat animation conservé exact, source/QA inchangées.
- Renderer : DLL alpha.9 `5D4EE06D84E0D6C6F6FB81797EAB0E9756B3ECE335EBF537E57C5597E0B40BCF`,
  bundle/source/animations/sprites/effects/overlays partagés conservés. Aucune recompilation DLL.
- Core : `[Shaders].EnableWaterOverlayRoute2=true`, `WaterOverlayStrength=1.00`,
  `EnableWaterEffect=true` ; valeurs de la revue finale acquise, restauration INI testée.
- Génération : `Compile-BG2HD-Release.ps1` → Phase2 → staging officiel → Phase4 → build
  `-ZipCompression NoCompression` → Phase6B → Phase5A → contrôle ZIP_STORED.
- Fixtures archive : installation/hash/désinstallation des 64 variantes actualisées,
  échantillons animation AR0603/AR0900/AR0516 conservés, anciens fichiers restaurés,
  nouveaux fichiers maps supprimés. Les fixtures ne qualifient pas un lancement réel.
- Reçus : `*-receipt.json`, `zip-verification.json`, `package-finalization.json` ;
  état final `docs/validation/maps-release-status-20261012-v1.json`.
- Publication : blocages existants conservés (Steam/jeu propre, EEex absent, renderer combiné,
  sauvegardes HD→vanilla, désinstallation complète, provenance/contact publics).
- Conservation physique : sources finales/staging/ZIP/inputs volumineux ignorés par Git ;
  un clone seul ne reconstitue pas le paquet. Ancien ZIP animations et staging antérieur conservés.

Scripts de recette : usage ponctuel, pas outils génériques à rejouer sur les sorties existantes.
`selection-manifest.json` et `-v2.json` sont des instantanés techniques supplantés par v3 ; v2
corrige l'inclusion WED, v3 épingle les deux encodages historiques. QA et assets inchangés.

```powershell
python -B pipeline/scripts/verify_map_release_candidates.py
pwsh -NoProfile -File releases/BG2-HD-Upscale/tools/Compile-BG2HD-Release.ps1
pwsh -NoProfile -File pipeline/recipes/maps-release-finalization-20261012-v1/build_and_validate.ps1
python -B pipeline/recipes/maps-release-finalization-20261012-v1/record_status.py
```
