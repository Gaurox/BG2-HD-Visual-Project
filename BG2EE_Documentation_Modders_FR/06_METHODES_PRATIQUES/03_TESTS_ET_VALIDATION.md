# Plan de tests et validation

> **Statut :** Synthèse pratique  
> **Dernière vérification :** 2026-08-27

## Niveaux de test

### 1. Validation structurelle

Le fichier se parse, les offsets restent dans les limites, les indices pointent vers des entrées existantes, les ressources référencées existent.

### 2. Validation sémantique

Cycles, orientations, actions, textes, tables et scripts ont le sens prévu.

### 3. Validation visuelle

Aucun décalage, trou, frange, scintillement, clipping, changement de palette ou anomalie d’alpha.

### 4. Validation en jeu

Chargement, sauvegarde, changement de zone, combat, mort, équipements, interface, résolution et langue.

### 5. Compatibilité

Installation propre, après d’autres mods, désinstallation, mise à jour et version 2.7.

## Rapport PASS/FAIL

Chaque test doit avoir :

- identifiant stable ;
- entrée ;
- résultat attendu ;
- résultat observé ;
- logs/captures ;
- version ;
- statut ;
- lien vers le correctif éventuel.

## Critères de blocage pour les sprites

- compteur de cycles différent ;
- centre incorrect ;
- frame absente ;
- page PVRZ manquante ;
- crash ou sprite invisible ;
- dérive entre corps et équipement ;
- corruption de palette ou alpha ;
- performance nettement dégradée.

## Critères de blocage pour l’UI

- crash F5 ou au démarrage ;
- écran inaccessible ;
- contrôle hors écran ;
- texte non localisable ou tronqué ;
- conflit silencieux avec un autre UI mod ;
- impossibilité de désinstaller proprement.
