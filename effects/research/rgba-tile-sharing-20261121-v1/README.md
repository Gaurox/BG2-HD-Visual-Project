# Mutualisation de tuiles RGBA non nulles

- Entrée géométrique `../rgba-tiles-20261121-v1/pack` ou `pack-live`. Le plan conserve les rectangles et les bitmaps des tuiles actives. Le générateur lit les couleurs uniquement dans les fichiers RGBA originaux.
- Identité `(largeur, hauteur, octets RGBA)` des tuiles, y compris les bords tronqués et le RGB sous alpha nul. Le hash répartit les tuiles et accélère la recherche. `memcmp` et les dimensions décident du partage. Recherche globale entre frames canoniques, après déduplication des frames. Vérification finale contre chaque fichier logique original, alias inclus.
- Dictionnaire des groupes dont le partage réduit les octets du flux. Référence u32 `1 + offset/4`. Les tuiles littérales et les rectangles denses conservent leurs octets RGBA. Chaque tuile de 4 octets reste littérale. Une tuile de 8 octets entre au dictionnaire à partir de trois occurrences.
- `IEETSHR1` lie le SHA-256 de `EffectTiles-X4.index`. En-tête `<8sII32s>`, enregistrements canoniques `<QQII>` (offset de flux, offset de bitmap, nombre de tuiles, nombre de références), puis bitmaps de partage little-endian. Les bits suivent les tuiles actives de gauche à droite et de haut en bas. Le flux contient une référence ou une tuile RGBA en ordre ligne. Une frame sans partage n'a pas de bitmap de partage. L’index de tuilage de base porte toujours géométrie et occupation.
- `results-release.json` / `results-live.json` mesurent les fichiers produits, dictionnaire et index inclus. Le registre et le manifeste identiques sont hors comparaison. Le pack d’essai reste hors du lecteur et de l’installeur.

```powershell
$sample = 'effects/research/rgba-tile-sharing-20261121-v1'
cmake -S $sample -B "$sample/build-parallel" -G 'Visual Studio 16 2019' -A x64
cmake --build "$sample/build-parallel" --config Release
python -B "$sample/build.py" build
python -B "$sample/build.py" build --live
python -B "$sample/build.py" verify
```
