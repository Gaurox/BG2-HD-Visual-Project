# DAYNITE — essai du sens temporel SeedVR

- Demande utilisateur : palissades mauvaises de jour, meilleures de nuit ; essayer l'inférence fin→début.
- Essai contrôlé : nouveau témoin direct ET passe inverse avec le même nœud SeedVR2 installé2.5.24, modèle3B FP16,seed42,LAB,batch33uniforme,overlap3,swap32,SDPA,bruits0,VAE encode1024/128 decode768/128. Ancien direct vient du nœud2.5.22 : comparaison historique seule confondrait version et direction.
- Workflows exacts : `forward-workflow.api.json`, `reverse-workflow.api.json`. Sortie ComfyUI ProRes MOV identique des deux côtés ; audio omis pendant l'inférence.
- Source : `video/daynite/daynite.wbm`,150frames/15fps/1280×720 ; deux MKV FFV1 YUV420 sans perte, `setpts=N/(15*TB)` et `reverse,setpts=N/(15*TB)`. Hashes des150frames décodées vérifiés identiques natif/direct et natif[::-1]/inverse (`source-check.json`).
- Prompts ComfyUI MCP : direct `7218388b-3133-4f47-ab3a-a14b51c82707`, inverse `4235a2d3-90b3-4e3b-8aa7-76cdc753f4fe` ; exécution sérialisée par ComfyUI. Attendre la fin des deux avant de lancer Topaz pour éviter la concurrence VRAM.
- Run : `video/daynite/runs/daynite-seedvr-direction-20261109-v1/` ; `forward-production.json` et `reverse-production.json` = hashes, commandes, sondes et contrôles.
- `finish.py forward|reverse` : remet la sortie inverse dans le sens jour→nuit, garde le direct dans son sens ; PTS15fps, audio natif complet remis ensuite ; x264CRF16/slow, BT709 limité cohérent pour les deux. Pas d'inversion de l'audio.
- Chaque sens : preview SeedVR15 et Apollo8 (`apo-8`,30fps,slowmo1,rdt−0,01) ;150→299frames ; flux AAC15/30 identique. Masters FFV1 Apollo temporaires supprimés après contrôle.
- Vérifications : courbe de luminance des150frames comparée au sens source (indicateur, avertissement si corrélation≤0,9 ; ne pas rejeter un changement de lumière dû au modèle), dimensions/fps/comptages, intermédiaires centraux distincts des voisins, audio identique.
- `add_comparator.py` : quatre nouveaux choix DIRECT/INVERSE ×15/30 ; anciens rendus conservés. Tous les fichiers proposés en lecture normale jour→nuit. Commencer par DIRECT30 à gauche, INVERSE30 à droite ; puis15/15 pour isoler SeedVR.
- Inspecter les mêmes instants :1,5s et3,5s (jour),8,5s (nuit). La direction change aussi les frontières des batches et l'affectation du bruit au temps physique malgré une seed identique ; ne pas conclure à une propagation causale depuis la nuit seule.
- Essai en attente utilisateur ; aucun fichier du jeu, sélection acceptée ou release modifié. Préserver les rendus historiques.
- Résultat technique : deux passes terminées ;150frames15fps/299frames30fps, audio identique entre les quatre rendus, sens jour→nuit conservé. `comparison-check.json` et `comparator-direct-inverse.png` dans le run ; lecture30/30 synchronisée vérifiée dans le navigateur.
- Observation provisoire sur captures1,5/3,5/8,5s : l'inversion change certains détails ; les taches claires des palissades persistent de jour, pas de correction évidente. Comparaison en mouvement laissée à l'utilisateur ; `palisades-direct-inverse.jpg` = source/direct/inverse aux mêmes instants.
