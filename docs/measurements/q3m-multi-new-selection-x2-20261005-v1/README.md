# Proposition Multi_new complète — 2026-10-05

**Analyse seule. Aucun traitement, installation, QA ou commit.** Monster_old demeure installé/QA en attente (`50dd3e8e`). Cible proposée : Q3m V7 K6 x2, couleurs améliorées, CatmullRom acquis, sans SDF ; pipeline contextuel systématique pour toutes les tuiles.

| Ensemble natif distinct | IDs / variantes | Tuiles | BAM physiques | Frames natives | Clés source de base |
|---|---|---:|---:|---:|---:|
| `MDR1` | `1200` rouge ; `1203` vert ; `1204` aqua ; `1205` bleu ; `1206` brun ; `1207` multicolore ; `1208` violet | 9 | 567 | 54 675 | 4 274 |
| `MDR2` | `1201` dragon noir | 9 | 567 | 54 675 | 4 277 |
| `MDR3` | `1202` dragon argent | 9 | 567 | 54 675 | 4 279 |
| `MDEM` | `1300` Démogorgon | 4 | 52 | 27 792 | 4 285 |

- **10/10 IDs disponibles, quatre modèles distincts** : hash indépendant des palettes sur suffixes BAM, indices, dimensions, centres, cycles ; aucun modèle entier identique entre préfixes. Sept variantes `MDR1` partagent exactement les mêmes sprites, avec sept contrats couleur natifs.
- **Aucun BAM ou BMP requis absent**. Les 1 753 BAM natifs ont été résolus depuis CHITIN.KEY/override, canonisés et comparés au SHA du plan source immuable ; trente BMP natifs vérifiés. `source_resources_verified`, `native_replacement_palettes` dans `analysis.json`.
- Palettes particulières des dragons : préfixe INI `MDR1_GR/AQ/BL/BR/MC/PU` + numéro de banque **1..5**. Les trente ressources suffixées existent ; le préfixe sans suffixe n'est pas le nom du BMP à charger. [Contrat natif IESDP](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/ini_anim.htm) : slots dragons `1200..12ff` utilisent `MonsterMulti` codé en dur malgré la rubrique INI `multi_new` ; Démogorgon `1300` utilise `MultiNew`. Deux chemins runtime, owner5 commun.

## Travail réel vérifié

- 191 817 frames natives physiques → **17 103 clés source uniques**, 174 714 répétitions évitées (91,08 %). Union non additive : douze clés communes entre modèles. Seize fichiers BAM doublons complets, douze groupes, tous Démogorgon ; identités/conventions de nommage runtime à conserver.
- Avec dix contrats natifs : **5 155 liaisons BAM /519 867 frames liées →42 772 encodages Q3m uniques**. 205 hits compatibles validés, **42 567 manquants** ;2 241 spéciaux sans inférence ;239 956 cibles K6 neuves uniques, zéro cible existante supplémentaire. Ces compteurs distinguent occurrences, pixels compatibles et palettes.
- Raccords : **5 411 contextes uniques**, dont4 338 à neuf tuiles et1 073 à quatre ;au plus32 466 cibles contextuelles supplémentaires K6. Pas d'estimation de durée à partir du nombre d'IDs. Aucun conflit frame→voisinage ;palettes K6 égales entre parties de chaque groupe. Le plan contextuel est analytique, aucun checkpoint/cible/encodage créé.
- Comparaison des familles restant à compléter, à contrat source identique : Multi_new17 103 ;Monster_icewind81 499 (44/132 IDs disponibles) ;Monster86 963 (77/102). Multi_new est le plus réduit en clés source et en créatures à tester ;les composites et dix contrats couleur en font néanmoins un lot conséquent.

## Adaptations nécessaires avant un futur « go »

1. `q3m_family_witnesses.validate_selection` suppose actuellement neuf parties/références de huit caractères pour tout `multi_new` : reconnaître explicitement le format MDEM à quatre parties. Ne pas contourner la validation en production.
2. `source_plan` charge actuellement un BMP global sans suffixe : représenter `palette_overrides_by_bank`, vérifier SHA des cinq BMP par variante et sélectionner la banque depuis le nom BAM. Préserver les clés/cache exacts et les palettes runtime natives.
3. Conserver les deux hooks owner5 MonsterMulti/MultiNew ;assembler avant fill/inférence contextuelle, bandes4px natifs uniquement, neuf/quatre parties selon le modèle. Vérifier les directions symétriques, banque/action et frontières dans la future QA complète.

`selection.json` est une **proposition native enrichie**, pas encore une sélection exécutable par le producteur actuel. `analyze.py` : lecture SQLite DISTINCT des travaux, oracle natif K6, cache et ressources sources ;aucun import Torch. Reproduction CPU :

```powershell
$env:PYTHONPATH=Join-Path (Get-Location) 'sprite/.work/q3m-runtime-tools-20261003-v1'
& 'C:/Users/Adrien/AppData/Roaming/chaiNNer/python/python/python.exe' -u 'docs/measurements/q3m-multi-new-selection-x2-20261005-v1/analyze.py'
```

Choisir un nouveau répertoire/version pour reproduire après changement source/cache ;`analysis.json` final de cette proposition est immuable. Aucun état canonique ni fichier ingame modifié.
