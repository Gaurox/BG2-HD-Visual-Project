# Inventaire graphique complémentaire BG2EE

Cet inventaire complète les sources métier déjà établies pour les maps, animations de zone et
sprites. Il lit l'installation stock via `chitin.key`, les BIF et les fichiers WBM libres, sans
écrire dans le jeu. Les CSV et manifests versionnés sont les autorités minimales de ces nouveaux
périmètres ; `asset-tracking/` reste leur projection jetable.

## Génération

```powershell
python pipeline/scripts/build_graphics_inventory.py --extract --verify-determinism
python pipeline/scripts/build_graphics_inventory.py --check
```

`BG2EE_GAME_DIR` ou `--game-dir` sélectionne l'installation source. `--extract` matérialise des
copies exactes dans les dossiers `source/` ignorés par Git. Une copie existante dont le SHA-256
diverge provoque un échec : les sources extraites ne sont jamais réécrites silencieusement.

## Autorités et granularité

| Périmètre | Autorité | Granularité |
|---|---|---|
| Cinématiques et tutoriels | `video/index/` | un WBM localisé ou tutoriel ; les WBM de zone restent dans `animations/index/` |
| HUD | `interface/gameplay-hud-bg2ee/index/` | une composition BAM/MOS ; les PVRZ sont des dépendances |
| UI complémentaire | `interface/index/` | une composition MOS non-map ou un BAM dont la famille BIF/nom est explicitement UI |
| Polices | `interface/fonts/index/` | un resref de police ; variantes FNT/TTF comme membres |
| Icônes | `icons/index/` | un jeu BAM partagé par les usages ITM/SPL ; usages dans `usages.csv` |
| Curseurs | `cursors/index/` | le jeu moteur `CURSORS.BAM` ; cycles sans identité sémantique inventée |
| Effets | `effects/index/` | un contrôleur VVC/VEF ; BAM/BMP référencés comme dépendances |
| Projectiles | `projectiles/index/` | un contrôleur PRO ; animations, palettes et effets comme dépendances |
| Compléments graphiques | `graphics/index/supplemental-*` | un jeu d'animation BAM lorsque la famille BIF prouve sans ambiguïté son domaine |

Les BAM `PaperDol`, `OBJAnim` et familles créatures explicites complètent le domaine `sprites`
sans modifier son catalogue de familles existant. Les BAM `SPELAnim`/`MISCAnim` complètent
`effects`. Les familles `25Gui*` complètent `ui`. Une entrée désigne le jeu d'animation moteur ;
ses frames et cycles restent des membres et ne deviennent pas des assets artificiels.

## Contrôles et limites

Chaque ressource présente conserve son resref, son BIF, son locator KEY, sa taille, son format et
son SHA-256. Les tables de dépendances signalent explicitement les références absentes. Le rapport
`graphics/index/coverage.json` mesure les ressources graphiques brutes classées, les réutilisations
entre domaines et les ressources sans propriétaire démontré.

L'état courant laisse 102 BAM issus de BIF de patch génériques non classés. Leur BIF ne suffit pas
à déterminer s'il s'agit d'UI, d'icône, de sprite ou d'effet ; ils restent donc dans
`graphics/index/unclassified-resources.csv` et ne sont pas projetés comme faux assets. Les 64
chevauchements bruts rapportés sont des dépendances partagées, pas des doublons d'assets logiques.

Les inventaires signalent aussi 48 resrefs d'icônes référencés mais absents, deux dépendances VVC
absentes et une animation de projectile absente dans l'installation stock analysée. Aucun de ces
écarts ne produit une décision de production, QA, installation ou release.
