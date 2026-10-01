# Character Q3m — contrat P2 V6

Périmètre : registre expérimental + DLL compatible ; pas d'installation, QA ingame,
P3, catalogue global ou release. Preuve locale :
`sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p2-20260930-v1/verification.json`.
P1 Q3m K6 inchangé : fractions 0..7, aucun tramage/mélange de classes/B.

## Identités et compatibilité

- Magic registre `IEECSXN\0`, version **6 réservée** ; versions 1..5 conservent leur sens.
- Catalogue **IEECSNC V2** uniquement ; feuilles V6 homogènes ; owners Character uniquement.
  Pas de lecteur V6 monolithique/set, pas de promotion automatique V5→V6.
- `class_profile_id=1` : `character-bg2ee-2.7.3.0` ; `decode_rule_id=1` :
  `ramp-lerp-srgb8-v1`. Namespaces distincts ; inconnus rejetés.
- Encodeur `character-exhaustive-oklab-squared-q3-integer-v1`, K6 et palettes = provenance
  producteur ; aucun rôle au décodage. Les tailles physiques dépendent du scale du registre.
- Géométrie/centres x1, resref, SHA source canonique, compte et ordre des frames,
  cycles/slots natifs conservés. Le runtime ne compare pas le SHA source au BAM vivant.
- `representatives[256]` reste u16 offset source, `0xffff` absent ; chaque offset présent
  doit être `<w*h`. Une nuance créée par Q3m ou son successeur peut n'avoir aucun représentant.
  V3/V4/V5 gardent leur contrôle historique de présence.

## Octets little-endian

En-tête registre `<8s6I>`, 32 octets : magic, version, scale(2/4), resources,
animation `0xffff`, class_profile_id, decode_rule_id.
Ressource `<8s32sII>`, 48 octets : resref ASCII nul-paddé, SHA256 source binaire,
frame_count, cycle_count. Frames puis cycles : u32 slot_count, u32 frame_index par slot.

En-tête frame `<HHhhBBBBI256H32sIB3x>`, **568 octets** :

| Offset | Taille | Champ |
|---:|---:|---|
| 0 | 2+2 | w, h natifs u16 non nuls |
| 4 | 2+2 | centre x/y i16 |
| 8 | 1 | indice transparent, 0 pour ce profil |
| 9 | 1 | codec I : 0 brut, 1 XPRESS_HUFF |
| 10 | 1 | F présent : 0/1 ; autres bits interdits |
| 11 | 1 | réservé = 0 |
| 12 | 4 | taille I stockée |
| 16 | 512 | representatives[256] u16 |
| 528 | 32 | dep_mask, bit i = octet i/8, bit i%8 |
| 560 | 4 | taille F stockée |
| 564 | 1 | codec F : 0 brut, 1 XPRESS_HUFF |
| 565 | 3 | réservés = 0 |

Suivent I puis F si présent ; `N=w*h*scale*scale` octets décodés par plan,
ordre row-major. **F est un octet/pixel, domaine 3 bits 0..7, sans packing 3 bits.**
F absent ⇒ zéro ; producteur omet F entièrement nul. F absent impose taille/codec F=0.
XPRESS_HUFF Windows Cabinet, par plan indépendant, seulement si strictement plus petit
que N ; sinon brut. **Aucun B** : bits/extension inconnus rejetés.

## Décodage, dépendances, cache

`succ(i)=i` pour 0..3, terminaux `(i-4)%12==11` dans 4..87,
`(i-88)%8==7` dans 88..255 ; sinon i+1. F non nul sur ces terminaux/spéciaux interdit.
RGB par octet : `(P[I]*(8-F)+P[succ(I)]*F+4)>>3` ; alpha = alpha de P[I].
F0 lit directement P[I]. Encodings existants RGBA/u8, BGRA/u8, BGRA/u32_8888_REV.
Transparent DWORD normalisé à zéro comme auparavant ; ombre/réservés restent indexés.
Ordre/copies de couches et bordure existants conservés, sans nouveau mélange alpha.

