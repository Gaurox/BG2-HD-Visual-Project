# Recherche palettes dynamiques — 0x6110

| Rôle | Référence |
|---|---|
| Guide de développement | [GUIDE_DEFINITIF_SPRITES_HD_BG2EE.md](GUIDE_DEFINITIF_SPRITES_HD_BG2EE.md) |
| Synthèse antérieure | [GUIDE_ULTIME_SPRITES_HD_BG2EE.md](GUIDE_ULTIME_SPRITES_HD_BG2EE.md) ; historique, corrigée par le guide définitif |
| Étude Claude, E3/E3b/E5 | [Guide](ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/GUIDE_ClaudeCode_HD_0x6110_palettes_dynamiques.md), [revue croisée Markdown](ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/REVUE_CROISEE_Codex_ClaudeCode_0x6110.md) |
| Étude Codex, moteur/inventaire/upscale | [Guide](CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.md) |
| Comparaison corrigée, temporel/3 bits | [Comparaison](CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/codex_palette_study_20260929/COMPARAISON_CODEX_CLAUDE_0x6110.md), [chemins](CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/codex_palette_study_20260929/README.md) |
| Implémentation actuelle de l'essai | [P1 2026-09-30](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p1-20260930-v1/README.md) |

## Statut

- Études = provenance historique ; conclusions E3/E3b/E5 conservées, pas de nouvelle validation ingame.
- P1 = Q3m K6, critères hors ligne satisfaits ; runtime/installation/release actuels non remplacés.
- Production courante : [sprite/README.md](../README.md), [PROCESSING.md](../PROCESSING.md).
- Scripts d'étude conservés comme preuves de protocole. Leurs chemins Desktop, `parents[3]`, sorties fixes et fetch `master` sont historiques ; ne pas les relancer dans ces dossiers. Les nouveaux essais utilisent `pipeline/scripts/palette_eval.py` et une nouvelle version de run.

## Rangement et Git

- Une arborescence Codex principale : inventaire, `palette/`, `upscale/`, `source_reference/`, `sources_inventory/`, `vanilla_inventory/`.
- `codex_palette_study_20260929/` conserve uniquement les ajouts de comparaison et leur protocole.
- Versionnés : Markdown/TXT, scripts, CSV/JSON/2DA/INI/IDS, inventaire `.json.gz`, tableaux numériques NPZ/NPY et provenance moteur épinglée.
- Locaux, ignorés : HTML, PNG/GIF/WEBP/BMP/autres médias, BAM extraits, ZIP de livraison, environnement `research_deps/`, caches, originaux de documents dont seuls les liens ont été adaptés.
- Les liens vers les médias des rapports historiques sont des références locales ; ces médias ne sont pas livrés par Git.
- `.gitattributes` préserve les octets importés : pas de conversion CRLF/LF, hashes des preuves historiques conservés.

## Consolidation 2026-09-30

- Inventaire initial : 5 117 fichiers, 191 090 818 octets ; 1 350 groupes SHA-256 dupliqués, 3 393 copies supplémentaires.
- 3 121 copies identiques supprimées (78 032 479 octets), dont 3 118 copies Codex et trois alias texte redirigés ; toute suppression comparée à sa copie conservée.
- 140 fichiers uniques déplacés depuis la copie d'étude vers l'arborescence Codex principale ; revue croisée et mesures conservées.
- 45 caches Python retirés ; JSON décompressé de 52 680 419 octets retiré après comparaison exacte avec `assets_inventory.json.gz`.
- 270 noms de ressources/visuels identiques conservés par liens physiques NTFS : noms et contenus inchangés, stockage partagé.
- Tous les contenus historiques uniques conservés, hormis les caches reconstruisibles et le JSON disponible octet pour octet par décompression.
- Revue Claude HTML transcrite en Markdown : 194 blocs texte vérifiés ; 22 lignes E5 matérialisées et comparées au JSON embarqué.
- Les deux guides de synthèse à la racine n'ont pas été modifiés par cette consolidation.
