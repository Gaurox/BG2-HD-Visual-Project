# Registre global agrégé des assets

Le registre global est une projection en lecture seule des sources de vérité métier. Il est
généré, reproductible et jetable : aucune décision de production, QA, installation ou release ne
doit y être saisie manuellement, et aucun pipeline métier ne doit le lire comme autorité.

Le contrat de chaque entrée est défini dans
[`ASSET_TRACKING_CONTRACT.md`](ASSET_TRACKING_CONTRACT.md). Le générateur lit uniquement les
catalogues et manifests existants, applique des adaptateurs déterministes puis valide chaque
entrée avant de produire :

- `asset-tracking/registry.json` : entrées transversales et références canoniques ;
- `asset-tracking/registry.csv` : vue humaine plate, filtrable dans Excel ;
- `asset-tracking/coverage.json` : métriques globales, par domaine et par axe ;
- `asset-tracking/anomalies.json` : conflits, valeurs non projetables et lacunes de couverture.

Les trois JSON portent l'empreinte de toutes leurs entrées. `registry.json` conserve en plus le
SHA-256 et le rôle de chaque fichier lu. Le CSV est dérivé des mêmes enregistrements validés, avec
un encodage UTF-8 BOM et des fins de ligne CRLF pour faciliter son ouverture dans Excel. L'instant
d'observation est dérivé des timestamps contenus dans les sources, pas de l'horloge de génération :
deux lectures du même état produisent donc les mêmes octets.

## Génération et contrôle

```powershell
python pipeline/scripts/build_global_asset_registry.py --verify-determinism
python pipeline/scripts/build_global_asset_registry.py --check
```

La première commande construit deux projections en mémoire, vérifie leur identité puis écrit les
quatre sorties. La seconde ne modifie rien et échoue si une sortie manque ou ne correspond plus aux
sources actuelles. Le dossier `asset-tracking/` peut être supprimé puis régénéré par la première
commande.

La projection humaine XLSX et les métriques structurées associées sont décrites dans
[`HUMAN_PROJECT_TRACKING_XLSX.md`](HUMAN_PROJECT_TRACKING_XLSX.md). Elles lisent ces sorties après
leur régénération et ne modifient aucune autorité.

Le CSV contient les colonnes `asset_id`, `domain`, `asset_type`, les cinq états indépendants,
`provenance_state`, la sélection éventuelle, le chemin et le locator de la source canonique, le
nombre de preuves, l'adaptateur et l'instant d'observation. Il est strictement jetable : une
modification manuelle est écrasée à la génération suivante.

## Granularité projetée

- maps : une entrée par variante jour/nuit connue dans `areas.csv` ;
- animations : une entrée par BAM/WBM inventorié et une par pack de zone candidat à la release ;
- sprites : une entrée par famille du catalogue canonique, plus les jeux BAM complémentaires dont
  la famille BIF prouve le rattachement (paperdolls, objets, créatures) ;
- UI : compositions extraites, HUD, polices, compléments UI et composants release prouvés ;
- portraits : une entrée par identité locale unique de chacun des inventaires CSV existants.
- vidéos : une entrée par cinématique localisée ou tutoriel WBM ;
- icônes : une entrée par jeu BAM partagé par les usages ITM/SPL ;
- curseurs : un asset pour le jeu `CURSORS.BAM` ;
- effets : une entrée par contrôleur VVC/VEF ou jeu d'animation d'effet explicitement classé ;
- projectiles : une entrée par contrôleur PRO.

Une ressource source et un composant produit peuvent donc être deux assets distincts. Le registre
ne propage jamais l'état d'un agrégat à ses membres sans preuve d'appartenance explicite.

## Lecture des rapports

`known_unprocessed` compte les assets connus en `not-started` ou `ready`. Il ne représente pas les
assets du jeu encore absents de tout inventaire. Ces ressources sont listées séparément dans
`uninventoried_scopes` avec `asset_count: null` et, lorsque disponible, un `resource_count` brut :
le nombre de ressources ne devient pas un faux nombre d'assets tant que leur granularité logique
n'est pas démontrée.

Pour chaque axe, `coverage_percent` mesure les valeurs résolues parmi les entrées auxquelles l'axe
s'applique. Un état `not-assessed`, `unknown` ou `not-evaluated` reste explicitement non résolu.
Les anomalies ne sont pas des corrections automatiques : elles indiquent la source métier à
consolider lors d'une phase ultérieure.
