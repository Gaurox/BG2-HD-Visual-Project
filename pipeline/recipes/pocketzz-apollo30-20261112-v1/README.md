# POCKETZZ FullHD30 — 2026-11-12

- Source sélectionnée : `video/pocketzz/runs/pocketzz-comfyui-experiments-20260814/ComfyUI_00002_.mp4`, SeedVR FP16 LAB,1920×1080/15fps/90images/6s. Durée du candidat accepté conservée (source native ~6,473s inchangée).
- `produce.py` réutilise Apollo8 `interpolate()` de `../endings-shared-30fps-20261111-v1/produce.py` : apo-8/30fps/rdt=-0.01/device0/vram0.8/instances0 ;179images générées +1tenue finale →180images/6s. 89/89images intermédiaires distinctes ; PTS/décodage complets contrôlés. AAC du candidat copié sans changement PCM/paquets/PTS.
- `deliver.py` : WBM VP8 CRF4/30M/qmax12 +Vorbis q6 ; SSIM complet0,994550 vs MP4. Décalage constant WebM12ms lié au priming Vorbis ; grille30fps vérifiée. Aucun nouvel upscale.
- Résultats : `video/final/pocketzz-apollo30-20261112-v1/POCKETZZ/default/` ; manifeste `video/index/pocketzz-finals30-20261112-v1.json`, SHA/contrôles sous `metadata/`.
- QA visuelle utilisateur acceptée : `video/index/qa-decisions/POCKETZZ/20261112-apollo30-visual-accepted-v1.json`. **QA ingame pending-user**, aucune intégration release.
- `install.py prepare` sauvegarde l’original puis `install.py install` remplace uniquement `config://bg2ee_game_root/movies/pocketzz.wbm` et crée `movies/HDPCKZZ.wbm` ; jeu/InfinityLoader fermés, SHA vérifiés. Reçu : `video/index/pocketzz-ingame-test-20261112-v1.json`.
- Console Ctrl+Espace en partie : `C:PlayMovie("HDPCKZZ")`.
- Restauration jeu fermé : vérifier SHA before/after du reçu, recopier `video/installations/pocketzz-apollo30-20261112-v1/before/movies/pocketzz.wbm` vers `config://bg2ee_game_root/movies/pocketzz.wbm`, supprimer uniquement l’alias `movies/HDPCKZZ.wbm` créé par ce run. Ne pas supprimer la sauvegarde.
