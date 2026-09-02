# Contrat commun de suivi des assets — v1

Ce contrat définit la projection commune utilisée par le registre agrégé. Il ne
remplace aucun catalogue ou manifeste métier. Une projection est générée en lecture seule depuis
les sources de vérité existantes, peut être supprimée puis reconstruite, et ne reçoit jamais de
correction manuelle d'état.

Le schéma machine est [`asset-tracking-record.schema.json`](asset-tracking-record.schema.json) et
le validateur léger est `pipeline/scripts/asset_tracking_contract.py`.

## Règles d'autorité

1. Chaque enregistrement cite une `canonical_source` et un `locator` précis dans cette source.
2. Une valeur inconnue reste inconnue ou non évaluée. L'absence de preuve ne se transforme pas en
   succès par déduction depuis un dossier, un run, un `override`, une capture ou une note libre.
3. Les cinq axes sont indépendants. Une installation ne prouve pas la QA ; une QA passée ne prouve
   pas l'intégration release ; `pipeline_ready` ne prouve aucune production.
4. Les anciens statuts combinés restent intacts dans leur source métier. La projection conserve la
   valeur brute dans `legacy` et la sépare au moyen d'un mapping versionné.
5. Un run, candidat, build, correctif ou génération retenu apparaît dans `selections` avec sa
   référence d'autorité. Sans candidat démontré, la liste reste vide.
6. `provenance.state=verified` exige des preuves hashées. `complete` signifie que la chaîne est
   suffisante mais que toutes les références ne sont pas nécessairement scellées par hash.
7. Les états release `eligible`, `approved`, `integrated` et `published` exigent une QA `passed`,
   une provenance au moins `complete` et une sélection explicite. Ils ne décrivent pas le statut
   global de la release, qui reste dans `manifests/release.json`.

## Identité et granularité

`asset_id` suit la convention `<domain>:<identité-native>[:<variante>]`. L'identité native est
stable et ne dépend pas du chemin de travail. Exemples : `maps:AR0404:day`,
`animations:bam:AM0602B`, `animations:pack:AR0602`, `sprites:family:0x6102:CDMB1`.

Un pack ou un catalogue est un asset agrégé distinct de ses membres. Son état ne se propage à un
membre que si la source canonique donne explicitement l'appartenance et si la preuve couvre ce
membre. Une map jour et sa variante nuit sont deux enregistrements, car leurs QA et installations
peuvent diverger.

Champs obligatoires :

| Champ | Rôle |
|---|---|
| `schema_version` | version du contrat, actuellement `1` |
| `asset_id` | identifiant transversal stable |
| `domain` / `asset_type` | domaine propriétaire et granularité de l'asset |
| `canonical_source` | chemin dépôt et sélecteur de la source de vérité métier |
| `states` | les cinq axes indépendants |
| `provenance` | disponibilité et niveau de vérification des preuves |
| `adapter` | mapping versionné ayant produit la projection |
| `observed_at_utc` | instant UTC de lecture des sources |

`selections` et `legacy` sont optionnels. Aucun champ libre de type `status` n'est admis dans le
contrat commun.

## États communs

| Axe | Valeurs | Sens essentiel |
|---|---|---|
| Source | `unknown`, `unavailable`, `available`, `extracted`, `verified`, `not-applicable` | disponibilité puis contrôle de la source native |
| Production | `unknown`, `not-started`, `ready`, `in-progress`, `produced`, `verified`, `rejected`, `blocked`, `not-applicable` | avancement technique ; `ready` ne signifie pas produit |
| QA | `not-assessed`, `pending`, `passed`, `failed`, `blocked`, `not-applicable` | décision qualité du périmètre exact de l'asset |
| Installation | `unknown`, `not-installed`, `staged`, `installed`, `drifted`, `restored`, `not-applicable` | état courant vérifiable dans le jeu ou le staging |
| Release | `not-evaluated`, `ineligible`, `eligible`, `approved`, `integrated`, `published`, `blocked`, `not-applicable` | sélection progressive pour la distribution |
| Provenance | `missing`, `partial`, `complete`, `verified`, `not-applicable` | reproductibilité de la sélection et de ses preuves |

`production=verified` désigne les contrôles techniques du produit. `qa=passed` est réservé à la
décision QA exigée par le domaine. `release=approved` désigne une approbation explicite ; la simple
présence d'un candidat n'y suffit pas.

## Mapping des domaines actuels

### Maps

- Autorité métier : `areas.csv`, une projection `day` et éventuellement une projection `night`.
- Source : colonnes `x1_tuiles_*` ; `source-pending` devient `source=available`, `source-only`
  devient `source=extracted` et `production=not-started`.
- `installed-pending-qa` devient `production=produced`, `qa=pending`,
  `installation=installed`.
- `validated-installed` devient `production=verified`, `qa=passed`,
  `installation=installed`.
- `runs`, `build`, `runs_nuit` et `build_nuit` alimentent `selections` et la provenance, sans
  rechercher un candidat de remplacement dans les dossiers.
- L'axe release vient de la sélection release et du `content.json` généré, jamais du seul statut
  d'`areas.csv`. Aucun statut map historique n'implique donc un état release.

### Animations de zone

- Inventaire et source : `animations/index/manifest.json`, `ressources.csv`, `occurrences.csv` et
  `zones.csv`.
- `animation_upscale_registry.csv` porte la décision spatiale : `validé-x4` et `validé-natif`
  deviennent uniquement `production=verified`. Un `qa-approval.json` interne à un run prouve une
  revue technique/vidéo, jamais la QA ingame définitive.
