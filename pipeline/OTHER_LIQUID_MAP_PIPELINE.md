# Liquides non classés — garde de production

Les overlays `WT*` ou `YS*` qui ne correspondent pas aux préfixes d'eau validés sont signalés par
le préflight comme `other-liquid` (lave, égout, marais, etc.). Ils ne doivent pas suivre
automatiquement [WATER_MAP_PIPELINE.md](WATER_MAP_PIPELINE.md) : leurs couleurs, effets et règles
de transparence peuvent être différents.

**Exception validée : `WTSWAM`.** Le marais legacy est traité par
[WATER_MAP_PIPELINE.md](WATER_MAP_PIPELINE.md), qui conserve son overlay générique stock mais
restaure, adoucit et libère les alphas des tuiles de zone. Référence : AR0500 — Pont.

**Exception validée : `WTOIL`.** L'huile legacy de six tuiles suit désormais la même branche
que `WTSWAM` et `WTSEW` dans [WATER_MAP_PIPELINE.md](WATER_MAP_PIPELINE.md) : elle est reconnue
comme liquide par le préflight, le builder et le moteur, mais son overlay générique reste
**strictement stock**. Ne jamais installer `WTOIL.TIS` ni ses pages associées : une substitution
du TIS générique crée des répétitions carrées dans les chemins carte/automap.

L'alpha original des tuiles de zone reste le contour réel. Les tuiles de base entièrement opaques,
exclusivement sous `WTOIL` et sans secondaire, doivent être libérées par
`--transparent-full-water-base`; les tuiles à secondaire conservent leurs alphas inverses. La DLL
les traite ensuite dans une source de liquide unique et supprime le passage secondaire `WATER_ALPHA`
pendant l'effet, ce qui élimine la différence de couleur entre cellules avec et sans secondaire.

Références structurelles : AR0413 (283 bases opaques à libérer et 12 sentinelles de bord corrigées
par delta TIS), AR0503 (84) et AR2102 (9). AR0413 a été validée en jeu par l'utilisateur le
2026-08-19 : le détail reproductible, y compris l'interdiction de reconstruire l'atlas pour les
sentinelles, est résumé dans [`../docs/DECISIONS.md`](../docs/DECISIONS.md). AR0603,
AR1203 et AR3024 ne nécessitent pas de libération de base parce que leurs cellules portent déjà une
seconde tuile au masque alpha inverse. Pour AR0503 et AR2102, une reconstruction DXT5 **x1** depuis
les maîtres x1 est une réparation de compatibilité alpha, pas un nouvel upscale.

**Exception validée : `WTSEW`.** L'égout legacy, également un TIS paletté de six frames animées
(64×64), suit exactement la même règle structurelle que `WTSWAM`/`WTOIL` : overlay gardé
**stock**, jamais `WTSEW.TIS` ni ses pages `A*SEW*`/`ASEW*` dans `override`. Il est classé dans
la même famille « liquide » que l'eau pour les besoins des outils (`WATER_PREFIXES` dans
`audit_water_area.py`, `audit_area_preflight.py` et `build_upscaled_area.py`), avec
`overlay_policy: keep-stock`.

Validé sur `AR0404` — Égouts des Bas Quartiers (2026-08-18, run `upscale-01`) : 140 cellules
liquides sur 2397, dont seulement 2 tuiles de base entièrement opaques sans secondaire (libérées
via `--transparent-full-water-base`) ; les 138 autres portaient déjà un masque alpha binaire sur
tuile secondaire, lissé bilinéairement comme tout masque de zone. Build DXT5 x4, PSNR 44,81 dB,
0 tuile hors limites. QA en jeu validée par l'utilisateur le 2026-08-18.

