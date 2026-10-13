# Installation essais 7B — dix effects

- Demande utilisateur : installer les10variantes7B, texturesx4/chronologie30FPS, fournir CLUA.
- Résultat : `installation-result.json`, statut installed-verified ;10packs unitaires vérifiés puis remplacement dans pack64ressources/3447backings/1841195968octets.54autres ressources/pixels/contrats inchangés.
- Modèle : seedvr2_7b_int8_convrot.safetensors ; spatialv2/LAB/x4/pad32 ; Apollo8 one-shot15->30,alpha-native-left,gaussσ1.2x4/featherintérieur12x4/premul.728phases sur10assets.
- Provenance réellement installée : `payload_checks`,545backings changés par rapport3B ; chaque fichier installé correspond au SHA du pack7B. Registre binaire SHA inchangé (géométrie/cycles/cadence identiques) ; manifeste/provenance/pixels nouveaux, manifest SHA `D3878796EBF60BDFFFF463C6BF885F8FA028189F4948096B0373D2FEDC78F2F2`.
- Renderer stable/cache64 conservé SHA `3BFD4F1B1C21C4D1E126F06E0DC5857B7A53C8E130A98F9DD8C99D514D4AEA88` ; INI,fpDraw/fpSprite/fpSELECT,cataloguecréatures identiques ; candidat personnages NearestRGB-SilhouetteAlphaAA inchangé.
- Natif C++ charge le candidat complet : `native-runtime-pack-check.log` ; vérification transaction/pixels/contrats réussie ; jeu et InfinityLoader fermés avant remplacement.
- Suivi : seuls10assets de `effects/index/processing.csv` changés (production7B+reçuinstallation) ; autreslignes/selected_run/QA/release préservés. **QA ingame7B en attente**.
- CLUA : `effects/batches/effects-lot10-seedvr7b-compare-20261013-v1/{CLUA.md,CLUA.lua,clua.json}` ; relancer InfinityLoader, une commande à la fois, fermer la console et reprendre le jeu.
- Planche historique3B/7B conservée ; page avec état installé : `effects/batches/effects-lot10-seedvr7b-compare-20261013-v1/preview/installed-7b.html`.
- Restauration : `python -B engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py restore effects/installations/lot10-seedvr7b-apollo30-20261013-v1/backups/20261013T202002717352Z-8c07e253/renderer-install-receipt.json` (jeu/loader fermés). Remet les octets3B précédents ; resynchroniser les10pointeurs production/installation depuis `installed-before/processing.csv`, préserver changements ultérieurs horslot.
