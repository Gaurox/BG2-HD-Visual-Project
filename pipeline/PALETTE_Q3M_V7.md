# Q3m x2 — quatre partenaires / huit niveaux, V7

- Producteur : `scripts/q3m_family_witnesses.py` ; sélection `../sprite/index/q3m-family-witnesses.json`.
- Codec : `scripts/palette_q3m_partners.py`, `scripts/palette_partner_registry.py`.
- Runtime : `../engine/InfinityEngine-Enhancer/source-patchee/src/iee/{creature_sprite_x2.cpp,hooks.cpp}`.
- Candidat témoin : `../docs/measurements/q3m-families-engine-x2-20261003-v2/current-generation.json`.
- Portée : 15 animations, une par famille ; 49 BAM complets pour les actions retenues. Autres actions/équipements → rendu natif. Aucune QA ingame acquise par les tests hôte.

## Format

Catalogue `IEECSNC` V2, échelle 2. Feuilles `IEECSXN` V7, échelle 2 exclusivement.
V6 conserve ses profils/règles/octets ; aucun changement des générations ou QA précédentes.

| Structure | Octets little-endian |
|---|---|
| Registre | `<8s6I>` : magic, version=7, scale=2, ressources, animation=0xffff, profil=8/9, règle=3 |
| Ressource | `<8s32sII>` : resref, SHA source canonique, frames, cycles |
| Extension ressource | **2052 octets** : u32 nativeKind, 256×BGRA u8 source, 256×4 partenaires u8 |
| Frame | `<HHhhBBBBI256H32sIB3x>`, 568 octets ; structure V6, plans I puis F |
| I / F | u8 row-major, dimensions `2w × 2h` ; brut ou XPRESS_HUFF indépendant |
| Cycle | u32 slots puis u32 indices ; valeurs u16 natives conservées, y compris slots sans frame |

`nativeKind=0`, profil 8 : palette fixe ; classes `{0}`, `{1}`, `{2}`, `{3..255}`.
`nativeKind=1`, profil 9 : palette à rampes ; classes Character acquises : spéciaux 0..3,
7 rampes de 12 indices 4..87, 21 rampes de 8 indices 88..255.
Chaque partenaire reste dans sa classe ; indices spéciaux associés uniquement à eux-mêmes.

`code = (B << 3) | F`, B=0..3, F=0..7. Plan F absent ⇒ code=0 partout.
F=0 impose B=0 ; mélange positif avec soi-même interdit. Aucun tramage.

```text
J = partners[I][B]
RGB = ((8-F)*nativePalette[I].RGB + F*nativePalette[J].RGB + 4) >> 3
alpha = nativePalette[I].alpha
type fixe + I=0 : alpha=0
dep_mask = union(I, J uniquement lorsque F>0), exactement
```

Palette vivante capturée dans le `Render` propriétaire puis `CVidPalette::Realize` natif.
Au dessin, CVidCell remet l'entrée transparente 0 à RGBA=0 ; l'oracle pixel applique cette remise à zéro.
Alpha des deux partenaires identique pour un mélange positif ; sinon rendu natif.
Palette fixe : nativeKind et RGB source complets comparés ; alpha source natif 0/255 admis.
Palette à rampes : nativeKind vérifié ; palette réalisée, recolorations et effets restent natifs.
RGBA/u8, BGRA/u8, BGRA/u32_REV testés. LUT locale aux couples utilisés ; cache palette borné.

## Encodage / réutilisation

- K6 fixe : six sorties de la fonction native type 0 émulée, comparées à l'oracle scalaire acquis ; exécutable SHA `b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57`.
- K6 rampes : six palettes du plan Character acquis, lues sans modification.
- Partenaire B=0 : successeur V6 pour les rampes ; voisin RGB K6 le plus proche pour le fixe.
- Trois partenaires supplémentaires : distance OKLab quadratique moyenne K6, indices stables en cas d'égalité, RGB distincts, même classe.
- Recherche exhaustive I/B/F, objectif OKLab quadratique K6 sur cibles float32 ; arrondi entier identique au runtime. Tous les candidats V6 restent disponibles.
- Guide d'indices xBR2 conservant les classes ; Q3m final produit par cibles ReboutCX float32 direct x4 → BOX x2. xBR et ReboutCX final première version restent historiques.
- Clé source = dimensions, transparence, indices exacts, RGB natifs utilisés ; centres/cycles par occurrence.
- Clé encodage = SHA(kind + table partenaires + palettes K6) + clé source ; namespace SHA du module encodeur. BGRA source reste dans chaque ressource, sans dupliquer un encodage compatible.
- Clé cible neuronale = recette/backend/model + clé entrée indexée + RGB K6 utilisés hors transparence. Regroupement global des requêtes avant inférence, jamais une boucle GPU indépendante par famille.
- Cache persistant `.npz`, contrôle dimensions/types/classes/deps, CRC ZIP ; écriture atomique et verrou Windows exclusif. Reprise entièrement en cache : aucun import Torch ni chargement modèle.
- Ce pilote : 11 586 occurrences → 2 730 sources → **2 731 encodages compatibles** ; une source spéciale a deux contrats sémantiques. 54 variantes de métadonnées inutiles regroupées après égalité des quatre tableaux. Reprise 2 731/2 731 hits, zéro cible/calcul nouveau.

