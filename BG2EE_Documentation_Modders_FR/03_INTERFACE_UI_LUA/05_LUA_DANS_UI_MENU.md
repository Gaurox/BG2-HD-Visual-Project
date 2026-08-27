# Lua dans UI.menu

> **Statut :** Officiel Beamdog - synthèse technique  
> **Dernière vérification :** 2026-08-27

## Principe

`UI.menu` accepte des portions de Lua. Le guide Beamdog montre trois usages fondamentaux :

- exécuter un bloc Lua ;
- afficher une variable Lua dans un label ;
- associer une action de bouton à un appel ou une boucle Lua.

## Exemple de texte piloté par une variable

```text
label
{
  area 362 568 50 54
  text lua "chargen.totalRoll"
  text style "normal"
  text align center center
}
```

Le champ affiché suit ici une variable du processus de création de personnage.

## Exemple d’action contrôlée

```lua
while chargen.totalRoll < 85 do
  createCharScreen:OnAbilityReRollButtonClick()
end
```

Cet exemple illustre une boucle et un appel de méthode moteur. Dans un mod réel, toute boucle doit avoir une condition de sortie sûre pour ne pas bloquer l’interface.

## Règles de prudence

- ne pas lancer de boucle sans borne ou watchdog ;
- ne pas supposer qu’une variable interne est stable entre versions ;
- vérifier l’existence d’un objet ou d’une fonction avant l’appel lorsque c’est possible ;
- isoler les variables du mod dans un espace de noms ;
- journaliser les erreurs pendant le développement ;
- tester l’ouverture, la fermeture et la réouverture de l’écran.

## Ce que le guide ne garantit pas

Le document enseigne les bases, mais ne fournit pas une référence exhaustive de toutes les fonctions Lua exposées par le moteur. Pour une fonction non documentée, la considérer comme interne et susceptible de changer.

## Sources
- Release notes 2.0, Using Lua in UI.menu: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
- Guide UI officiel: https://forums.beamdog.com/discussion/48994/the-new-ui-system-how-to-use-it
