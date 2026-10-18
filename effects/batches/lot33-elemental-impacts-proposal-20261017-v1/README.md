# Proposition lot33 — impacts, jets et particules élémentaires

- Proposition seulement ; aucune production, QA, installation ou release modifiée.
- **33productions distinctes /36RESREF**,1107enregistrements source,91cycles,1311slots natifs (cycles alternatifs, pas une durée globale),449657344octets RGBA x4 avant interpolation/déduplication.
-33BAM disponibles/hashés et visuellement inspectés ; aucune production commencée ; hashes déjà produits et animations acceptées exclus.33références exactes présentes dans `BaldurReal.exe` (insensibles à la casse, bornes de chaînes vérifiées), SHA/offsets dans `batch.json`. Ces références ne prouvent pas leur exécution dans une session particulière.
- L’index VVC/PRO marque encore ces33sources `unresolved` : leurs usages natifs codés dans l’exécutable échappent à ce graphe. Preuve locale dans cette proposition ; index source global inchangé.
- Alias : SPBRNHND→BURNHAND ; SPPRISM2→SPPRISM3/SPPRISMT. Une seule inférence par BAM canonique ; consommateurs réunis lors de la production.
- Feu/explosions/souffles5 : SPBOOM SPBRNHND SPBURN SPMETSWM SPRDRASI.
- Froid/projections3 : SPCCOLDL SPICESTM SPSCORIC.
- Lumière/rayons/impacts13 : HLYMITE SHAREA SHEARTH SHWATER SPGENHLA SPHLYSM2 SPHLYSM3 SPUNHBL2 SPUNHBL3 SPCSPRA2 SPCSPRA3 SPPRISM2 SPSPARKS.
- Fumées/dissipations5 : SPHORPUF SPRING SPSMKJET SPSMPUFF STNKCLDD.
- Impacts organiques7 : BLOODCR BLOODL BLOODM BLOODS SPBLOOD SPCHUNKS SPDEATH3.
- Cohérence : animations courtes à énergie, projections, nappes ou particules ; contours fins/alpha et mouvements natifs à conserver. Les impacts organiques étendent le même traitement aux particules physiques ; pas de personnages complets, objets solides ou décors ajoutés pour gonfler le lot.
- Doublons :112slots répétés sur9BAM : SPBURN12,SPGENHLA39,SPHLYSM2=2,SPUNHBL2=3,SPPRISM2=3,SPHORPUF28,STNKCLDD18,BLOODCR6,SPDEATH3=1. Aucun cycle constant. Audit ancré natif RGBA par cycle : `native-duplicate-audit.json`.
- Recette proposée : SeedVR7B x4 RGB, Apollo30 par cycle/direction ; condenser les poses répétées puis réétaler sur la durée native. Ne pas convertir les cycles/directions en une seule animation. Pas de cadence15FPS affirmée depuis le nom : owner natif/FPS/once-loop/blend/teinte à observer pendant intégration.
- Alpha : conserver alpha palette/indice natif et contrat normal/lumineux ; éviter les fonds noirs. Particules fines : pas de feather12 universel, pas de retrait ; SDF sans inset seulement si le contour le nécessite. Sang/étincelles/fumées gris peuvent être recolorés en runtime : absence de tag `palette` dans ce graphe incomplet ne garantit pas une teinte fixe ; préserver/reproduire le contrat natif.
- Exclusions proches : SHAREAB/SPSDIMSP/SPSDRAE2/SPSDRABU ont RGB visible entièrement noir, donc masques/runtime distincts ; projectiles à palettes déclarées regroupés séparément ; DUST n’a pas de référence exacte démontrée (le premier match est un suffixe d’une autre chaîne) ; portes/boucliers/vignes/arbres/personnages hors cohorte.
- [Planche native](preview/native.png), `batch.json`, audit ; reproduction : `python -B pipeline/recipes/effects-next-impacts-proposal-20261017-v1/propose.py`. Nouveau dossier si le périmètre change après cette proposition.
