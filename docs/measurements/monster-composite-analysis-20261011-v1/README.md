# Monster : retours vanilla / composition incomplète

- Demande : diagnostic dernière session + proposition famille ; aucune correction/install effectuée.
- Preuves : `analysis.json`, `session-excerpt.log` ; états QA/release inchangés.
- Log source : `config://bg2ee_game_root/InfinityEngine-Enhancer.log`.
- Dernier démarrage conservé : 2026-10-11 10:52:17.600, ligne 38245 ; fin conservée 10:52:40.313.

## Cause confirmée — 0x7F3E

À 10:52:33.062, lignes 38702–38703 : texture native **87x193**, remplacement corps seul
attendu **87x173** ; rendu BAM conservé. La frame native 551 reproduit exactement ce cas :

| BAM/frame | Dimensions | Centre |
|---|---|---|
| MFIGG12/551 | 85x171 | 53,137 |
| MFIGG1WH/551 | 20x21 | 8,157 |
| MFIGG1AX/551 | 16x25 | 7,160 |

- Corps : `[-53,32] x [-137,34]` ; marteau : `[-8,12] x [-157,-136]`.
- Union corps+marteau : `85x191` ; bordure logique 1 => **87x193**.
- Union corps+hache : bordure comprise **87x196** ; autre équipement, même défaut potentiel.
- Géométrie x1 lue directement dans KEY/BIF stock ; aucun upscale exécuté.
- Shards HD marteau G1/G2 présents dans l'installation ; références dans
  `docs/measurements/q3m-monster-stability-x2-20261007-v1/accepted-asset-scope.csv`.
- Explication de l'intermittence : arme hors du rectangle du corps => rejet de dimensions ;
  arme contenue dans ce rectangle => la taille seule peut accepter un remplacement corps seul,
  sans garantir la conservation de l'arme. Ce second effet est déduit du code, pas validé ingame.

## Moteur / périmètre

`engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp:2736` limite la collecte
multicouche de Monster à `animationId == 0x7F09` (sahuagin).
Le contrat natif est commun à toute la classe, confirmé par désassemblage du build identifié :

| Ordre | Cellule | Activation | Appel FXRender RVA |
|---|---|---|---|
| 1 | this+0xCD8 | corps | 0x32DAF7 |
| 2 | this+0x1288 | int32 this+0x127C != 0 | 0x32DB26 |
| 3 | this+0xF88 | int32 this+0x125C != 0 et pointeur non nul | 0x32DB64 |

- Deuxième Realize classé `foreign` : compatible avec équipement omis par le scope.
- `captured=0` affiche `compositionCount` ; en voie monocouche, ce compteur reste nul.
  Il **ne prouve pas** un échec de capture de palette ; le rejet de dimensions est explicite.
- Les warnings de dimensions sont limités au premier par session ; celui d'absence de remplacement
  au premier par animation. Aucun taux de frames vanilla ne peut être déduit de ce log.
- Inventaire `q3m-work-items.csv` : 77 IDs `monster` avec sources, 9 avec équipements G1/G2
  séparés, dont un déjà pris en charge. Les 8 autres sont exposés quand un équipement est actif :

| ID | Modèle |
|---|---|
| 0x7F0C | KUO-TOA |
| 0x7F10 | RAKSHASA |
| 0x7F23 | SAHUAGIN_LARGE |
| 0x7F28 | KUO-TOA_LARGE |
| 0x7F3B | SOLAR |
| 0x7F3C | DEVA_MONADIC |
| 0x7F3E | GIANT_FIRE |
| 0x7F3F | GIANT_YAGA-SHURA |

- Yaga-Shura partage les BAM MFIG mais a sa palette/profil propre : ne pas fusionner les IDs.
- 0x7F47 GIANT_FIRE_2 / MFI2 : sources absentes, hors du défaut confirmé.
- Autres avertissements historiques retenus : Ellesime, Irenicus, efreeti noble ; leur message
  générique ne suffit pas à leur attribuer cette cause. Aucun défaut universel des 77 IDs affirmé.

## Correctif proposé — commun, activation conditionnelle

1. Retirer l'exception `0x7F09` de la collecte des cellules Monster ; utiliser les offsets
   `monsterCompositeCells/Enabled` existants et les conditions natives ci-dessus pour chaque ID.
2. Corps seul : conserver la voie monocouche ; couches supplémentaires actives : composition HD
   complète, ordre natif, centres natifs, palette propre et frame courante de chaque cellule.
3. Réutiliser `bind_composite_texture` : union exacte + bordure 1 ; toute couche active manquante,
   non enregistrée ou incompatible conserve le composite natif complet.
4. Aucun élargissement de tolérance géométrique ; aucun changement de palettes ; aucun recalcul
   Q3m nécessaire pour les équipements déjà produits. Ne pas traiter les armes comme tuiles spatiales.
5. Ajouter un diagnostic borné par ID/cause : resrefs, frames, nombre de couches, union et taille
   présentée. Adapter aussi le libellé composite encore limité à `0x7F09` dans le logger.

Validation utile lors de l'implémentation : cas natif MFIG marteau 551 (87x193), hache 551 (87x196),
arme contenue dans le corps, palettes distinctes, cellule facultative absente, couche non enregistrée,
et régression sahuagin/corps seul. QA ingame : combat/directions des 8 IDs équipés, palette Yaga-Shura.
Compiler un candidat runtime seulement ; installation après fermeture jeu/InfinityLoader ;
aucune compilation globale d'assets ni modification release.