## Routage natif

Offsets/signatures : `src/iee/game/build_manifest.{h,cpp}` ; appartenance INI : `src/iee/core/sprite_family_owners.h`.
`scripts/analyze_native_sprite_families.py` vérifie l'exécutable, 15 vtables, slot Render 38,
slot parseur INI 61, noms INI et 465 appartenances source.

- Owners 1..5 acquis : Character, Icewind, Monster, Quadrant, MultiNew.
- Owners 6..15 : CharacterOld, MonsterOld, Layered, Ankheg, Large, Large16, Ambient, AmbientStatic, TownStatic, Flying.
- Large et Large16 partagent Render ; vtable exacte distingue leurs owners.
- INI `multi_new` : implémentations natives MultiNew **et** MonsterMulti ; 9 parties pour 1200..1208, 4 pour 1300, compte natif strict.
- CharacterOld/Layered/Icewind : découvrir les cellules effectivement réalisées ; remplacer le composite complet avec chaque palette/cellule. Une couche manquante invalide le composite.
- Ankheg : conserver les deux soumissions natives et leurs centres.
- Les cellules dynamiques ne sont acquises qu'au callsite natif Realize épinglé, dans le Render propriétaire. Un Render imbriqué non ciblé masque le contexte extérieur.
- Géométrie x1, centres, rectangles/clipping, ordre natif et sauvegardes inchangés. V7 autorise la texture sans bord uniquement si ses dimensions natives correspondent exactement au BAM ; sinon contrat bordé strict.
- Exécutable inconnu, signature/vtable/profil/alpha/dépendances/dimensions erronés → rendu natif. Les tests hôte ne prouvent pas les ombres/occlusions en jeu.

## Commandes locales

```powershell
$q3mPython=(Get-Content config/workspace-paths.local.json -Raw|ConvertFrom-Json).paths.chainner_python
# Unicorn déjà disponible dans ce dossier local ignoré, sans installation globale.
$env:PYTHONPATH=(Resolve-Path sprite/.work/q3m-runtime-tools-20261003-v1).Path
& $q3mPython pipeline/scripts/q3m_family_witnesses.py plan --cache sprite/.work/q3m-family-witnesses-x2-20261003-v1
& $q3mPython pipeline/scripts/q3m_family_witnesses.py run --cache sprite/.work/q3m-family-witnesses-x2-20261003-v1
# Destination pack obligatoirement neuve ; candidat correct = pack-v3.
& $q3mPython pipeline/scripts/q3m_family_witnesses.py pack --cache sprite/.work/q3m-family-witnesses-x2-20261003-v1 --output sprite/.work/q3m-family-witnesses-x2-20261003-v1/pack-v4
& $q3mPython -m unittest discover -s pipeline/tests -p test_palette_q3m_partners.py -v
& $q3mPython pipeline/scripts/analyze_native_sprite_families.py
& engine/InfinityEngine-Enhancer/source-patchee/build-q3m-families-20261003-v1/Release/iee_palette_partner_tests.exe sprite/.work/q3m-family-witnesses-x2-20261003-v1/pack-v3 sprite/.work/q3m-family-witnesses-x2-20261003-v1/pack-v3/witnesses.oracle
```

Build DLL local : VS2019, CMake `IEE_BUILD_WINDOWS_DLL=ON`, C++20 ; `BUILD_TESTING=ON` pour les tests.
Installation : fermer jeu/InfinityLoader avant remplacement ; ce pilote n'écrit aucun fichier installé/release.

## Large16 : scope et palettes fixes — 2026-10-04

- Cas `../docs/measurements/q3m-monster-large16-full-x2-20261004-v1/README.md` : native owner11, cellules G1/G2/G3 + E ; préfixe MWYV inclut aussi douze BAM Quadrant inutilisés par Large16. Une famille disponible complète peut déclarer ses IDs sans source, exactement selon l'inventaire ; ne pas produire des quadrants/frames 0×0 hors appels natifs pour satisfaire un compteur de préfixe.
- `general.new_palette` remplace réellement la palette BAM fixe : A200 utilise BMP-P8 `MWYV_WS` (SHA dans sélection), avant guides/cibles/fitting/clés/source-palette guard. Couleurs natives distinctes = contrats distincts ; RGB/indices identiques compatibles restent dédupliqués. `q3m_family_witnesses.py` exige cet override explicite pour une famille complète ; pilote historique partiel préservé.
- NativeFixed index1 peut avoir RGB non noir ; tint natif aussi appliqué à son RGB sous flag 0x20000. Ajustement de l'attente scalaire locale, comparaison Unicorn épinglée sur les 256 entrées K6 ; producteurs/preuves historiques non réécrits. V7 ordinary conserve cette ombre native.
- Vérifié : dix tests hôte, sondes native isolée/combinée 20 ressources/1 692 frames × six palettes × trois formats, reprise 1 570 hits sans Torch. Aucun SDF nouveau ni moteur recompilé.
