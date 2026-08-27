# Mécanismes externalisés en 2DA et SPL

> **Statut :** Officiel Beamdog - paraphrase technique  
> **Dernière vérification :** 2026-08-27

## Principe

Beamdog appelle « externalisation » le déplacement d’un comportement auparavant inaccessible vers une ressource modifiable par les outils existants.

## `PPBEHAVE.2da` - réactions au pickpocket

Les options documentées sont activées par défaut ; une valeur `0` désactive la fonction correspondante.

- `TURN_HOSTILE` : déclenche une réaction d’attaque après un échec ;
- `REPORT_FAILURE` : envoie le trigger d’échec de pickpocket ;
- `BREAK_INVISIBILITY` : même une réussite brise furtivité et invisibilité.

## `BARDSONG.spl` - chant de barde par défaut

Les effets du chant de barde standard sont regroupés dans cette ressource. Modifier le SPL permet d’altérer le comportement par défaut sans recréer tout le système.

## `STATDESC.2da` - icônes d’état

Une colonne `BAM_FILE` permet de référencer un BAM qui sera réduit pour devenir une icône d’état sur le portrait. Une cellule vide ou `****` est ignorée par les opcodes utilisant la table.

Risques à tester : ressource absente, proportions extrêmes, alpha/palette, lisibilité après réduction et conflit d’index.

## `SAVENAME.2da` - noms et rotation des sauvegardes

Colonnes documentées :

- `SLOTNAME` : texte utilisé pour le nom ;
- `START` : index de départ du slot ;
- `COUNT` : nombre de sauvegardes tournantes.

Cette table permet notamment d’ajuster la quantité de sauvegardes rapides conservées.

## `CONCENTR.2da` - interruption d’incantation

Modes documentés :

- `0` : tout dégât interrompt ;
- `1` : `1d20 + chance` contre `niveau du sort + dégâts reçus` ;
- `2` : `1d20 + Concentration` contre `15 + niveau du sort`.

Beamdog avertit que les jeux Baldur’s Gate n’ont pas de compétence Concentration native. Le mode `2` retombe donc sur une formule simple basée sur chance dans ce contexte.

## Bonne pratique de patching

Ne jamais livrer une table complète lorsque quelques cellules suffisent. Utiliser WeiDU pour copier, modifier seulement les lignes/colonnes nécessaires et conserver les ajouts des autres mods.

## Sources
- Release notes officielles 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
