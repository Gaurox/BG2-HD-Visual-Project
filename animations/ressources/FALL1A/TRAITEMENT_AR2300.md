# FALL1A — recette validée ingame (AR2300)

- Base : upscale spatial SeedVR2 x4 ; ne modifier ni RGB, centres, cycles, durées ni géométrie.
- Les six frames ont le même alpha source : produire, contrôler puis appliquer le même masque final aux six frames.
- Lisser la silhouette en Fit 1 ; conserver la tranche gauche nette et le nuage de raccord supérieur doux.
- Remplacer les pixels isolés du haut par un fade alpha continu, sans ligne horizontale nette.
- Refaire la tranche droite comme une bande diagonale nette ; lisser uniquement son pic supérieur par un petit flou local.
- Vérifier en jeu avant interpolation ; la feuille AR2300 de test doit conserver les autres ressources déjà servies.
