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

Courant : `sprite/catalogs/creature-x2-reboutcx/jobs/playable-characters-reboutcx-progress-p12-v1.json`
épingle **33/78 familles complètes, 2 109 composants ; 45 familles restantes**, par manifeste+SHA-256.
Historique immuable : `playable-characters-reboutcx-progress-p9-v1.json` (23 familles/1 471 composants).
Le P12-v1 ajoute dix familles et référence la mesure P12 déjà scellée de `0x5211`.
Mesure/reprise : [REBOUTCX_P12_DIX_FAMILLES_20260915.md](REBOUTCX_P12_DIX_FAMILLES_20260915.md).

Instantanés de production vérifiée, **pas** des catalogues dérivés, une QA, une installation ou une
release : des familles partagent des RESREF xBR alors que leurs sorties ReboutCX diffèrent.
Après reprise, créer une nouvelle version ; conserver les instantanés antérieurs.

Décompte : une famille = ID d'animation (race/sexe/apparence/variante LOW), pas un personnage nommé.
L'ancien job xBR référence 76 familles sous `playable-characters` et deux entrées historiques sous
`sprite/jobs` (`0x6102`, `0x6110`), soit **78**. Répartition : 30 LOW, 46 ordinaires, 2 moines.

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
