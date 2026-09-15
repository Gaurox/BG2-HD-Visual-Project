# ReboutCX P12 — cache de session implémenté, 2026-09-15

## État

- Demande : appliquer la piste de `REBOUTCX_P12_RECHERCHE.md` après les commits
  `09129723` / `7d971636`. Implémentation et tests courts terminés ; **aucune famille P12 produite**.
- Nouveau run : `reboutcx-p12-cache86-v1`, contrat `p12-cached-fixed86-q32-v1`.
- Aucun job/run existant modifié ; pas de catalogue global, installation, release ni extinction.
- Fichiers Python/jobs P12 écrits en LF ; les SHA de code sont enregistrés dans chaque nouveau run.

## Architecture appliquée

| Fichier dans `pipeline/scripts/` | Rôle |
|---|---|
| `reboutcx_cache_p12.py` | SHA des entrées pixels, propriétaire unique par clé, futures partagées, résultats immuables, éviction LRU |
| `reboutcx_plan_p12.py` | Lecture des seules sources des jobs à produire ; comptes d'occurrences en RAM ; clones de ressources exclus |
| `reboutcx_runtime_p12.py` | Réutilisation xBR + préparation RGB + modèle + BOX + quantification ; réservations par groupe actif |
| `reboutcx_batch_p12.py` | Canvas q32, entrée normalisée, forme CUDA N=86, places vides remplies de zéro ; téléchargement des seules sorties utiles |
| `reboutcx_full_p12.py` | Dérivation de jobs P8–P11 ; écriture/validation par composant ; publication versionnée ; refus d'écrasement |
| `reboutcx_playable_p12.py` | Contrôleur 3 composants, 2 préparateurs CPU, 3 postprocesseurs, un modèle/GPU persistants, vérificateur séparé |
| `Run-ReboutCX-PlayableCharacters-P12.ps1` | Affiche le plan par défaut ; exécution explicite avec `-Run` |

- Clé : indices + dimensions + transparence + RGBA natif + palette native complète + palette
  de référence réelle + classes + configuration/hash modèle + contrat pixels + outil xBR.
  Resref, numéro de frame, centres, item et couche restent propres aux enregistrements écrits.
- Cache : guide uint8 x2, indices quantifiés x2, cible RGB uint8 x2, métriques, représentants.
  Aucun crop float32 x4 conservé. Le consommateur conserve sa frame source et sa palette.
- Contrôleur : admission des seules clés répétées ; libération après dernière demande prévue.
  Accès direct à un composant : LRU sans précomptage. `-CacheMiB 0` désactive la rétention,
  conserve la fusion des demandes simultanées ; ce n'est pas un témoin P11 sans cache.
- Budget cache par défaut **1 024 MiB**, séparé des **4 096 MiB estimés** des groupes actifs.
  Charge des tableaux/objets + réserve conservative de 4 KiB par future ; métadonnées d'admission
  plafonnées à min(cache/16, 32 MiB). Éviction sans attente de place.
  Ces budgets ne sont pas une limite stricte du RSS Windows ou de la VRAM ; sources décodées,
  runtime CUDA/processus et tableaux temporaires du précomptage s'ajoutent.
- Antiblocage : réserver un groupe avant ses clés ; aucun propriétaire dans un groupe futur ;
  finir/publier tout le travail possédé avant d'attendre ses dépendances. Le préchargement du
  groupe suivant de P11 est retiré ; les trois composants assurent le recouvrement des phases.
- Écriture et vérification restent individuelles. Alpha, classes, indices admissibles, représentants,
  centres, cycles et contrats de registres restent contrôlés. Les GIFs internes au contrat hérité
  ne constituent pas une décision de QA humaine.
- Mesures séparées : frames source, frames modèle logiques, frames réellement calculées,
  hits cache, slots GPU et remplissage. Débit comparable à P11 = **frames logiques / temps jusqu'à
  la dernière vérification**, précomptage inclus. `unique_model_frames` compte les calculs réels.

## Gain : estimation révisée, pas un résultat de production

Lecture de 65 composants / 630 BAM / 113 groupes ; mêmes données P11, aucune inférence.
Preuve : `measurements/reboutcx-p12-20260915/fixed86-slots-v2.json` ; **3,897 s**, processus 4,167 s.

| Mesure / hypothèse | Valeur |
|---|---:|
| Frames modèle logiques P11 | 146 066 |
| Identités pixels différentes | 97 831 |
| Répétitions supprimables avec rétention suffisante | 48 235 / **33,02 %** |
| Pixels P11 avec padding spatial | 403 672 064 |
| Pixels utiles après cache | 291 731 456 |
| Pixels réellement soumis avec remplissage à 86 | 337 989 632–338 518 016 |
| Réduction de pixels GPU, remplissage compris | **16,14–16,27 %** |
| Places vides selon trois ordres de groupes | 11 475–11 647 |
| Estimation du pic de cache prêt, hors réservations actives | 517–849 MiB |

