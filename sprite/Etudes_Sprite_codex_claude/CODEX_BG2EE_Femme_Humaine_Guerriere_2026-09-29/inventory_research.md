# Inventaire indépendant Codex — BG2EE, humaine guerrière, 2026-09-29

## Périmètre et preuves

- Lecture directe `config://bg2ee_game_root/chitin.key` → BIFF ; aucun contenu `override`, aucun audit externe/Claude consulté.
- Générateur : `inventory_tools/build_inventory.py` ; APIs locales `pipeline/scripts/bg2lib.py`, `bam_export.py`.
- KEY SHA-256 : `1818ffebb2424992fb39fb13509e7f629ac819b08a553c2dd4ac25f2e40a979f`.
- Corps/objets sources : `data/GUIIcon.bif`, `data/OBJAnim.bif`, `data/PaperDol.bif`. `6110.INI` : `data/Patch2.bif`.
- Inventaire propre aux archives installées ; pas de certification Steam de leurs octets. Aucun BAM de ce périmètre présent dans `override` au relevé.
- Livrables : `assets_inventory.csv` (774 BAM), `assets_inventory.json` (palettes, histogrammes, géométrie, cycles/lookup), `assets_inventory_items.csv` (870 ITM avec apparence ou catégories armure/casque/bouclier/cape), `assets_inventory_shared_slots.json`.
- `vanilla_inventory/` contient les BAM extraits et 6110.INI/ANIMATE.IDS/ANISND.IDS/ITEMANIM.2DA/EXTANIM.2DA ; quelques extractions exploratoires WPL ne font pas partie du CSV final. Le CSV constitue le périmètre.

## Famille vérifiée

`ANIMATE.IDS` : `0x6110 FIGHTER_FEMALE_HUMAN` ; ne pas confondre `0x5110` alias LOW ni `0x6621` version BG1.

`6110.INI` : `animation_type=6000`, `armor_max_code=4`, `false_color=1`, `split_bams=1`, `equip_helmet=1`, `resref=CHFB`, `resref_armor_base=B`, `resref_armor_specific=F`, `resref_paperdoll=CHFF`, `height_code=WQN`, `height_code_helmet=WQN`, `height_code_shield=` (repli WQN).

| Rôle | Préfixes / suffixes | BAM | Frames table | Frames >1 pixel |
|---|---|---:|---:|---:|
| Corps en monde | CHFB1, CHFB2, CHFB3, CHFF4 | 92 | 41 294 | 11 090 |
| Corps inventaire | CHFF1INV..CHFF4INV | 4 | 9 | 9 |
| Armes principales | WQN + code + action | 166 | 46 087 | 45 094 |
| Armes secondaires | WQN + code + O + action | 72 | 25 013 | 24 897 |
| Boucliers | WQN + C0..C7 / D0..D4 | 65 | 18 018 | 18 017 |
| Casques | WQN + H0..H6 / J0..JC | 280 | 54 180 | 54 160 |
| Ailes, stock optionnel | WQNZW | 14 | 572 | 14 |
| Équipement inventaire | WPN + code + INV / OIN | 81 | 162 | 141 |
| **Total stock/famille** | | **774** | **185 335** | **153 422** |

Niveaux corps : 1 sans armure, 2 cuir/clouté, 3 mailles/armure d'éclisses selon l'ITM, 4 plates. Lire l'apparence ITM à 0x22 : `2A→CHFB2`, `3A→CHFB3`, `4A→CHFF4`. Une nouvelle pièce d'armure n'exige généralement aucun BAM propre : elle choisit un corps et des couleurs. Les ITM `2W/3W/4W` sont des robes ; ne pas fabriquer CHFW pour une guerrière en extrapolant uniquement la lettre W.

