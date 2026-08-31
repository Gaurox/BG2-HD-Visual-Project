# Animations de décor — point d'entrée

Les animations BAM sont indépendantes des pixels de maps. Leur géométrie logique reste x1 ; le
moteur charge des textures physiques x4 et, lorsque le registre le demande, une timeline visuelle
30 fps.

## Sources de vérité

- `index/manifest.json` : snapshot de l'inventaire.
- `index/occurrences.csv` : chaque occurrence ARE, avec son type `BAM`/`WBM`/`PVRZ` et sa palette.
- `index/ressources.csv` : les BAM extraits ; `index/zones.csv` : synthèse typée par zone.
- `index/animation_upscale_registry.csv` : validation spatiale par resref.
- `index/animation_alpha_corrections.csv` : correctifs alpha approuvés ou expérimentaux.
- `qa-approval.json` du run : seule approbation temporelle.
- `releases/BG2-HD-Upscale/manifests/animation-release-candidates.json` : candidats release.
- `index/path-migrations.json` : résolution physique des anciens chemins `proto/` et des packs
  historiques déplacés, sans statut.
- `index/qa-evidence-migrations.json` : résolution bornée vers les blobs Git exacts lorsqu'une QA
  scellée cite une ancienne version d'un catalogue canonique mutable ; sans nouveau statut.

`runs/`, `packs-par-zone/`, `proto/`, backups et captures ne décrivent jamais à eux seuls l'état
courant.

## Méthodes actives

| Besoin | Procédure | Entrée principale |
|---|---|---|
| Upscale spatial x4 | [`../pipeline/ANIMATION_UPSCALE_PIPELINE.md`](../pipeline/ANIMATION_UPSCALE_PIPELINE.md) | `run_animation_upscale.py` |
| Interpolation d'un cycle natif | [`../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md`](../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md) | `run_animation_interpolation.py` |
| 15 → 30 fps pause-aware | [`../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../pipeline/ANIMATION_UPSCALE_30FPS_V2.md) | `run_animation_upscale_30fps_v2.py` |
| Correctif alpha | [`../pipeline/ANIMATION_ALPHA_CORRECTIONS.md`](../pipeline/ANIMATION_ALPHA_CORRECTIONS.md) | builders alpha spécialisés |
| Fond/halo sur une animation `Blended` | [`../pipeline/ANIMATION_BLENDED_RGB_NEUTRALISATION.md`](../pipeline/ANIMATION_BLENDED_RGB_NEUTRALISATION.md) | `build_blended_rgb_neutral_pack.py` |
| Packs par zone | [`../pipeline/ANIMATION_PACKS_PAR_ZONE.md`](../pipeline/ANIMATION_PACKS_PAR_ZONE.md) | `split_animation_pack_by_area.py` |
| Masque différent par occurrence | [`../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md`](../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md) | registre v3 lié aux coordonnées ARE |
| Contrat runtime complet | [`UPSCALE_ANIMATIONS_ZONE.md`](UPSCALE_ANIMATIONS_ZONE.md) | registre + DLL |

TimedTimeline v2 est la méthode retenue pour la timeline 30 fps. Le registre v3 conserve cette
timeline et ajoute le routage par occurrence. Les prototypes d'horloge antérieurs sont archivés.

## Organisation

```text
animations/
  index/                 # catalogues canoniques
  ressources/            # sources BAM et planches, données ignorées par Git
  runs/                  # production, variantes et preuves historiques, données ignorées
  packs-par-zone/        # seuls packs actifs/indexés, données ignorées
```

Le nettoyage P3 conserve six racines actives : les sources exactes des cinq candidats release, le
dernier lot installé/validé incluant AR1400, et le split canonique FIRE_1/FIRE_4 (une même racine
peut remplir plusieurs rôles). La classification des 71 racines antérieures, leurs manifests
hashés et les chemins d'archive sont dans
`docs/workspace-animation-packs-p3-manifest.json`. Ce reçu est physique uniquement : il ne remplace
ni les catalogues, ni les QA, ni `animation-release-candidates.json`.

Depuis la migration physique de 2026-08-31, aucun travail animation ne doit être créé sous
`proto/`. Les anciens prototypes ont conservé leur nom sous `animations/runs/`; leurs rôles
(`canonical-prototype`, expérience rejetée, référence QA, etc.) sont décrits sans décision métier
dans `index/path-migrations.json`. Les manifests scellés qui citent encore leur ancien chemin ne
sont pas réécrits. Deux racines de sortie du workshop portails n'existaient déjà plus au moment du
déplacement ; elles sont marquées `obsolete-unmaterialized` et ne doivent pas être recréées. Une
reprise éventuelle utilise un nouvel identifiant sous `animations/runs/`.

Le script Potracer du workshop AM0604A reste un fichier historique inchangé. Sa dépendance
`potracer==0.0.4` est déclarée dans `requirements.txt` : l'ancien ajout de chemin `.tools` incorporé
au script n'est plus un prérequis de reproduction et ne doit pas être recréé sous `runs/`.

Traiter chaque frame RGB et alpha séparément. Ne jamais upscaler une planche concaténée. Un pack
global dépassant 512 Mio doit être découpé par zone.

## Promotion

Le contrat runtime accepte les registres v2 et v3 avec le candidat renderer
`iee-0.1.0-alpha.6`, encore soumis aux gates clean-game et cycle de vie. Le manifeste `alpha.5`
est rejeté et conservé uniquement comme preuve historique avec sa source Git ; il ne constitue
plus un arbre de travail ni une source de release. Depuis le 2026-08-28 AR0602 est passée en v3
(PORTL1B en 30 fps + FLAME2S) : le témoin de
rétrocompatibilité v2 est désormais **AR0603** (registre v2, TimedTimeline sans routage par
occurrence). AR0900 v3 reste le témoin du routage par occurrence. Toute autre zone doit être
ajoutée explicitement à `animation-release-candidates.json` avec sa version, ses hashes et son
approbation.

QA et intégration release restent deux décisions distinctes. Un run `pending-qa`, un prototype ou
un pack présent dans l'override n'est pas éligible.

Après une intégration explicitement approuvée, valider le seul pack concerné
avec `Test-BG2HDAreaAnimationCandidate.ps1 -Area ARxxxx`. Cette gate génère un
manifest et un staging temporaires limités à la zone ; ne pas lancer le
staging global ni Phase 4 à chaque tâche. Ils restent obligatoires avant un
package, ou après une modification du runtime, du générateur, du format de
pack ou du Core.

## Tests légers

```powershell
python -m unittest `
  pipeline.tests.test_animation_upscale_pipeline `
  pipeline.tests.test_animation_interpolation_pipeline `
  pipeline.tests.test_animation_upscale_30fps_v2 `
  pipeline.tests.test_animation_runtime_pack `
  pipeline.tests.test_animation_pack_area_split `
  pipeline.tests.test_combine_area_pack_splits
```
