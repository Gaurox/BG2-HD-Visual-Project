# Suivi projectiles — analyse des travaux

- Instantané UTC : `2026-11-09T21:12:44.996260+00:00` ; [rapport figé](analysis.json).
- Projection générée ; décisions métier : `index/work-tracking.json`. Ne pas éditer les CSV générés.
- Cette analyse conserve les autorités effets/animations/sprites ; aucune production, QA, installation ou release accordée.

| Inventaire | Nombre |
|---|---:|
| PRO stock vérifiés contre KEY/source/SHA | 243 |
| Types 2 / 3 | 100 / 143 |
| Entrées PROJECTL (incluant plusieurs IDs par PRO) | 253 |
| IDs moteur sans PRO suivis, dont IDs non résolus | 78 |
| BAM visuels explicites + INI fumées/fragments | 107 |
| Contextes source canonique + palette RGB | 175 |
| SPL / ITM / EFF parcourus | 1648 / 2867 / 559 |
| Références dans les capacités SPL/ITM | 6086 |

## Travail sur les images — sans double inférence

| État observé du contexte | Nombre | Action |
|---|---:|---|
| Asset accepté, source et métadonnées liées vérifiées | 86 | Réutiliser le résultat exact ; préserver la portée QA. |
| Pack de palette vérifié, pas de QA projectile déduite | 81 | Réutiliser ; raccord propriétaire/palette et QA restent distincts. |
| Upscale spatial présent | 0 | Terminer/reprendre temporalité et pack ; ne pas relancer SeedVR. |
| Job réservé sans sortie spatiale complète | 0 | Reprendre le job existant ; aucun lot en doublon. |
| Masque noir natif | 8 | Aucun upscale IA ; préserver indices/alpha/mélange natifs. |
| Source sans sortie correspondante trouvée | 0 | Confirmer chemin moteur puis produire seulement ce manque. |

### Sources nouvelles candidates

| BAM | Appels PRO/rôle | Source | Poses natives uniques / correspondances exactes existantes |
|---|---|---|---|

- Ces trois BAM ne sont ni des équipements superposés ni des sprites multipart Q3m : animations moteur de classe `effect`. Le rendu de ces propriétaires reste à raccorder/confirmer.
- Planche : `analysis/20261109-cow-raccorde-projectiles3-valides-v5/new-source-candidates.png`.

### Cas à préserver

- Masques sans IA : `SHAREAB`, `SHGLYPH`, `SHSKULL`, `SPSDIMSP`, `SPSDRABU`, `SPSDRAE2`, `SPSHADOW`, `TRAVELB`.
- Alias exact `SPIPLARI` → production `SPIPLAAI` : preuve `effects/batches/lot26-accepted-20261017-v1/acceptance.json:source_alias`. Ne pas produire SPIPLARI une seconde fois.
- Missile magique : preuve historique ciblée `effects/index/qa-decisions/SPMAGMIS/2026-09-07-accepted-spmagmis-final-fx-r8.json`. Elle ne valide pas chaque ID moteur/compte de missiles.
- `PRO`, `VVC`, `VEF`, `BMP` de palette, IDs, sons, particules procédurales : pas de tâche IA autonome.

## Travail sur les projectiles complets

| Prochaine action statique dominante | PRO |
|---|---:|
| `native-or-non-raster-route-review` | 13 |
| `resolve-engine-visual-routes` | 91 |
| `resolve-missing-dependency` | 1 |
| `reuse-outputs-and-check-owner-contract` | 138 |

- Ces classes sont exclusives par priorité ; les tâches détaillées peuvent se cumuler dans `index/work-items.csv:owner_contract_tasks`.
- Couverture images ≠ couverture projectile : consulter `accepted_asset_contexts`, `verified_pack_contexts`, `spatial_only_contexts`, puis les états indépendants intégration/QA/installation/release.
- `LIGHTSTO` déclare `MAGMIS`, absent de KEY/BIF. Ne pas remplacer arbitrairement par SPMAGMIS ; vérifier usage et branche native.
- Appels implicites : 29 fumées, 4 fragments, 21 effets d’explosion moteur ; liste exhaustive `index/engine-routes.csv`.
- Les fumées 0x0300/0x0301, les fragments 0x0400 et les effets FIREBALL sont des chemins moteur : identifier leurs ressources effectives avant toute inférence supplémentaire. Un libellé IDS ne prouve pas un BAM.
- Les IDs moteur sans PRO possèdent leurs propres lignes (`index/engine-projectiles.csv`) ; instantané/sans image et variants multi-missiles ne doivent pas devenir autant de jobs IA.

## Contrat runtime observé statiquement

- `hooks.cpp:detour_projectile_bam_render` : cellule projectile primaire via offset manifesté ; `g_effectOnceProfile=false` = table de base, pas preuve d’une boucle universelle.
- `hooks.cpp:resolve_effect_animation_cell` : recherche par RESREF/séquence/slot/géométrie ; aucun choix de pack par palette PRO dans cette résolution.
- Un RESREF partagé par plusieurs palettes/contextes ne peut pas être couvert par la simple présence d’une entrée du registre. Prévoir dispatch par propriétaire/palette ou représentation compatible ; conserver les sorties existantes.
- Fumées/fragments, ombres/traînées et autres classes : ne pas déduire leur prise en charge du seul hook de la cellule primaire. Vérifier le chemin final et préserver le fallback natif.
- Catalogue installé : 743 noms, SHA registre/manifeste concordants ; aucune observation de draw ni validation palette/propriétaire actuelle déduite.

## Fichiers et commandes

| Besoin | Fichier |
|---|---|
| Une ligne par PRO, travaux/états indépendants | `index/work-items.csv` |
| IDs moteur sans PRO, décisions et travaux distincts | `index/engine-projectiles.csv` |
| Déduplication des BAM + alias exacts | `index/visual-assets.csv` |
| Une ligne par source canonique + palette réalisée | `index/visual-contexts.csv` |
| Décisions explicites, notes/priorités humaines | `index/work-tracking.json` |
| Dépendances développées, PRO secondaires, usages, contrats natifs | `analysis/20261109-cow-raccorde-projectiles3-valides-v5/` |
| Source/QA/run/pack/palette et SHA des entrées | `analysis/20261109-cow-raccorde-projectiles3-valides-v5/analysis.json`, `contexts.json` |

```powershell
python -B pipeline/scripts/projectile_tracking.py status
python -B pipeline/scripts/projectile_tracking.py queue --action new-context-required
# Actualiser : choisir un NOUVEAU nom, les instantanés existants sont immuables.
python -B pipeline/scripts/projectile_tracking.py refresh --snapshot AAAAMMJJ-vN
```

## Limites vérifiables

- Analyse exhaustive des 243 PRO stock, références explicites développées, IDs/flags et autorités disponibles. Résolution des chemins hardcodés et validation en jeu restent des travaux explicitement listés, pas des images déclarées terminées.
- Sources hachées ; sélections : SHA source/QA/run/manifest/registre ; backings : existence/taille. Pas de rehash global des payloads, ni de modification du jeu/release.
- Les usages SPL/ITM sont statiques : absence de référence directe ne signifie pas inutilisé (scripts/opcodes/création moteur). Les 559 EFF ont leur champ de provenance inspecté, sans le confondre avec un lancement.
- Snapshot d’une production pouvant évoluer : relancer `refresh` pour actualiser. Entrées changeantes pendant cette lecture : `[]`.
- Références de format : [PRO](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/pro_v1.htm), [PROJECTL / IDs sans PRO](https://gibberlings3.github.io/iesdp/files/ids/bgee/projectl.htm).
