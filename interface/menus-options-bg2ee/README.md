# Ressources des menus BG2EE

> **Séquence, mécanisme et critères de passage : [`../README.md`](../README.md).** Ce fichier ne
> décrit que l'organisation des dossiers de variantes.

Ce dossier sépare la production courante, les sources et les comparaisons historiques.

- `x4-topaz-recovery-v2-d50/` : seule variante de production active des menus.
- `reference/` : extraction originale, non modifiée, des ressources de l'écran Options.
- `archive/variants/` : anciennes variantes SeedVR 3B/7B, AdaIN et Topaz x2/x4 ; elles sont
  conservées pour comparaison ou restauration historique, mais ne sont ni actives ni des sources
  de statut ou de release.
- `archive/` hors `variants/` : diagnostics et prototypes remplacés.
- Les anciens workspaces `exports/` SeedVR/AdaIN/Topaz sont conservés sous
  `archive/legacy/workspace-p2-20260831/ui/menus-options-bg2ee/exports/`, hors de cette branche
  active et sans valeur de statut.
- `docs/MENU_UPSCALE.md` : carte des ressources du menu principal et procédure complète de maintenance.
