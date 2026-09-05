# Sélecteur des trois jeux — Recover v2, Detail 50, x4 — validé

Extension validée en jeu de la variante `../`. Elle traite l'écran `START3EE` présentant *Shadows of Amn*, *Throne of Bhaal* et *The Black Pits II*.

## Éléments

- `START3EE.MOS` : fond complet, couvertures, grands titres imprimés et décor ; source unique `START3EE-background-x1.png`.
- `LOGOTOB.BAM` : deux états de l'emblème *Throne of Bhaal*.
- `LOGOTBP.BAM` : deux états de l'emblème *Black Pits II*.
- `MAINEEAN.BAM` : douze libellés et états (Play / Tutorial / Black Pits).
- `LOGOSOA.BAM` et les boutons `STARTMBT.BAM` réutilisent les exports Recover v2 x4 déjà validés dans le menu principal ; ils ne sont pas régénérés.

Les 17 nouvelles sources sont sous `topaz-input-x1/`; leurs exports Topaz sont sous `upscale-topaz-recovery-v2-d50/`. `build_selector_x4_atlases.py` fusionne les nouvelles zones avec `MOS0181` et `MOS0258` déjà traités, puis génère les pages complémentaires `MOS0182`, `MOS0183`, `MOS0184`, `MOS0185` et `MOS0259` dans `assets/`.

Le script de traitement emploie Topaz Gigapixel 8.4.1, **Recover v2**, **Detail 50**, x4, PNG RGBA et couleur préservée. Il est réexécutable sans écraser les exports existants.

`Install-Selector-X4-Topaz-RecoveryV2-D50-Overlay-Test.ps1` installe les pages supplémentaires, les deux atlas fusionnés, la DLL étendue et la configuration x4. Il sauvegarde l'état précédent ; `Restore-Selector-X4-Topaz-RecoveryV2-D50-Overlay-Test.ps1` restaure cette sauvegarde jeu fermé.

La variante est validée avec les 17 nouveaux exports et les sept atlas de l'overlay installés. Une prochaine capture du sélecteur peut être archivée dans `captures/` comme référence finale.
