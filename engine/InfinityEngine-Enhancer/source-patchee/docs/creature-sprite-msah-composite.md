# MSAH 0x7F09 : composition corps + équipement

- Exécutable : BG2EE 2.7.3 Windows x64, `BaldurReal.exe` SHA256
  `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`.
- Échec v4, session 2026-09-19 15:16:36 : à 15:17:07.020, corps `50x73`,
  texture native `72x75`, rejet du contrat `ObservedBordered` limité à +4.
- Cause : la texture finale est une composition. La seconde palette `Realize`
  jusque-là considérée étrangère correspond à une couche native d'équipement.
  La différence de dimensions ne prouve ni padding ni désynchronisation de frame.

## Preuve native (RVA)

`CGameAnimationTypeMonster::Render = 0x32D770` :

| Ordre | Cellule | Condition | Appel CInfinity::FXRender à 0x29E260 |
|---|---|---|---|
| 1 | `this+0xCD8` | corps | `0x32DAF7` |
| 2 | `this+0x1288` | int32 `this+0x127C != 0` | `0x32DB26` |
| 3 | `this+0xF88` | int32 `this+0x125C != 0`, pointeur non nul | `0x32DB64` |

Une seule présentation finale : `0x32DD32 -> 0x29DFF0` après clipping.
Offsets centralisés dans `AreaAnimationRuntime.monsterCompositeCells/Enabled`.

## Preuve assets / géométrie

Source : `sprite/families/monsters/7fxx/7f09-msah-sahuagin/runs/reboutcx-p12-cache86-v1/manifest.json`.

| Ressource/frame | Largeur/hauteur | Centre x/y |
|---|---|---|
| MSAHG1 / 145 | 50 / 73 | 30 / 46 |
| MSAHG1SP / 145 | 56 / 43 | 50 / 38 |
| MSAHG12 / 415 | 47 / 84 | 33 / 67 |
| MSAHG1SP / 415 | 14 / 37 | -2 / 35 |

- Combat : union `[-50,20] x [-46,27]`, bordure 1 => **72x75**.
  Origine corps `(21,1)`, équipement `(1,9)` en pixels logiques.
- Repos : union `[-33,16] x [-67,17]`, bordure 1 => **51x86**,
  exactement la texture du log à 15:16:40.986.

## Contrat v5

- Périmètre nouveau : owner Monster ET animation `0x7F09` seulement.
- Collecter les cellules actives selon les conditions natives ; capturer chaque
  palette et résoudre sa frame au moment de `Realize`, dans l'ordre natif.
- Réutiliser le compositeur multicouche existant : centres BAM, union exacte,
  une bordure logique, remplacement des pixels non transparents dans l'ordre natif.
- Refuser si couche manquante/non enregistrée, capture incomplète ou union différente
  de la taille native. Aucune tolérance numérique sur la taille.
- Supprimer `ObservedBordered`. Ne pas confondre corps seul et composite complet.
- Tests natifs : cas réels combat/repos ci-dessus, offsets d'équipement, contrôles
  existants de composition Character ; suite native passée.

## Validation en jeu

- 2026-09-19 : utilisateur confirme « validé ! commite » après installation v5,
  en réponse au test des animations de combat du capitaine.
- Runtime : `pipeline/runtime/manifests/iee-monster-msah-composite-v5.json`.
- DLL installée/vérifiée : SHA256
  `C6AA1CFA15083E12F9015F7D9B85A343BEB849CCE80B5EC717EF4FBAB06EE0A6`.
- Catalogue ReboutCX installé : SHA256
  `E0B20D6A9A721B90D30F9891D44A5224AA12C30093118B2648DB89B893CC5B6C`.
- Shard MSAH actif (19 ressources, corps + équipements) : SHA256
  `A10F52B3D9FB484EA2D3BA9896DBA219B71EFD8D33C2A5A8EE2A2FB854A1603D`.
- Validation limitée à cet essai ingame ; aucune intégration release effectuée.
