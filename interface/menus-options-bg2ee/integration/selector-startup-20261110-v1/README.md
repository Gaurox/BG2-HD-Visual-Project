# Sélecteur x4 — correction et installation locale, 2026-11-10

- Empreintes : `MOS0182/0183/0184/0185/0259` corrigées contre le payload DXT5 natif.
- Activation `[Shaders] EnableSelectorX4=true` : seules les 7 pages de l'overlay ;
  flags globaux menus, BIGLOGO, HUD inchangés. Pages 0181/0258 partagées avec d'autres compositions.
- Chargement : hook `CResPVR::Demand` validé par manifeste/signature ; interception
  `glCompressedTexImage2D` installée **avant** l'appel natif, sur le thread possédant le contexte GL.
  Pas d'attente de SwapBuffers, pas de throttling ; reprise sur demande suivante si contexte absent.
  Installation dédiée au seul upload compressé ; initialisation shader/eau conservée.
- Sources graphiques et atlas existants inchangés ; boutons inférieurs/polices non régénérés.
- Aucun payload/staging/TP2/manifeste release modifié. Audit antérieur conservé dans `../../analysis/`.

## État installé

- Reçu : `backup-20261110T212208Z/receipt.json` ; DLL/INI antérieurs à côté, ignorés par Git.
- DLL : `build/iee-selector-startup-20261110-v1/Release/InfinityEngine-Enhancer.dll`.
- SHA256 installé : `ee2eef18753665ea41cb1f2f87cf7890a62f6accbb68d508e76f31203486b333`.
- INI : insertion unique `EnableSelectorX4 = true` ; retrait de cette ligne = octets antérieurs exacts.
- 7/7 atlas installés : SHA256 inchangés, consignés dans le reçu.
- Jeu/InfinityLoader fermés avant remplacement ; installation transactionnelle.

## Vérification

- Build DLL + `iee_menu_upscale_tests` + `iee_tests` : MSVC v142, Release x64, réussi.
- `iee_tests` : réussi via CTest.
- `iee_menu_upscale_tests.exe <fixtures>` : 7 payloads natifs acceptés ; pages BIGLOGO/HUD/autre-menu
  exclues ; empreinte/format/dimensions incorrects refusés ; désactivation/libération/config isolée vérifiées.
- Fixtures DXT5 natives extraites des BIF en lecture seule : `build/.../native-fixtures/`.
- Contrôle natif au démarrage : session `2026-11-10 22:25:37.177`, lancement manuel.
  Hook GL prêt `22:25:40.925` ; pages `0258/0259/0181/0182` remplacées dès `22:25:42.133–142`.
- QA visuelle utilisateur : « c'est ok », 2026-11-10 ; décision et octets dans `accepted-20261110-v1.json`.
  1 démarrage observé ; survol ToB/MOS0183 non observé séparément ; pas de statut release déduit.

```powershell
python -B interface/menus-options-bg2ee/integration/selector-startup-20261110-v1/verify_session.py
# État normal : 4 pages remplacées, 7 préparées, hook avant premier remplacement.
# MOS0183 concerne le survol ToB (frame 1) ; son absence au démarrage normal est attendue.
```

## Restauration exacte, jeu fermé

```powershell
python -B interface/menus-options-bg2ee/integration/selector-startup-20261110-v1/install.py --restore interface/menus-options-bg2ee/integration/selector-startup-20261110-v1/backup-20261110T212208Z/receipt.json
```

Refus si DLL/INI ont changé depuis l'installation ; ne pas écraser une nouvelle modification utilisateur.
Réinstallation depuis une DLL compilée : `install.py --dll <DLL>` ; nouveau snapshot distinct.