- dep_mask **exact** = union I + succ(I) seulement là où F>0 ; manque/excès rejetés.
  Le producteur vérifie aussi le maintien des classes/spéciaux depuis le guide P1/xBR.
  Ce guide n'est pas transporté ; le runtime vérifie les limites de classes et le masque.
- LUT scratch 2048 dwords par frame/couche : remplissage des couples utilisés seulement.
  Pas de lecture de couleurs hors masque pour reconstruire cette LUT.
- Empreinte existante FNV : format/type natifs + IDs profil/règle + DWORDs dépendants
  après normalisation transparent. Representatives exclus de l'empreinte V6.
- Cache composite existant : handle/position/géométrie/palette par couche ; deux acteurs
  utilisant le même BAM gardent leurs palettes propres. Effet pulsé ⇒ recomposition si
  une dépendance change ; couleur inutilisée ⇒ cache hit. Alpha primaire participe.
- I/F chargés et évincés **ensemble**, budget cache décodé inchangé 128 Mio ; SHA par plan,
  identité fichier et quarantaine composants existantes. `forget_engine_textures()`
  invalide le cache CPU ; gestion WGL/IDs GL existante conservée.
- `index_bytes` catalogue reste I uniquement ; compteurs F distincts dans les preuves.

## Rejet et digests

Bornes existantes ressources/frames/cycles/slots, fichiers, dimensions, arithmetic et
lookups ; N*(1+Fprésent) ≤128 Mio/frame ; contrat P2 initial : somme I+F
≤128 Mio(x2)/512 Mio(x4)/shard. Extension x2 complète ci-dessous.
Décompression exactement N ; flags/codec/IDs inconnus, offsets représentants, F>7,
masques inexacts, troncatures, données restantes et corruption XPRESS rejetés.
Prévalidation temporaire I/F avant publication des métadonnées V6 ; recharge lazy vérifiée.
Contrat P2 initial : catalogue Python homogène en version ; lecteur natif détecte et met en
quarantaine un composant incompatible lors du chargement lazy. Extension P3 ci-dessous.
Repli = **BAM natif** ;
comparateurs Q0/xBR sont des packs explicites, pas une deuxième feuille V5 automatique.
Anciennes DLL échouent fermé sur une feuille V6 ; pas d'installation avec une ancienne DLL.

Identités physiques SHA/CRC = octets stockés. Identités logiques : en-têtes codecs=0,
tailles=N, I/F décompressés, dep_mask/reps/geometry/source/cycles conservés.
Domaines nouveaux : `IEECSNC-SOURCE-COMPONENT-V2\0` (IDs profil/règle inclus),
`IEECSXN-RESOURCE-CONTRACT-V6\0` (scale+IDs+record entier). Digests hérités inchangés.
F absent et F explicitement nul ont les mêmes pixels ; leurs octets/identités logiques
peuvent différer. `source_tree_hash` Python/Install-CreatureSprite-XN-Test.ps1 inclut
`src/iee/core/palette_fraction.h` ; anciens reçus de build ne prouvent pas cette DLL.

## Producteurs, lecteurs, essais

- `palette_registry.write/inspect/logical_chunks/write_catalog` : API V6 contrôlée ;
  output existant refusé, publication frame/shard après validation.
- `run_creature_sprite_x2.inspect_registry/inspect_registry_catalog`,
  `catalog_source_component_sha256`, `reboutcx_catalog.resource_contract_digest` : consommation V6.
  Anciennes voies d'écriture conservent V3/V5 et refusent une conversion implicite V6.
- `creature_sprite_x2.cpp` : parse_registry, charge lazy I/F, LUT upload/composition,
  empreinte, cache ; `core/palette_fraction.h` : arithmétique entière et invariants.
- `palette_p2.py fixtures --output <nouveau-build>` : NPZ P1 épinglé + palettes alpha
  arbitraire + cas corrompus authentifiés extérieurement ; CMake/CTest l'appellent.
