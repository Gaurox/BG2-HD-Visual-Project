# AR0900 jour — mélange natif DXT1 reproduit en DXT5

> Fiche historique du candidat alpha128. Le candidat final réparant aussi les raccords est
> validé ingame le 2026-09-12 ; recette complète, références et hashes dans
> [`WATER_REPAIR_RUNBOOK.md`](WATER_REPAIR_RUNBOOK.md). `areas.csv` sélectionne ce dernier run.

## Périmètre retenu au commit `309c1db2` du 2026-09-12

- Autorité courante : `areas.csv`, ligne AR0900, variante jour.
- Retour utilisateur : résultat presque parfait ; conserver le correctif, analyser les fins
  rebords noirs restant sur certaines tuiles. QA globale encore `installed-pending-qa`.
- Aucun changement nuit, WED, renderer, couleurs RGB ou overlay WTLAKE dans ce candidat.
- Aucune généralisation, intégration release, reconstruction de payload ou promotion implicite.
- Artefacts lourds et script exécuté restent dans le run ignoré par Git ; cette fiche conserve
  recette, références et empreintes. Le builder général n'est pas modifié.

## Cause et recette exacte

Le rendu natif applique un alpha de dessin 128 aux primaires d'eau sans secondaire sur pages
DXT1 (PVR 7), mais pas sur DXT5 (PVR 11). Les secondaires reçoivent explicitement cet alpha.
Copier l'alpha255 source en DXT5 masque donc l'animation ; alpha0 supprime l'art local.

1. Lire le WED stock AR0900 ; couche liquide WTLAKE, bit 2.
2. Sélectionner les 775 primaires exclusivement utilisés avec eau et secondaire `0xFFFF` ;
   exclure les tuiles partagées avec un autre usage. Source : DXT1, alpha255.
3. Partir du build parent ci-dessous ; conserver TIS, RGB DXT et autres alpha octet pour octet.
4. Pour chaque tuile x4 de 256 px, inclure sa marge d'atlas répliquée de 4 px : zone 264×264.
5. Remplacer seulement les huit octets alpha de chaque bloc DXT5 ciblé par
   `80 80 00 00 00 00 00 00` ; endpoints128, indices0. Ne pas réencoder le RGB.
6. Conserver en-tête PVR, dimensions4096, positionnement et mip unique ; recomprimer zlib9.
7. Contrôler les octets hors masque, RGB inchangé, alpha128 exact, inventaire et hashes.
8. Installer par `inject_build.py`, jeu et InfinityLoader fermés, sauvegarde transactionnelle.

Cette équivalence vaut pour le mélange courant, avec `EnableWaterEffect=false` ; ne pas cumuler
alpha128 texture et alpha128 de dessin. Ne pas réutiliser ici la recommandation legacy
`--transparent-full-water-base` d'`audit_water_area.py` : elle impose alpha0.

## Artefacts et preuves

Racine des chemins relatifs : dépôt. Destination jeu : `config://bg2ee_game_root`.

| Objet | Référence |
|---|---|
| Run parent | `maps/AR0900/runs/voie1-source-alpha-x4-jour-20260912/` |
| Build parent | `05_build/x4-source-alpha-preserved-spline-fit1.0/` sous ce run |
| Run retenu | `maps/AR0900/runs/voie1-native-blend-alpha128-x4-jour-20260912/` |
| Build retenu | `05_build/x4-native-alpha128-spline-fit1.0/` sous ce run |
| Recette figée | `request.json` sous le run retenu |
| Producteur exécuté | `build-candidate.py` sous le run retenu |
| Contrôles | `alpha128-report.json` sous le run retenu |
| Installation | `backups/maps/AR0900-20260911T232537299699Z-c2c28853/install-backup.json` |
| Capture utilisateur | `20260912012622_1.jpg` |

| Empreinte SHA-256 | Valeur |
|---|---|
| Ensemble parent | `C7862BBA6C8501271983F62D2244B2318C137677DA938BCD273146A168A55860` |
| Ensemble installé | `9DE7EDB09EBD019B45DA1DC1EB3064A88846C8905561D55A35EEB4FDD86D953B` |
| Producteur | `984E1F34F393298F34647CB077C5D2DA70617307D741221573391C591ED2E789` |
| WED stock | `471B1A2A5FBF4D78DDDF44851E8A95F18CDA6883B6C048D3382BC84AEE67092A` |
| Capture utilisateur | `94873D163EEB7F7D92B95DF1CEDFF3188DB29695C609E26CD85E8AB2835E99EF` |

- 27 fichiers installés : 1 TIS inchangé, 26 PVRZ dont 22 modifiées ; aucun fichier retiré.
- 3 174 400 blocs alpha intérieurs + 201 500 blocs de marge = 3 375 900 blocs ciblés.
- Zéro bloc RGB ou alpha hors sélection modifié ; vérification du flux recompressé effectuée.
- Reçu, sauvegardes et état installé revérifiés après le retour utilisateur.
- Fichiers source/build/run scellés non réécrits ; le retour QA courant n'est pas injecté dans
  leurs manifests historiques.

## Preuve native

- BG2EE2.7.3.0, exécutable SHA-256
  `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`.
- `CInfTileSet::Render`, RVA `0x2A46D7` : lecture format PVR ; `0x2A46FC` : branche DXT5
  sautant l'alpha de dessin ; `0x2A4700` : contrôle secondaire absent.
- `0x2A4706..0F` : appel DrawAlpha avec valeur128 lue à `0x65B4E4` ; passe secondaire :
  `0x2A47DE..E7`. Valeur par défaut de l'exécutable, pas une capture mémoire du processus.

## Défaut restant à ce stade historique

- Très fins segments noirs sur certains côtés de tuiles ; cause encore à analyser au commit.
- Distinguer RGB caché/marges d'atlas, alpha de contour et couverture/UV de rendu.
- Ne pas modifier l'opacité globale ni réupscaler WTLAKE pour masquer ce défaut sans preuve.
- Résolu depuis par greffe RGB du maître secondaire continu et restauration alpha des interfaces
  internes uniquement ; voir la notice complète. Le présent run reste immuable.
