# P7 — pilote ingame CHFF1INV Q3m K6 x2

- Périmètre utilisateur : corps guerrière humaine sans équipement `CHFF1INV` uniquement ; deux moitiés natives, aucune armure/arme/autre famille produite.
- État : candidat installé et vérifié le 2026-10-02 ; dessin HD effectif et QA visuelle **en attente de nouvelle session utilisateur**. La session native précédente valide le contrat palette/géométrie, pas ce routage HD.
- Entrées immuables : [plans Q3m existants](../palette-q3m-p7-chff1inv-20261002-v1/README.md), [mesure native](../palette-q3m-p7-ui-measurement-20261002-v1/README.md). `build-pack.py` assemble les NPZ ; 0 inférence ; `pack.json` fixe hashes du paquet/oracle.
- Paquet autonome `work/CHFF1INV-Q3m-X2.registry` → `iee-assets/paperdolls/CHFF1INV-Q3m-X2.registry`, 74 028 octets ; V6 brut, profil1/règle1, source SHA `7362904c…da86d8a`, cycle `[0,0,1,1]`.
- Runtime [manifeste](../../../../../../pipeline/runtime/manifests/iee-sprite-p7-chff1inv-q3m-20261002-v1.json) : DLL `5686D1FC…021B1` ; INI `B037C327…C556A` ; `EnablePaperdollQ3mTest=true` et sonde native conservée.
- Contrat natif : capture Realize corrélée à la même CVidCell/slot, type1/256/BGRA8888_REV ; vérification palette au dessin ; taille/centres/source/clip128×160/placement/flags`0x4005`/Bitmap6 inchangés. Échec → rendu natif.
- GPU : descriptor logique x1, backing x2 ; deux textures mutables ; flush natif validé avant toute actualisation de palette ; restauration du binding/unpack après upload et du binding après dessin. Aucun octet BAM ni champ de sauvegarde modifié.
- Filtrage **UI : Nearest, aucun mipmap** ; chemin Bitmap natif, aucun branchement fpSprite/BOX UI. BOX reste la réduction des cibles neuronales avant Q3m. **Monde : x2+BOX inchangé** ; catalogue et shaders contrôlés, jamais remplacés.
- Vérifications : `iee_tests` 1/1 ; `iee_paperdoll_q3m_tests` = lecteur strict/rejets malformed+truncated et 128 décodages BGRA octet-exacts contre palettes réelles ; `verification.json` = installation/Verify/Restore sur fixture, restauration DLL/INI exacte, retrait du seul paquet UI, refus dérives INI/pack/baseline et overrideCHFF1INV.
- Installation : `installation-verification.json` = copie figée du reçu ; reçu actif et backups locaux `ingame-installation/active-test.json` + `previous-InfinityEngine-Enhancer.{dll,ini}`. Baseline restaurable = sonde native P7v2 ; ancienne transaction v2 est désormais supersédée par ce pilote, sans réécriture de sa preuve.
- Aucune QA utilisateur déduite, aucune release modifiée, aucun contrôle PC, aucun commit automatique.

## Essai manuel

1. Lancer normalement le jeu avec InfinityLoader ; charger la guerrière humaine.
2. Retirer l'équipement ; ouvrir inventaire, observer taille/placement, raccord taille, contours/fond et détails du corps.
3. Essayer quelques couleurs contrastées (vêtements/peau/cheveux) ; fermer le sélecteur pour regarder la figurine ; fermer/rouvrir l'inventaire et vérifier leur conservation.
4. Quitter le jeu et InfinityLoader, signaler fin de session et anomalies éventuelles.

Preuve runtime attendue : `P7_Q3M_PACK ready`, `P7_Q3M ready`, `P7_Q3M_DRAW … bound=true` pour slots0/2 ; `colors`, `paletteCrc32`, `pixelCrc32` vérifiables avec les plans. Logs bornés à64 clés palette/slot/contrat ; pas de preuve exhaustive de toutes les combinaisons.

## Commandes ciblées

```powershell
# depuis ce dossier ; GameRoot passe par config://bg2ee_game_root
./install.ps1 -Mode Verify
./install.ps1 -Mode Restore # jeu et InfinityLoader fermés ; sonde P7v2 exacte
```

Build ciblé : `build/sprite-p7-chff1inv-q3m-20261002-v1/cmake` (VS16/2019 x64, deps locales P2), cibles `InfinityEngine-Enhancer`, `iee_tests`, `iee_paperdoll_q3m_tests`. Test pilote : `iee_paperdoll_q3m_tests.exe <paquet.registry> <work/measured-palettes.oracle>`. Reproduction des artefacts : nouveau run frère, aucune réécriture des preuves de ce run.
