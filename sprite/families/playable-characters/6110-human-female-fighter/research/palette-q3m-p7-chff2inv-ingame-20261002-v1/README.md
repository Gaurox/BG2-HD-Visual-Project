# P7 — pilote ingame CHFF2INV cuir Q3m K6 x2

- État 2026-10-02 : **installé et vérifié ; dessin HD effectif/QA utilisateur à confirmer dans une nouvelle session**.
- Ajout : `CHFF2INV` seulement, deux moitiés, x2/Nearest sans mipmaps ; Bitmap natif, géométrie/centres/source/clip128×160 conservés ; contrat divergent → natif.
- CHFF1INV : plans/paquet préservés exactement ; nouveau runtime lit chaque corps avec son SHA source, ses plans et deux textures distinctes. Les autres corps restent natifs. Aucune nouvelle QA CHFF1INV déduite.
- Monde : catalogue et shaders inchangés, x2+BOX `0x6110` conservé ; aucune release modifiée.
- Paquet : `work/CHFF2INV-Q3m-X2.registry`, 74 028 octets ; `pack.json` fixe les entrées/hashes. Oracle = 64 palettes **natives CHFF1INV historiques**, réutilisées pour vérifier le décodeur cuir ; aucune capture CHFF2INV live encore acquise.
- Contrôles : `iee_tests` PASS (cwd moteur) ; tests paperdoll sur chacun des deux paquets = 128 décodages BGRA exacts/corps, rejets troncatures/contrats/identité croisée ; install/Verify/Restore fixture exact, dérives INI/pack/baseline et override refusées, ancien paquet CHFF1INV intact (`verification.json`).
- Runtime : `pipeline/runtime/manifests/iee-sprite-p7-chff2inv-q3m-20261002-v1.json` ; build `build/sprite-p7-chff2inv-q3m-20261002-v1/cmake`.
- Installation : `installation-verification.json` copie figée ; reçu actif/backups sous `ingame-installation/`. Seuls DLL/INI et nouveau paquet cuir écrits ; baseline restaurable = **pilote CHFF1INV validé**, pas sonde P7v2. Ne pas employer l'ancien installateur pour restaurer le nouveau candidat.

## Essai

1. Lancer normalement avec InfinityLoader ; charger la guerrière humaine `0x6110`.
2. Équiper une armure de cuir simple ; retirer arme/bouclier/casque pour isoler le corps ; ouvrir l'inventaire.
3. Observer détails, taille/position, contours et raccord taille ; changer quelques couleurs contrastées puis fermer le sélecteur.
4. Retirer/remettre le cuir, fermer/rouvrir l'inventaire : corps sans armure HD conservé, cuir HD attendu ; aucune contamination entre corps/couleurs.
5. Quitter jeu et InfinityLoader ; signaler résultat. Journal attendu : `P7_Q3M_PACK ready: CHFF2INV` et `P7_Q3M_DRAW resref=CHFF2INV … bound=true` slots0/2, palette/pixel CRC vérifiables aux plans. Preuve technique ≠ QA visuelle.

```powershell
./install.ps1 -Mode Verify
./install.ps1 -Mode Restore # jeu/InfinityLoader fermés ; retour exact pilote CHFF1INV
```
