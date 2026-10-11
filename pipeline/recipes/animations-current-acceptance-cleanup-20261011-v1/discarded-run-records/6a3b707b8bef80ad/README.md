# AM0205A — interpolation temporelle x4

Statut : **validé en jeu le 2026-08-21**. Les 9 frames BAM source sont
remplacées de façon réversible par 27 frames runtime x4 à 15 FPS pour conserver
la boucle de 1,8 s. Le patch conserve également l'interpolation déjà validée
de `AM0205E`.

Référence à transmettre à l'outil d'interpolation :

[`01_handoff/AM0205A-x4-source.mp4`](01_handoff/AM0205A-x4-source.mp4)

Contrat de retour :

```text
27 PNG contigus
480x700 px
15 FPS
1,8 seconde
pas de première frame dupliquée à la fin
alpha non requis
```

Le `handoff.json` conserve les hashes et la chaîne de registre qui préserve
l'interpolation validée de `AM0205E`. Le correctif alpha validé ensuite est
isolé dans `../AM0205A-pod-canvas-feather-x4/` : fade de canvas 32 px x4,
RGB inchangé, sur les 27 frames.
