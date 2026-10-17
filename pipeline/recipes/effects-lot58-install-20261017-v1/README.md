# Lot58 — installation / CLUA

- Entrée scellée : `effects/batches/lot58-seedvr7b-apollo30-20261016-v1/{batch,verification,production}.json`.
- Candidat/reçu : `effects/installations/lot58-7b-x4-nearest30-20261017-v1/`.
- Commandes : `python -B pipeline/recipes/effects-lot58-install-20261017-v1/install.py prepare`, puis `install` ; jeu/InfinityLoader fermés.
- 161 ressources actives conservées (registre v3 et pixels) +58 BAM +2 alias normaux =219 assets /221 RESREF runtime ; DLL streaming active conservée par SHA256.
- DLL+INI actifs conservés octet pour octet. Métadonnées natives :15470842octets (<16Mio) ; budgets CPU/GPU/in-flight inchangés.
- Tables v3 ponctuelles ajoutées depuis les phases scellées ; SPFLAST1 : table primaire ponctuelle 8→30,34 phases sur9/8s, aucune table alternative incompatible.
- RGB droit : MINORGLB,OHBGOLD,SPSTURNI,SPSKULLT,BDWOFOGA,SPCLOUDK,SPCLOUDS,SPDFOGA. Compagnons droits déjà scellés ; aucune nouvelle inférence.
- Deux consommateurs VVC normaux mixtes : SPFIRSD2 → X58SDI, SPFLMBLD → X58BLD. Seul le champ BAM `[8:16]` change ; alias BAM = même carrier natif/padding. Contrôleurs lumineux restent sur le RESREF original.
- VVC `Z580001…` :397 profils isolés,15FPS (SPFLAST1:8), ponctuels ou boucles bornées ≥4s. Aucun dégât, son, trajectoire ou orchestration PRO reproduit ; choix principal = profil visible de la galerie.
- CLUA58 : `CLUA.md`; cycles/modes397 : `CLUA-tous-profils.md`; contrats machine : `runtime-contracts.tsv`.
- Transaction : mêmes sauvegardes/empreintes/restauration pour BAM,VVC,registre,RGBA,DLL,INI. Installateur étendu aux VVC explicitement déclarés/hashés et noms RGBA à3/4 chiffres.
- Intégrité : chaque copie candidat/sauvegarde hashée pendant préparation ; toutes les cibles installées hashées avant statut `installed`. Seconde relecture complète `verify_transaction` non répétée ; finalisation = empreintes DLL/INI/shaders/manifeste +résolveur natif. Reprise après installation déjà accomplie : `runpy.run_path(.../install.py)['finish'](Path(<reçu>))`.
- Vérification :19 tests transactionnels ; lecteur natif streaming `--catalogue-only` sur candidat puis jeu (résolutions de toutes phases, zéro lecture RGBA dans ce mode). Premier essai à plafond32Mio conservé dans le log initial ; contrôle final au plafond actif16Mio. Pixels vérifiés séparément par SHA256 de la transaction.
- QA visuelle non acquise ; cadence PRO15FPS = défaut de compatibilité, mesure ingame distincte. Les CLUA isolés ne prouvent pas la couverture de chaque classe projectile, ombre, trajet ou dispersion par les hooks actuels.
- Installation seule ; aucune sélection QA ni release.
- Formats : [VVC](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/vvc_v1.htm), [PRO](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/pro_v1.htm). Flags natifs conservés ; choix RGB selon le contrôleur, à apprécier visuellement en jeu.
