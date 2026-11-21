# Essai de rognage RGBA x4

- Alpha.10 · `BDFORCEW`, `SPRDRABU`, `Y31N058`, `Y31N059`, `Y31P059`.
- Rectangle serré autour de tous les pixels RGBA non nuls. Pixels stockés bruts. Reconstruction sur canevas original rempli de zéros.
- `pack/frames.index` associe ID physique, dimensions, rectangle et offset. L'en-tête épingle le registre et l'index de partage existants. La table logique conserve les 23 références partagées.
- `results.json` consigne les tailles mesurées et les SHA-256. Le lecteur a comparé 969 reconstructions aux octets originaux et vérifié les 992 références logiques.
- 3 223 522 368 → 906 798 104 octets, index de 31 272 octets inclus. Gain net de 2 316 724 264 octets.
- Essai local autonome. Le format reste à intégrer et à qualifier côté renderer.

```powershell
python -B effects/research/rgba-crop-pilot-20261121-v1/pilot.py verify
```
