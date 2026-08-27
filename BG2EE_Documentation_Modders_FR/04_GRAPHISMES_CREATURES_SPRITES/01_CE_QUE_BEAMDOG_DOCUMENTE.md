# Ce que Beamdog documente officiellement sur les créatures et graphismes

> **Statut :** Officiel Beamdog + limites explicites  
> **Dernière vérification :** 2026-08-27

## Publication dédiée

Beamdog fournit l’archive **Beamdog Creature Process**, décrite comme un exemple d’ajout d’une nouvelle créature aux Enhanced Editions. C’est la seule publication officielle recensée qui vise directement un processus de création de créature.

## Documentation indirecte utile

Les release notes 2.0 documentent aussi :

- l’usage de BAM dans l’interface ;
- la réduction d’un BAM référencé par `STATDESC.2da` pour créer une icône d’état ;
- l’utilisation de TTF et de PNG dans le nouveau système UI ;
- les cadres et séquences BAM dans `UI.menu`.

## Ce que Beamdog ne fournit pas dans ces documents

- spécification complète de BAM V1 et V2 ;
- table exhaustive des conventions d’animation de toutes les créatures ;
- limites détaillées de taille par type de sprite ;
- algorithme de composition des armures, casques et armes ;
- guide officiel d’upscale ;
- comportement garanti des offsets lors d’un changement d’échelle ;
- méthode générale de reconstruction de PVRZ.

## Conséquence

Pour un travail sur les sprites joueurs, la documentation officielle donne une orientation et un exemple de processus, mais la validation technique doit s’appuyer sur :

- l’IESDP pour les structures ;
- Near Infinity pour inspecter les ressources ;
- les tests en jeu ;
- le code de ton pipeline et des comparaisons automatisées.

## Sources
- Beamdog Creature Process: https://files.beamdog.com/
- Release notes 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