Paperdoll : humain femme = taille N ; `WPNxxINV`, `WPNxxOIN` main gauche. Vérification indépendante par stock natif + [GemRB avatars](https://github.com/gemrb/gemrb/blob/master/gemrb/unhardcoded/bg2/avatars.2da), [pdolls](https://github.com/gemrb/gemrb/blob/master/gemrb/unhardcoded/bg2/pdolls.2da), [assemblage PaperDoll](https://github.com/gemrb/gemrb/blob/master/gemrb/GUIScripts/PaperDoll.py). Les 81 sont un stock, incluant `WPNWMOIN` orphelin de WQNWM ; pas 81 variantes nécessairement équipables.

## Séquences, directions et conservation

23 suffixes par niveau : `A1 A2 A3 A4 A5 A6 A7 A8 A9 CA G1 G11 G12 G13 G14 G15 G16 G17 G18 G19 SA SS SX`.

| Suffixe corps | Cycles utiles attendus | Action |
|---|---|---|
| A1/A3/A5 | 0..8 | coups 1 main : taille/revers/estoc |
| A2/A4/A6 | 0..8 | mêmes familles, 2 mains |
| A7/A9 | 0..8 | deux armes |
| A8 | 0..8 | lancer / coup overhead selon arme |
| SA/SS/SX | 0..8 | arc / fronde / arbalète |
| CA | 0..71, blocs de 9 | préparation/lancement, 4 variantes |
| G11 | 0..8 | marche |
| G1 | 9..17 | posture combat 1 main |
| G12 | 18..26 | repos |
| G13 | 27..35 | posture combat 2 mains |
| G14 | 36..44 | touchée |
| G15 | 45..53 | mort ; premières poses compatibles touchée |
| G16 | 54..62 | corps au sol / twitch |
| G17/G18 | 63..71 / 72..80 | variantes repos |
| G19 | 81..98 | sommeil/chute/relevé inversé |

- 9 vues stockées : S, SSW, SW, WSW, W, WNW, NW, NNW, N ; 7 orientations est par miroir. Conserver centres et miroir pour les quatre couches.
- Corps split ; overlays WQN non split : leur G1 regroupe les états. Ne pas appliquer la découpe corps aux équipements.
- Les tables G1/G11..G19 comprennent souvent 846 frames et 99 cycles. La plupart des frames hors segment sont des **placeholders 1×1 index 2 opaques** : ni pixels transparents, ni véritables sprites. Ex. CHFB1G11 : 90 frames >1 pixel ; CHFB1G1 : 54 ; CHFB1G14 : 54 ; CHFB1G15 : 171.
- A1..A9 peuvent contenir 135 frames mais seulement 126 référencées par 9 cycles de 14. Ne pas réindexer automatiquement en supprimant les frames inutilisées.
- Les quatre corps comptent 10 764 frames distinctes référencées par les groupes attendus ci-dessus (2 691 par niveau), versus 41 294 entrées de tables. Les frames >1pixel hors groupes peuvent rester nécessaires à d'autres chemins moteur : préserver le contrat complet, dédupliquer seulement le calcul/cache.
- 18 841 cycles de stock, 376 417 références de frames ; 15 136 cycles référencent au moins une image >1 pixel. Ces nombres décrivent les BAM, pas une trace d'utilisation moteur.
- Near Infinity emploie G15 pour GET_HIT ; les ressources montrent une compatibilité des six premières poses G14/G15. Conserver les deux, vérifier en jeu plutôt que conclure à une ressource dispensable. Source : [CharacterDecoder](https://github.com/Argent77/NearInfinity/blob/master/src/org/infinity/resource/cre/decoder/CharacterDecoder.java), [INI IESDP](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/ini_anim.htm).

## Stock versus équipement utilisable

- Stock WQN : 597 BAM. Sous-ensemble ayant au moins un ITM de la bonne catégorie autorisé humain+guerrier par masque de base : **536 BAM** = 166 arme principale +72 secondaire +60 bouclier +238 casque.
- Ce sous-ensemble n'est **pas** une liste de butin accessible : restrictions de kit/alignement/caractéristiques, objets de quête et objets scriptés restent à filtrer. Le CSV conserve nom, type, flags, effets et exemples ITM pour cette étape.
- Hors sous-ensemble : WQND0 (5, aucun ITM) ; WQNH3/H4/H6 (42, aucun casque ITM) ; WQNZW (14, WINGS01 interdit humain). Les 59 ITM apparence H6 sont des attaques de créatures, **pas 59 casques**.
- WINGS01 : catégorie7, apparence ZW, nom « Fallen Archer », humain interdit. Famille utile pour généralisation/essai debug ; pas nécessaire au personnage guerrière normalement équipé. Ne pas annoncer « ailes humaines manquantes » : le stock existe mais les images utiles sont minimales.
- Extensions EE déjà dans archives : C0..C7 boucliers, F0..F3 fléaux/armes enflammées, GS/Q2/Q3/Q4 bâtons, M2 masse, S0 épée, J0..JC casques. Les inclure dans inventaire, sans tout produire dès l'essai initial.
- Paperdoll `WPND0INV`, `WPNZWINV` absents du stock ; cela correspond à des codes hors sous-ensemble normal. `WPNWMOIN` présent sans famille monde WQNWM : garder classé stock optionnel, ne pas inventer une dépendance humaine.
- Armes une main possèdent `G1 A1 A3 A5 A7 A8 A9` + main gauche `OG1 OA7 OA8 OA9` ; deux mains `G1 A2 A4 A6` ; arcs `G1 SA`, fronde `G1 SS`, arbalète `G1 SX`. Le CSV constitue l'énumération réelle, pas un produit cartésien arbitraire.
- Apparence ITM/effects vérifiables : [format ITM IESDP](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/itm_v1.htm). Les changements de couleurs équipées proviennent notamment des effets 7/8/9/50/51/52 ; ne pas traiter chaque ITM comme une nouvelle texture.
- Cape, gants, bottes, anneaux, ceinture : pas de couche avatar indépendante déduite du slot seul. Inspecter effets/couleurs/changement d'animation. Ex. les capes natives sont majoritairement sans apparence. Sorts, projectiles, VVC et effets globaux restent des ressources partagées : tests d'interaction, pas production massive imposée au personnage de référence.

## Partage et périmètre d'installation futur

- CHFB1..3 sont partagés avec humaine prêtresse et femmes demi-orques ; CHFF4 est partagé avec guerrière demi-orque.
- WQN partagé par 13 INI trouvés : 5010,5110,5210,5310,6010,6015,6110,6115,6210,6215,6310,6315,6510. Voir `assets_inventory_shared_slots.json`.
- Une substitution globale de ces resrefs affecterait d'autres personnages, même si les calculs ont été faits pour 6110. Phase de référence : montage isolé/identité de test/alias ou routage EEex à choisir ; ne pas installer le stock partagé sous ses noms natifs sans périmètre validé.
- Ombre native présente via index1 dans corps et certains objets ; pas d'obligation de créer une famille CSHD séparée pour ce type moderne.

## Quantité et automatisation

- 774 payloads BAM : **19 727 419 octets** archivés/extraits (18,81 MiB). Indices décodés toutes entrées : 252 343 474 pixels (240,65 MiB P8).
- Grossissement géométrique brut stock complet : x2 ≈0,94 GiB P8 /3,76 GiB RGBA ; x4 ≈3,76 GiB P8 /15,04 GiB RGBA ; palettes/tables et compression non incluses. Ce sont volumes de buffers cumulés, **pas estimation RAM moteur simultanée ni taille finale BAMC**.
- Traitement séquentiel par BAM/frame + cache source/paramètres ; préserver les 1×1 et centres explicitement. Les quatre variantes peuvent partager décodage, masques, lookup, analyses de couleurs et géométrie de référence.
- Tous histogrammes sont mesurés sur frames stockées (incluant placeholders/frames non référencées). Ne pas interpréter un index rare comme libre. Corps : 726 592 pixels stockés dans 168..254 ; les valeurs hautes servent déjà. La sémantique de remplacement moteur prime sur le RGB de la palette source.
- Base d'automatisation : INI → préfixes corps/objets ; ITM → apparence/catégorie/flags/effets ; KEY → BAM présents ; BAM → contrats géométrie/cycles/indices ; empaquetage seulement après choix de traitement et QA.
- Essai vertical utile : CHFB1G11 marche + CHFB1A1 attaque + CHFB1CA ; puis CHFF4 équivalents ; équipement `WQNS1`, `WQNDDO`, `WQNC1`, `WQNJ6`, `WQNFS`, `WQNBW` ; sélectionner cycles et images réellement renseignés.

## Limites

- Aucune validation en jeu ; pas d'installation, génération release ni mutation de ressources natives.
- Comptages primaires reproductibles par script ; sémantique de séquences corroborée IESDP/NI/GemRB, avec divergence G14/G15 rendue explicite.
- Les 774 BAM constituent une borne de famille complète et utile à généralisation. La première production monde ciblée doit partir des 92 corps +536 overlays liés au masque humain/guerrier, puis filtrer les restrictions restantes selon objectifs de couverture ; ailes et stocks inutilisés restent annexes.
