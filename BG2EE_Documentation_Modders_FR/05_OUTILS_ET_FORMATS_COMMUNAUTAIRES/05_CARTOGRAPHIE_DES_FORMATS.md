# Cartographie des principaux formats BG2:EE

> **Statut :** Synthèse communautaire  
> **Dernière vérification :** 2026-08-27

## Graphismes et zones

| Format | Rôle principal |
|---|---|
| `BAM` | animations, créatures, effets, icônes, boutons, polices |
| `PVRZ` | pages de texture compressées utilisées par les formats EE |
| `TIS` | tuiles graphiques d’une zone |
| `WED` | organisation visuelle des tuiles, portes et overlays |
| `MOS` | grandes images ou cartes/minimaps selon le contexte |
| `BMP` | search map, light map, height map selon le suffixe |
| `PNG` | ressource graphique prise en charge par le système EE moderne |

## Contenu de jeu

| Format | Rôle principal |
|---|---|
| `ARE` | définition d’une zone : acteurs, conteneurs, portes, régions, etc. |
| `CRE` | créature |
| `ITM` | objet |
| `SPL` | sort ou capacité |
| `STO` | magasin |
| `PRO` | projectile |
| `VVC` / `VEF` | effets visuels et séquences d’effets |

## Scripts et texte

| Format | Rôle principal |
|---|---|
| `BCS` / `BS` | scripts compilés ou scripts d’IA |
| `DLG` | dialogues |
| `IDS` | identifiants symboliques |
| `2DA` | tables de données |
| `TLK` | table globale des textes localisés |
| `TRA` | fichiers de traduction utilisés couramment par WeiDU |

## Interface EE

| Format | Rôle principal |
|---|---|
| `MENU` | définition de l’interface depuis 2.0 |
| `LUA` | logique et tables de l’interface |
| `TTF` | police TrueType |

## Dépendances d’une zone

L’IESDP décrit une zone comme un ensemble : `ARE` pour le contenu, `TIS` pour les graphismes, `WED` pour la disposition et les portes, plus des BMP spécialisés, scripts, créatures, objets et animations référencés. Modifier seulement l’image d’une grande map ne dispense donc pas de préserver les conventions du TIS/WED associé.

## Sources
- Index des formats IESDP: https://gibberlings3.github.io/iesdp/file_formats/index.htm
- ARE - vue d’ensemble: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/are_v1.htm
- TIS: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/tis_v1.htm