Modèle simplifié : `329,633 - 236,618 × 0,1614 ≈ 291,44 s` : **4 min 51**, débit **×1,131**.
Il remplace l'estimation initiale de 4 min 24 qui ignorait le remplissage. Ce n'est ni une mesure
du débit P12 ni une garantie : précomptage/hachage/attentes s'ajoutent ; économies xBR/quantification
s'y opposent ; ordonnancement réel et évictions peuvent changer les valeurs. Les trois scénarios
supposent une rétention suffisante, sans simuler exactement les trois composants concurrents.

## Validation courte effectuée

- `pipeline/tests/test_reboutcx_p12.py` : **13/13**, 0,527 s ; processus 0,876 s, timeout externe 12 s.
  Clés, contenu immuable, éviction, admission/dernière utilisation, budget nul, cache intercomposants,
  cycle forcé A→B/B→A, échecs préparation/post, registre/clone/cycles/publication/refus d'écrasement,
  postprocesseur Windows spawn, comptage du contrôleur jusqu'à la vérification.
  Les sorties synthétiques sont dans des répertoires temporaires dédiés, supprimés après test.
- `pipeline/tests/check_reboutcx_p12_gpu.py` : **5,364 s processus** ; deux entrées réelles
  `WQMWHA1:0` et `WQMH0A1:0`, canvas 32×32 et 64×64. Froid/chaud/re-froid : mêmes RGB uint8 et
  indices ; chaud = zéro frame modèle ; float crops identiques aux slots 0/85 avec voisins différents.
  Alpha, classes, indices admissibles et guides antérieurs conformes sur ces deux entrées.
  Zéro run de production, zéro fichier temporaire produit. Ce sondage ne prouve pas l'identité
  pixel à pixel de toute la famille ni celle de P12 avec P11.
- Analyse de syntaxe Python/PowerShell : OK. **147 couples chemin/SHA** épinglés par 130 manifestes
  P10/P11 inchangés, 1,212 s. Le diff des fichiers déjà suivis est vide.
- Sonde de coût initiale arrêtée à son plafond de 7 s ; réécrite pour exploiter l'identité native
  équivalente sans reconstruire les RGBA. Deux relevés suivants terminés en moins de 4,2 s processus.
  `fixed86-slots-v1.json` utilisait une provision d'objets plus faible ; v2 durcit cette estimation.

## Utilisation et prochaine mesure

Python = `config://chainner_python`, résolu via `workspace_paths.get_path` ; aucune commande de
production ci-dessous exécutée pendant cette implémentation.

```powershell
$taskPython = python -B -c "import sys; sys.path.insert(0,'pipeline/scripts'); from workspace_paths import get_path; print(get_path('chainner_python',required=True))"
$family = 'sprite/families/playable-characters/5211-elf-female-mage-low'
$queue = "$family/family-runs/complete-reboutcx-p12-v1/jobs/elf-female-mage-low-p12-v1.json"
& $taskPython -B pipeline/scripts/reboutcx_playable_p12.py prepare --family-job "$family/family-runs/complete-reboutcx-p8-v1/jobs/elf-female-mage-low-complete-reboutcx-p8-v1.json" --output $queue
& pipeline/scripts/Run-ReboutCX-PlayableCharacters-P12.ps1 -Queue $queue
# Lors d'une reprise autorisée de cette seule famille : ajouter -Run.
```

Protocole de mesure : même famille 0x5211, 65 composants, sortie P12 neuve ; conserver tous les runs
antérieurs. Lire le dernier événement `complete` dans `sprite/.work/reboutcx-p12-production/` ;
exiger 65 vérifications, 180 494 frames source et 146 066 frames modèle logiques. Comparer le temps
total à 329,633 s P11 ; publier calculs réellement évités, slots vides, pic/évictions et coût du
précomptage. Comparer alpha/classes/centres/cycles/indices/représentants sur un échantillon ciblé.

Risques restants : précision numérique hors des deux cas testés, coût des lots incomplets,
IPC de la cible RGB conservée pour toute frame, perte du préchargement suivant, admission et pression
mémoire. Si le remplissage domine : prochaine piste = assembler au propriétaire GPU des demandes
de même canvas venant de plusieurs composants, avec vidage borné et N=86 constant. **Aucun plafond
matériel établi** ; mesurer P12 avant d'ajouter cette modification.
