# Sauvegardes, nettoyage et reproductibilité

> **Statut :** Synthèse pratique  
> **Dernière vérification :** 2026-08-27

## Avant une mise à jour du jeu

Les release notes Beamdog avertissent historiquement que l’application d’une mise à jour peut effacer les mods installés. Conserver :

- une copie de l’installation propre ;
- le journal WeiDU ;
- les sauvegardes ;
- les fichiers de configuration ;
- les ressources générées non reproductibles ;
- la version exacte du jeu et des outils.

## Construction reproductible

Une commande unique doit pouvoir :

1. nettoyer les sorties ;
2. vérifier les dépendances ;
3. reconstruire les ressources ;
4. exécuter les validations ;
5. générer le manifeste ;
6. empaqueter la distribution ;
7. calculer les hash.

## Grand ménage

Supprimer ou déplacer hors du contexte actif :

- anciennes sorties remplacées ;
- essais manuels sans provenance ;
- copies de ressources du jeu non nécessaires ;
- logs très anciens ;
- scripts doublons ;
- variantes abandonnées ;
- archives de build intermédiaires.

Conserver dans une archive froide uniquement ce qui a une valeur de preuve ou de retour arrière.

## Données critiques

Pour chaque ressource produite : source, paramètres, version de modèle/outil, seed si pertinente, hash de sortie, statut de validation et version du moteur testée.

## Sources
- Avertissement des release notes 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
