# Suivi vidéo — 2026-11-12

- Autorités : sources=`index/resources.csv` ; périmètre=`index/production-scope.json` ; production courante=`index/status.csv`, détails `index/processing.csv`, `index/intro-finals30-20261111-v1.json`, `index/endings-finals30-20261111-v1.json` et `index/outro-finals30-20261112-v1.json` ; QA=`index/qa-decisions/` ; installation=`installations/*/installation.json` ; release séparée.
- Périmètre actif37cinématiques (variantes linguistiques comprises) :35productions complètes,1partielle en pause (ENDCRDIT),1sans production ;2cinématiques à terminer (≈2min24s de sources entières).31installées localement ;8versions validées ingame (7END15FPS/MELISSAN +OUTRO) ; autres QA ingame séparées. POCKETZZ validé visuellement, test ingame en attente ; anomalie DAYNITE ouverte. Aucun asset vidéo intégré à la release.
-13tutoriels retirés du suivi et exclus des futurs traitements sur demande utilisateur2026-11-11 ; décision `index/production-scope.json`. Inventaire50sources et fichiers natifs conservés.

| Vidéo | Production conservée | QA | Installation locale |
|---|---|---|---|
| NITEDAY | DAYNITE H3 01604 inversé/recalé,300images/FullHD30/10s vidéo,10,942s total déclaré,son NITEDAY natif | H3 inversé accepté2026-11-12 ; ingame en attente | WBM +alias `HDNTDAY` installés |
| FLYTHR02 | SeedVR FP16 LAB1080 →Apollo8,404images/30fps/~13,47s,son natif complet | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDFLY02` installés |
| DORNGORG | SeedVR FP16 LAB1080 →Apollo8 ; PTS natifs reconstruits,464images/30fps/~15,47s,son natif | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDDGORG` installés |
| RASAADMI | SeedVR FP16 LAB1080 →Apollo8 ; PTS natifs reconstruits,484images/30fps/~16,13s,son natif | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDRASAMI` installés |
| FLYTHR04 | SeedVR FP16 LAB1080 →Apollo8,490images/30fps/~16,33s,son natif | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDFLY04` installés |
| NEERAES | SeedVR FP16 LAB1080 →Apollo8 ; PTS natifs reconstruits,507images/30fps/16,9s,son natif | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDNEERA` installés |
| HEXXATDR | SeedVR FP16 LAB1080 →Apollo8 ; PTS natifs reconstruits,531images/30fps/17,7s,son natif | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDHEXX` installés |
| MANAFORG | SeedVR FP16 LAB1080 →Apollo8,549images/30fps/18,3s,son natif complet | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDMANA` installés |
| DORNTREE | SeedVR FP16 LAB1080 →Apollo8 ; PTS natifs reconstruits,553images/30fps/~18,43s,son natif | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDDTREE` installés |
| RASAADTE | SeedVR FP16 LAB1080 →Apollo8 ; PTS natifs reconstruits,599images/30fps/~19,97s,son natif | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDRASATE` installés |
| FLYTHR01 | SeedVR FP16 LAB1080 →Apollo8,670images/30fps/22,333s,son natif complet | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDFLY01` installés |
| SARADUSH | SeedVR FP16 LAB1080 →Apollo8,694images/30fps/23,133s,son natif complet | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDSARAD` installés |
| BLACKPIT | SeedVR FP16 LAB1080 →Apollo8 ; PTS natifs reconstruits,733images/30fps/~24,44s,MP4/MKV/WBM | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDBLKPIT` installés |
| DEATHAND | SeedVR LAB15 → Apollo8 FullHD30, MP4 parent + MOV final | méthode validée2026-08-31 ; livraison/QA asset non définies | non |
| FLYTHR03 | SeedVR LAB15 → Apollo8 FullHD30, MP4 parent + MOV final | méthode validée2026-08-31 ; livraison/QA asset non définies | non |
| RESTDUNG | SeedVR FP16 LAB15 → Apollo8 FullHD30 | comparaison15/30 acceptée | WBM15 ; test ingame en attente |
| RESTINN | SeedVR FP16 LAB15 → Apollo8 FullHD30 | comparaison acceptée | non |
| REST | SeedVR FP16 LAB15 → Apollo8 FullHD30 | comparaison acceptée | non |
| DAYNITE | H3 01604 → fondus10s → nearest FullHD24 → Apollo8 FullHD30 + son natif | sélection pour test local ; post-SeedVR rejeté ; ancienne vidéo signalée ingame | WBM30 présent et SHA conforme ; anomalie ingame non résolue |
| POCKETZZ | SeedVR FP16 LAB FullHD15 → Apollo8 FullHD30,180images/6s | visuelle acceptée2026-11-12 ; ingame en attente | WBM +alias `HDPCKZZ` installés |
| INTRO (défaut/DE/PL) |3assemblages SeedVR FullHD~30, audios natifs | visuelle selon décisions/index INTRO |3WBM installés ; test ingame en attente |
| INTRO15F (défaut/DE/IT/PL) |4assemblages SeedVR + Apollo8 FullHD30, audios natifs |4versions acceptées visuellement |4WBM installés ; test ingame en attente |

