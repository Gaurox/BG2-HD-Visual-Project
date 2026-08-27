# Polices, couleurs et styles de texte

> **Statut :** Officiel Beamdog - synthèse avec recommandations  
> **Dernière vérification :** 2026-08-27

## Couleurs

Le guide 2.0 décrit une table `fontcolors` dont les valeurs sont des codes hexadécimaux ARGB sur huit caractères. Les styles peuvent référencer une clé de cette table ou, techniquement, une valeur hexadécimale directe.

Recommandation Beamdog : centraliser les couleurs dans `fontcolors` pour garder une configuration cohérente.

## Propriétés de style documentées

- `color` : clé de couleur ou valeur directe ;
- `font` : nom de la police ;
- `point` : taille de base ;
- `valign` : alignement vertical ;
- `halign` : alignement horizontal ;
- `upper` : conversion en majuscules ;
- `pad` : marges gauche, haut, droite, bas ;
- `useFontZoom` : adaptation au réglage de taille de police de l’utilisateur.

Exemple synthétique :

```lua
styles.mon_bouton = {
  color = 'B',
  font = 'MONFONT',
  point = 12,
  valign = 'center',
  halign = 'center',
  upper = 0,
  pad = {8, 8, 8, 8},
  useFontZoom = 0,
}
```

## Polices TTF

Le guide recommande de copier le TTF dans `override`. Il précise que le nom de fichier doit tenir sur huit caractères ou moins pour être reconnu dans le contexte décrit. Renommer proprement le fichier est donc plus sûr qu’utiliser un nom long.

## Choix de `useFontZoom`

- `0` : taille fixe, utile pour un texte qui doit rester dans un bouton ;
- valeur active : le style suit le réglage de taille de police de l’utilisateur, préférable pour les textes longs et l’accessibilité.

## Validation visuelle

Tester chaque style :

- en plusieurs langues ;
- avec texte court et long ;
- avec plusieurs réglages de taille ;
- sur plusieurs rapports d’écran ;
- avec caractères accentués et glyphes absents ;
- après rechargement F5 et redémarrage complet.

## Sources
- Release notes 2.0, Changing Game Fonts: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
- Guide UI officiel: https://forums.beamdog.com/discussion/48994/the-new-ui-system-how-to-use-it
