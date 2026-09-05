# Colonne gauche — x4 Topaz Recovery v2 Detail 50

Lot réversible pour les 17 boutons de `GUILS10.BAM` et leurs quatre états. Les coordonnées des BAM ne changent pas : seuls les atlas DXT5 sont remplacés par leur version x4, puis affichés à la taille native de l'interface.

Ressources couvertes :

- `MOS0140.PVRZ` → `HUD-MOS0140-x4.dxt5` (1024² → 4096²) ;
- `MOS0141.PVRZ` → `HUD-MOS0141-x4.dxt5` (512² → 2048²).

Réglages : Topaz Gigapixel 8.4.1, **Recovery v2**, **Detail 50**, x4, couleurs préservées, DXT5.

`build_left_toolbar_x4_atlases.py` extrait les atlas originaux ou conditionne les exports Topaz. `Run-Topaz-RecoveryV2-D50-X4.ps1` relance l’upscale. Les deux aperçus PNG et les deux payloads DXT5 finis sont dans `assets/`.

Jeu fermé, `Install-Left-Toolbar-X4-Topaz-RecoveryV2-D50-Test.ps1` installe le DLL mis à jour et les deux payloads, en créant une sauvegarde horodatée. `Restore-Left-Toolbar-X4-Topaz-RecoveryV2-D50-Test.ps1 -BackupPath <dossier>` restaure exactement l’état précédent.

Ce lot nécessite `EnableMainMenuX4Test = true` dans `InfinityEngine-Enhancer.ini`, déjà actif dans la configuration validée du menu x4 ; ce drapeau charge les atlas UI statiques enregistrés.