## END15FPS / MELISSAN — 7versions validées ingame

- Production : `index/endings-finals30-20261111-v1.json` ; 2masters SeedVR FP16 LAB → Apollo8 FullHD30,7assemblages à audios Vorbis natifs. Défaut/DE/IT partagent les flux vidéo ; PL recalé sur ses PTS,fin blanche MEL prolongée sans IA supplémentaire.
- Installation : `index/endings-ingame-test-20261111-v1.json` ;7WBM canoniques +7alias (`HDENEN/DE/IT/PL`, `HDMLEN/DE/PL`),sauvegardes réelles conservées. 7WBM acceptés ingame par l’utilisateur2026-11-11 ; décision immuable `index/qa-decisions/endings-ingame-accepted-20261111-v1.json` liée aux SHA des fichiers testés. Aucune intégration release.
- Console/restauration/réglages : `../pipeline/recipes/endings-shared-30fps-20261111-v1/README.md`.

## OUTRO — validé ingame

- Source muette1225images15fps →4portions SeedVR2 3B FP16 LAB/1080 (contexte33images) →master1225images →Apollo8/2450images30fps (~81,667s). MP4,MKV,WBM restent sans piste audio.
- Résultats/contrôles : `index/outro-finals30-20261112-v1.json` ; recette `../pipeline/recipes/outro-seedvr-apollo30-20261112-v1/README.md`. QA visuelle acceptée2026-11-12 : `index/qa-decisions/OUTRO/20261112-fullhd30-visual-accepted-v1.json`. Installation locale : `index/outro-ingame-test-20261112-v1.json`, `movies/outro.wbm` +alias `HDOUTRO`, sauvegarde réelle conservée. Test `C:PlayMovie("HDOUTRO")` accepté par l’utilisateur2026-11-12 ; décision immuable `index/qa-decisions/OUTRO/20261112-fullhd30-ingame-accepted-v1.json`, liée au SHA du WBM installé. Aucune intégration release.

## POCKETZZ — validé visuellement, test ingame en attente

- Production : `index/pocketzz-finals30-20261112-v1.json` ; recette `../pipeline/recipes/pocketzz-apollo30-20261112-v1/README.md`. Candidat SeedVR accepté →Apollo8/1920×1080/30fps/180images/6s ; audio candidat copié en MP4, Vorbis pour WBM.
- QA visuelle acceptée2026-11-12 : `index/qa-decisions/POCKETZZ/20261112-apollo30-visual-accepted-v1.json`. Installation : `index/pocketzz-ingame-test-20261112-v1.json`, sauvegarde réelle conservée ; `movies/pocketzz.wbm` +alias `HDPCKZZ`. Test restant : `C:PlayMovie("HDPCKZZ")`. **QA ingame en attente**, aucune intégration release.

## BLACKPIT — validé visuellement, vérification ingame en attente

