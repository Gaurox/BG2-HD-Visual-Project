# ReboutCX — sprites BG2EE

Référence opérationnelle. Flux commun : [`../sprite/PROCESSING.md`](../sprite/PROCESSING.md) ;
publication/installation : [`../sprite/FAMILY_APPEND.md`](../sprite/FAMILY_APPEND.md).

## Deux modes raster, un runtime

| Mode | Production | Catalogue |
|---|---|---|
| xBR | xBR2x déterministe, sans modèle | base canonique cumulative |
| ReboutCX | modèle x4, réduction BOX x2, quantification sémantique | dérivé complet de la base xBR |

Un catalogue ReboutCX contient les composants explicitement remplacés et conserve xBR partout
ailleurs. Les deux modes utilisent le même format x2, le même runtime, les mêmes BAM/palettes x1 et
le même emplacement installé. Aucun choix par instance ingame ; changer de mode signifie installer
un autre catalogue complet.

## Appliquer ReboutCX

1. Résoudre la famille/composant dans `sprite/index/`. Le composant complet doit déjà exister dans
   le catalogue xBR parent.
2. Matérialiser les sources via le job xBR si nécessaire.
3. Créer un job ReboutCX versionné à partir d'un cas validé du même profil palette/calque.
4. Annoncer l'usage GPU, puis produire et vérifier :

```powershell
python pipeline/scripts/reboutcx_full.py run <job-reboutcx>
python pipeline/scripts/reboutcx_full.py verify <job-reboutcx>
```

5. Créer un job de catalogue dérivé cumulatif sous
   `sprite/catalogs/creature-x2-reboutcx/jobs/`, puis :

```powershell
python pipeline/scripts/reboutcx_catalog.py build <job-catalogue-reboutcx>
python pipeline/scripts/reboutcx_catalog.py verify <job-catalogue-reboutcx>
```

6. Installer transactionnellement selon [`../sprite/FAMILY_APPEND.md`](../sprite/FAMILY_APPEND.md),
   BG2EE et InfinityLoader fermés. QA seulement sur le delta utile ; décision limitée aux
   compositions réellement vues.

`reboutcx_full.py run` est la seule étape GPU. Vérification, catalogue et installation sont CPU.
Une source, recette ou sélection modifiée exige un nouveau job/run ; `verify` reprend un run scellé.

## GPU — micro-lots Character (mesure 2026-09-15)

- Stratégie cible : **un processus modèle GPU**, file de frames réelles regroupées par géométrie, puis
  micro-lots de **86** au plus. Ne jamais ajouter de doublon en production ; le dernier lot peut être
  inférieur à 86.
- Mesure RTX 5090 sur 60 frames réelles `0x5000/CHMB1`, `60x26` (répétitions uniquement pour saturer
  le benchmark) : `86 = 1 008 img/s, 557 Mio`; `84 = 1 001`; `88 = 997`; `90 = 949`.
  `128/256/512` sont viables mais moins rapides et consomment davantage de VRAM.
- Le mode historique *un processus par composant* est à éviter : 32 processus a échoué avec
  `CUDNN_STATUS_INTERNAL_ERROR_HOST_ALLOCATION_FAILED`; 16 processus donne un débit global très
  inférieur au micro-lot.
- Le calcul par lot varie de 1–2 niveaux RGB bruts par rapport à un appel unitaire. Il exige donc un
  **nouveau job/run versionné** et une vérification des indices quantifiés/classes/palette et QA avant
  production. Les runs P8 scellés restent immuables.

## Contrat raster

```text
RGBA BAM source ──xBR2x──> guide indices/classes/transparence
RGB préparé ──ReboutCX x4──BOX x2──> cible RGB
cible + guide + palette de référence ──OKLab sans dithering──> indices x2
```

