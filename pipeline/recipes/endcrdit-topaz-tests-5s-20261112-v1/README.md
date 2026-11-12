# ENDCRDIT — essais Topaz 0–5s,2026-11-12

- Demande : plusieurs traitements exploratoires,texte lisible ;aucun traitement intégral/installation/release.
- Source `video/endcrdit/endcrdit.wbm`,1280×720/15fps ;75premières images seulement →1920×1080/15fps. Aucun interpolateur.
- `produce.py` : source décodée FFV1 RGB16,bT601 limited→RGB full ;Topaz local puis RGB→YUV420p bt709 limited H264CRF12. Même extrait audio AAC5s partout ;son source non modifié.
- R0 Lanczos ;R1 Spline+unsharp0.3 ;T1 Proteus neutre ;T2 Proteus doux/blend50% ;T3 Proteus détails/netteté ;T4 GaiaCG ;T5 GaiaHQ ;T6 ArtemisHQ ;T7 ArtemisMQ ;T8 Nyx1x doux+Lanczos ;T9 Proteus1x doux+Lanczos ;T10 Iris2.
- TopazCLI utilisé pour exposer les réglages manuels et dimensions que le connecteur ne permet pas de spécifier. Modèles locaux uniquement,téléchargement désactivé ;GPU0/VRAM0.8,une tâche à la fois.
- Médias/logs `video/endcrdit/runs/endcrdit-topaz-tests-5s-20261112-v1/` ;rapport final `metadata/production.json` :commandes,temps,SHA,dimensions/FPS/comptes. Les sorties ratées sont distinguées des clips vérifiés.
- Préfixe SeedVR historique rejeté et checkpoint ENDCRDIT restent immuables. Aucun candidat sélectionné sans validation utilisateur.

- Compléments :T8b Nyx3 doux1x ;T11 Iris3 ;T12=25%T1+75%R0 ;T13=50%T4+50%R0. T6 ArtemisHQ et T8 Nyx2 ont échoué localement avant toute image (logs conservés),non inclus dans la comparaison.
- `review.py` :2mélanges CPU,planche de crops à4s,montage séquentiel étiqueté14×5s ;suppression des seuls intermédiaires RGB après vérification MP4. Source/recette/logs/clips finaux conservés.
- Revue agent :T1/T2 compromis les plus prometteurs sur captures ;Gaia plus doux ;ArtemisMQ plus texturé ;Iris3 reforme notamment des petites lettres. Aucun verdict utilisateur déduit,stabilité en mouvement à valider.

- Décision finale utilisateur2026-11-12 :T1 seul retenu pour production complète +Apollo30 ;secondes passes/SeedVR7B non sélectionnés. [Production/install/QA courantes](../endcrdit-proteus-T1-apollo30-20261112-v1/README.md). Les états pending des rapports expérimentaux restent des instantanés historiques.