- Plus longue nouvelle vidéo restante sélectionnée2026-11-12 :24,437s. SeedVR2 FP16 LAB1080/2portions avec contexte33images ;611images natives conservées. Apollo8 puis reconstruction à partir des PTS irréguliers →733images/1920×1080/30fps/~24,44s. Audio Vorbis natif identique dans MKV/WBM ; MP4 AAC.
- Résultats : `index/blackpit-finals30-20261112-v1.json` ; recette `../pipeline/recipes/blackpit-seedvr-apollo30-20261112-v1/README.md`. Décodage complet,comptes/PTS/audio contrôlés ; SSIM runtime échantillonné0,994395. QA visuelle acceptée2026-11-12 : `index/qa-decisions/BLACKPIT/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/blackpit-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/blackpit.wbm` +alias `HDBLKPIT` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDBLKPIT")`. **QA ingame en attente**, aucune intégration release.

## SARADUSH — validé visuellement, vérification ingame en attente

- Plus longue nouvelle vidéo restante après BLACKPIT :23,133s ;315images15fps/21s +queue audio. SeedVR2 FP16 LAB1080/1passage →Apollo8/630images30fps ;64images de maintien terminal couvrent le son complet →694images/1920×1080/30fps/23,133s.
- Résultats : `index/saradush-finals30-20261112-v1.json` ; recette `../pipeline/recipes/saradush-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),SSIM runtime échantillonné0,994839. QA visuelle acceptée2026-11-12 : `index/qa-decisions/SARADUSH/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/saradush-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/saradush.wbm` +alias `HDSARAD` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDSARAD")`. **QA ingame en attente**, aucune intégration release.

## FLYTHR01 — validé visuellement, vérification ingame en attente

- Plus longue nouvelle vidéo restante après SARADUSH :22,332s ;301images15fps/~20,067s +queue audio. SeedVR2 FP16 LAB1080/1passage →Apollo8/602images30fps ;68images de maintien noir terminal couvrent le son complet →670images/1920×1080/30fps/22,333s.
- Résultats : `index/flythr01-finals30-20261112-v1.json` ; recette `../pipeline/recipes/flythr01-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),SSIM runtime échantillonné0,995238. QA visuelle acceptée2026-11-12 : `index/qa-decisions/FLYTHR01/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/flythr01-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/flythr01.wbm` +alias `HDFLY01` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDFLY01")`. **QA ingame en attente**, aucune intégration release.

## RASAADTE — validé visuellement, vérification ingame en attente

- Source19,964s,499images à PTS irréguliers ; SeedVR2 FP16 LAB1080/2portions avec contexte33images →Apollo8 puis reconstruction native30fps :599images/1920×1080/~19,97s. Son Vorbis natif copié sans étirement en MKV/WBM,MP4 AAC.
- Résultats : `index/rasaadte-finals30-20261112-v1.json` ; recette `../pipeline/recipes/rasaadte-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),images intermédiaires Apollo vérifiées,SSIM runtime échantillonné0,994993. QA visuelle acceptée2026-11-12 : `index/qa-decisions/RASAADTE/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/rasaadte-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/rasaadte.wbm` +alias `HDRASATE` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDRASATE")`. **QA ingame en attente**, aucune intégration release.

## DORNTREE — validé visuellement, vérification ingame en attente

- Source18,429s,461images à PTS irréguliers ; SeedVR2 FP16 LAB1080/2portions avec contexte33images →Apollo8 puis reconstruction native30fps :553images/1920×1080/~18,43s. Son Vorbis natif copié sans étirement en MKV/WBM,MP4 AAC.
- Résultats : `index/dorntree-finals30-20261112-v1.json` ; recette `../pipeline/recipes/dorntree-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),images intermédiaires Apollo vérifiées,SSIM runtime échantillonné0,995561. QA visuelle acceptée2026-11-12 : `index/qa-decisions/DORNTREE/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/dorntree-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/dorntree.wbm` +alias `HDDTREE` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDDTREE")`. **QA ingame en attente**, aucune intégration release.

## MANAFORG — validé visuellement, vérification ingame en attente