Le diagnostic hors-jeu initial avait confirmé que le build de zone ne modifiait pas l'asset : une
recomposition 100 % vanille (WED + alpha d'origine + frame stock `WTSEW`) et le rendu recomposé
depuis les fichiers installés ne différaient que de 1,2/255. Le défaut observé ensuite en jeu ne
venait donc ni de l'upscale de la map ni d'un remplacement de `WTSEW`, mais du **profil optique
commun** : trop d'écume blanche et de spéculaire éclaircissaient fortement l'eau d'égout.

Correctif matière validé par l'utilisateur sur `AR0404` le 2026-08-23 : le mode moteur `sewage`,
appliqué à toute la famille `WTSEW*` et pas à cette seule zone, utilise une palette brun-olive
sombre, une force d'écume de `0.18` et un spéculaire de `0.08`. Les vagues et les six frames stock
restent inchangées. Ce correctif ciblé rend au fluide une couleur proche du sol sans altérer l'eau,
l'huile, le marais ou la lave.

**Exception validée : `WTLAVA`/`WTLAVB`/`WTLAVC`/`WTLAVD`.** La lave de l'Abyme suit la même
branche structurelle que l'huile : les alphas x1 de la primaire et de la secondaire sont restaurés
par le builder, et les bases opaques exclusivement sous lave et sans secondaire sont libérées par
`--transparent-full-water-base` si l'audit les recense. Le moteur classe cette famille en mode
`lava` et lui applique son profil émissif orange dédié.

État retenu après essai comparatif du 2026-08-23 : les quatre overlays de lave x4 sont conservés
dans l'override. Il s'agit d'une exception explicitement testée et acceptée, pas d'une autorisation
d'upscaler automatiquement toute animation liquide. Référence de QA : `AR2903`.

## Couleur naturelle et profils de matière — état retenu au 2026-08-23

Le traitement est volontairement séparé en deux niveaux :

1. **Niveau générique — couleur auteur.** Le moteur classe le resref de l'overlay, lit sa teinte
   propre et la capture dès le chargement du WED. La couleur ne dépend donc plus de l'ordre de
   chargement des PVRZ. Si l'échantillonnage n'est pas encore disponible, un fallback exact,
   dérivé de l'asset correspondant, évite qu'un liquide hérite du gris ou de la couleur d'un autre.
2. **Niveau matière — comportement optique.** Écume, spéculaire, profondeur, hauts-fonds et
   émission doivent être réglés par famille. Une bonne teinte auteur ne suffit pas : appliquer les
   optiques d'une eau claire à de l'égout, de l'huile ou de la lave peut dénaturer le fluide.

Fallbacks actuellement verrouillés dans le moteur, en RGB linéaire :

| Famille | Teinte de fallback |
|---|---|
| `WTLAKA` | `(0.067051, 0.368126, 0.406010)` |
| `WTLAKB` | `(0.067983, 0.372867, 0.409764)` |
| `WTLAKC` | `(0.066039, 0.363237, 0.403121)` |
| `WTLAKD` | `(0.067860, 0.371557, 0.409053)` |
| `WTLAKE` | `(0.062000, 0.089000, 0.117000)` |
| `WTPOOL` | `(0.089065, 0.149378, 0.234645)` |
| `WTSWAM` | `(0.036129, 0.099635, 0.094358)` |
| `WTSEW` | `(0.044581, 0.059381, 0.041765)` |
| `WTOIL` | `(0.019028, 0.015909, 0.020098)` |

État des profils :

| Matière | État retenu | Zone de référence | À reprendre en fin de patch |
|---|---|---|---|
| Eau (`WTLAK*`, `WTPOOL`) | Teinte auteur + optiques eau ; état AR2300 validé | `AR2300` | Contrôle global seulement |
| Égout (`WTSEW*`) | Profil brun-olive ciblé ; écume `0.18`, spéculaire `0.08` ; validé | `AR0404` | Contrôle de non-régression sur d'autres égouts |
| Lave (`WTLAV*`) | Profil émissif orange dédié ; overlays x4 conservés | `AR2903` | Contrôle global des quatre variantes |
| Marais (`WTSWAM*`) | Teinte propre correcte, optiques encore communes à l'eau | `AR1201` | Calibrer écume, spéculaire et profondeur |
| Huile (`WTOIL*`) | Teinte propre correcte, optiques encore communes à l'eau | `AR0413` | Calibrer brillance, profondeur et écume |
| Goo (`WTGOO*`) | Famille reconnue par le moteur, profil non calibré | à choisir | Échantillonner l'asset et créer une QA de référence |

La méthode est donc **généralisable**, mais pas sous la forme d'un correctif unique appliqué à
tous les fluides. Il faut réutiliser la classification et la capture de couleur auteur, puis créer
un profil optique ciblé pour chaque matière après comparaison vanilla/patch. Le profil `sewage` ne
doit jamais être copié tel quel sur l'huile, le marais, le goo ou une eau claire.

État technique reproduisible :

- `InfinityEngine-Enhancer.dll` actif : SHA-256
  `A3809480CA5F7E8F3EC6F1525F45115CE791975AD0046137688DC0B63900555C` ;
- `override/fpSEAM.glsl` actif : SHA-256
  `606E26CD9993C9520B0E48725B6DF6AEA314A9CB1FC8DD4FCE90DD6594002B90` ;
- sauvegarde réversible du correctif égout :
  `backups/engine/InfinityEngine-Enhancer-20260823-011213-wtsew-dirty-grade-test/`.

### Reprise prévue à la fin du patch

Pour chaque famille encore non calibrée : inventorier tous les resrefs, choisir une zone témoin,
comparer vanilla et patch dans les mêmes conditions, régler seulement son profil matière, tester
une zone secondaire de non-régression, puis verrouiller les paramètres et les hashes ici. Ne pas
modifier les assets globaux pendant cette passe tant qu'un défaut d'asset distinct n'est pas
démontré.

**État pour tout autre liquide : aucune recette de matière générique n'est validée.** Le préflight
bloque la production jusqu'à ce qu'un cas de référence documente l'overlay, son alpha, son
éventuelle animation et les paramètres de build/QA appropriés. Une fois validé, ajouter sa
classification, sa route et son profil matière au lieu d'élargir sans preuve la liste des préfixes
eau ou de réutiliser le profil d'un autre fluide.
