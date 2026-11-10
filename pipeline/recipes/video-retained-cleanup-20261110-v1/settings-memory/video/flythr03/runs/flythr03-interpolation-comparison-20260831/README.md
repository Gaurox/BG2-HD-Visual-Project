# Prototype interpolation Topaz 30 fps

État : `completed`. Apollo 8 sélectionné ; comparaison non canonique.

| Fichier | Modèle | `rdt` | Frames Topaz | Doublons exacts retirés | Frames finales | Durée |
|---|---:|---:|---:|---:|---:|---:|
| `FLYTHR03-30fps-01-apollo-v8-rdt001.mov` | Apollo 8 | 0.01 | 517 | 0 | 517 | 17.233 s |
| `FLYTHR03-30fps-02-apollo-v8-rdt010.mov` | Apollo 8 | 0.10 | 521 | 9 | 512 | 17.067 s |
| `FLYTHR03-30fps-03-chronos-v2-rdt005.mov` | Chronos 2 | 0.05 | 523 | 5 | 518 | 17.267 s |
| `FLYTHR03-30fps-04-chronos-fast-v3-rdt005.mov` | Chronos Fast 3 | 0.05 | 523 | 5 | 518 | 17.267 s |
| `FLYTHR03-30fps-05-aion-v1-rdt005.mov` | Aion 1 | 0.05 | 515 | 1 | 514 | 17.133 s |

Contrat : 1920×1080, CFR 30 fps, progressif, ProRes 422 HQ test, sans audio, zéro doublon exact
adjacent final. `rdt>0` traite aussi les quasi-doublons ; la durée varie. Ne pas promouvoir avant
choix visuel. La recette canonique retenue désactive `rdt` et conserve le post-traitement exact.

Preuves et hashes : `trials.json`. Reproducteur : `run_trials.py`.
