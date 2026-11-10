# DAYNITE : ancienne vidéo signalée en jeu

- Retour utilisateur2026-11-10 : ancienne vidéo visible après installation ; QA ingame non acquise.
- Rapport physique : `diagnosis.json` ; collecte reproductible, lecture seule :
  `python -B pipeline/recipes/daynite-runtime-diagnosis-20261110-v1/collect.py --output <nouveau-rapport.json>`.
- SHA installé = runtime préparé = reçu : `f71b042e9e4cd1f3af6f78d42c1485511d49a5ae17a8aa90c0055c73029617c9`.
- WBM installé : VP8,1920×1080,30fps,300frames ; Vorbis natif ; durée conteneur10,292s.
- Aucun autre DAYNITE/NITEDAY dans les profils Documents, `override`, `lang` ; aucun dans `chitin.key`.
- `MOVIDESC.2DA` natif : DAYNITE→62087 ; NITEDAY→62086 ; `MVESND.2DA` ne remappe que ENDMVE1/2/3.
- Documents réel : `C:/Users/Adrien/Documents` ; `engine.lua` : `Baldur's Gate II - Enhanced Edition`,mode1 ; languefr_FR.
- Raccourcis bureau HD/InfinityLoader : `config://bg2ee_game_root/InfinityLoader.exe`,répertoire courant identique ; raccourci VANILLA distinct=`G:/AI/BG2_Vanilla_23534562/Baldur.exe`.
- Steamapp257350 : installé dans `G:/SteamLibrary/steamapps/common/Baldur's Gate II Enhanced Edition` ; loader `ExeNames=BaldurReal.exe,BaldurII.exe,icewind.exe,SiegeOfDragonspear.exe`.
- Logs moteur courants/rotations : aucun nom de film ni cheminWBM ; dernier log01:37:15local,après installation01:32:15local. Flags MOVIES du profil = films débloqués ; ne prouvent pas le film joué.
- Blocage : Computer Use a refusé le lancement de Baldur (`Computer Use was not approved to use baldur`). Aucun contournement/second lancement ; aucune reproduction visuelle possible cette nuit.
- Aucun correctif ingame établi ; aucun fichier du jeu remplacé à nouveau. DAYNITE et NITEDAY restent deux ressources distinctes ; ne pas remplacer NITEDAY/REST sans identifier celle réellement lue.
- Reprise : reproduire l'action exacte ; relever exécutable/dossier du processus et fichierWBM ouvert ; comparer lecture directe DAYNITE vs action observée ; seulement ensuite corriger la résolution/ressource prouvée et produire un nouveau reçu d'installation.
- Priorités de recherche documentées : [IESDP,override folders](https://gibberlings3.github.io/iesdp/appendices/override.htm) ; les chemins prioritaires contrôlés ne contiennent pas de doublon.
