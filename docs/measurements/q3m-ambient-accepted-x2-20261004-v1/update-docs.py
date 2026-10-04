"""Update current queue summaries; leave immutable production/installation notes historical."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
qa='index/qa-decisions/ambient/2026-10-04-accepted-full-available-ambient-q3m-v7-x2-catmullrom-v1.json'
proposal='../docs/measurements/q3m-character-old-selection-x2-20261004-v1/README.md'
p=ROOT/'sprite/SUIVI_Q3M.md';s=p.read_text(encoding='utf-8')
assert '## Ambient : famille complète disponible validée' not in s
s=s.replace('| `ambient` | 18/21 | — | **Famille disponible complète Q3m V7 x2 améliorée sans SDF installée**, 18 IDs/16 modèles/34 BAM/2 580 frames ; QA ingame en attente. KEG1/2/3 sans BAM. |',
    '| `ambient` | 18/21 | — | **Famille disponible complète Q3m V7 x2 améliorée sans SDF installée et validée**, 18 IDs/16 modèles/34 BAM/2 580 frames. KEG1/2/3 sans BAM. |')
s=s.replace('59 IDs /7 familles disponibles complètes installées ; 40 IDs /5 familles validées','59 IDs /7 familles disponibles complètes installées ; 58 IDs /6 familles validées')
s=s.replace('`town_static` V7 sans SDF)** ; colonnes','`town_static` V7 sans SDF, `ambient` V7 sans SDF)** ; colonnes')
s+='\n## Ambient : famille complète disponible validée — 2026-10-04\n\n'
s+='- Utilisateur : « tout validé » ; **18 IDs/16 modèles/34 BAM/2 580 frames physiques acceptés ingame**, Q3m V7 K6 x2 palette améliorée/CatmullRom, sans SDF ; cinq bindings alias chauve-souris/rat conservés. KEG1/2/3 sans BAM exclus.\n'
s+=f'- QA immuable `{qa}` : exactes34feuilles/39bindings et runtime/DLL/INI/shaders installés, provenance production/vérification/snapshot ; catalogue `58e78576…afc2d`. Preuves historiques de production/installation non réécrites ; aucune modification ingame à cette étape.\n'
s+='- Totaux recette : sept familles/59 IDs installés, **six familles/58 IDs validés** ; Ogre QA en attente, aucune release.\n'
s+=f'- Prochain lot proposé seulement : **character_old**, sept IDs avec BAM sur8, six ensembles de sprites (cinq corps visibles +un transparent), 99 BAM/4 725 frames physiques →3 771 travaux uniques, **288 hits compatibles →3 483 nouveaux travaux dont41transparents**. Drizzt/Elminster/moine/squelette/Sarevok ; gardes funestes6405/6406 partagent22BAM entièrement transparents natifs ; XHFF6621 sans BAM. `{proposal}` ; aucun traitement/installation.\n'
p.write_text(s,encoding='utf-8')
p=ROOT/'sprite/index/README.md';s=p.read_text(encoding='utf-8')
s+='\n- Ambient **famille complète disponible acceptée ingame**, [QA exacte](qa-decisions/ambient/2026-10-04-accepted-full-available-ambient-q3m-v7-x2-catmullrom-v1.json), 18 IDs/16 modèles/34 BAM/2 580 frames physiques ; sept familles/59 IDs installés, six familles/58 IDs acceptés. Nouveau lot [Character_old proposé, non traité](../../docs/measurements/q3m-character-old-selection-x2-20261004-v1/README.md) : sept IDs/six ensembles/99 BAM, 3 483 travaux nouveaux après cache/déduplication ; XHFF absent, MDGU transparent natif.\n'
p.write_text(s,encoding='utf-8')
p=ROOT/'.gitattributes';s=p.read_text(encoding='utf-8')
for line in ('docs/measurements/q3m-ambient-accepted-x2-20261004-v1/** -text -whitespace','sprite/index/qa-decisions/ambient/*.json -text -whitespace'):
    assert line not in s;s+=line+'\n'
p.write_text(s,encoding='utf-8')
