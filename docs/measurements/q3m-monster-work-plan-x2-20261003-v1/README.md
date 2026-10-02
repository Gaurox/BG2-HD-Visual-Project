# Phase 2 — plan CPU Q3m Monster x2

État : **plan source complet**, entrée de l'adaptation producteur/lecteur en phase 3.
Contrat inchangé : `../q3m-monster-contract-x2-20261002-v1/contract.json`.
Écritures limitées à ce dossier ; aucun GPU, nouveau guide xBR, cache de production,
registre courant, QA, build, assemblage, configuration, installation, release ou commit.

## Résultat exact

| Cible | ID / famille | BAM / payloads BAM distincts | Frames natives | Tâches Q3m distinctes | Nouvelles tâches modèle | Spéciaux sans GPU |
|---|---|---|---|---|---|---|
| Spectateur | `0x7F02 / MBEH` | `13 / 9` | `6 831` | `1 054` | `1 052` | `2` |
| Bodhi | `0x7F30 / NBOH` | `13 / 11` | `8 100` | `1 244` | `1 242` | `2` |
| Golem geôlier `IGOLEM02` | `0x7F07 / MGLC` | `13 / 13` | `5 994` | `892` | `890` | `2` |
| Total | 3 familles | `39 / 33` | `20 925` | `3 190` | `3 184` | `6` |

- `2 288` cycles, `41 217` slots ; aucune occurrence perdue.
- `4 228` occurrences nécessitant le modèle → `3 184` tâches après déduplication exacte.
  `16 697` marqueurs nuls → `6` tâches spéciales, une par profil palette.
- `3 185` rasters natifs distincts = `3 184` modèle + un marqueur commun.
  `3 185` demandes de guide RGB distinctes ; `3 190` travaux finaux car six profils
  palette restent distincts même sur leur marqueur commun.
- K6 : `19 104` cibles de frame à calculer (`3 184 × 6`), **pas un nombre de batches GPU**.
  Aucun partage supplémentaire des six cibles entre travaux d'encodeur de ce lot.
- Géométrie native entière : aucune crop, rotation, miroir, remap d'indice ou tolérance.
  Centres/cycles hors clés pixel, stockés par occurrence.
- `279` frames MGLC non référencées par les cycles sont conservées. Leurs clés ont
  également des occurrences référencées ; elles n'ajoutent pas de tâche modèle exclusive.

## Ressources / variantes / profils

- Préfixes `MBEH`, `NBOH`, `MGLC`, chacun avec les suffixes
  `G1,G11,G12,G13,G14,G15,G2,G21,G22,G23,G24,G25,G26`.
- Aliases BAM complets vérifiés par octets : `MBEHG2=G21=G22=G23=G24` ;
  `NBOHG2=G23`, `NBOHG22=G24`. Les 39 resrefs et leurs tables restent présents.
- MBEH profils `2/3`, NBOH `4/5`, MGLC `6/7`, règle `2`, owner `3`.
  Les profils G1/G2 séparent les travaux finaux ; aucune fusion avec Character.
- L'audit MBEH manquant en phase 1 est résolu pendant ce décodage nécessaire : toutes
  les `5 184` frames utilisant l'indice `2` sont exclusivement `1×1`, centre `(0,0)`.
  Même propriété confirmée pour NBOH `6 543`, MGLC `4 970`.

## Partages et réutilisation

| Niveau | Résultat | Conséquence |
|---|---|---|
| Entre les trois familles | Un seul input commun : `1×1 / pixel=2` | Aucun partage de frame modèle ; six sorties spéciales par profil |
| Plan Character acquis | Un input et une clé RGB communs, le même marqueur | `0` adoption I/F/dep ; classes/successeurs/fits/alpha/owner différents |
| Anciens traitements MBEH | `1 052` inputs modèle communs à leurs sources | Sources réutilisées ; sorties Q0 incompatibles avec le nouveau Q3m |
| Ancien traitement NBOH | `1 242` inputs modèle communs à ses sources | Sources réutilisées ; sorties Q0 incompatibles avec le nouveau Q3m |
| Autres monstres traités retrouvés | Seulement le marqueur ; aucun input modèle commun | Pas d'inférence réutilisable |
| Guides anciens xBR des trois familles | `3 185` demandes distinctes couvertes | `0` nouveau guide xBR à générer |
| Résultats Q3m Monster compatibles | `0` | `3 184 new_model + 6 new_special`, aucun `reused` encodé |

- Character : SQLite acquis ouvert `mode=ro&immutable=1`, taille/schema/statut lus,
  recherche par index ; comparaison des octets sur égalité de hash. Aucun rebuild,
  rehash global, validation source/QA ou balayage du cache Character.
  Référence : `sprite/index/palette-work-plan.json`, namespace x2
  `15e582a92931128f728d9532113ba86a8a5958361d2989caadb7fbcb6dd20ae2`.
