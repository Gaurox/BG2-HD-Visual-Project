# ReboutCX — mesure famille 0x5211 (2026-09-15)

- Famille : elfe femme mage, variante basse ; **65/65 composants produits et vérifiés**.
- P9 : **804.981 s** ; **181.45 frames modèle/s**.
- P10 : **437.261 s** ; **334.05 frames modèle/s**.
- Gain retenu sur cette famille : **×1.841** ; durée **−45.68 %** ; **367.72 s économisées**.
- Inventaire identique : 180 494 frames source, 146 066 frames réellement inférées ; SHA des sources et ensembles RESREF identiques.
- Paramètres P10 : 3 composants, 2 workers préparation, 3 workers BOX/quantification, 1 modèle GPU persistant, 1 worker vérification, plafond 86, canvas 64, réservations ressources 4 096 Mio.
- Budget 4 096 Mio nécessaire : ressource maximale estimée 2 692,1 Mio, supérieure au défaut 2 048 Mio ; maximum réservé mesuré 4085.3 Mio.
- Chargement modèle unique : 8.358 s. Somme CUDA modèle : 347.606 s. Les autres sommes de phases se chevauchent.
- Périmètre temporel : lancement → dernière vérification ; préparation des jobs exclue. P9 reconstitué depuis les logs historiques (précision ≈1 s), P10 chronométré. Mesure unique, comparaison historique.
- Pixels P10/P9 non équivalents : correction RGB 0–255 → 0–1. Aucune validation humaine/ingame déduite.
- P8/P9, catalogue global, QA, installation et release inchangés. Calcul arrêté après cette seule famille. Aucun arrêt du PC programmé par cette mesure.

## Preuves

- Mesure + manifests/SHA : `throughput-p10-v1.json`.
- Référence P9 + manifests/SHA : `p9-reference-v1.json`.
- Session P10 : `sprite/.work/reboutcx-p10-production/session-1789453658358315600.jsonl`.
- Queue bornée à cette famille : `sprite/families/playable-characters/5211-elf-female-mage-low/family-runs/complete-reboutcx-p10-v1/jobs/elf-female-mage-low-p10-throughput-v1.json`.
