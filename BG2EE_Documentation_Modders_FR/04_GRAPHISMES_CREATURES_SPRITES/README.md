# Graphismes, créatures et sprites - parcours spécialisé

> **Statut :** Index thématique  
> **Dernière vérification :** 2026-09-14

Cette section distingue clairement :

- ce que Beamdog a publié officiellement ;
- ce que les formats communautaires permettent d’établir ;
- les invariants à préserver pour modifier des sprites ;
- l'architecture x2 actuelle : base xBR et remplacements ReboutCX.

## Ordre de lecture

1. [`01_CE_QUE_BEAMDOG_DOCUMENTE.md`](01_CE_QUE_BEAMDOG_DOCUMENTE.md)
2. [`02_BAM_V1_V2_ET_PVRZ.md`](02_BAM_V1_V2_ET_PVRZ.md)
3. [`03_CHECKLIST_INVARIANTS_SPRITES.md`](03_CHECKLIST_INVARIANTS_SPRITES.md)
4. [`04_APPLICATION_UPSCALE_X2_X4.md`](04_APPLICATION_UPSCALE_X2_X4.md)

## Idée centrale

La qualité visuelle n’est qu’une partie du problème. Un sprite agrandi doit conserver la structure logique attendue : cycles, nombre de frames, ordre, centres, découpe, transparence, palette ou pages PVRZ, noms et dépendances. Une image parfaite mais mal ancrée reste une ressource invalide en jeu.
