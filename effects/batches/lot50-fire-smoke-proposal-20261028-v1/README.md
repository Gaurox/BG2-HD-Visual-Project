# Proposition lot50 — flammes, explosions, fumées et éruptions

- Date2026-10-28 ; proposition source uniquement, aucune production/QA/installation/release modifiée.
- 50BAM canoniques distincts/50RESREF ; tous `spatial_state=not-started`, sans sélection ; sources disponibles/hashées. Hashes déjà produits dans effects et sélections existantes du registre animations exclus ; aucun alias interne.
- 990enregistrements source,123cycles,1291slots alternatifs ;303slots répétés dans5BAM. Audit RGBA ancré par cycle : `native-duplicate-audit.json`. Répétition ne signifie pas durée supprimable : préserver temps/pauses natifs.
- Sources inspectées visuellement : [01–25](preview/native-1.png), [26–50](preview/native-2.png). Même famille de textures diffuses, flammes et particules ; pas de personnages, armes ou décor architectural.
- Limite explicite : aucun consommateur VVC/PRO indexé ni chaîne exacte NUL-terminée dans l'exécutable pour ces50noms. Cela ne prouve pas l'absence d'usage (références dynamiques/autres types possibles), ni un usage réel. FPS/blend/teinte/owners natifs restent non résolus. Proposition de production visuelle, pas promesse d'améliorer50sorts actifs.
- Réemploi détecté hors lot parmi les183entrées `not-started` : BURNHAND SPARMOUR SPFDETH3 SPFIRIMP SPFLMSTI SPHLHI01 SPHLHI02 SPICEIMP SPILUSIO SPIPLARI SPPRISM3 SPPRISMT ont déjà un hash canonique produit ; exclus, états historiques inchangés.

| Numéros | Sous-famille | RESREF |
|---|---|---|
|01–23|Flammes colorées|FIM1YEL FIM2YEL FIRE_1B FIRE_1C FIRE_1GR FIRE_1GS FIRE_2 FIRE_2A FIRE_4BL FIRE_4G2 FIRE_4GR FISM1YEL FLLGBLU FLLGBLUE FLLGRED FLM1PUR FLM1RED FLM2RED FLMDBLU FLML FLSM1PUR FLSM1RED LAVAFIR1|
|24–38|Explosions et jets de feu|EXPLODE SPBDBUR SPBDBURS SPBURNS1 SPFBSMAL SPFINODI SPFIRE SPFIRET SPFLADOW SPFLSTRI SPFSTRMI SPPFIRAI SPPFIRXI SPRDRAEX SPMETSWN|
|39–47|Fumées et nuages|DSTDVL2A FALLMIST STEAM1 STEAM4 SPSMOLD SPSTINK SPAGSCHO SPGREACI ACIDDTH|
|48–50|Bulles et éruptions|LAVABUB1 LAVABUB2 SPOUTA|

Recette compatible proposée : SeedVR7B x4 RGB ; Apollo30 par cycle/direction, condenser poses répétées avec chronologie/durée native conservées ; sources indexées/palettes immuables. Alpha natif gradué conservé ; rendu normal/lumineux séparé selon owner. Les fonds noirs/verts visibles sur les sources ne justifient pas un détourage automatique universel. Pas de feather/retrait global : flammes minuscules et particules à préserver. Usage/cadence natifs à établir avant intégration, ne pas présenter15FPS comme mesuré.

Reproduction vers un nouveau dossier si changement : `python -B pipeline/recipes/effects-next-fire-smoke-proposal-20261028-v1/propose.py`. Le script refuse d'écraser `batch.json`.
