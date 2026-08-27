# Interface BG2EE — point d'entrée

**Commencer ici avant de toucher aux menus ou au HUD.** Ce fichier orchestre le domaine :
mécanisme, séquence, critères de passage et état d'avancement. Les autres documents contiennent
le détail d'une étape ou l'inventaire d'un écran.

| Document | Rôle |
|---|---|
| **`README.md`** (ce fichier) | Mécanisme commun, séquence, état des deux branches. |
| [`menus-options-bg2ee/README.md`](menus-options-bg2ee/README.md) | Carte des dossiers de variantes des menus. |
| [`menus-options-bg2ee/docs/MENU_UPSCALE.md`](menus-options-bg2ee/docs/MENU_UPSCALE.md) | **Procédure complète des menus** : ressources, atlas, reprise. |
| [`gameplay-hud-bg2ee/README.md`](gameplay-hud-bg2ee/README.md) | Périmètre du HUD de jeu. |
| [`gameplay-hud-bg2ee/analysis/HUD_RESOURCE_INVENTORY.md`](gameplay-hud-bg2ee/analysis/HUD_RESOURCE_INVENTORY.md) | **Inventaire des pages HUD** et plan d'intégration. |

---

## Ce domaine ne fonctionne pas comme les cartes

Confondre les deux mécanismes est l'erreur la plus coûteuse ici. Les différences sont structurelles :

