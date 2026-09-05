# Application à un pipeline d’upscale x2 puis x4

> **Statut :** Synthèse spécifique au projet, non officielle  
> **Dernière vérification :** 2026-08-27

## Objectif

Concevoir un pipeline dont le facteur d’échelle est un paramètre, et non une hypothèse dispersée dans le code. Un pipeline x2 propre doit pouvoir évoluer vers x4 sans réécrire toute la logique structurelle.

## Architecture recommandée

```text
lecture ressource
  -> extraction structurelle
  -> reconstruction frame RGBA
  -> upscale image
  -> traitement alpha/contours
  -> recalcul géométrique
  -> découpe/packing cible
  -> reconstruction BAM/PVRZ
  -> validations statiques
  -> test en jeu
```

## Paramètres à centraliser

- `scale_factor` ;
- règle d’arrondi des dimensions ;
- règle d’arrondi des centres ;
- marge de sécurité ;
- taille maximale d’une page/bloc ;
- format de sortie V1 ou V2 ;
- méthode de palette/quantification ;
- politique alpha ;
- conventions de nommage.

## Passage x2 vers x4

Facile si :

- aucune constante `2` n’est codée en dur ;
- la géométrie est recalculée depuis la source, pas depuis le résultat x2 ;
- le packer PVRZ accepte des frames plus grandes et plusieurs blocs ;
- les tests attendus sont exprimés par formule ;
- les couches d’équipement utilisent la même fonction de transformation.

Difficile si :

- le x4 est obtenu en ré-upscalant le x2 ;
- les offsets ont été corrigés manuellement ;
- le packing dépend de tailles fixes ;
- la palette ou l’alpha sont traités différemment selon les cas ;
- les sprites complexes utilisent une branche de code séparée non paramétrée.

## Règle d’or

Toujours générer x2 et x4 depuis la ressource originale. Le x2 peut servir de référence visuelle, pas de source technique du x4.

## Validation en jeu

Créer une scène ou sauvegarde de test couvrant : marche, attaque, lancer, blessure, mort, changement d’orientation, changement d’armure/casque, invisibilité/transparence et superposition avec les décors. Enregistrer des captures image par image lorsque possible.

## Sources
- IESDP BAM V1: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v1.htm
- IESDP BAM V2: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v2.htm
- Beamdog Creature Process: https://files.beamdog.com/