- Géométrie, cycles, centres, ordre, resrefs et palettes dynamiques restent ceux du BAM x1.
- `unique(indices_sortie) ⊆ unique(indices_source_frame)`.
- Transparence exacte ; ombre/indices spéciaux restent dans leur classe.
- Quantification uniquement dans la classe sémantique du guide xBR ; aucun nearest global.
- Palette/classes inconnues ou candidat vide : arrêter ce composant, sans deviner.
- Character false-color : profil `character-bg2ee-2.7.3.0`, palette réalisée RANGES12 fixe pour
  l'entrée/quantification, classes Character pour body/arme/bouclier/casque.
- Le guide xBR reste une provenance interne ; une sortie ReboutCX n'est jamais étiquetée xBR.

## Catalogue dérivé

Chaque remplacement épingle :

```text
animation_id + owner + component_index xBR
digests physique/logique + shards + ensemble RESREF exact
manifest ReboutCX + SHA-256
```

Sélectionner par `(animation_id, component_index)`. Un composant xBR partagé peut être remplacé pour
une animation et conservé pour les autres. Mapper les ensembles RESREF exacts ; ne jamais associer
préfixes et indices par position. Le job dérivé redéclare tous les remplacements antérieurs à
conserver. Le pointeur xBR canonique reste intact.

## Suivi des personnages jouables

Courant : `sprite/catalogs/creature-x2-reboutcx/jobs/playable-characters-reboutcx-progress-p13-v2.json`
épingle **78/78 familles complètes, 4 896 composants**, par manifeste+SHA-256.
Historiques immuables : `…-p13-v1.json` (77/4 831), `…-p12-v1.json` (33/2 109), `…-p9-v1.json` (23/1 471).
Mesure/reprise P12 : [REBOUTCX_P12_DIX_FAMILLES_20260915.md](REBOUTCX_P12_DIX_FAMILLES_20260915.md).

### P13 — cache partagé entre familles (2026-09-21)

`pipeline/scripts/reboutcx_shared_p13.py` compose `execute`/`verify`/`Runtime` P12 sans les modifier
(manifestes = runs P12 valides). `docs/measurements/reboutcx-p13-shared-20260921-v1/` : `plan.json`,
`queue*.json`, `production-report.json` (44 familles, 2 722 composants, 7 631 830 frames, **568 613
inférences pour 6 272 668 logiques = 91 % réutilisées**, 5,79 M évitées).

```powershell
$py = 'config://chainner_python'   # interpréteur chaiNNer
python reboutcx_shared_p13.py prepare <dir>            # jobs P12 des familles en attente → queue.json
python reboutcx_shared_p13.py shard <queue> 4          # cohortes entières par shard (perte de partage 0,5 %)
python reboutcx_shared_p13.py run <queue-shard> --tag shard-K --components 3 --pre-workers 2 --post-workers 2 --gpu-fraction F
python reboutcx_shared_p13.py aggregate                # progress.json + milestones.log (jalons 5 %)
python reboutcx_shared_p13.py finish <queue> --report <report.json> ; python reboutcx_shared_p13.py snapshot <plan> --report <report.json>
```

- **Un seul processus est GIL-borné** (décodage/écriture/vérification interne en threads) : 231 frames/s
  mesurés, bien en deçà du GPU. **4 processus par cohortes** (composants de mêmes BAM ensemble) : ≈ 3 700
  frames/s cumulés ; cohortes triées par coût décroissant, pic de rétention du cache estimé 1,3 Gio.
- **VRAM** : un lot fixe de 86 sur canvas ≈ 224 px demande > 17 Gio (allocation unique de 8,2 Gio). Un plafond
  `--gpu-fraction` trop bas ⇒ OOM CUDA ; `LockedRuntime` sérialise les canvas ≥ 128×128 entre processus (mutex
  Windows) et vide le cache CUDA après. Donner ≥ 0,45 aux shards qui portent les COMPS39/gros canvas.
