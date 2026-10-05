# Proposition — Monster_old complet disponible, Q3m x2

- **Proposition seulement** : aucun traitement neural, encodage, installation, QA ou release. Famille native owner7 déjà supportée ; Q3m V7 K6 x2 palette améliorée/CatmullRom, sans SDF.
- Périmètre : **46/54 IDs, 18 modèles distincts**, toutes actions/directions G1/G2/G1E/G2E ; sept INV auxiliaires conservés dans la sélection complète. Les variantes de chaque ligne partagent leurs BAM/indices/centres/cycles ; contrats couleur natifs distincts.

| Modèle | Créatures / variantes | IDs disponibles | BAM physiques / frames |
|---|---|---|---:|
| `MOGH` | Demi-ogre | `7000` | 4 / 304 |
| `MOGN` | Ogrillon | `7001` | 4 / 384 |
| `MBAS` | Basilic / basilic majeur | `7100`, `7101` | 4 / 360 |
| `MBER` | Ours noir, brun, des cavernes, polaire | `7200`, `7201`, `7202`, `7203` | 6 / 404 |
| `MDOG` | Chien sauvage, de guerre, lunaire, gris | `7400`, `7401`, `7402`, `7603` | 4 / 272 |
| `MDOP` | Doppelganger / doppelganger majeur | `7500`, `7501` | 4 / 352 |
| `METT` | Ettercap | `7600` | 4 / 376 |
| `MGHL` | Maurezhi, goule, revenant, blême | `7601`, `7700`, `7701`, `7702` | 4 / 352 |
| `MSPI` | Myrlochar ; araignées aquatique, géante, énorme, de phase, sabre, spectrale | `7602`, `7604`, `7A00`, `7A01`, `7A02`, `7A03`, `7A04` | 5 / 402 |
| `MGIB` | Gibberling / couvée | `7800`, `7801` | 4 / 304 |
| `MSLI` | Gelée noire ; limons vert, olive, moutarde, ocre ; vase grise | `7802`, `7900`, `7901`, `7902`, `7903`, `7904` | 5 / 481 |
| `MWLF` | Loup normal, worg, sanguinaire, des glaces, vampirique, de terreur | `7B00`, `7B01`, `7B02`, `7B03`, `7B04`, `7B05` | 6 / 384 |
| `MWLS` | Loup des ombres | `7B06` | 4 / 380 |
| `MXVT` | Xvart | `7C00` | 4 / 288 |
| `MTAS` | Tasloi | `7C01` | 4 / 320 |
| `MZOM` | Zombie | `7D00` | 4 / 560 |
| `MWER` | Loup-garou | `7E00` | 4 / 496 |
| `MGWE` | Loup-garou majeur | `7E01` | 5 / 498 |

## Travail réel

- Union physique : **79 BAM /6 917 frames originales →6 701 sources uniques** ;216 répétitions. Un BAM entier partagé : `MWLF0INV` = `MWLF3INV` (SHA canonique identique).
- Palettes/consommateurs : **218 bindings ressources /17 754 frames →16 785 encodages Q3m uniques**, soit969 répétitions évitées ;**zéro hit compatible acquis**, donc16 785 nouveaux travaux.
- Inférence K6 dédupliquée séparément : **100 644 cibles uniques** (et non100 710) ;aucune cible présente dans le cache backend courant. 66 cibles supplémentaires évitées par déduplication des entrées réellement utilisées, sans partager abusivement les contrats partenaires.
- 18 modèles monde distincts vérifiés par indices/dimensions/centres/cycles, palette/INV exclus : `model-geometry.json`. Les palettes de remplacement sont toutes disponibles/SHA authentifiées (`analysis.json`). Le témoin ancien chien gris sans palette de remplacement ne fournit pas de hit compatible avec `MDOG_GR`.
- Méthode contextuelle multituile : aucun groupe spatial dans ce lot ;les G1/G2 sont des banques/actions et E des orientations, pas des tuiles voisines.
- Comparaison des familles encore incomplètes (sources originales, hors variantes couleur) : `monster_old`6 701 ;`multi_new`17 103 +contextes multituile ;`monster_icewind`81 499 ;`monster`86 963 ;`character`couverture V6 acquise/QA distincte,563 969. Ces nombres servent au choix ;coût final du reste non recalculé.

## Sources absentes

| ID | Animation | Préfixe absent |
|---|---|---|
| `7D01` | `SLAVE_FIGHTER` | `NSLF` |
| `7D02` | `CHICKEN_BROWN` | `ACHB` |
| `7D03` | `CHICKEN_WHITE` | `ACHW` |
| `7D04` | `HARLOT_FIGHTER` | `NPRF` |
| `7D05` | `NOBLEMAN_FIGHTER` | `NNMF` |
| `7D06` | `NOBLEWOMAN_FIGHTER` | `NNWF` |
| `7D07` | `PEASANT_MAN_FIGHTER` | `NSMF` |
| `7D08` | `PEASANT_WOMAN_FIGHTER` | `NSWF` |

- Absence vérifiée dans CHITIN.KEY et override ;ne pas fabriquer ces huit animations. Aucun BAM ni BMP requis manquant dans les46 IDs proposés.
- Autorités : `selection.json` (refs/palettes SHA/exclusions) ;`plan-summary.json` (source/profil exact) ;`analysis.json` (sources/cache/doublons) ;`model-geometry.json` (18 modèles et46 consommateurs). Source plan acquis en lecture seule ;aucun import Torch.
- Lot à produire seulement sur accord utilisateur ;catalogue/DLL installés inchangés.