- Source18,286s ;251images15fps/~16,733s +queue audio. SeedVR2 FP16 LAB1080/1passage →Apollo8/502images30fps ;47images de maintien terminal couvrent le son complet →549images/1920×1080/30fps/18,3s.
- Résultats : `index/manaforg-finals30-20261112-v1.json` ; recette `../pipeline/recipes/manaforg-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),SSIM runtime échantillonné0,996581. QA visuelle acceptée2026-11-12 : `index/qa-decisions/MANAFORG/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/manaforg-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/manaforg.wbm` +alias `HDMANA` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDMANA")`. **QA ingame en attente**, aucune intégration release.

## HEXXATDR — validé visuellement, vérification ingame en attente

- Source17,696s,442images à PTS irréguliers ; SeedVR2 FP16 LAB1080/2portions avec contexte33images →Apollo8 puis reconstruction native30fps :531images/1920×1080/17,7s. Son Vorbis natif copié sans étirement en MKV/WBM,MP4 AAC.
- Résultats : `index/hexxatdr-finals30-20261112-v1.json` ; recette `../pipeline/recipes/hexxatdr-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),images intermédiaires Apollo vérifiées,SSIM runtime échantillonné0,994966. QA visuelle acceptée2026-11-12 : `index/qa-decisions/HEXXATDR/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/hexxatdr-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/hexxatdr.wbm` +alias `HDHEXX` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDHEXX")`. **QA ingame en attente**, aucune intégration release.

## NEERAES — validé visuellement, vérification ingame en attente

- Source16,896s,422images à PTS irréguliers ; SeedVR2 FP16 LAB1080/2portions avec contexte33images →Apollo8 puis reconstruction native30fps :507images/1920×1080/16,9s. Son Vorbis natif copié sans étirement en MKV/WBM,MP4 AAC.
- Résultats : `index/neeraes-finals30-20261112-v1.json` ; recette `../pipeline/recipes/neeraes-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),images intermédiaires Apollo vérifiées,SSIM runtime échantillonné0,994889. QA visuelle acceptée2026-11-12 : `index/qa-decisions/NEERAES/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/neeraes-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/neeraes.wbm` +alias `HDNEERA` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDNEERA")`. **QA ingame en attente**, aucune intégration release.

## FLYTHR04 — validé visuellement, vérification ingame en attente

- Source16,329s,245images15fps ; SeedVR2 FP16 LAB1080/1passage →Apollo8 :490images/1920×1080/30fps/~16,33s. Son Vorbis natif conservé en MKV/WBM,MP4 AAC ; aucune extension terminale supplémentaire nécessaire.
- Résultats : `index/flythr04-finals30-20261112-v1.json` ; recette `../pipeline/recipes/flythr04-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),images intermédiaires Apollo vérifiées,SSIM runtime échantillonné0,995657. QA visuelle acceptée2026-11-12 : `index/qa-decisions/FLYTHR04/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/flythr04-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/flythr04.wbm` +alias `HDFLY04` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDFLY04")`. **QA ingame en attente**, aucune intégration release.

## RASAADMI — validé visuellement, vérification ingame en attente

- Source16,127s,403images à PTS irréguliers ; SeedVR2 FP16 LAB1080/2portions avec contexte33images →Apollo8 puis reconstruction native30fps :484images/1920×1080/~16,13s. Son Vorbis natif copié sans étirement en MKV/WBM,MP4 AAC.
- Résultats : `index/rasaadmi-finals30-20261112-v1.json` ; recette `../pipeline/recipes/rasaadmi-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),images intermédiaires Apollo vérifiées,SSIM runtime échantillonné0,995021. QA visuelle acceptée2026-11-12 : `index/qa-decisions/RASAADMI/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/rasaadmi-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/rasaadmi.wbm` +alias `HDRASAMI` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDRASAMI")`. **QA ingame en attente**, aucune intégration release.

## DORNGORG — validé visuellement, vérification ingame en attente

- Source15,462s,386images à PTS irréguliers ; SeedVR2 FP16 LAB1080/2portions avec contexte33images →Apollo8 puis reconstruction native30fps :464images/1920×1080/~15,47s. Son Vorbis natif copié sans étirement en MKV/WBM,MP4 AAC.
- Résultats : `index/dorngorg-finals30-20261112-v1.json` ; recette `../pipeline/recipes/dorngorg-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),images intermédiaires Apollo vérifiées,SSIM runtime échantillonné0,992080. QA visuelle acceptée2026-11-12 : `index/qa-decisions/DORNGORG/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/dorngorg-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/dorngorg.wbm` +alias `HDDGORG` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDDGORG")`. **QA ingame en attente**, aucune intégration release.

