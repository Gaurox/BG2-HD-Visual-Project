# BG2 HD Upscale — documentation de release

Ce dossier est la source de la release WeiDU `bg2hd` pour **Baldur's Gate II:
Enhanced Edition Steam sous Windows x64**. Il ne doit pas etre confondu avec
l'override de developpement ni avec les archives locales de test.

## Etat de l'alpha de test

Cette variante installe BG2HD directement dans le jeu Steam et remplace le
chemin de lancement par le shim InfinityLoader controle. Elle conserve
l'executable officiel sous `BaldurReal.exe` et propose un retour vanilla
complet. Le garde save-neutral est inclus pour les futures sauvegardes ; son
test natif HD -> desinstallation -> vanilla reste a effectuer par l'utilisateur.
Le payload est genere depuis les selections explicites du generateur, controle exactement contre
`areas.csv`, puis couvert par des composants derives. La Phase 2 statique est PASS avec 6 327
entrees et 286 composants. La release reste non publiable uniquement tant que les gates de cycle
de vie, restauration vanilla et provenance enumeres dans `manifests/release.json` ne sont pas
franchis.

`manifests/release.json` reste la source de statut. Les payloads developpes,
arbres installateur et ZIP sont des sorties regenerables et ne vivent plus dans
ce dossier source ; les snapshots anterieurs au nettoyage sont conserves sous
`G:/AI/BG2_Upscale-artifacts/pre-cleanup-20260827/` avec leurs checksums.

Commencer par le guide correspondant a votre langue :

- [Guide utilisateur francais](README_FR.md)
- [English user guide](README_EN.md)

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — chaine WeiDU, Steam, EEex et renderer.
- [Dependances et bootstrap](docs/DEPENDENCY_BOOTSTRAP.md) — contrat EEex,
  InfinityLoader, Visual C++ et futur installeur guide.
- [Integration Steam](docs/STEAM_INTEGRATION.md) — lancement, Verify et Repair.
- [Recuperation](docs/RECOVERY.md) — interruption, erreurs et rapport de bug.
- [Compatibilite](docs/COMPATIBILITY.md) — perimetre supporte et exclusions.
- [Licences et provenance](docs/LICENCES.md) — statut de redistribution.
- [Politique de diffusion](docs/DISTRIBUTION_POLICY.md) — regles de l'alpha
  gratuite future.
- [Contrat installeur et integration des upscales](docs/INSTALLER_AND_UPSCALE_WORKFLOW.md)
  — reference courte pour les agents qui maintiennent le package.
- [Manifestes](docs/MANIFESTS.md), [maintenance](docs/MAINTENANCE.md),
  [localisation](docs/LOCALIZATION.md) et [tests](docs/TESTING.md) — regles
  detaillees pour mainteneurs.
- [Changelog](CHANGELOG.md) et [problemes connus](KNOWN_ISSUES.md).