- Reprise : relancer le même `run` ; les composants scellés sont revérifiés, seuls les manquants sont calculés.
  Nettoyer les `.reboutcx-p12-cache86-v1.tmp-<pid>` orphelins des processus tués (run final présent).
- **0x6110** : 4 sources xBR d'août (`chfb1/2/3`, `chff4`) sans champ `layer` ⇒ `prepare` P12 (scellé) échoue.
  P13 (`prepare_with_derived_layer`) lit `source-p13-layer/manifest.json`, dérivé (layer=body, défaut xBR ;
  BAM/hashes scellés inchangés). Run séparé `docs/measurements/reboutcx-p13-0x6110-20260921-v1/`, 65 composants.
  Jobs de famille P8 de 0x6102/0x6110 créés par `reboutcx_character_family.py bootstrap`.
- **Catalogue dérivé** `catalog-reboutcx-playable-characters-p13-v1` (`reboutcx_shared_p13.py catalog <snapshot>
  --seed <catalogue précédent> --job-id …`) : 4 902 remplacements (136 hérités), 733 shards ; sélection par
  (animation, component_index), sans ambiguïté de RESREF partagé. `reboutcx_catalog.py build` ≈ 46 min
  (lecture ≈ 380 Gio, mono-processus). Installé en thin-catalog avec
  `-RuntimeManifest pipeline/runtime/manifests/iee-monster-msah-composite-v5.json` (le défaut du script est un
  runtime plus ancien). État `installed-pending-qa` : QA en jeu et release non faites.

Les snapshots de suivi sont des instantanés de production vérifiée, pas une QA ni une release.
Après reprise, créer une nouvelle version ; conserver les instantanés antérieurs.

Décompte : une famille = ID d'animation (race/sexe/apparence/variante LOW), pas un personnage nommé.
L'ancien job xBR référence 76 familles sous `playable-characters` et deux entrées historiques sous
`sprite/jobs` (`0x6102`, `0x6110`), soit **78**. Répartition : 30 LOW, 46 ordinaires, 2 moines.

Recherche des doublons : [groupes de frames inter-familles](REBOUTCX_GROUPES_FRAMES_RESTANTES_20260915.md) ;
partage inter-familles **appliqué en P13** (ci-dessus).

## Références validées

| Cas | Référence |
|---|---|
| Monster sans false-color | `sprite/families/monsters/7fxx/7f02-mbeh-beholder/jobs/reboutcx-p2-mbeh-v2.json` |
| Composite MultiNew | `sprite/families/composite-monsters/multi-new/12xx/1200-mdr1-dragon-red/jobs/reboutcx-full-v1.json` |
| Character false-color | `sprite/families/playable-characters/6100-human-male-fighter/chmb3/jobs/reboutcx-p8-full-v1.json` |
| Catalogue mixte complet | `sprite/catalogs/creature-x2-reboutcx/jobs/catalog-reboutcx-character-6100-complete-p8-v1.json` |

État validé `0x6100` : 65/65 composants produits et vérifiés ; génération
`CB24B195ABABF62F29DAFE1543A178EC52F692789A9477B8E67390EF3E1F514D`, catalogue
`EFCD5763901262458ED7E4154E3C2B24E37C4F093022B66B4594748BE269D121`. QA ingame acceptée sur
Minsc/Anomen et les préfixes `CHMB3`, `WQLS2`, `WQLWH`, `WQLJ6`, `WQLC3` ; ne pas étendre cette
preuve visuelle aux 60 autres composants.

## Garde-fous utiles

- Préserver xBR et les runs/QA scellés ; aucun `--force` sur un run existant.
- Fermer jeu et InfinityLoader avant install/restore ; ne pas éditer l'INI à la main.
- Une QA xBR n'est pas une QA ReboutCX. Une installation n'est ni QA ni release.
- Pas de TP2, payload, staging, `content.json` ou rebuild global pendant la production d'un asset.
- Modèle et outils externes via `config://`; ne pas inscrire de chemin machine.
