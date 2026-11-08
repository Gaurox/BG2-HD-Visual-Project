# Nouveau lot50 · magie, ombres et eau · 2026-11-08

**Sélection initiale à lire avec la correction de réemploi** : [audit](../../research/next50-reuse-audit-20261108-v1/README.md), `conclusions.json` : 41 candidats propres, 3 adaptations/réemplois, 6 masques natifs sans IA. Planche par défaut annotée ; batch.json initial conservé.

- **Proposition source uniquement**, après acceptation du précédent lot50. [Planche50 animée](http://127.0.0.1:8798/), `review/index.html` ;50cartes, choix cycle, lecture/pause/phase/vitesse/fond, parcours automatique des cycles.
-50productions visuelles distinctes /51RESREF ; AMDEMGT couvre aussi SP_DEMGT (même BAM canonique). Aucun doublon RGBA complet/géométrie/cycles dans les50 ; réemplois achevés effects/animations exclus d'après états actuels et correspondances de l'audit antérieur.
-1402records source,114entrées de cycle dont86animables et28vides ;1676slots,266répétitions dans11BAM. Poses/pauses/ancrages conservés ; cycles alternatifs séparés, pas concaténés.15FPS d'aperçu non mesuré ingame.
- Étendue :13portails/manifestations,16rayons/impacts/protections,7ombres/poussière/précipitations,10eau/bulles/ondes,4matières/toiles. Pas de personnages DEMB/MSOLG1, poissons, arbres, glyphes statiques, pièces architecturales AM découpées. AM6200C/D =deux animations complètes de colonne lumineuse conservées séparément.
- Sources toutes disponibles et hashées ; états `not-started`, aucune sélection.6assets avec consommateurs indexés,44usages non résolus : pas une promesse de50sorts actifs. Sources/controllers/production/QA/installation/release inchangés.
- **Alpha gradué réellement utilisé** : SHAREAB, SPSDIMSP, SPSDRABU, SPSDRAE2, TRAVELB ; préserver alpha palette natif dès export. Les ombres/souffles sombres ne doivent pas subir aveuglément la conversion de flux lumineux en alpha du lot précédent.
- **Fond vert opaque** : WHIRLY,69.672% du support couvert ; hypothèse de masque indexé de bord à comparer avant inférence. Aperçu ici fidèle à la source.
- Préparation des futures recettes : réutiliser SeedVR sur textures diffuses et comparer xBR pour motifs fins ; retour du lot50 précédent = glyphes inventés sur micro-effets. Aucun modèle/inférence/interpolation HD lancé par cette proposition.
- Preuves utiles : `batch.json`, `native-duplicate-audit.json`, `preview/native-1.png`, `preview/native-2.png`, `review/catalog.json` ;50PNG RGBA décodables,1676indices valides. Les atlas de lecture préservent les centres natifs. Aucun audit global ni rehash des médias achevés.
- Recette : `pipeline/recipes/effects-next50-magic-water-proposal-20261108-v1/{propose.py,board.html}` ; refuse d'écraser batch/index existants. Dérivée du builder de planche native du lot précédent. Le CSV de suivi est vérifié inchangé par SHA256 pendant la préparation.

| N° | Groupe | RESREF |
|---|---|---|
|01–13|Portails/manifestations|AM3000G AM6200C AM6200D AMDEMGT HARPDISC SPARMOR2 SPDIMDR1 SPDIMDR2 SPMIRROI SPRESURI SPWIRBLA WHIRL01 WHIRLY|
|14–29|Rayons/impacts/protections|HIHEDGE SHAREAB SPBASEWT SPCCOLDE SPCCWOUI SPCHROMI SPCSPRAI SPENTAXI SPGENHLB SPHLYSMT SPHOLMIG SPHOLYWD SPRWRA2I SPSDIMSP SPSNRAYI SPUNHBLT|
|30–36|Ombres/précipitations|DUST SNOWFAL1 SNOWFAL2 SPSDRABU SPSDRAE2 SPSHADOW TRAVELB|
|37–46|Eau/bulles/ondes|BUBBLES1 BUBLES FOUNT2 FOUNTN RIPPLE_1 RIPPLE_2 RIPPLE_3 SPLASH WTRBODY2 WTRDROP1|
|47–50|Matières/toiles|TRBLOBA TRBLOBB WEBBOMB WEBC|
