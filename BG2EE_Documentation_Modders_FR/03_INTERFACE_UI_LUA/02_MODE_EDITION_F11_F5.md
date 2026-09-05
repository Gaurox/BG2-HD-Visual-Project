# Mode d’édition UI : F11, F5 et Tab

> **Statut :** Officiel Beamdog - procédure paraphrasée  
> **Dernière vérification :** 2026-08-27

## Activation

Dans le fichier `baldur.lua` du dossier utilisateur/sauvegardes, ajouter :

```lua
SetPrivateProfileString('Program Options','UI Edit Mode','1')
```

## Commandes

### F11

Entre dans le mode d’édition. Les rectangles des éléments deviennent manipulables. Un second appui quitte le mode et enregistre les changements.

### F5

Recharge `UI.menu` pour prévisualiser les modifications sans redémarrer le jeu. Selon l’écran, il peut être nécessaire de changer de menu pour voir tous les effets.

### Tab

Lorsque le pointeur survole un élément, Tab affiche des informations de localisation : type du contrôle, ligne approximative dans `UI.menu`, position et taille.

## Déplacement et redimensionnement

- lorsque tout le rectangle est sélectionné, le glisser déplace l’élément ;
- lorsque le bord est sélectionné, le glisser redimensionne le cadre ;
- redimensionner un cadre graphique change surtout la zone visible, pas nécessairement l’échelle du BAM ;
- le texte peut se réorganiser automatiquement dans un cadre plus étroit.

## Risques signalés par Beamdog

- sauvegarder fréquemment ;
- conserver des copies de `UI.menu` ;
- ne pas renommer ou supprimer `UI.menu` pendant que le jeu tourne ;
- presser F5 après suppression du fichier peut provoquer un crash ;
- modifier le fichier pendant l’exécution peut le corrompre.

## Procédure sûre

1. Copier l’installation ou le fichier original.
2. Activer le mode.
3. Effectuer un seul changement.
4. Quitter F11 pour enregistrer.
5. Fermer le jeu avant de restaurer un fichier.
6. Comparer le diff texte et conserver le patch minimal.

## Sources
- Guide UI officiel: https://forums.beamdog.com/discussion/48994/the-new-ui-system-how-to-use-it
- Release notes 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
