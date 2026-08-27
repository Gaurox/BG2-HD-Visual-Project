# Fichiers M_*.lua et modification incrémentale de BGEE.lua

> **Statut :** Officiel Beamdog - version 2.2  
> **Dernière vérification :** 2026-08-27

## Fonctionnement documenté

À partir de 2.2, le moteur charge les fichiers `.lua` dont le nom commence par `M_` lorsqu’ils sont placés dans `override`. Ils sont évalués en complément de `BGEE.lua`.

## Usage recommandé

Ajouter ou modifier une petite partie d’une table plutôt que remplacer tout le fichier système.

Exemple générique d’ajout de portrait :

```lua
local function ajouter_portrait(nom, genre)
  table.insert(portraits, {nom, genre})
end

ajouter_portrait('MODHEROL', 1)
```

Exemple de modification ciblée d’une couleur :

```lua
fontcolors['1'] = 'FFCAE2E9'
```

## Bénéfice de compatibilité

Une mise à jour du jeu peut modifier `BGEE.lua`. Un mod distribuant le fichier complet risque alors d’effacer les corrections de Beamdog ou celles d’un autre mod. Un fichier `M_<mod>.lua` ne porte que le changement voulu.

## Limite officielle

Cette fonction agit sur l’environnement Lua, pas sur `UI.menu`. Beamdog précise qu’il n’existe pas, dans ce mécanisme, de patch incrémental équivalent pour `UI.menu`.

## Points non précisés officiellement

- ordre garanti entre plusieurs fichiers `M_*.lua` ;
- politique de résolution des noms identiques ;
- stabilité de toutes les tables internes ;
- comportement exact en cas d’erreur Lua.

Ne pas dépendre d’un ordre implicite entre plusieurs fichiers. Regrouper les dépendances d’un même mod dans un fichier ou mettre en place des vérifications explicites.

## Sources
- Release notes 2.2: https://items.gog.com/releasenotes_2_2.pdf
- Guide officiel M_*.lua: https://forums.beamdog.com/discussion/57210/m-lua-files-and-bgee-lua