- `palette_p2.py packs --output <nouveau-run> [--scale 2|4]` : 5 BAM monde `0x6110`,
  4230 frames ; 84 frames P1 Q0/Q3m, 4146 xBR communes, cycles complets, 756 placeholders.
  Tables natives complètes nécessaires ; ce pack ne constitue pas une verticale complète.
  Aucun nouvel appel neural/GPU ; xBR CPU/Node pour le complément.
- Hôte `iee_palette_fraction_tests --pack <assets> <decoder-oracle.bin>` : résolution
  cycles, tous pixels/18 palettes comparés au SHA Python pour chaque frame ; hors GL.

Build : CMake, MSVC x64, SDK Windows, Python+NumPy (`-DPython3_EXECUTABLE=...`).
XPRESS requiert Windows. Target `iee_palette_fraction_tests` + DLL `InfinityEngine-Enhancer`.
Provenance P2 : commandes, toolchain, empreintes sources, DLL, catalogues et oracles.

## Limites restant à P3

- Fixture P1 alpha synthétique ; tests supplémentaires alpha arbitraire prouvent la copie
  primaire/packing, pas la réalisation native d'effets dans BG2EE.
- Hôte : CPU LUT/composition/cache/reset et byte identity prouvés ; pas de capture
  palette vivante, upload/queue GL, changement réel WGL, fps, captures ou QA visuelle.
- Coûts mesurés = mélange expérimental 84 Q3m/4146 xBR ; ni coût d'une production
  entièrement Q3m, ni working set total du processus. Prévalidation implique I/O et
  inflation transitoire d'un shard ; sharding global hors P2.
- Régression REF P1 inchangée +6,10% x2/+11,59% x4 : décision visuelle utilisateur future,
  ou nouveau P1 pondéré REF. Aucun changement de K/palettes ici.
- Guide disponible non modifié : §8 est logique, version désormais réservée ; §8.5
  LUT complète/pulsation chaque frame doit se lire avec les dépendances effectivement
  utilisées ; §14 « fallback V5/xBR » n'est pas un mécanisme actuel de repli automatique.
  Mentions « aucune DLL/V6 » décrivent P1, pas le nouveau résultat P2.

## Extension P3 — coexistence V5/V6, 2026-10-01

- Catalogue V2 existant, octets V5/V6 inchangés ; versions `{5,6}` permises entre
  composants **homogènes**. Versions distinctes dans un composant : rejet/quarantaine.
- Restriction Character appliquée à tous les memberships des composants V6 ; les
  composants V5 des autres owners restent accessibles. Ordres V5→V6 / V6→V5 testés.
- Capability runtime explicite `mixed_v5_v6_components=true` ; manifeste pack :
  `registry_catalog_shard_versions=[5,6]` et `registry_catalog_frame_storages`.
  Scalar version=0 signifie mixte ; il ne remplace pas les identités de feuilles.
  Installateur refuse une DLL sans cette capacité, même si elle connaît V6 isolé.
- `palette_p3_catalog.derive` : parent P13 complet épinglé ; 828 shards réutilisés,
  48 records V5 résiduels copiés octet pour octet, feuille expérimentale P2 conservée.
  Remplacements limités à `0x6110` ; 194 autres routes/memberships inchangés.
- SHA source ancien = BAMC ; SHA P1/P2 = BAM canonique. Équivalence autorisée seulement
  après SHA des deux fichiers + identité exacte du contenu décompressé et des tables
  géométrie/cycles. Preuve dans `generation/preservation.json` ; aucun SHA réécrit.
- `Q3M_P3_PALETTE` limité aux frames V6 ; `Q3M_P3_DRAW` corrélé par generation prouve
  la substitution native du composite. Le checker exige cette corrélation par défaut ;
  `--cpu-only` reste une preuve CPU explicite, sans QA visuelle ni GPU readback.
