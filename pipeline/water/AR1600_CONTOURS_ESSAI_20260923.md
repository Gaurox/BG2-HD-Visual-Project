# AR1600 — contours du bateau, essai installé

2026-09-23. Statut : **installé, QA utilisateur ingame en attente**. Masque avant/après accepté par
l'utilisateur ; autorisation explicite de terminer le correctif et de l'installer. Pas de release.

## Portée et fichiers

- WED x1 : `(x=1856,y=2048,w=384,h=320)` ; coordonnées cellules `(29..34,32..36)`.
- 26 paires primaire/secondaire,52 tuiles ; pas d'extension à AR1600 entier ni à AR1600N.
- Huit fichiers override : `A160037.PVRZ`, `A160038.PVRZ`, `A160039.PVRZ`, `A160040.PVRZ`,
  `A160041.PVRZ`, `A160056.PVRZ`, `A160057.PVRZ`, `A160058.PVRZ`.
- Jeu : `config://bg2ee_game_root`. Aucun WED/TIS/ARE, overlay animé, shader, DLL ou INI modifié.
- Reçu : [`manifests/ar1600-contour-installed-20260923-v1.json`](manifests/ar1600-contour-installed-20260923-v1.json).
- Run : `maps/water-batches/runs/ar1600-contour-colour-trial-20260923-v2/`.
- Entrée masque : `maps/water-batches/runs/ar1600-contour-mask-preview-20260923-v2/`.
- Producteurs : `pipeline/scripts/preview_water_contours.py`, `build_water_contour_trial.py`,
  `install_water_contour_trial.py`.

## Recette appliquée

1. Reprendre le masque accepté ; géométrie native en coordonnées monde, contexte64px x1.
2. Nettoyer les couleurs de bord depuis l'intérieur du même domaine connexe : donneurs locaux
   jusqu'à6px x4, cœur à3px ou axe local pour traits fins ; pondération des donneurs proches.
   Réparer jusqu'à3px autour du bord ; aucun seuil RGB noir, aucune génération SeedVR.
3. Primaire et secondaire séparés, même géométrie `M`. Alpha effectif marin `a=128/255` :
   `S=1-M`, `P=M/(1-a*(1-M))`, pour l'ordre overlay→primaire→secondaire du chemin observé.
   RGB droit, sans prémultiplication exportée. Le domaine connexe ne garantit pas l'identité
   sémantique de chaque matériau : vérifier particulièrement les intersections corde/mât.
4. Raccord de la zone expérimentale : périphérie4px x4 exacte, transition12px vers l'état actuel.
5. BC3 sélectif : blocs4×4 touchés seulement ; alpha/RGB remplacés séparément ; marges d'atlas4px
   recalculées uniquement pour les canaux changés. Aucune recompression des blocs hors sélection.
6. Alpha BC3 : rechercher les deux modes de palette à partir des valeurs du bloc ; conserver les
   valeurs0/255 exactement. Le RGB reste encodé par Pillow. Ne pas utiliser l'encodeur alpha
   standard seul pour ce masque : candidat couleur `v1` rejeté avant installation.

## Vérifications et limites

- Couverture effective après décodage : `P*(1-a*S)` ; erreur moyenne sur38213pixels de bord
  =0,00617 (0,617point de couverture),p99=0,06188,max=0,09396 ; encodeur initial : moyenne0,04764.
- Comptes au seuil128 : masque accepté, composition cible et BC3 effectif ont1composante de décor
  (connexité8),110composantes d'eau dont99fermées (connexité4). Ce contrôle ne prouve pas chaque
  épaisseur locale ni l'apparence sous le filtre du moteur.
- Blocs hors sélection byte-exacts ; contrôles alpha/RGB séparés dans `build.json`.
- Comparatifs `comparison-colour-bc3.png` et `comparison-colour-detail-bc3.png` : **simulations**
  avec une phase d'overlay, sans éclairage/filtrage de la scène ; aucune capture ingame revendiquée.
- Installation : jeu/InfinityLoader absents ; sauvegarde puis hashes installés vérifiés.
- 30 FPS normal/pluie : identités AR1600 du registre existant vérifiées. Leurs listes `base_tis.pages`
  sont vides ; modifier ces PVRZ ne change aucune preuve utilisée par ces identités. TIS/WED,
  QALAK0/R, QLAK000/QLAK0R00, DLL, shaders et INI identiques au départ. Aucun registre reconstruit.
- Le résultat reste un candidat de validation, pas une recette acquise pour toutes les maps.
- Postérieur (soir du 2026-09-23) : overlay AR1600 remplacé par la v2 30 FPS `QBLKV0`/`R` ;
  WED réécrit, pages `A1600*` non touchées ; registre v2 : `base_tis.pages` toujours vide.

## Reproduction ciblée

`prepare` utilise SciPy/NumPy/Pillow (runtime `config://chainner_python` compatible) ; `encode`
utilise Pillow avec encodeur DDS/DXT5 (runtime Python fourni par Codex). Sortie nouvelle obligatoire.

```text
python -B pipeline/scripts/build_water_contour_trial.py prepare --preview maps/water-batches/runs/ar1600-contour-mask-preview-20260923-v2 --vanilla-root G:/AI/BG2_Vanilla_23534562 --output maps/water-batches/runs/NOUVELLE-VERSION
python -B pipeline/scripts/build_water_contour_trial.py encode --output maps/water-batches/runs/NOUVELLE-VERSION
python -B pipeline/scripts/install_water_contour_trial.py --candidate maps/water-batches/runs/NOUVELLE-VERSION --receipt pipeline/water/manifests/NOUVEAU-RECU.json --run
```

Les hashes du masque témoin figent son installation source : **ne pas relancer la préparation
contre l'installation désormais corrigée**. Pour un autre essai, restaurer le témoin ou produire
une nouvelle entrée ; les runs et reçus existants restent historiques.

## Test utilisateur et retour arrière

Relancer via InfinityLoader ; console `C:MoveToArea("AR1600")`. Examiner le même bateau : voiles,
cordages/filets et mâts au-dessus de l'eau, zoom normal/fort, déplacement caméra et eau animée.
Zone témoin centrée vers les coordonnées map `(2048,2208)` ; la périphérie conserve une transition
vers les contours anciens. Le mouvement de l'eau doit rester celui du témoin30FPS précédent.

Sauvegarde : `backups/water/ar1600-contour-colour-trial-20260923-v2/` ; sous-dossier précis dans
`backup_receipt` du reçu installé. Restauration via `pipeline/scripts/Restore-AreaOverrideAssets.ps1`,
paramètres `-BackupPath <parent du install-backup.json>` et `-GameRoot <config://bg2ee_game_root résolu>` ;
jeu/InfinityLoader fermés. Vérifier que les fichiers courants correspondent aux hashes installés
avant restauration ; ne pas écraser une correction ultérieure.
