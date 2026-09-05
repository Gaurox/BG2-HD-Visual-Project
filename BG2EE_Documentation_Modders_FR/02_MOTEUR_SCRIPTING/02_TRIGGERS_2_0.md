# Triggers ajoutés et documentés en version 2.0

> **Statut :** Officiel Beamdog - paraphrase technique  
> **Dernière vérification :** 2026-08-27

## Liste documentée

| Trigger | Entrée IDS | Fonction |
|---|---:|---|
| `ModalStateObject(O:Object*, I:ModalState*Modal)` | `0x40F1` | Vrai si la créature utilise l’état modal demandé, par exemple furtivité ou danse du chaman. |
| `ClassLevel(O:Object*, I:Category*CLASSCAT, I:Value*)` | `0x40FD`, `0x40FE`, `0x40FF` | Compare le niveau dans une catégorie de classe : voleur, guerrier, mage ou prêtre. |
| `HaveKnownSpell(I:Spell*Spell)` | `0x4102` | Vrai si la créature courante connaît le sort demandé. |
| `IsForcedRandomEncounterActive(S:Area*)` | `0x40FB` | Vrai si une rencontre aléatoire a été forcée pour la zone mais ne s’est pas encore déclenchée. |
| `OriginalClass(O:Object*, I:Class*CLASS)` | `0x40EA` | Vrai si la classe inactive d’un personnage biclassé correspond. |
| `SecretDoorDetected(O:Object*, I:Open*BOOLEAN)` | `0x4100` | Teste si une porte secrète est marquée comme détectée ou non. |
| `ImmuneToSpellLevel(O:Object*, I:Level*)` | `0x40F9` | Vrai si la créature est immunisée aux sorts du niveau demandé. |
| `StoryModeOn()` | `0x40FA` | Vrai si le mode Histoire est actif. |

## Notes de comportement

### `ClassLevel`

Les catégories sont définies dans `CLASSCAT.IDS`. Le document présente trois entrées IDS pour des variantes de comparaison ; vérifier dans la version actuelle la correspondance exacte entre égalité, supérieur et inférieur avant d’écrire un script générique.

### `OriginalClass`

Conçu pour les personnages biclassés. Les monoclassés et multiclassés ne doivent pas répondre vrai. `OriginalClass(0)` est documenté comme vrai pour toute créature biclassée.

### `SecretDoorDetected`

À employer uniquement sur une porte secrète. Une porte ordinaire n’est pas marquée comme « détectée » par ce mécanisme.

## Modèle de validation

Pour chaque trigger :

1. préparer un cas vrai et un cas faux ;
2. afficher une trace par `DisplayStringHeadNoLog` ou un journal de test ;
3. tester après sauvegarde/rechargement ;
4. tester avec des objets cibles absents ou invalides ;
5. confirmer la signature réellement exposée dans `TRIGGER.IDS` de l’installation cible.

## Sources
- Release notes officielles 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
