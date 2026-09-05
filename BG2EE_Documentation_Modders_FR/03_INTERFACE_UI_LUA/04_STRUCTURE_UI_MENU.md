# Structure de base de UI.menu

> **Statut :** Officiel Beamdog - synthèse technique  
> **Dernière vérification :** 2026-08-27

## Repérer un bloc

Le mode F11 + Tab fournit quatre informations utiles : type, ligne, position et taille. La ligne mène au bloc correspondant dans `UI.menu`.

## Exemple de bloc simplifié

```text
button
{
  bam 'STARTMBT'
  sequence 6
  area 50 306 300 44
  align center center
  text style "button"
  text "TUTORIAL_BUTTON"
  action "startEngine:OnTutorialButtonClick()"
}
```

## Champs expliqués

- `button` : type de contrôle ;
- `bam` : ressource graphique ;
- `sequence` : cycle ou séquence utilisée ;
- `area x y largeur hauteur` : rectangle du contrôle ;
- `align` : alignement ;
- `text style` : style défini côté Lua ;
- `text` : clé ou valeur affichée ;
- `action` : code ou appel exécuté au clic.

## Coordonnées

La position correspond au coin supérieur gauche. La taille est exprimée en largeur et hauteur de cadre. Le cadre d’un BAM et les dimensions internes de ses frames sont deux choses différentes : agrandir le cadre ne garantit pas un upscale de l’image.

## Méthode de modification

1. Localiser le bloc avec Tab.
2. Copier uniquement le bloc dans un fichier de travail.
3. Modifier un champ à la fois.
4. Vérifier la syntaxe des guillemets et accolades.
5. Recharger avec F5.
6. Comparer le diff final.

## Risque de conflit

`UI.menu` n’est pas conçu, dans la documentation officielle, pour recevoir des fragments `M_*.lua`. Deux mods qui remplacent ou patchent les mêmes blocs peuvent se contredire. Un installateur doit détecter les versions attendues et refuser un patch textuel si le contexte ne correspond plus.

## Sources
- Release notes 2.0, The Basics of UI.menu: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
- Guide UI officiel: https://forums.beamdog.com/discussion/48994/the-new-ui-system-how-to-use-it
