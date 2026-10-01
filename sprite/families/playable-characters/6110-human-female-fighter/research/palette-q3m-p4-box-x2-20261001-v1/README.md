# P4 — x2 + BOX, candidat 2026-10-01 v1

- Demande utilisateur : « ok installe x2 et BOX uniquement » ; extension explicite du filtre BOX x4 vers x2. Aucun essai Catmull-Rom/Mipmaps x2 ajouté.
- Installation réelle : `installation-verification.json` ; catalogue x2 existant SHA256 `5F0596DDAC14ECDBFD1915978736C160DF1F7F465156472FD410A8705CDC6044`, 1 312 shards V6 vérifiés, 358 697 frames. Aucun I/F, BAM, palette, cycle, géométrie, sauvegarde ou asset release réencodé/modifié.
- Catalogue partagé : **0x6100 + 0x6110 en x2** ; filtre **BOX sur 0x6110 seulement**, 0x6100 reste Nearest. Aucun autre acteur ajouté. Le format impose une échelle commune à ses routes ; ni catalogue mixte x2/x4 ni retrait de route.
- Nouveau runtime : `pipeline/runtime/manifests/iee-sprite-p4-box-x2-20261001-v1.json` ; DLL SHA256 `400B54F7D0F10B9182C11AF074D77B8F705CCA4D2CAF2286A03CF1161C5172CC`, 1 965 568 octets. BOX autorisé en x2/x4 ; Mipmaps garde son périmètre x4. Mipmaps désactivé dans la configuration installée.
- Shaders fpDraw/fpSprite/fpSELECT identiques au candidat P4 précédent ; RGBA droit, MAX_LEVEL=0, MIN=MAG=NEAREST, intégrale BOX explicite dans le shader. Masque natif utilise BOX avec la même provenance ; aucune chaîne mip générée.
- Modification C++ : `TextureRegistry::effective_mode` accepte BOX pour les échelles 2/4 ; garde de périmètre animation conservée. Test publication composite/masqué x2 → décision shader mode=3, scale=2 ; échelle invalide et autre animation → Nearest.
- Installateur catalogue : accepte BOX seulement si runtime déclare `box_scales`, contrat shader V1, trois shaders installés conformes et route 0x6110 ; INI/reçu fixent `CreatureSpriteFilterAnimation=0x6110`.
- Vérifications : `verification.json` ; CTest 4/4, 24 tests Python installateur (incluant capacité x4 seule refusée et dérive shader refusée), transaction complète sur copie locale avec 1 312 shards, refus de dérive utilisateur, restauration exacte DLL/INI/catalogue. Oracles GPU précédents réutilisés : mêmes octets shaders, empreintes/magnification/alpha et masque uScale=2 déjà couverts. Aucun jeu lancé/contrôlé.

## Installation active / retour

Depuis la racine du dépôt, jeu et InfinityLoader fermés :

```powershell
$p4x2 = 'sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p4-box-x2-20261001-v1/install.ps1'
& $p4x2 -Mode Verify
& $p4x2 -Mode Restore
```

- `install.ps1` : transaction runtime + catalogue via installateurs existants, backups sous `ingame-installation/`, bascule BOX et sonde. Verify contrôle hashes DLL/INI/catalogue/reçu/shaders et tous les shards ; Restore refuse toute dérive avant remplacement.
- Reçu actif x2 : `ingame-installation/active-test.json` ; couplage exact DLL/INI/catalogue : `ingame-installation/box-state.json`. Historique `installation-verification.json` immuable.
- Retour exact : **x4 + Mipmaps** précédent ; SHA DLL `D96B9E86B7840339B3C3DFBFFBCBD4FC9A37AC8FDEFCEAB33EEB4CD532795D5E`, INI `6505D1497031CD5D9DABB926FBB9355AB5FE0EC45C7EF15311BD08ED38A38111`, catalogue `637DBC809EAD7A9AD2A771BB760F5C0042109C5A4B6A19BE68A75CC41D50E0B8`. Shaders et reçus P4 v1 antérieurs conservés intacts ; leur ancien Verify/Select doit refuser pendant x2 (DLL/catalogue divergents). Restaurer via le nouveau wrapper avant réutilisation.
- Captures conservées : anciennes BOX/Mipmaps x4 ; nouvelles sous `captures/box-x2/p4-*.csv`, sonde mode=3 attendue, scale=2, MAX_LEVEL=0. Mesure uniquement après signal utilisateur.

## Essai utilisateur

1. Même sauvegarde/scène/équipement ; fenêtre de même taille ; attendre 10 s après entrée du monde, sans pause.
2. Maximum en butée : immobile 20 s.
3. Maximum −7 crans : immobile 20 s.
4. Minimum en butée : immobile 20 s.
5. Revenir au maximum, attendre stabilisation puis −7 crans ; marcher 20 s, puis avatar immobile/panoramique caméra 20 s en gardant l'avatar visible. Garder le même zoom pour ces deux phases (retour Mipmaps précédent différent).
6. Quitter jeu et InfinityLoader ; avis détail/contours/scintillement et signal autorisant la mesure.

- Au zoom habituel précédent ~2.48 : empreinte x2 ≈0.806 texel/pixel écran, magnification Nearest ; BOX agit en réduction aux zooms plus faibles. Au minimum précédent ~0.823 : empreinte x2 ≈2.43, réduction BOX.
- QA ingame x2 BOX et décision P4 finale **en attente** ; P3 acceptée conservée, aucune QA/release déduite des tests techniques. Source documentaire précédente et bilans x4 immuables.
