# ENDCRDIT — secondes passes sur T1,2026-11-12

- Utilisateur :T1 préféré/accepté puis demande de comparer des secondes passes ;scope extrait0–5s uniquement. QA immuable `video/index/qa-decisions/ENDCRDIT/20261112-topaz-T1-first5s-visual-accepted-v1.json` ;aucune validation du film entier.
- Base exacte :MP4 T1 accepté de `endcrdit-topaz-tests-5s-20261112-v1`,SHA contrôlé ;aucune réinférence première passe. Décodage RGB16 depuis bt709 limited ;toutes sorties1920×1080/15fps/75images,audio T1 copié ;aucune interpolation.
- `produce.py` :P1 Proteus1x neutre ;P2 Proteus1x très doux/blend50% ;P3 antialias léger ;P4 détails0.15/netteté0.08/blend25% ;P5 Nyx3 doux1x ;P6 GaiaCG x2/réduction ;P7 ArtemisMQ x2/réduction ;P8 Proteus doux x2/réduction ;P9 unsharp0.25 sans IA supplémentaire.
- `review.py` :B0 copie binaire T1 témoin ;P10=50%P4+50%T1 ;P11=25%P1+75%T1 ;planche crops4s ;montage séquentiel5s par variante.
- Topaz local,GPU0,VRAM0.8,une tâche à la fois,download0. Intermédiaires FFV1 RGB16 supprimés après MP4 contrôlé ;base/logs/commandes/SHA conservés.
- Médias `video/endcrdit/runs/endcrdit-topaz-second-pass-5s-20261112-v1/` ;rapport `metadata/production.json`. Secondes passes en attente de QA utilisateur ;T1 reste accepté même si aucun complément ne gagne. Préfixe SeedVR/checkpoint inchangés ;pas de reprise intégrale/installation/release.

- Résultat :11candidats+T1 témoin,tous75images/FullHD15 ;montage12×5s=60s. Audio encodé identique à T1 pour les11candidats.
- Revue captures4s :gain limité ;P4 et P8 à comparer pour contours légèrement renforcés ;P10 option plus modérée. Aucun vainqueur évident sur lisibilité ;ne pas remplacer automatiquement T1. QA mouvement/utilisateur en attente.

- Décision finale utilisateur2026-11-12 :T1 seul retenu pour production complète +Apollo30 ;secondes passes/SeedVR7B non sélectionnés. [Production/install/QA courantes](../endcrdit-proteus-T1-apollo30-20261112-v1/README.md). Les états pending des rapports expérimentaux restent des instantanés historiques.
