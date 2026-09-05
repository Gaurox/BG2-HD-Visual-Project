# Pratiques robustes pour un mod d’interface

> **Statut :** Synthèse pratique  
> **Dernière vérification :** 2026-08-27

## Principe général

Traiter l’interface comme du code : source versionnée, changements atomiques, tests automatisables et restauration fiable.

## Organisation conseillée

```text
mod-ui/
  src/
    ui/
      patches/
      lua/
      assets/
  tests/
  tools/
  dist/
```

`src` contient la vérité ; `override` ne doit être qu’une cible de test ou d’installation.

## Stratégie pour `BGEE.lua`

- utiliser `M_*.lua` pour les deltas ;
- éviter de réaffecter une table entière lorsqu’une insertion suffit ;
- préfixer fonctions et variables ;
- tester avec d’autres fichiers `M_*.lua`.

## Stratégie pour `UI.menu`

- conserver le hash et la version de base attendue ;
- appliquer un patch contextuel, pas un remplacement aveugle ;
- refuser le patch si les ancres ne correspondent pas ;
- sauvegarder le fichier existant ;
- documenter les zones modifiées.

## Tests essentiels

- démarrage du jeu ;
- ouverture de chaque écran touché ;
- retour arrière et fermeture ;
- redimensionnement ou changement de résolution ;
- langue avec texte plus long ;
- réglage de taille de police ;
- installation après un autre mod UI ;
- désinstallation et restauration.

## Anti-corruption

- fermer le jeu avant restauration ;
- ne jamais éditer l’unique copie ;
- conserver des snapshots fréquents ;
- vérifier que F5 n’a pas laissé un fichier partiellement écrit ;
- valider la syntaxe Lua avant lancement si un parseur est disponible.

## Sources
- Guide UI officiel: https://forums.beamdog.com/discussion/48994/the-new-ui-system-how-to-use-it
- Guide M_*.lua: https://forums.beamdog.com/discussion/57210/m-lua-files-and-bgee-lua
