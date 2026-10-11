# Mouches arrondies — préparation et installation de test

- **État courant 2026-10-11 : installé pour test ingame**, 21 zones / 216 occurrences ; reçu `installation-v1.json`. Feu vert utilisateur après commit AR3000 `8c63b816`.
- 21 préflights `VerifyOnly` réussis ; textures/registres installés comparés aux sources et verrou actif mis à jour. SHA DLL/INI/pack AR3000 inchangés. QA ingame encore attendue ; sélections natives et release inchangées.
- [CLUA](CLUA.md) : deux points de vue avec FLIESL + FLIESS, puis les 216 coordonnées ARE par zone.
- **QA courante : les deux ressources acceptées ingame le 2026-10-11**, demande « ok je valide les 2. maj le suivi et committe ». `acceptance.json`, décisions immuables et sélections courantes ; statut `validé-x4`, conservation native antérieure remplacée. Les octets du resref sont partagés entre zones ; aucune affirmation de visite des 216 occurrences. Release inchangée.

- Demande 2026-10-11 : préparer les packs ; **aucune installation avant confirmation utilisateur que le travail DLL parallèle est terminé et committé**.
- `FLIESL` : ellipses par composante 8-connexe, centre/surface conservés, aspect ≤ 1,6 ; suréchantillonnage 16 → BOX x4.
- `FLIESS` : ouverture disque rayon 1,25 px x4, suréchantillonnage 8 → LANCZOS x4 ; premier essai PNG retenu.
- 18 frames/asset ; 216 occurrences ; 21 zones. Cadence/cycles/centres/dimensions BAM natifs conservés. Aucune interpolation temporelle.
- Palette source ; RGB droit prolongé aux bords depuis les pixels opaques. Aucun usage ARE `Blended` dans l'inventaire de ces assets.
- `reference-previews/` : PNG sources de comparaison ; les crops runtime des frames 000/009 des deux assets sont byte-identiques.

## Artefacts

- Production : `animations/batches/flies-rounded-native-cadence-20261011-v1/{manifest,local-checks}.json`, `resources/{FLIESL,FLIESS}/`, `03_runtime_pack/`.
- Split neuf : `animations/packs-par-zone/flies-rounded-native-cadence-20261011-v1/`.
- Feuilles complètes : `animations/packs-par-zone/flies-rounded-native-cadence-20261011-v1-complete-v1/<zone-minuscule>/<ZONE>/`.
- Reprise : `preparation-v1.json` ; baseline par zone, signatures installées, SHA du registre, pack complet et politique d'installation différée.
- Scellement final : `seal_preparation.py v1` a validé les 21 feuilles avec le cœur de l'installateur. Sous Windows, sa résolution stricte des chemins nécessitait une exécution hors sandbox ; aucune installation exécutée.
- `AR0206`, `AR1900` : aucun pack installé au moment de la préparation ; nouvelles feuilles mouches seules. Autres zones : union exacte de l'état verrouillé + mouches.
- Contrôles de préparation : SHA source/inventaire ; géométrie/cycles natifs ; quatre crops PNG identiques ; validation des packs par le cœur de l'installateur ; ressources préexistantes identiques ; empreintes installées/verrou inchangés.

## Commandes

```powershell
# Production + composition, destinations neuves seulement :
python pipeline/recipes/flies-rounded-native-cadence-20261011-v1/build.py
# Si une autre installation a changé une zone entre préparation et feu vert :
python pipeline/recipes/flies-rounded-native-cadence-20261011-v1/build.py --compose-only --composition-version v2
```

## Conditions d'installation / reprise

1. Attendre le message utilisateur confirmant fin + commit du travail DLL.
2. Comparer **les 21 entrées concernées** du verrou et les signatures installées à `preparation-v1.json`. Un changement ailleurs n'invalide pas ce lot. Si changement local : nouvelle composition v2, pas de réécriture des preuves v1.
3. Fermer jeu + InfinityLoader ; utiliser `config://bg2ee_game_root` ; `Install-AreaAnimation-AreaTest.ps1 -AreaPack <feuille> -VerifyOnly`, puis installation ciblée de chaque feuille.
4. Ne pas utiliser l'installateur global `Install-AreaAnimations-PerArea.ps1` : le lot ne contient que 21 zones.
5. Aucun déploiement DLL/INI/ARE/override par ce lot. Conserver les reçus ; QA ingame à recueillir avant changement des sélections `validé-natif`.
6. PNG acceptés ≠ QA ingame. QA/sélections natives, verrou installé et release restent inchangés pendant la préparation.