## FLYTHR02 — validé visuellement, vérification ingame en attente

- Source13,462s ;187images15fps/~12,467s +queue audio. SeedVR2 FP16 LAB1080/1passage →Apollo8/374images30fps ;30images de maintien terminal couvrent le son complet →404images/1920×1080/30fps/~13,47s.
- Résultats : `index/flythr02-finals30-20261112-v1.json` ; recette `../pipeline/recipes/flythr02-seedvr-apollo30-20261112-v1/README.md`. MP4/MKV/WBM contrôlés (décodage/comptes/PTS/audio natif PCM et paquets MKV/WBM),SSIM runtime échantillonné0,992152. QA visuelle acceptée2026-11-12 : `index/qa-decisions/FLYTHR02/20261112-fullhd30-visual-accepted-v1.json`. Installation : `index/flythr02-ingame-test-20261112-v1.json` ; original sauvegardé, `movies/flythr02.wbm` +alias `HDFLY02` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDFLY02")`. **QA ingame en attente**, aucune intégration release.

## NITEDAY — H3 inversé retenu, vérification ingame en attente

- Choix utilisateur2026-11-12 : version H3 inversée retenue ; décision `index/qa-decisions/NITEDAY/20261112-h3-reverse-visual-accepted-v1.json`. Le candidat SeedVR antérieur reste historique non sélectionné (`index/niteday-finals30-20261112-v1.json`),sans suppression ni validation déduite.
- Réemploi DAYNITE H301604/nearest/Apollo30 en inverse,sur progression lumineuse et fondus natifs NITEDAY :300images/1920×1080/30fps/10s vidéo,durée déclarée totale10,942s ; audio NITEDAY Vorbis PCM/paquets/PTS identiques. Convention native du dernier paquet Vorbis23ms conservée via Duration Matroska +CRC ; aucun nouveau calcul IA/GPU. DAYNITE historique inchangé.
- Production sélectionnée : `index/niteday-h3-reverse-finals30-20261112-v1.json` ; recette `../pipeline/recipes/niteday-h3-reverse-20261112-v1/README.md` ; analyse historique `index/niteday-reverse-analysis-20261112-v1.json`. WBM copié à octets identiques depuis l’aperçu validé ; SSIM échantillonné0,994300 face au master.
- Installation : `index/niteday-h3-reverse-ingame-test-20261112-v1.json` ; original réel sauvegardé,`movies/niteday.wbm` +alias `HDNTDAY` installés et SHA vérifiés. Test restant : `C:PlayMovie("HDNTDAY")`. **QA ingame en attente**, aucune intégration release.

## ENDCRDIT — pause après première portion

- Demande utilisateur2026-11-11 : montrer la première portion puis libérer le GPU.330images/0–22s SeedVR FullHD15 conservées ;1671images source restantes, Apollo non démarré. Source/FFV1/SHA/commandes gardés ; reprise à l’image330 avec contexte natif297–329.
- Point de reprise : `index/endcrdit-paused-20261111-v1.json` ; aperçu et comparaison : `../pipeline/recipes/endcrdit-seedvr-apollo30-20261111-v1/README.md`. QA utilisateur2026-11-11 : rendu apprécié mais lettres trop déformées, portion SeedVR refusée ; décision `index/qa-decisions/ENDCRDIT/20261111-first-seedvr-portion-text-rejected-v1.json`. Essais Topaz reportés à une reprise demandée ; pause maintenue, médias conservés. Aucune installation/release.

## À terminer — 2cinématiques

- `ENDCRDIT`, `LOGO`.
- Sources entières cumulées143,566s (≈2min24s) ;1état `not-started` +ENDCRDIT `partial-paused` dans `index/status.csv`.13tutoriels exclus. POCKETZZ en attente de test ingame et anomalie DAYNITE restent suivis séparément.