- Essai corrigé : `palette-q3m-p3-20261001-v2`, Q0/Q3m dérivés du même parent.
  Profils x1 fpSprite/fpSELECT désactivés temporairement ; restauration INI intégrale.

## Extension P3 — couverture intégrale 0x6110, 2026-10-01

- `palette_complete.py` : 656 BAM, toutes les frames/cycles ; six palettes P1,
  Q3m K6 x2, fixed86 FP16 q32, sans tramage/B. Reprise uniquement d'un run de travail
  non scellé avec recette identique ; les runs historiques restent immuables.
- `palette_p3_catalog.derive` accepte plusieurs feuilles V6 ; doublons resref rejetés.
  Un composant homogène par BAM ; composants parents partagés conservés.
- Deux grandes animations d'armes dépassent le budget cumulé initial avec F.
  Nouvelle borne **I+F décodés cumulés ≤256 Mio/shard x2**, I seul ≤128 Mio.
  Fichier physique ≤128 Mio, frame I+F ≤128 Mio, cache résident I/F ≤128 Mio : inchangés.
  x4 conserve 512 Mio cumulés ; aucun changement d'octets/profil/version V6.
- Manifestes : pack `required_q3m_x2_decoded_shard_bytes` = maximum réel I+F des
  feuilles ; runtime `q3m_x2_decoded_shard_limit_bytes=268435456`. Si besoin >128 Mio,
  l'installateur exige explicitement la capacité ; les petits packs restent compatibles.
- Fixture `eviction-x2` : cinq frames de 32 Mio I+F, cumul 160 Mio ; éviction/recharge
  sous 128 Mio. `x2-index-budget` : I seul 144 Mio, F absent, cumul <256 Mio ;
  rejet indépendant par la borne I de 128 Mio, catalogue authentifié.
- `iee_palette_fraction_tests --pack-complete <assets> <oracle>` : toutes les frames,
  18 palettes, oracle scalaire distinct du décodeur Python ; quatre couches réelles V6,
  BAM partagé de `0x6115` toujours V5. Oracles bornés à 60 000 frames/fichier.
- Essai `palette-q3m-p3-20261001-v3-full-6110` ; aucune QA ingame implicite.

## Extension P3 — Q3m x4 complet, 2026-10-01

- `palette_complete.py --scale 4` : memes 656 BAM / 178 360 frames, six palettes P1,
  K6, fixed86 FP16 q32 ; cibles x4 directes, guide xbr4X, aucune reduction x2 ni
  reprise de pixels ReboutCX historiques. Identite de cache distincte du x2.
- `write_complete_x4_catalog` : catalogue V2 isole `0x6110`, toutes feuilles V6 ;
  couverture exacte/doublons verifies. Autres animations = BAM natif pendant le test.
- Budget V6 x4 cumule I+F <=1 Gio/shard ; **I seul/fichier <=512 Mio**, frame I+F et
  caches I/F/metadonnees <=128 Mio inchanges ; octets/profils/codecs V6 inchanges.
- Pack `required_q3m_x4_decoded_shard_bytes` ; runtime
  `q3m_x4_decoded_shard_limit_bytes=1073741824`. Au-dela de 512 Mio cumules,
  capacite explicite exigee avant installation, anciennes DLL refusees.
- Fixtures : `eviction-x4-large` = 272 Mio I + 272 Mio F, eviction sous 128 Mio ;
  `x4-index-budget` = I seul 544 Mio, F absent, rejet meme si cumul <1 Gio.
- Verification P1 : les 144 echantillons x4 sont identiques en I/F/dep ; 732 cibles
  float32 x4 rencontrees pendant l'inference identiques (cles de pixels dedupliquees).
  Oracles natifs : toutes frames/18 palettes,
  puis 656 BAM dans une session avec retour au premier ; composition 4 couches V6
  aussi exigee pour catalogue isole sans `0x6115`. Aucun resultat ingame deduit.