- `index/qa-decisions/<RESREF>/*.json` porte la décision ingame immuable ;
  `index/selections/<RESREF>.json` sélectionne soit le run x4 final, soit la source BAM native,
  avec sa référence par hash. Ce couple exact est requis pour `qa=passed`. Les approbations release
  v1 déjà suivies restent un fallback legacy.
- `non-traité`, `à-compléter`, `à-corriger` et `écarté` deviennent respectivement
  `not-started`, `in-progress`, `blocked` et `rejected`; `écarté` est aussi `release=ineligible`.
- `animation_alpha_corrections.csv` conserve le statut historique
  `validated-prototype-installed`; la projection le sépare en production vérifiée, QA passée,
  installation installée et release inéligible tant qu'il reste un prototype.
- Les packs approuvés sont des assets `animations:pack:<AREA>`. Le
  `qa-approval.json` hashé prouve la QA, `animation-release-candidates.json` prouve l'éligibilité ou
  l'approbation, et `content.json` prouve l'intégration. Le blocage global reste dans `release.json`.

### Sprites

- Inventaire/source : `sprite/index/manifest.json` et ses quatre CSV. Le statut
  `generated-verified-read-only-source` devient seulement `source=verified`.
- `pipeline_ready=yes` devient `production=ready`; `no` devient `production=blocked` sous les
  règles du pipeline courant. Aucun des deux ne fixe la QA ni l'installation.
- `current-generation.json` sélectionne la génération ; son build manifest prouve une production
  vérifiée et ses snapshots/hashs alimentent la provenance.
- `active-test.json` porte l'installation courante. `installed-pending-qa` devient seulement
  `installation=installed` et `qa=pending`; `validated-installed` ajoute `qa=passed`.
- Une décision portée par un catalogue ne s'applique à une famille que si le manifeste de la
  génération prouve son appartenance.

### Interface, portraits et inventaires graphiques complémentaires

- Interface : les manifests d'extraction, d'assets, de sprites et d'atlas existants, ainsi que les
  index HUD, UI complémentaire et polices, sont projetés à leur granularité propre. Les PVRZ sont
  des dépendances et ne sont pas des assets autonomes.
- Portraits : `portraits/inventaire_portraits.csv` suit une base logique déclarée dans la table
  `portraits` de `BGEE.lua` ou référencée par un CRE. Les ressources L/M/S, leurs BIF et SHA-256 sont
  des membres de cet asset. Les inventaires recrutables/rencontres décrivent des occurrences sans
  créer d'assets supplémentaires. PPE reste un corpus tiers non installé, hors registre du patch.
  Faute d'autorité métier, production, QA, installation et release valent `not-applicable`.
- Vidéos : `video/index/resources.csv` inventorie un asset par WBM cinématique ou tutoriel ;
  `processing.csv` porte les runs validés par étape et la sélection patch. Upscale et interpolation
  validés deviennent `production=verified`, `qa=passed`; `patch_state=not-integrated` devient
  `installation=not-installed`. Les WBM de zone restent sous `animations/index/`.
- Icônes : `icons/index/` inventorie un jeu BAM par resref partagé par les usages ITM/SPL. Les
  références manquantes restent des anomalies et ne créent pas de source fictive.
- Curseurs : `cursors/index/` suit `CURSORS.BAM` comme un jeu unique, faute de noms sémantiques
  fiables pour ses cycles.
- Effets et projectiles : `effects/index/` suit un contrôleur VVC/VEF par asset et
  `projectiles/index/` un contrôleur PRO par asset. Leurs BAM, BMP, palettes et effets imbriqués
  restent des dépendances. Les jeux BAM de familles BIF explicitement dédiées sont inventoriés
  séparément comme animations d'effet.
- Compléments : `graphics/index/supplemental-assets.csv` rattache les paperdolls, animations
  d'objets et autres familles BIF non ambiguës aux domaines existants sans modifier leurs manifests
  historiques. Les BIF de patch génériques restent non classés.

## Incompatibilités assumées et transition

- Les statuts combinés de `areas.csv`, des prototypes animation et des états sprites restent
  nécessaires aux scripts actuels. Les adapters les lisent sans les réécrire.
- Animation distingue validation spatiale, validation temporelle d'un run et validation d'un pack
  par zone. Elles ne sont pas interchangeables.
- Sprite distingue disponibilité technique d'une famille, build d'une génération, installation du
  catalogue et QA ingame. Les décisions ont des granularités différentes.
- UI conserve plusieurs autorités locales ; portraits ne suit que la source native et fusionne ses
  vues d'usage par base. Le registre n'invente aucune décision métier.
- `release.json` décrit la release entière tandis que `content.json` et les registres de candidats
  décrivent la sélection. Un asset peut donc être `integrated` alors que la release globale reste
  `blocked`.

## Projection globale

La Phase 3 implémente ces mappings dans `pipeline/scripts/build_global_asset_registry.py`. Le
générateur valide chaque enregistrement par le présent contrat et produit un registre jetable,
un rapport de couverture et un rapport d'anomalies. Son fonctionnement et ses commandes sont
documentés dans [`GLOBAL_ASSET_REGISTRY.md`](GLOBAL_ASSET_REGISTRY.md).

La projection n'écrit dans aucune source métier, n'invente pas les domaines sans autorité et ne
promeut automatiquement aucun état QA ou release. Les périmètres encore non inventoriés sont
déclarés avec une quantité inconnue plutôt qu'avec un faux total nul.
