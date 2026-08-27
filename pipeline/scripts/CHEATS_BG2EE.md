# Cheats BG2EE — console de debug

Aide-mémoire pour la QA en jeu (étape 7 du pipeline). Prérequis : mode debug actif dans
`Baldur.lua` (voir `Enable-BG2Debug.ps1` / raccourci `Activer-Cheats-BG2.lnk`, réinitialisé à
chaque fermeture du jeu). Console : **Ctrl+Espace**, jeu lancé via `InfinityLoader.exe`.

## Touches de triche (raccourcis clavier)

Nécessitent d'avoir tapé une fois dans la console : `CLUAConsole:EnableCheatKeys()`.

| Touche | Effet |
|---|---|
| **Ctrl+J** | **Téléporte le groupe à la position du curseur de la souris** |
| Ctrl+Y | Tue la créature sous le curseur |
| Ctrl+Q | La créature sous le curseur rejoint le groupe |
| Ctrl+R | Soigne/ressuscite le personnage sous le curseur |
| Ctrl+S | Change l'animation d'avatar sélectionnée |
| Ctrl+X | Affiche position souris/tuile/case de recherche/zone (debug overlay) |

## Commandes de console les plus utiles

Toutes se tapent dans la console (Ctrl+Espace), avec ou sans le préfixe `CLUAConsole:` selon
le raccourci déjà en place dans le projet (`C:MoveToArea(...)` = `CLUAConsole:MoveToArea(...)`).

| Commande | Effet |
|---|---|
| `MoveToArea("ARxxxx")` | Téléporte le groupe vers la zone `ARxxxx` |
| `ExploreArea()` | Révèle entièrement le brouillard de guerre de la zone courante |
| `EnableCheatKeys()` | Active les touches de triche ci-dessus (une fois par session) |
| `SetCurrentXP(x)` | Fixe l'XP des personnages sélectionnés à `x` (plafond 2 950 000) |
| `AddGold(x)` | Ajoute `x` pièces d'or au groupe |
| `CreateItem("resref", n, c1, c2)` | Crée `n` exemplaires de l'objet `resref` (charges `c1`/`c2` optionnelles) |
| `CreateCreature("resref")` | Fait apparaître la créature `resref` |
| `SetGlobal("nom","zone",valeur)` | Fixe une variable globale de script |
| `GetGlobal("nom","zone")` | Affiche la valeur d'une variable globale |
| `SetWeather(x)` | Change la météo courante |
| `PlayMovie("resref")` | Joue la cinématique `resref` |
| `StrrefOn()` / `StrrefOff()` | Affiche/masque le strref à côté de chaque texte |

## Usage QA upscale

Séquence type pour contrôler une zone traitée :

```
C:EnableCheatKeys()
C:MoveToArea("ARxxxx")
C:ExploreArea()
```

Puis `Ctrl+J` en pointant la souris sur un point précis de la carte pour s'y rendre
instantanément sans marcher — pratique pour inspecter un coin éloigné (rive, tuile secondaire,
overlay liquide) sans traverser toute la zone.

## Sources

- [CLUA Console — IESDP (Gibberlings3)](https://gibberlings3.github.io/iesdp/appendices/clua/bg2.htm)
- [Console — Baldur's Gate Wiki (Fandom)](https://baldursgate.fandom.com/wiki/Console)