## DAYNITE — chaîne conservée

`daynite.wbm` + SeedVR historique → frames30/114 à2/7,6s → imagesT2 → nuitT2 conservée + jourT4 généré depuis sa géométrie → H3 `MiniMax_H3_01604_-original.mp4` → `rebuild.py`/fondus corrigés → crop6lignes noires haut/bas → nearest1920×1080 → Apollo8/30fps → WBM VP8/Vorbis installé.

- Le graphe embarqué du H3 confirme les deux imagesT4 en entrée ; prompt exact conservé sous `../pipeline/recipes/video-retained-cleanup-20261110-v1/retained-h3-01604-prompt.api.json`.
- Entrées nearest relocalisées dans `daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1/` : MKV crop sans perte + AAC original extrait sans réencodage.
- ImagesT2/T4, sourceH3, montage, inputs nearest, nearest24, final30 et WBM installable conservés ; T1/T3, sens inverse, H3 antérieur et post-upscale SeedVR supprimés.

## Diagnostic ingame DAYNITE

- Retour utilisateur2026-11-10 : ancienne vidéo visible ; QA=`index/qa-decisions/daynite-ingame-old-video-reported-20261110-v1.json`.
- WBM installé conforme au SHA du runtime retenu ; aucun doublon prioritaire trouvé ; logs sans identifiant de film.
- Accès Computer Use/Baldur refusé : reproduction bloquée ; aucun nouveau remplacement spéculatif. Diagnostic/reprise=`../pipeline/recipes/daynite-runtime-diagnosis-20261110-v1/README.md`.

## Nettoyage2026-11-11 — terminé sans GPU

-141fichiers supprimés,14 631 402 684octets (~13,63Gio) :109fichiers projet (~11,75Gio),32entrées/sorties vidéo BG2 de ComfyUI (~1,87Gio).34contrôles de doublons CPU ; aucun décodage/inférence/GPU.
-748fichiers protégés inchangés :50sources,42finaux canoniques,preuves QA,sauvegardes,chaîne DAYNITE ouverte,candidat POCKETZZ et pause ENDCRDIT.5copies QA historiques (~1,47Gio) conservées. Jeu/release/autres projets intacts.
- Reçu : `index/cleanup-20261111-v1.json` ; inventaire courant/8alias de copies exactes supprimées : `index/retained-media-20261111-v1.json`. Manifestes/QA/reçus antérieurs inchangés ; comparateur courant sans référence aux suppressions.

## Nettoyage global

Analyse intros multilingues2026-11-10 :7sources natives,2films distincts ; tronc visuel partageable, cartons traduits séparés, INTRO15F polonais zoomé/recadré.2masters + cartons ≈62% d'images à inférer en moins (estimation, pas benchmark). Aucun traitement/sélection/QA/release lancé. Bilan : `../docs/validation/video-intro-locales-analysis-20261110-v1.json` ; recette : `../pipeline/recipes/video-intro-locales-analysis-20261110-v1/README.md` ; preuves locales : `research/intro-locales-analysis-20261110-v1/`.

-467fichiers supprimés,4 680 715 222octets ; gain net≈4,27Gio après relocalisation des entrées utiles et archivage des réglages.
- Essais FLYTHR03 nonLAB/Chronos/Aion, branches DAYNITE écartées,270frames et4MP4 POCKETZZ,36conversions WebM historiques et captures temporaires supprimés.
-50sources natives, résultats retenus, parents nécessaires et sauvegardes installées vérifiés par SHA256 ; aucun fichier du jeu ou de release modifié pendant ce nettoyage.
- Mémoire/réglages : `../pipeline/recipes/video-retained-cleanup-20261110-v1/settings-memory/` ; plan/reçu=`plan.json`/`cleanup.json` ; médias conservés et alias de chemins=`index/retained-media-20261110-v1.json`.
- Les run.json historiques archivés gardent leurs chemins et octets originaux ; les chemins retirés ne sont pas des productions manquantes à régénérer.
- Comparateur : `tools/comparator.html` ; uniquement sources, résultats retenus et étapes utiles encore présentes.