| | Cartes (`pipeline/`) | Interface (ce dossier) |
|---|---|---|
| Mécanisme | Fichiers `TIS`/`PVRZ` déposés dans `override\` | **Textures DXT5 remplacées au chargement OpenGL** par la DLL |
| Originaux | Remplacés dans l'override | **Jamais écrasés** — les `BAM` et `MOS` d'origine restent intacts |
| Géométrie | Grille WED inchangée, tuiles x4 par défaut | **Géométrie d'interface native** — l'atlas x4 est affiché à taille constante |
| Installation | Copie de fichiers + comparaison SHA-256 | **Scripts `Install-*.ps1` / `Restore-*.ps1`** par variante |
| Activation | Aucune clé | **Clés `[Shaders]`** dans `InfinityEngine-Enhancer.ini` |
| Modèle validé | SeedVR2 7B / LAB | **Topaz Gigapixel Recovery v2, Detail 50, x4** |

> ⚠️ **Le preset Topaz n'est pas le même que celui des cartes.**
> [`pipeline/TOPAZ_GIGAPIXEL_CLI_REFERENCE.md`](../pipeline/TOPAZ_GIGAPIXEL_CLI_REFERENCE.md) décrit
> le preset **CGI neutre** réservé aux corrections locales sous masque des cartes. Il ne s'applique
> pas ici. L'interface utilise **Recovery v2 / Detail 50 / x4, couleurs préservées**, réglage validé
> visuellement sur les 34 éléments du menu principal.

## Principes non négociables

- **La géométrie d'interface ne bouge jamais.** Un élément x4 est affiché à sa taille native ; on
  augmente la densité de pixels, pas la taille apparente. Les coordonnées des `BAM` sont inchangées.
- **Traitement élément par élément, puis recomposition.** Chaque sprite `BAM` et chaque `MOS` est
  upscalé séparément, puis les résultats sont recomposés dans les atlas `DXT5`. Ne jamais upscaler
  un atlas entier : les sprites y sont juxtaposés et fuiraient l'un dans l'autre.
- **Le remplacement runtime est gardé par empreinte.** Chaque page est protégée par sa taille, son
  format DXT5 et son empreinte FNV-1a : une texture de même taille mais différente n'est jamais
  remplacée. Le registre est dans
  `engine/InfinityEngine-Enhancer/source-patchee/src/iee/biglogo_ui_upscale.cpp`.
- **Toute installation est réversible.** Chaque variante fournit son `Install-*.ps1` et son
  `Restore-*.ps1`, avec sauvegarde horodatée de la DLL, de la configuration et des assets.

---

## Séquence

### Étape 0 — choisir la branche

| Cible | Aller à |
|---|---|
| Menu principal, écrans-titre, sélecteur des trois jeux | [`menus-options-bg2ee/docs/MENU_UPSCALE.md`](menus-options-bg2ee/docs/MENU_UPSCALE.md) |
| Habillage du jeu : colonnes, cadres, barre basse | [`gameplay-hud-bg2ee/analysis/HUD_RESOURCE_INVENTORY.md`](gameplay-hud-bg2ee/analysis/HUD_RESOURCE_INVENTORY.md) |

### Étape 1 — identifier les ressources

Repérer les pages `PVRZ` porteuses, leur taille, leur empreinte et les éléments qu'elles composent.
Les deux documents d'inventaire ci-dessus donnent ces tables pour le périmètre déjà analysé.

> **Critère : chaque page visée a taille, empreinte FNV-1a et éléments composés identifiés.**

### Étape 2 — extraire les sources

Pages `PVRZ` décodées et sprites `BAM` extraits dans le `sources/` de la variante.

### Étape 3 — upscale élément par élément

Topaz Gigapixel 8.4.1, **Recovery v2, Detail 50, x4, couleurs préservées**. Les sorties existantes
sont conservées, ce qui permet de ne régénérer qu'un élément ciblé.

> **Critère : un fichier de sortie par élément, aucun atlas traité en bloc.**

### Étape 4 — recomposer les atlas

Le script `build_*_atlases.py --package` de la variante reconstruit les pages `DXT5` et leurs
aperçus PNG.

> **Critère : les pages produites gardent la taille attendue (x4 de l'originale) et le format DXT5.**

### Étape 5 — installation réversible

Jeu **et InfinityLoader fermés**, lancer l'`Install-*.ps1` de la variante. Il sauvegarde la DLL, la
configuration et les assets existants dans son propre `backups/` horodaté.

Vérifier les clés `[Shaders]` requises dans `InfinityEngine-Enhancer.ini` :

```ini
EnableBigLogoX4Test = true
EnableMainMenuX4Test = true
EnableMenuX2Test = false
```

`EnableMenuX2Test = true` active la variante x2 et **prend priorité sur les clés x4** au démarrage.

### Étape 6 — vérification en jeu

Démarrer par **`InfinityLoader.exe`**, jamais `Baldur.exe` ni Steam. Contrôler dans
`InfinityEngine-Enhancer.log` les lignes `Replacing MOS...` : une page attendue absente de ces
lignes signifie que son empreinte ne correspond pas.

> **Critère : une ligne `Replacing MOS...` par page installée.**

Archiver une capture dans le `captures/` de la variante.

---

## État des deux branches

### Menus et écrans-titre — **validé, actif**

Variante active : `menus-options-bg2ee/x4-topaz-recovery-v2-d50/`. Les 34 éléments visuels du menu
principal sont traités et recomposés dans huit atlas DXT5 x4 : fond, cadre décoratif, panneaux de
boutons, titres et médaillon central.

Le sélecteur des trois jeux (`START3EE`) est validé en jeu : 17 exports x4, fusion avec `MOS0181`
et `MOS0258`, plus cinq pages supplémentaires.

Variantes de comparaison conservées, non installées :
`menus-options-bg2ee/archive/variants/`. Elles ne sont ni des méthodes actuelles ni des sources de
release.

### HUD de jeu — **analyse terminée, production partielle**

L'inventaire des pages statiques est fait et aucun fichier chargé par le jeu n'a été modifié par
l'analyse. Un premier lot de production existe :
[`upscale/x4-topaz-recovery-v2-d50/left-toolbar/`](gameplay-hud-bg2ee/upscale/x4-topaz-recovery-v2-d50/left-toolbar/README.md)
— les 17 boutons de `GUILS10.BAM` et leurs quatre états, via `MOS0140` (1024² → 4096²) et
`MOS0141` (512² → 2048²), avec installation et restauration réversibles.

Le reste du périmètre HUD — cadre du journal, barre basse, séparateurs — reste à produire. La zone
centrale de jeu, les portraits, les icônes et le texte sont hors périmètre de cette passe.

---

## Diagnostic

| Symptôme | Cause | Action |
|---|---|---|
| Aucune ligne `Replacing MOS...` dans le log | Clé `[Shaders]` manquante ou à `false` | Vérifier les clés de l'étape 5 |
| Une page précise n'est pas remplacée | Empreinte FNV-1a différente de celle enregistrée | La ressource a changé : réextraire la source et réenregistrer l'empreinte |
| Le x4 ne s'applique pas alors que les clés x4 sont vraies | `EnableMenuX2Test = true` | Le x2 est prioritaire : le passer à `false` |
| Élément flou ou fuite entre sprites voisins | Atlas upscalé en bloc | Reprendre à l'étape 3, élément par élément |
| Élément agrandi à l'écran au lieu d'être plus net | Géométrie d'interface modifiée | Ne jamais changer les coordonnées BAM ; seule la texture change |
| Le jeu ne charge ni EEex ni la DLL | Lancement par `Baldur.exe` ou Steam | Lancer `InfinityLoader.exe` |
