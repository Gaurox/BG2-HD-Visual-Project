# END15FPS / MELISSAN — masters partagés et installation locale, 2026-11-11 v1

- Demande : traitement complet des2films, reconstruction de7versions linguistiques, installation ingame puis commit. Analyse : `docs/validation/video-endings-locales-analysis-20261111-v1.json`.
- Films/langues : END15FPS défaut/DE/IT/PL ; MELISSAN défaut/DE/PL. Aucun fichier français séparé dans l’installation ; défaut = anglais commun.
- Production : `python -B pipeline/recipes/endings-shared-30fps-20261111-v1/produce.py` ; premier SeedVR peut être lancé séparément par `seedvr.py --film END15FPS`. Reprise : étapes vérifiées réutilisées, manifeste final immuable ; en cas d’échec, inspecter les journaux avant de reprendre.
- GPU séquentiel : END SeedVR → END Apollo → MEL SeedVR → MEL Apollo. Assemblages/encodages CPU au fil des résultats,2workers maximum. Aucun travail GPU par langue.
- SeedVR :2sources défaut entières,1829+525images15fps ; 3B FP16/VAE FP16/LAB,1080,seed42,batch33 uniforme,overlap3,portions330,bruits0,SDPA,swap32,CPU offload,VAE encode1024/128/decode768/128. Bootstrap borné existant des intros, export par8images ; sources natives FFV1 vérifiées par SHA image.
- Apollo : apo-8,30fps,slowmo1,rdt−0.01,GPU0,vram0.8,instances0,download0. RGB24 → gbrp16le → conversion pc/tv bt601 identique à INTRO15F. 2N−1images IA +1maintien terminal ; masters muets30fps.
- Défaut/DE/IT : mêmes H264 et VP8 réutilisés par copie de flux, seuls origine PTS vidéo et audio natif changent. VP8 encodé une seule fois pour chaque groupe identique.
- PL : master30 rééchantillonné aux temps natifs, aucun nouvel upscale ni nouvelle interpolation IA. END : appariement luma intégral160×90, alignement monotone à pénalité d’édition0,45, voisinage±5images ; revue RGB avant/pendant/après les16transitions (`review_mapping.py`). MEL :525images de contenu dans le même ordre puis maintien de l’image finale. Deux PTS0 natifs conservés comme preuve, dernier ancrage retenu pour l’échantillonnage30fps. `native-mapping.json` conserve toutes les correspondances.
- Apparence/cadrage : masters défaut partagés, cadrage source conservé ; le PL adopte les niveaux du master défaut (notamment blanc final MEL). Aucun carton traduit ou plan linguistique identifié.
- Livrables : `video/final/endings-shared-30fps-20261111-v1/<film>/<locale>/` : MP4 H264/AAC192k de lecture, MKV H264/Vorbis natif, WBM VP8/Vorbis pour jeu. Pas de `shortest`, coupe ou étirement audio ; queues natives conservées indépendamment de la durée vidéo.
- Profil WBM : libvpx/VP8,CRF4/30M,qmax12,cpu-used2,yuv420p,1920×1080,30fps,Vorbis copie. Vérifications intégrées : décodage complet/nombres/PTS images, SHA PCM et flux Vorbis, nombre/PTS paquets audio, SSIM1image/s >0,99. QA visuelle utilisateur et ingame restent distinctes.
- Autorité finale (après production) : `video/index/endings-finals30-20261111-v1.json` ; copie `metadata/manifest.json`. Aucun changement de payload/staging/release.

- Validation utilisateur2026-11-11 :7WBM acceptés après tests ingame ; décision immuable `video/index/qa-decisions/endings-ingame-accepted-20261111-v1.json`, SHA des7runtimes/alias liés au reçu. Les manifestes techniques et reçus historiques restent inchangés ; état QA courant = décision + `video/index/status.csv`. Aucune intégration release.

## Installation et test

- Jeu/InfinityLoader fermés ; `python -B pipeline/recipes/endings-shared-30fps-20261111-v1/install.py prepare` :7cibles natives sauvegardées réellement,7alias neufs vérifiés ; `install.py install` :14copies temporaires/SHA/remplacement atomique, reçu final et index après vérification.
- Reçu : `video/installations/endings-shared-apollo30-20261111-v1/installation.json` ; sauvegardes `before/` ; index versionné `video/index/endings-ingame-test-20261111-v1.json` et `metadata/installation.json`.
- Cibles canoniques via `config://bg2ee_game_root` : `movies/end15fps.wbm`, `movies/melissan.wbm`, variantes `lang/de_DE/movies/`, END italien sous `lang/it_IT/movies/end15fps.wbm`, PL sous `lang/pl_PL/movies/END15FPS.wbm` et `MELISSAN.wbm`.
- Charger une partie, Ctrl+Espace, une commande à la fois ; aucun changement de langue du jeu nécessaire :

```lua
C:PlayMovie("HDENEN") -- END15FPS anglais/défaut
C:PlayMovie("HDENDE") -- END15FPS allemand
C:PlayMovie("HDENIT") -- END15FPS italien
C:PlayMovie("HDENPL") -- END15FPS polonais
C:PlayMovie("HDMLEN") -- MELISSAN anglais/défaut
C:PlayMovie("HDMLDE") -- MELISSAN allemand
C:PlayMovie("HDMLPL") -- MELISSAN polonais
```

- `C:PlayMovie("END15FPS")` / `C:PlayMovie("MELISSAN")` : résolution habituelle selon langue du jeu. Référence locale de commande : recette `../intro15f-ingame-test-20261111-v1/README.md`.
- Restauration : jeu/loader fermés ; uniquement les14entrées du reçu, SHA actuel=`after_sha256` exigé ; cibles préexistantes ← sauvegardes réelles/`before_sha256`, alias neufs retirés après contrôle. Garder reçus et sauvegardes.
