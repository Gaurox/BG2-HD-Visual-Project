# Installation lot33 — 2026-10-14

- Autorisation : installer les33 effets x4/nearest/30FPS, conserver les personnages.
- `installation-result.json`, `install-plan.json`, `before.json` : candidat97effets, 5407backings, 3428013696octets ; 64 ressources précédentes et tous leurs SHA inchangés.
- Nouveaux33 : `seedvr2_7b_int8_convrot.safetensors`, x4, Apollo15→30, GaussianRGB1.2px, feather12px ; packs autonomes et contrôles33/33 liés dans `effects/batches/lot33-seedvr7b-apollo30-20261014-v1/`.
- DLL : `5207E6259B4B72AFEC4755B575A61DEF1ADAE870FBB2146867D5215C224D234C` ; seule modification renderer : limite CPU2→4Gio. NEAREST, RGBA8 sans compression, niveau0, cache GPU64 conservés.
- `renderer-tests.log`, `renderer-tests-detail.log` : 3/3 tests ; chargeur, pixels GPU nearest/cache720frames avec allocation Character, minification personnages.
- `native-runtime-pack-check.log` : pack97 chargé intégralement, filtreNEAREST/cache64. Ce contrôle natif ne constitue pas une validation ingame.
- INI, fpDraw/fpSprite/fpSELECT, catalogue personnages : SHA identiques avant/après ; NearestRGB-SilhouetteAlphaAA conservé. Header eau identique à la compilation précédente.
- Reçu : `backups/20261014T203620188663Z-f6be26de/renderer-install-receipt.json`, statutinstalled ; sauvegarde précédente autonome, transaction vérifiée.
- Index : seules les colonnes installation des33 changent ; production/QA/sélections existantes et release conservées. `processing-before.json` : état juste avant cette mise à jour.
- `CLUA.md` : 33 commandes VVC natives individuelles. Démarrer via InfinityLoader ; QA visuelle utilisateur en attente.
- Reproduction : `python -B pipeline/recipes/effects-lot33-seedvr7b-apollo30-20261014-v1/install.py {compose,prepare,install}` ; résultat enregistré immuable, nouvelle version requise pour une autre installation.
