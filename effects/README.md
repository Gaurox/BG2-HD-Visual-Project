# Effets BG2EE

## Portée et autorités

Un asset de production est un BAM visuel : `effects:bam:<RESREF>`. Les VVC/VEF restent des contrôleurs et consommateurs ; un BAM partagé n'est traité qu'une fois.

Affichage par défaut des effets x4 (demande utilisateur 2026-10-13) : **NEAREST** min/mag,
niveau 0 seul, sur texture directe et sortie du masquage décor. Défaut du chargeur natif,
indépendant de la recette 3B/7B et du pack ; aucune activation INI nécessaire.
Personnages : conserver [`NearestRGB-SilhouetteAlphaAA`](../sprite/DISPLAY_DEFAULT.md).
Pack d'effets installé :
[`lot33-retimed-7b-x4-nearest-20261014-v2`](installations/lot33-retimed-7b-x4-nearest-20261014-v2/installation.json).
97 effets : 64 précédents byte-identiques +33 en7B x4/NEAREST/Apollo30 retimé ; 2202images RGB/RGBA distinctes, zéro doublon, durées natives conservées. SPSUMP128/128 sur64/15s.
Recette : [`lot33-retimed`](../pipeline/recipes/effects-lot33-retimed-20261014-v2/README.md) ; 33BAM runtime avec padding transparent, pixels/ancrage monde natifs préservés ; reconnaissance RESREF insensible à la casse. 4974résolutions natives vérifiées sur candidat puis installation ; **33/33 acceptés explicitement par l'utilisateur le 2026-10-15**, [décisions et sélections exactes](batches/lot33-accepted-20261015-v1/acceptance.json).
Réserve runtime distincte : SPIMPFR mesure ~29.83–29.86 changements/s en moyenne, mais cadence irrégulière 50/16.7ms et phases initiales0–1 absentes ; images produites distinctes, aucun fallback observé. [Preuve et périmètre de l'acceptation](batches/lot33-accepted-20261015-v1/README.md). Scheduler inchangé ; aucune cadence parfaitement régulière déduite de la validation visuelle.
Incident initial2026-10-14 : [`échec LoadArea/MinHook`](installations/lot33-seedvr7b-apollo30-nearest-20261014-v1/runtime-failure-20261014-v1/README.md).
RéparationMinHook : [`hooks-startup-repair`](../engine/InfinityEngine-Enhancer/installations/hooks-startup-repair-20261014-v1/README.md), tous hooks actifs et rendu x4 vérifié techniquement à23:05 ; retour visuel utilisateur : mosaïque initiale corrigée seulement après zoom.
Le [`rafraîchissement initial`](../engine/InfinityEngine-Enhancer/installations/map-first-frame-refresh-20261014-v1/README.md) corrige ensuite le cache automatiquement ; il ne suffisait pas à empêcher l'image initiale native.
Base du renderer courant : [`renderer-startup-barrier`](../engine/InfinityEngine-Enhancer/installations/renderer-startup-barrier-20261014-v1/verification-result.json), préservée dans la correctionretimed ci-dessus. Démarrage du host attendu jusqu'aux hooks/assets prêts ; premierLoadArea observé ensuite. Session23:22AR3000, zéroerreur ; utilisateur : affichage correct dès apparition sans zoom. NearestRGB-SilhouetteAlphaAA conservé octet pour octet ; aucune QA globale des33effets déduite de ce test.
Renderer diagnostique courant : [`SPIMPFR presentation trace`](../engine/InfinityEngine-Enhancer/installations/spimpfr-presentation-trace-20261015-v1/installation.json), DLL seule +INI identique. Capture ciblée après draw final/masquage et retour du swap ; QPC/phase/backing/pause/fallback, publication différée après disparition. Analyse : `python -B pipeline/recipes/spimpfr-presentation-trace-20261015-v1/analyze.py`. Scheduler, effets97/33BAM, cartes et shaders personnages inchangés.
Chargeur CPU borné à4Gio (packretimed3.51Gio), cache GPU64 inchangé ; profil personnages conservé octet pour octet.
Référence du filtre : [`effects-nearest-20261013-v1`](../engine/InfinityEngine-Enhancer/installations/effects-nearest-20261013-v1/result.json).

Lot54 accepté ingame en **3B x4 / Apollo30 / gauss1.2 / feather12 / nearest** :
[`acceptance.json`](batches/lot54-accepted-cleanup-20261013-v1/acceptance.json).
Installation 54x3B + 10 effets précédents conservés :
[`lot54-accepted-3b-nearest`](installations/lot54-accepted-3b-nearest-20261013-v1/result.json).
Essais 7B non retenus retirés ; métadonnées et comparatifs finaux conservés dans
[`lot54-accepted-cleanup`](batches/lot54-accepted-cleanup-20261013-v1/README.md).

## Quotidien — minimum utile

```powershell
python -B pipeline/scripts/effect_tracking.py queue --limit 10
python -B pipeline/scripts/effect_workflow.py status --resref <BAM>
# Après QA utilisateur explicite du pack mono-BAM : une seule transaction.
python -B pipeline/scripts/effect_workflow.py accept --resref <BAM> --pack <pack> --decision "<décision utilisateur>" --date YYYY-MM-DD --run
```

- Lire la ligne de l'asset et la recette utile ; aucun parcours documentaire global.
- Producteurs : `--run --register` = produire puis enregistrer automatiquement le run réussi.
- `status`/`queue` lisent les index ; aucun hash global. `status --deep`/`check --resref <BAM>` sont des diagnostics facultatifs.
- Tags, priorités et limites techniques = aides ; aucun gate supplémentaire. Une recette compatible peut être réutilisée directement.
- Nouvelle tentative = pointeurs de production courants ; sélection acceptée et ancienne QA conservées.
- Acceptation = résultat exact, jamais installation/release implicite. Pas de retest d'une QA acquise à octets/contrat identiques.
- Après l'asset : arrêt. Composition globale uniquement en finalisation explicitement demandée.

| Fichier | Rôle | Édition |
|---|---|---|
| `index/manifest.json`, `resources.csv`, `dependencies.csv` | inventaire VVC/VEF et graphe de dépendances | généré |
| `index/bam-assets.csv` | inventaire unifié des BAM d'effet, provenance, consommateurs et source | généré |
| `index/work-items.csv`, `consumers.csv`, `source-work-plan.json` | géométrie/cycles, usages, coût x4, réutilisation ; aucun statut acquis | généré, refresh exceptionnel |
| `index/classification.json` | overrides facultatifs : recette, tags, priorité, usage, note | uniquement les exceptions utiles |
| `index/processing.csv` | derniers essais spatiaux/temporels ; références indépendantes QA/installation/release | commandes verrouillées |
| `index/selections/<RESREF>.json` | résultat retenu exact, source, run, pack, alpha/géométrie et QA hashés | `accept`, transaction récupérable |
| `index/qa-decisions/<RESREF>/*.json` | décisions QA ingame explicites et preuves hashées | immuable |

`bam-assets.csv` inclut les BAM directement référencés par VVC/VEF, les BAM référencés directement par un PRO et les BAM des BIF dédiées effets. Les BAM partagés avec les projectiles restent des assets `effects`; leurs consommateurs PRO sont listés, sans duplication sous `projectiles/`. `origin=projectile-member` désigne un BAM connu uniquement par un PRO.

## Layout

```text
effects/
  index/qa-decisions/<RESREF>/*.json # décision QA ingame immuable
  index/selections/<RESREF>.json   # sélection courante, distincte des essais
  source/{vvc,vef}/                 # contrôleurs stock extraits
  runtime-geometry/<RESREF>-vN.json # mesures runtime liées au hash du BAM
  ressources/<RESREF>/
    source.bam                       # BAM stock unique, ignoré Git
    runs/<run-id>/
      run.json                       # docs/workspace-run.schema.json
      00-frames-x1/                  # optionnel
      01-spatial-x4/                 # run spatial
      02-interpolation/              # seulement dans un run dérivé
    packs/<pack-id>/                 # nouveau pack mono-BAM immuable ; --output explicite
```

Créer un run directement sous le BAM concerné. Aucun nouveau run sous `effects/runs/`. Un run d'interpolation est distinct, scellé et porte son run spatial parent dans `provenance.parents`. Ne pas créer de répertoires permanents `x4/` ou `interpolation/` hors d'un run. Ne jamais modifier un run scellé.

## Workflow de production

La voie quotidienne suit [`../docs/PRODUCTION_RAPIDE.md`](../docs/PRODUCTION_RAPIDE.md) : le pack
mono-BAM accepté est l'unité finale ; les packs cumulatifs et projections sont différés.

`pipeline/scripts/effect_workflow.py` ne génère pas d'image. Il contrôle l'autorité et les descripteurs scellés ; le producteur écrit les fichiers du run avant son enregistrement.

| Étape | `pipeline.id` imposé | Entrée et lineage requis | Écriture autorité |
|---|---|---|---|
| spatial | `effects.spatial-x4.v1` | une preuve `source-bam` vers `source.bam`, hashée comme `bam-assets.csv` | `spatial_run`, `spatial_state=produced` |
| interpolation | `effects.interpolation-30fps.v1` | parent unique = `spatial_run`; preuve `parent-spatial-output` égale à une sortie parent | `interpolation_run`, `interpolation_state=produced` |

```powershell
# Prépare seulement l'identifiant, sans écrire.
python pipeline/scripts/effect_workflow.py new-run --resref <RESREF> --stage spatial --recipe <recipe>

# Réserve explicitement l'identifiant ; le producteur crée ensuite runs/<run-id>/run.json.
python pipeline/scripts/effect_workflow.py new-run --resref <RESREF> --stage spatial --recipe <recipe> --run

# Vérifie hash, tailles, source et lineage. Sans --run, aucune autorité n'est modifiée.
python pipeline/scripts/effect_workflow.py register-run --resref <RESREF> --stage spatial --run-id <run-id>
python pipeline/scripts/effect_workflow.py register-run --resref <RESREF> --stage spatial --run-id <run-id> --run
python pipeline/scripts/effect_workflow.py check --resref <RESREF>
```

`new-run`/`register-run` ne sélectionnent aucun résultat et ne déclarent aucune QA.
`accept` lie une décision utilisateur explicite aux octets du pack, puis écrit QA immuable,
sélection et CSV dans une transaction. `--qa-evidence <ancienne-décision.json>` réutilise une QA
existante sans la réécrire. `--native --decision "..." --date ...` enregistre une conservation native
explicite, distincte d'un blocage. Aucun de ces chemins n'installe ni n'approuve une release.

Verrou OS partagé par workflow, synchronisation et classification ; une panne libère le verrou.
La prochaine écriture termine un commit interrompu ; une modification extérieure divergente est
préservée et signalée. Lecture pendant un commit interrompu : `recover --run`. Aucun journal à
renseigner à la main.

## Producteur spatial

`run_effect_spatial.py` crée uniquement un run spatial mono-BAM ; il ne choisit aucun asset par défaut. Le workflow SeedVR doit être un fichier du workspace et reste hashé dans `recipe.json`.

```powershell
# Plan sans écriture ni appel ComfyUI.
python pipeline/scripts/run_effect_spatial.py --resref <RESREF> --workflow <workflow.json> --recipe-id <recipe>

# Production explicite, puis enregistrement distinct après revue du run.
python pipeline/scripts/run_effect_spatial.py --resref <RESREF> --workflow <workflow.json> --recipe-id <recipe> --run --register
```

Le producteur écrit `00-frames-x1/`, `01-spatial-x4/`, `recipe.json` et `run.json` sous le run réservé.
Source/alpha conservés ; aucun run scellé modifié. Sans `--register`, le CSV reste inchangé.
`run_effect_interpolation.py` propose aussi `--run --register` ; le parent spatial reste obligatoire.

Effets one-shot à 15 FPS :

```powershell
python pipeline/scripts/run_effect_interpolation.py --resref <RESREF> --spatial-run <run-spatial> --recipe-id apollo8-rgb-left-alpha-one-shot-dedup --native-fps 15 --target-fps 30 --one-shot --alpha-phase left --deduplicate --run --register
```

`--one-shot` maintient la dernière pose au lieu de relier fin→début. Alpha `left` = masque du slot
natif courant ; RGB des phases natives repris exactement du spatial. `--deduplicate` partage les
PNG/RGBA identiques sans raccourcir la timeline ; une pause native peut donc référencer un seul
fichier vide. `duplicate_audit` compare les pixels RGBA ancrés, ignore le RGB sous alpha nul et
refuse de sceller ce mode si des phases lumineuses sont identiques sans origine native démontrée.
Les pauses et sous-séquences natives répétées restent exactes (`native_repeat_duplicates`),
ainsi que la dernière pose one-shot ; `unexpected_visible_duplicates` doit rester vide.
**Ce mode n'assure pas l'absence de doublons visibles.** Demande2026-10-14 sans doublons à durée constante : retirer les poses répétées avant Apollo et étaler les poses distinctes sur toutes les phases, sans maintien final ; exemple exécutable et contrôle RGB strict dans la [recette retimed](../pipeline/recipes/effects-lot33-retimed-20261014-v2/README.md).

Adoucissement léger après interpolation :

```powershell
python pipeline/scripts/run_effect_visual_treatment.py --resref <RESREF> --interpolation-run <run-30fps> --run-id <nouveau-run> --sigma-x4 0.6 --inner-feather-x4 4 --run --register
```

Nouveau run lié au manifeste temporel source ; géométrie/timing identiques, 0 doublon lumineux
inattendu ; répétitions natives démontrées héritées du parent.
RGB de sortie **prémultiplié** pour `Blended` : ne pas prémultiplier une seconde fois au pack.
Une preview sur noir affiche directement le RGB de ces frames ; un composite RGBA standard
multiplierait leur alpha une seconde fois.

Pack 30 FPS : `build_effect_runtime_pack.py --deduplicate` conserve toutes les phases et tous les
slots natifs, mais partage les backings RGBA/géométrie/ancre identiques ; le registre v2 accepte
ces références répétées. Installation ciblée : packs mono-BAM + snapshot du pack actif sous
`effects/installations/<id>/`; candidat = DLL/INI actifs inchangés + pack composé. Installer avec
`engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py`, puis vérifier
son reçu et enregistrer uniquement les trois lignes concernées avec `effect_authority.guard/commit`.

## Initialisation / extraction

```powershell
python pipeline/scripts/build_graphics_inventory.py --extract-effects --run
python pipeline/scripts/sync_effect_processing.py
python pipeline/scripts/sync_effect_processing.py --run
python -B pipeline/scripts/effect_tracking.py refresh --run
```

La première commande régénère l'inventaire et extrait seulement les contrôleurs et BAM d'effets.
La synchronisation complète `processing.csv` sans changer un état existant.
`refresh` recalcule uniquement les vues techniques après changement d'inventaire/source ; pas pendant
chaque production. Sources comparées aux hashes ; pixels décodés en mémoire, aucune image générée.
La classification manuelle reste conservée.

Deux BAM stock absents restent `blocked`; ne pas créer de `source.bam` fictif.

## Suivi

`processing.csv` contient une ligne par `asset_key` de `bam-assets.csv` :

```text
asset_key,asset_directory,spatial_run,spatial_state,interpolation_run,
interpolation_state,selected_run,qa_state,qa_evidence,installation_state,
installation_receipt,release_state,release_candidate,notes
```

États de production : valeurs du contrat commun (`not-started`, `in-progress`, `produced`, `verified`, `rejected`, `blocked`, `not-applicable`). `qa=passed` exige un `selected_run` et une preuve. Installation et release restent des décisions séparées.

`qa=native` = décision native explicite, sélection hashée sans run x4. Source absente ≠ native accepté.
Les reçus du CSV décrivent l'installation enregistrée, pas une vérification actuelle du jeu.
`status.release.matches_current_selection` vérifie le lien vers le candidat existant ; une nouvelle
sélection n'hérite pas de son approbation. Autorité release : manifeste de candidats, puis `content.json`.

Tags combinables : `static`, `one-shot`, `loop`, `staged`, `directional`, `alpha`, `palette`, `unresolved`.
`alpha` signale un chemin Blended, sans déduire une recette émissive. `unresolved` : aucun owner
démontré dans VVC/VEF/PRO ; conserver l'asset. Les cycles ne démontrent pas un découpage spatial.
`usage=known` = référence trouvée, pas preuve de présence ingame ou de couverture runtime.
`native-shadow` reste natif ; les cadences PRO non déclarées restent à observer. Timings VEF bruts
conservés dans `consumers.csv.flags_json`, sans réécrire l'orchestration.

```powershell
# Facultatif ; aucun fichier manuel par asset.
python -B pipeline/scripts/effect_tracking.py classify --resref <BAM> --recipe <recette> --priority 20 --run
```

Réutilisation : source canonique/RGBA/ancre identiques ne suffisent pas ; conserver contexte modèle,
canevas, palette, alpha et contrat runtime. `reuse_animation` indique une source identique ; jamais
transférer automatiquement un masque WED, un déplacement local ou sa QA.

Initialisation 2026-10-12 : 494 identités, 492 sources, 478 contenus canoniques ; 19 418 frames,
17 241 contenus RGBA/géométrie uniques ; 296 mono-cycles, 196 multicycles, 17 statiques,
23 avec cycle vide. Trois sélections importées depuis les QA existantes ; aucune nouvelle QA.
Deux références locales de candidat corrigées depuis les approbations existantes ; release inchangée.

## Gate runtime

`EffectAnimations-X4.registry` couvre les BAM de projectile via `CProjectileBAM` et
les BAM VVC/VEF via `CVEFVidCell`. Les deux owner scopes convergent uniquement sur
le `CInfinity::FXRender` final : resref/cycle/dimensions exacts, géométrie x1,
backing x4, fallback BAM natif à toute divergence. Le registre v1 conserve la
cadence BAM native ; le v2 ajoute une timeline QPC pause-aware ancrée sur les slots
BAM pour les runs 30 FPS. Les adresses/offsets restent manifestés par build et
échouent fermés sur signature divergente.

Si la géométrie logique observée sur le `CInfinity::FXRender` final d'un owner scope
diffère des dimensions du BAM,
`build_effect_runtime_pack.py --runtime-geometry <preuve.json>` exige une mesure
pour chaque slot, applique un crop ou reframe validé autour de l'ancre BAM et inscrit
cette preuve dans le manifeste dérivé. Les tirages intermédiaires de
`FXRenderClippingPolys` restent natifs : les remplacer produirait deux couches
visibles. Une politique alpha asset-spécifique peut reconstruire un masque depuis le
RGB source, le RGB x4 produit (seuil ou rampe de luminance) ou la géométrie runtime,
puis prémultiplier le RGB pour les chemins `Blended`. Le run scellé reste inchangé ;
tout slot absent ou terminal conserve le fallback natif strict.

Vérifier seulement les risques nouveaux : ancrage, cycle/timing, alpha, palette,
partage ou owner non démontré. Les contrats déjà acquis restent utilisables.
Une production temporelle ou une installation ne vaut jamais QA ingame.

Limites connues, signalées par asset : interpolation mono-cycle/boucle fermée/ratio FPS entier ;
cycles vides refusés ; palettes runtime à démontrer ; versions v1/v2 non mélangées ; pack chargé
intégralement, 512 ressources/2 Gio RGBA (candidat lot54). Catalogue estimé ≈7,2 Gio x4 à cadence native : prévoir
chargement/cache bornés et timeline optionnelle par cycle pour l'intégration complète. Ces évolutions
moteur restent séparées de la mise en place du suivi. Candidat lot54 (2026-10-13) : limite RGBA
portée de 512 Mio à 2 Gio, 512 ressources ; chargement natif du pack composé vérifié avant installation.

## Packs cumulatifs — finalisation

Produire un pack immuable par BAM. Composer un nouveau pack cumulatif seulement pour une
finalisation ou un essai cumulatif explicitement demandé, sans relancer extraction, upscale ou
interpolation :

```powershell
python pipeline/scripts/compose_effect_runtime_packs.py `
  --pack <pack-cumulatif-précédent> `
  --pack <nouveau-pack-mono-resref> `
  --output <nouveau-pack-cumulatif>
# Après contrôle du plan : même commande avec --run.
```

Contraintes : packs plats complets, resrefs uniques, même version de registre.
Ne pas mélanger v1 natif et v2 30 FPS ; un lot 30 FPS reste entièrement v2. Le
manifeste composé garde les ressources, frames, hashes et packs sources. Le pack
précédent reste immuable et installable.
