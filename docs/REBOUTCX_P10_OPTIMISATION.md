# ReboutCX P10 — optimisation, 2026-09-15

## État

- Implémentation seule ; aucune production, queue réelle, QA, installation, release ou catalogue dérivé créé.
- P8/P9 + helpers historiques + instantané `playable-characters-reboutcx-progress-p9-v1.json` conservés.
- Identités nouvelles : job/run `reboutcx-p10-stream86-v1`, contrat `p10-normalized-padded86-v1`.
- P9 omet `/255` avant le modèle. P10 normalise en float32 avant FP16 ; changement de pixels attendu, aucune équivalence P9/P10 ni validation visuelle déduite.

## Code

| Fichier sous `pipeline/scripts/` | Rôle |
|---|---|
| `reboutcx_cpu_p10.py` | représentants vectorisés/réutilisés ; validation indépendante ; caches bornés palette OKLab/classes ; mêmes calculs f64 et départages |
| `reboutcx_batch_p10.py` | entrée 0–1 ; padding 64 ; crops x4 float32 ; événements CUDA ; pas de conversion x4 uint8 inutile |
| `reboutcx_runtime_p10.py` | un propriétaire CUDA/modèle ; 2 processus préparation + 3 processus BOX/quantification ; prélecture d'une ressource ; deux micro-lots de post-traitement maximum par composant |
| `reboutcx_full_p10.py` | dérivation P8/P9 → P10 ; registres V3 ; publication atomique du manifeste définitif ; SHA des helpers historiques et P10 |
| `reboutcx_playable_p10.py` | queue explicite épinglée par SHA ; composants longs d'abord ; 3 composants actifs ; processus de vérification séparé ; logs de session exclusifs |
| `Run-ReboutCX-PlayableCharacters-P10.ps1` | Python via `config://chainner_python` ; affiche l'ordre par défaut ; exécution uniquement avec `-Run` |

Contrats conservés : frames réelles sans duplication ; ordre/centres/cycles/RESREF ; guide xBR/provenance ; transparence ; palette réalisée ; indices présents dans la frame ; classes ; BOX float32 ; quantification f64 sans dithering. Regroupement conservé **par ressource et géométrie**, max 86 : pas de regroupement variable entre ressources.

Mémoire : réservations estimées en octets, défaut 2 048 Mio, entrée/guide/IPC + crops ; dépassement d'une ressource = erreur explicite. Ce plafond concerne les ressources en traitement, pas le RSS total, les sources déjà décodées ni la VRAM du modèle. Représentants : chemin historique pour les frames natives >65 535 pixels afin de conserver le comportement uint16/sentinelle.

## Mesures courtes

| Vérification | Résultat |
|---|---|
| `pipeline/tests/test_reboutcx_p10.py` | 10 tests CPU, 1,065 s ; registres/classes/transparence, corruption, clone, publication, immutabilité, singleton modèle, workers Windows spawn, mémoire libérée après échec, départ pendant vérification |
| `pipeline/tests/check_reboutcx_p10_gpu.py <job>` | 2 frames CHMB1 ; référence normalisée indépendante ; crops/BOX/indices exacts ; 3,824 s, plafond externe 8 s ; aucun fichier de sortie |
| Représentants, 24 frames WQMFSA1 / 301 389 pixels | 219,114 → 1,490 ms, **×147 local** |
| Écriture + vérification d'un registre des mêmes 24 frames | 452,635 → 21,165 ms, **×21,39 local**, SHA identiques |
| Microbenchmark CPU complet | 0,915 s ; répertoire temporaire supprimé ; aucun appel CUDA |

Gain par famille **estimé ×1,5–2**, non mesuré. Référence P9 : 154–181 frames réellement inférées/s ; 13–16 min/famille hors préparation des jobs. Un gain local n'est pas un gain global.

## Usage après autorisation d'une reprise

Exécuter depuis la racine avec le Python configuré. Les commandes ci-dessous ne sont pas exécutées par cette modification.

```powershell
$python = python -B -c "import sys; sys.path.insert(0,'pipeline/scripts'); from workspace_paths import get_path; print(get_path('chainner_python',required=True))"
# $familyJob : job de famille P8 déjà préparé ; aucune préparation P8 implicite.
# $queue : nouveau chemin JSON de queue P10, jamais un catalogue.
& $python -B pipeline/scripts/reboutcx_playable_p10.py prepare --family-job $familyJob --output $queue
& $python -B pipeline/scripts/reboutcx_playable_p10.py plan $queue
# Production : seulement lors d'une reprise demandée.
& ./pipeline/scripts/Run-ReboutCX-PlayableCharacters-P10.ps1 -Queue $queue -Run
```

Queue existante : nouvelle exécution → vérification des runs déjà présents, aucun écrasement. Run temporaire interrompu : erreur explicite ; ne pas effacer/remplacer un run historique. Une évolution du contrat/code après production exige une nouvelle version.

## Lecture des performances

- Logs `sprite/.work/reboutcx-p10-production/session-*.jsonl` : démarrages, fin de rendu, vérifications, échecs, durée jusqu'à dernière vérification, frames réellement calculées, chargement modèle unique, réservations mémoire.
- GPU : `model_cuda_seconds` = événements autour du descripteur ; `model_wait_and_d2h_seconds` = attente modèle + conversion/clamp + D2H, **pas** transfert seul.
- CPU : préparation/xBR/mapping/remplissage, BOX/arrondi/quantification, temps CPU des processus, attente file/IPC, écriture, vérification interne ; sérialisation/écriture du manifeste dans l'événement `render-finished`.
- Sommes de phases concurrentes non additionnables. Débit de session = nouvelles frames modèle / durée jusqu'à dernière vérification ; reprises avec vérifications d'existants à distinguer des sessions entièrement nouvelles.
- Tests courts sans production : script CPU ; script GPU dans un sous-processus avec `timeout=8`. Une mesure globale nécessite ultérieurement un lot représentatif autorisé, incluant COMPS39.
