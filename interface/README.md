# Interface BG2EE

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

L'interface remplace des textures DXT5 au chargement OpenGL ; les BAM/MOS natifs et leur géométrie
restent inchangés. Ne pas appliquer le pipeline TIS/PVRZ des cartes.

## Périmètre réduit — décision utilisateur 2026-11-10

- Conserver : fonds/grands panneaux des menus, grands titres et médaillons, `DONATE` (fondu alpha
  natif), `INNROOMS`, papier `QUESTBG`, colonnes décoratives gauche/droite.
- Sortir de la production UI : boutons, petites icônes, contrôles/texte.
- Cadres `GMPWMSG0`, `GUWBTP10`, `GUISTBBB`, `GUWPKPC0` : finalement conservés,
  décision utilisateur révisée pendant la revue visuelle ; boutons superposés exclus.
- Réutiliser les exports déjà validés ; ne pas les régénérer pour ce changement de périmètre.
- Éléments conservés/exclus dans une même page : nouvelle recomposition ciblée avant installation.
  Ne pas activer un ancien pack complet pour rétablir seulement un fond.
- Analyse et décisions : [`analysis/large-surfaces-20261110-v1/README.md`](analysis/large-surfaces-20261110-v1/README.md).
- Cette décision de périmètre ne supprime aucun historique et ne modifie pas à elle seule
  installation, QA acquise ou release.

## Autorités et routage

| Besoin | Référence |
|---|---|
| Inventaire UI global | `index/manifest.json`, `resources.csv`, `dependencies.csv` |
| Menus et sélecteur | [`menus-options-bg2ee/docs/MENU_UPSCALE.md`](menus-options-bg2ee/docs/MENU_UPSCALE.md) |
| Sources menus | `menus-options-bg2ee/reference/extraction-manifest.json` |
| Pack x4 menus | `menus-options-bg2ee/x4-topaz-recovery-v2-d50/sprite-manifest.json` |
| Pack sélecteur | `.../selection-des-trois-jeux/assets/asset-manifest.json` |
| HUD | [`gameplay-hud-bg2ee/README.md`](gameplay-hud-bg2ee/README.md) |
| Inventaire HUD | `gameplay-hud-bg2ee/index/` |
| Polices | `fonts/index/` |
| Release | `../releases/BG2-HD-Upscale/manifests/content.json` |

Les quantités et états ne sont pas recopiés ici.

## Contrat

- Topaz Gigapixel Recovery v2, Detail 50, x4, couleurs préservées.
- Extraire/upscaler chaque sprite BAM ou élément MOS séparément, puis recomposer l'atlas.
- Ne jamais upscaler un atlas complet : les éléments voisins contamineraient leurs bords.
- Dimensions physiques de page ×4, format DXT5, géométrie UI x1 inchangée.
- Chaque remplacement est gardé par format, taille et empreinte FNV-1a dans le renderer.
- Chaque variante possède son installateur/restaurateur et son backup propre.

Le preset CGI de [`../pipeline/TOPAZ_GIGAPIXEL_CLI_REFERENCE.md`](../pipeline/TOPAZ_GIGAPIXEL_CLI_REFERENCE.md)
est réservé aux corrections locales de cartes.

## Séquence

1. Identifier les pages et éléments dans les manifests du domaine.
2. Extraire les sources natives sans les modifier.
3. Upscaler élément par élément avec le preset UI.
4. Exécuter avec `--package` le builder Python nommé par le README de la variante.
5. Vérifier dimensions, DXT5, previews et hashes.
6. Jeu et InfinityLoader fermés : utiliser le script `Install-*.ps1` de la variante.
7. Pour la QA locale, démarrer via InfinityLoader et contrôler les lignes `Replacing MOS...`.
8. Restaurer avec le script `Restore-*.ps1`; la release normale se lance ensuite via Steam.

## Diagnostic

| Symptôme | Vérification |
|---|---|
| aucun remplacement | clés `[Shaders]`, chargement EEex/DLL |
| une page ignorée | empreinte FNV-1a et dimensions de la source |
| x4 inactif | `EnableMenuX2Test` ne doit pas prendre priorité |
| fuite/flou entre éléments | atlas probablement traité en bloc |
| taille apparente modifiée | coordonnées BAM/MOS modifiées à tort |

Une validation locale n'intègre pas automatiquement `content.json`.

Révision du périmètre HUD : tous les candidats explicitement refusés lors de la revue sont finalement
conservés (dont `GUIW12_1..8`, `GUIVERB`, `DLGDIVI`, `PAPERSEP`, `PCHAPTER`).
Décisions finales : `analysis/large-surfaces-20261110-v1/decisions.json` ; boutons/icônes/contrôles hors périmètre.

## Suivi actif

Autorité des travaux retenus : [suivi UI/HUD](tracking/README.md).
Les inventaires source et anciens packs restent historiques ; leurs boutons/icônes ne sont plus
des travaux actifs. États production, QA, installation et release séparés par ressource.

Quatre menus SeedVR2 7B x4 retenus pour test ingame (2026-11-11) : `INVENTOR`, `QUESTBAK`, `GUIREC2`, `STONEOPT`.
Installation/retour exact : [`integration/four-menus-seedvr7b-20261111-v1/README.md`](integration/four-menus-seedvr7b-20261111-v1/README.md).
La recette Topaz reste inchangée pour les autres ressources.

Lot supplémentaire 2026-11-11 : dix compositions 7B x4 retenues et installées, QA ingame en attente.
Reçu/restauration : `integration/next-ten-seedvr7b-x4-20261111-v1/README.md`.
La recette inscrite dans `index/work-tracking.json:resources[].production` prévaut pour chaque
ressource ; les lots SeedVR retenus ne changent pas les sorties Topaz déjà validées.

Lot4 : `integration/fourth-ten-seedvr7b-x4-20261111-v1/`, dix nouvelles ressources installées pour QA ; DONATE/INNROOMS traités par frame, alpha natif progressif préservé après DXT5.

Lot6 installé/validé sur rendu observé : `integration/sixth-ten-seedvr7b-x4-20261111-v1/` (GUIDLC tactile hors observation PC). Lot7 produit pour comparaison : `experiments/seventh-ten-seedvr7b-x4-20261111-v1/`, dix fonds/panneaux 7B x4, non installés ; suivi et compteurs courants dans `tracking/progress.json`.

Mise à jour lot7 : installé après validation des planches ; `integration/seventh-ten-seedvr7b-x4-20261111-v1/README.md`. Dix variantes historiques sans route actuelle établie, pas de QA ingame inférée. Total71/204 sorties complètes retenues +1 partielle ; compteurs canoniques `tracking/progress.json`.