- Historique : neuf manifestes de runs complets retrouvés sous `monsters`,
  `monster-icewind`, `composite-monsters`, comparaison depuis leurs BAM canoniques
  seulement pour les géométries candidates. `95 668` correspondances de records,
  `2 295` inputs distincts ; le premier nombre cumule runs/occurrences répétés.
- Au-delà de MBEH/NBOH : Sahuagin `7F09`, lapin `7F17`, Irenicus `7F37` partagent
  le marqueur avec RGB source égal. Géants `7F3E/7F3F`, dragon rouge `1200` partagent
  ses indices/forme mais pas son RGB source. Zéro input modèle commun dans ces cas.
- `frame_records.indices_sha256` des anciens ReboutCX = **sortie quantifiée x2**,
  pas raster source. Ce hash n'est pas utilisé pour conclure un doublon natif.
- Aucun NPZ de cibles flottantes retrouvé dans ces neuf runs ; leurs quantifications Q0
  ne permettent pas de reconstruire les six cibles du contrat Monster. Prototypes
  MBEH P1 à cycles synthétiques exclus. Pas de scan natif global des autres monstres.

## Guides acquis : portée de l'adoption

- Reprise des trois `runs/x2-nearest-v1/build/build-manifest.json` et registres V3
  référencés ; `x2-nearest` nomme ce run/filtre, les guides proviennent bien de xBR2X.
- Identités physiques vérifiées pour cette adoption : source manifest, hash/taille des
  trois registres, SHA source dans chaque record, frames/centres/transparence du
  représentant ; kernels `xbr2x_batch.js` et `config://mmpx_scalepix` identiques.
  La validation historique xBR acquise est reprise, aucun xBR ni QA relancé.
- Transport du guide inchangé : RGBA source = RGB natif, alpha `0` pour indice `0`,
  `255` ailleurs. **Cet alpha de transport n'est pas l'alpha rendu.** Le décodeur
  Q3m conserve l'alpha de la palette live, notamment l'ombre native du contrat de phase 1.
- `guides.locator_json` = registre/SHA/offset/taille/resref/frame/shape ; `guide_sha256`
  épingle les octets de chaque guide distinct. Aucun PNG/NPZ de guide créé ici.
- L'ancien registre V3 n'est pas installé/mélangé dans le catalogue Q3m : seules ses
  planes de guide sont relues. À l'adoption en phase 3 : relire les octets épinglés,
  valider les classes/spéciaux sous le nouveau profil puis encoder I/F/dep.

## Artefacts / consommation

- `processing-plan.sqlite` : plan local `20 578 304` octets, ignoré Git.
  SHA/taille dans `plan.json` ; générateur et bilans versionnables.
- `plan.json` : descripteur local, **aucun pointeur actif sprite/index modifié**.
- `summary.json`, `verification.json` : bilans CPU ; pas production/QA/installation.
- `analyze.py` : reproduction ciblée ; refuse des sorties existantes.
- Tables : `profiles`, `families`, `resources`, `inputs`, `guides`, `work_items`,
  `frames`, `cycles`, intersections Character et correspondances historiques exactes.
- Vues : `processing_queue`, `frame_map`, `neural_queue`. File modèle et travail
  spécial exhaustifs ; restauration des resrefs/centres/cycles depuis `frames/cycles`.
- Identité commune de comparaison : `analyze_playable_frame_dedup.identities`.
  Travail final = domaine Monster + namespace sémantique profil/contrat + clé RGB source.
  Les namespaces sémantiques CPU **ne sont pas encore des namespaces de cache de production** :
  la phase 3 ajoutera les identités du producteur/encodeur implémentés. Aucun hit par seule clé.
- Aucun consommateur Monster existant : ne pas passer ce descripteur au `WorkPlan`
  Character, qui exige son autre schéma et les 78 IDs acquis.

```powershell
# Depuis le dépôt ; Python config://chainner_python, numpy ; nouvelle destination.
& $phase2Python -B docs/measurements/q3m-monster-work-plan-x2-20261003-v1/analyze.py `
  --output <nouveau-dossier-sous-docs/measurements>
```

## Prochaine unité de travail

**Phase 3** : consommateur de ce plan, cache persistant versionné et encodeur fixe,
writer/lecteur V6 owner 3 avec profils `2..7/règle 2`, tout en préservant
Character `owner 1/profil 1/règle 1`, ses 78 animations et les paperdolls/UI.
Vérifications ciblées du nouveau contrat et dispatch, sans nouvelle QA Character globale.

Puis pilote de phase 4 `NBOHG1 + NBOHG2` : `1 242` frames natives, `117` cycles,
`2 331` slots, **270 tâches modèle + 2 tâches spéciales**, `1 620` cibles K6,
guides déjà disponibles. GPU, assemblage et installation restent des phases suivantes.
