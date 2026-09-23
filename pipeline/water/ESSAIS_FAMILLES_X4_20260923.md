# Essais x4 — neuf témoins de surfaces liquides — 2026-09-23

## État et périmètre

- **Installé et vérifié :147fichiers de payload, dont116override +31surface locale AR3021.**
- QA utilisateur : **rendu spatial accepté globalement** le 2026-09-23
  ([décision](manifests/liquid-families-spatial-user-qa-20260923-v1.json)) ; météo/jour-nuit non détaillés,
  fluidité non qualifiée. Aucune intégration release.
- AR1600 : overlay `Q9LAKE`/`R` remplacé par `QBLKV0`/`R` (30 FPS v2 validé) ; les autres témoins
  gardent les alias `Q9*` ci-dessous.
- Run : `maps/water-batches/runs/liquid-families-x4-20260923-v1/` ; abrégé `RUN` ci-dessous.
- Demande machine : `RUN/request.json` ; overlays : `RUN/overlays-plan.json`.
- Référence de stratégie : [BASE_PIPELINES_SURFACES_LIQUIDES.md](BASE_PIPELINES_SURFACES_LIQUIDES.md).
- Sélection installée et empreintes finales :
  `pipeline/water/manifests/liquid-families-x4-trial-installed-20260923-v1.json`.
- Sources de géométrie/masques/cycles : KEY/BIF de `G:/AI/BG2_Vanilla_23534562` ; jamais les overlays
  déjà modifiés du jeu HD. Destination : `config://bg2ee_game_root`.
- Huit WED témoins + surface locale constitutive d'AR3021 ; aucune animation sans rôle dans ces
  surfaces. Jour AR1000 seulement ; sa variante nocturne appartient à une autre famille.
- Assets de release, autres maps/variantes, DLL et INI : hors modification de cet essai.

## Témoins et commandes CLUA

Noms issus d'`areas.csv`. Les commandes déplacent vers les zones ; elles ne prouvent ni l'heure,
ni la météo, ni le chargement de la ressource attendue.

| Famille / composition | Map | Nom catalogue | Commande |
|---|---|---|---|
| Lac / mer WTLAKE | AR1600 | Brynnlaw | `C:MoveToArea("AR1600")` |
| Bassin WTPOOL | AR1000 **jour** | Gouvernement | `C:MoveToArea("AR1000")` |
| Marais WTSWAM | AR1607 | Githyanki Assault | `C:MoveToArea("AR1607")` |
| Égouts WTSEW | AR0404 | Égouts des Bas Quartiers | `C:MoveToArea("AR0404")` |
| Huile WTOIL | AR0413 | Sphère Planaire — salle des machines | `C:MoveToArea("AR0413")` |
| Pavage turquoise WTLAKA–D | AR3000 | Tour de Garde | `C:MoveToArea("AR3000")` |
| Lave WTLAVA–D | AR0011 | Candlekeep Dream 1 (Do you remember Candlekeep?) | `C:MoveToArea("AR0011")` |
| Rivière brune WT5000A–D | AR5203 | Camp du siège | `C:MoveToArea("AR5203")` |
| Surface locale ARE/BAM | AR3021 | Watcher's Keep -- Illithids | `C:MoveToArea("AR3021")` |

AR1000 : vérifier visuellement le jour ; ne pas attribuer au candidat WTPOOL un rendu provenant
d'AR1000N/WTSWAM. AR3021 : une sauvegarde déjà visitée peut porter son ARE ; conserver la preuve
de la ressource effectivement chargée si le résultat diffère du candidat.

## Recette spatiale et temporelle du lot

| Élément | Contrat de l'essai |
|---|---|
| SeedVR | 7B INT8 ConvRot, x4, correction couleur `none`, seed `959948902156062` |
| Ressource répétée unique | Motif64×64 répété en contexte3×3, inférence, crop central256×256 |
| Groupes A–D | Assemblage conjoint en motif2×2 selon le plan ; contexte3×3 du motif ; crop central puis séparation des quatre tuiles |
| WTPOOL sec/pluie | Bilinéaire x4 périodique non génératif ; témoin de contrôle après les anciens quadrillages SeedVR |
| Lave WTLAVA–D sec/pluie, sélection finale | Bilinéaire x4 depuis le motif natif ; SeedVR `none` essayé puis rejeté pour quadrillage persistant |
| Alpha overlay | Source palette : index0 transparent seulement si palette0 porte la clé verte ; masque binaire natif conservé en x4 |
| Animation WED | Nombre de frames, lookup, vitesse et durée du cycle vanilla conservés ; aucun passage systématique6→36 |
| Runtime | Alias non enregistrés dans route2, composition native/q0 ; aucune eau procédurale enrichie revendiquée |
| Stock partagé | Ressources WT originales conservées ; seuls les WED ciblés pointent vers les alias du lot |
| Atlas | TIS PVRZ x4, tuile256, padding4, BC3 réel ; noms de ressources≤8octets |

Les groupes2×2 constituent le contexte d'inférence ; le WED conserve ses choix de slots natifs.
La compatibilité des bords doit être jugée sur les **adjacences réellement utilisées**, y compris
les répétitions d'un même membre du groupe ; un motif2×2 propre ne prouve pas tous les raccords.

`none` est nécessaire pour comparer ce lot selon un même contrat de couleur, mais **ne garantit
pas l'absence de tuilage**. Un contexte périodique ne contraint pas mathématiquement SeedVR à
produire des bords identiques. Les profils de bords/corrections éventuelles restent consignés par
le producteur ; ils ne doivent pas supprimer l'art intérieur ou créer une pulsation selon la frame.

Sélection technique retenue : `RUN/overlays-selected-v3/` =14groupes de `RUN/overlays-r2/` +
`lava`/`lava_rain` de `RUN/overlays-lava-bilinear/`. Pour égouts, huile, turquoise et rivière brune,
r2 applique un profilRGB prélevé dans l'intérieur généré à8–11px du bord, avec collier8px selon les
adjacencesWED ; nombre de frames et alpha natif inchangés. Les petits motifs restent naturellement
répétés : égaliser les raccords n'efface pas cette répétition.
Sélection explicite des fichiers et sources : `RUN/overlays-selected-v3/selection.json`.

Lave : les essais SeedVR `none`, donneur2 et correction basse fréquence ne sont pas retenus ;
la grille restait visible. Le fallback bilinéaire constitue une recette distincte explicite,
pas une validation universelle de `none` ou du traitement génératif.
La prévisualisation du fallback ne présente plus la bande lissée générative entre A/B et C/D ;
la topologieWED irrégulière conserve toutefois des raccords natifs imparfaits : ratio maximal11,211,
MAE16,876/255 en phase1. **Conserver le natif ne garantit pas zéro raccord.** Référence :
`RUN/qa-overlays-final-lava/summary.json`. Les8TIS lave sec/pluie ont été vérifiés :12frames chacun,
tuiles256×256, payloadBC3 et alpha255.

## Alias isolés

**34 alias TIS installés :17secs +17pluie, soit68fichiers TIS/PVRZ.** Le WED nomme l'alias sec ; sa variante pluie suit le
routage alternatif natif. Ressources source pluie : suffixe`R`, présence vérifiée dans le KEY par
le producteur/assembleur, pas déduite de la seule existence d'un fichier HD.

| WED | Sources sèches | Alias secs | Alias pluie |
|---|---|---|---|
| AR1600 | WTLAKE | Q9LAKE | Q9LAKER |
| AR1000 | WTPOOL | Q9POOL | Q9POOLR |
| AR1607 | WTSWAM | Q9SWAM | Q9SWAMR |
| AR0404 | WTSEW | Q9SEWG | Q9SEWGR |
| AR0413 | WTOIL | Q9OIL0 | Q9OIL0R |
| AR3000 | WTLAKA/B/C/D | Q9LKA0/Q9LKB0/Q9LKC0/Q9LKD0 | mêmes alias +`R` |
| AR0011 | WTLAVA/B/C/D | Q9LVA0/Q9LVB0/Q9LVC0/Q9LVD0 | mêmes alias +`R` |
| AR5203 | WT5000A/B/C/D | Q9500A/Q9500B/Q9500C/Q9500D | mêmes alias +`R` |

La QA sèche ne qualifie pas automatiquement la pluie ; présence installée et variante observée
doivent rester distinctes.

## Bases HD retenues : `bases-v4`

Producteur : `pipeline/scripts/build_liquid_base_x4_trial.py`.

- Entrées : TIS/PVRZ **installés** x4 copiés, WED/ARE/TIS source vanilla, masters secondaires HD
  explicités dans `request.json`. Aucune réinférence de la carte entière.
- Sélection : tous les bits des slots demandés ; primaires opaques DXT1 natives, exclusivement
  liquides, sans secondaire ni usage logique ambigu. AlphaARE effectif0→128 ; AR1607=100.
- Ne pas appliquer cet alpha aux overlays ou aux secondaires : ceux-ci conservent leur propre
  contrat de dessin. AR0011 n'a aucune centrale éligible.
- Interfaces internes : garde vraie rive1px x1, bande8px x4, donneur secondaire de même coordonnée,
  padding4 ; RGB changé seulement si différence moyenne au donneur>6/255. **Aucune greffe RGB
  déclenchée dans bases-v4.** Alpha secondaire corrigé seulement dans les bandes sûres.
- Référence finale : `RUN/bases-v4/base-repair-report.json` ; candidats :
  `RUN/bases-v4/maps/<WED>/`.
- `RUN/bases` : partiel, non sélectionnable. `bases-v2`/`bases-v3` : versions intermédiaires non
  retenues ; ne pas les assembler par défaut.

| Map | Centrales qualifiées | Alpha effectif | Pages modifiées | Nature du delta |
|---|---:|---:|---:|---|
| AR1600 | 166 | 128 | 0 | Base déjà conforme |
| AR1000 jour | 0 | 128 | 0 | Toutes les cellules liquides ont un secondaire |
| AR1607 | 525 | 100 | 0 | Base déjà conforme |
| AR0404 | 2 | 128 | 2 | Alpha des interfaces secondaires |
| AR0413 | 283 | 128 | 6 | Alpha des interfaces secondaires ; centrales déjà conformes |
| AR3000 | 184 | 128 | 0 | Base déjà conforme |
| AR0011 | 0 | 128 | 0 | Aucun alpha central appliqué |
| AR5203 | 366 | 128 | 32 | Centrales255→128, marges comprises |
| **Total** | | | **40** | **Aucun RGB modifié** |

Contrôles CPU achevés pour bases-v4 :369pages vraiBC3/PVR11, tailles de payload exactes,
inventaires et hashes relus ;40pages modifiées décodéesRGBA ;8TIS byte-identiques au live,
aucune nouvelle page. Les blocs hors sélection restent identiques.

AR0413 : ID54 et12sentinelles repointées partagent le slotpage0/(4,4). Ce slot live est déjà
alpha128 sur cœur+marges. L'isolation tentée dans v3 était inutile : **v4 conserve tout le TIS**.
Les66sentinelles natives restent hors réparation automatique. Cette conservation n'établit pas
une nouvelle QA des12cellules historiques de bord.

## Surface locale AR3021

- Ressources : `AM3021D`, `AM3021E`, `AM3021F` ;10frames natives chacune, **30frames au total**.
  Ce nombre ne désigne pas30FPS.
- Ces BAM composent directement les surfaces du décor ARE ; aucun autre asset d'animation dans
  le périmètre de cet essai.
- Producteur : `pipeline/scripts/build_liquid_local_surface_x4_trial.py` ; préparation `RUN/local/`.
- RGB : nouveau SeedVR7B INT8 `none`, x4 ; **straight RGB**, neutralisation seulement aux pixels
  alpha0. ARE flags`0x1141`, sans bit`Blended` : cette politique évite une atténuationRGB préalable
  non imposée par ces flags.
- Alpha : donneurs historiques acceptés `Spline fit1 + feather4px x4`, géométrie/centres natifs
  conservés ; pack source
  `animations/packs-par-zone/ar3021-illithids-apo8-x4-30fps-v2-spline-fit1-feather4-20260911/AR3021/`.
- Seules les10frames correspondant aux indices natifs sont réemployées ; playback`Native`,
  aucune timeline Apollo30FPS héritée du nom historique du pack.
- Surface locale installée :31fichiers ; reçu
  `backups/water/liquid-families-x4-20260923-v1/local/AR3021-20260922T233851177160Z-a1a9aaba/install-backup.json`.
  La sélection courante des animations et la QA historique des donneurs n'approuvent pas ce nouveauRGB.

## Producteurs et commandes de référence

Commandes destinées à un **nouveau run**, ou à une étape encore non produite de ce run. Ne pas
réécrire une sortie finale existante. `$py` doit désigner le Python validé pour l'étape ; export
BC3/Pillow : runtime bundlé avec encodeur DXT5 fonctionnel. Pillow9.2 peut ignorer `pixel_format`
et produire un DDS RGBA : signature, longueur BC3 et décodage sont à vérifier avant emballagePVRZ.
Les bases-v4 n'ont appelé aucun encodeur DDS : leurs modifications portent sur les blocsBC3 existants.

```powershell
# Variables : $trialRun, $vanillaRoot, $gameRoot, $py ; plan et chemins source explicites.
& $py -B pipeline/scripts/assemble_liquid_family_x4_trial.py `
  --run $trialRun --game-root $gameRoot --vanilla-root $vanillaRoot --stage snapshot
& $py -B pipeline/scripts/build_liquid_periodic_x4_trial.py `
  --vanilla-root $vanillaRoot --plan "$trialRun/overlays-plan.json" `
  --output "$trialRun/overlays" --stage prepare
& $py -B pipeline/scripts/build_liquid_periodic_x4_trial.py `
  --vanilla-root $vanillaRoot --plan "$trialRun/overlays-plan.json" `
  --output "$trialRun/overlays" --stage generate
& $py -B pipeline/scripts/build_liquid_periodic_x4_trial.py `
  --vanilla-root $vanillaRoot --plan "$trialRun/overlays-plan.json" `
  --output "$trialRun/overlays" --build-output "$trialRun/overlays-r2" --stage build
& $py -B pipeline/scripts/build_liquid_base_x4_trial.py `
  --vanilla-root $vanillaRoot --game-root $gameRoot `
  --plan "$trialRun/request.json" --output "$trialRun/bases-v4" --run
& $py -B pipeline/scripts/build_liquid_local_surface_x4_trial.py prepare `
  --vanilla-root $vanillaRoot --output "$trialRun/local"
# Jobs GPU locaux : argv consignés dans local/preparation.json ; orchestration séparée.
& $py -B pipeline/scripts/build_liquid_local_surface_x4_trial.py assemble `
  --vanilla-root $vanillaRoot --output "$trialRun/local"
& $py -B pipeline/scripts/assemble_liquid_family_x4_trial.py `
  --run $trialRun --game-root $gameRoot --vanilla-root $vanillaRoot `
  --bases-root "$trialRun/bases-v4" --overlays-root "$trialRun/overlays-selected-v3" `
  --candidate-name override-candidate-v3 --stage assemble
```

**Source finale de l'assembleur : `overlays-selected-v3`.** La constructionr2 montrée ci-dessus
précède la sélection explicite des14groupesr2 et des deux groupes lave bilinéaires. `overlays/`
conserve préparation/génération ; aucune sortie intermédiaire ou lave générative ne doit être
substituée à la sélection finale. Candidat : `override-candidate-v3/` ; rapport :
`override-candidate-v3-assembly-report.json`.

L'assembleur repart du WED vanilla : seuls les8octets des resrefs ciblés changent. Restauration
inverse des noms = WED original byte-exact ; lookup/vitesse/portes/polygones inchangés. Contrôler
collisions des alias, nombres de tuiles natifs, inventaire des pages et état live avant installation.

## QA restante après export BC3 puis en jeu

- **Après compression BC3** : bords des couples adjacents réellement rendus, padding, masques alpha,
  différences de couleur et de luminosité ; les métriquesPNG avant compression ne suffisent pas.
- Par témoin : rive/centre, transitions primaire-secondaire, reflets/art local, répétitions,
  contours noirs/bleus, zoom/pan, pause/reprise et boucle complète.
- Groupes A–D : répétitions identiques et raccords entre membres ; inspecter toutes les phases
  natives, pas seulement une image de contact.
- Sec/pluie : noter précisément la variante observée et l'alias chargé. Variante non observée =
  QA encore absente, même si elle a été installée.
- AR3021 : jointure surface/fond x4, alpha doux sans atténuationRGB préalable indésirable, contour et mouvement
  natif des trois ressources.
- Verdicts séparés : accepté / rejeté / réserve + WED/variante/ressources/empreintes concernés.
  Une carte témoin acceptée autorise une proposition de recette, pas l'acceptation implicite de
  tous les consommateurs de la famille.

## Installation, reçus et rollback

| Élément | État / emplacement |
|---|---|
| Baseline live | `RUN/live-before.json` |
| Candidat WED/overlays/pages modifiées | `RUN/override-candidate-v3/manifest.json` ;116fichiers installés =8WED +40pages de bases +68fichiers des alias |
| Rapport assemblage | `RUN/override-candidate-v3-assembly-report.json` |
| Révision overlays retenue | `RUN/overlays-selected-v3/selection.json` :14groupesr2 +2groupes lave bilinéaires |
| Reçu assets maps/overlays | `backups/water/liquid-families-x4-20260923-v1/override/override-backup-20260923-014259/install-backup.json` |
| Pack/reçu surface locale AR3021 | **Installé,31fichiers** ; `backups/water/liquid-families-x4-20260923-v1/local/AR3021-20260922T233851177160Z-a1a9aaba/install-backup.json` |
| Contrôle final fichiers/runtime protégés |116hashes override et31payloads locaux vérifiés ; baseline385fichiers contrôlée hors deltas sélectionnés,48ressources partagées protégées, DLL/INI préservés |
| Sélection installée | `pipeline/water/manifests/liquid-families-x4-trial-installed-20260923-v1.json` ; statut`installed-pending-user-ingame-qa` |
| QA ingame | **En attente utilisateur**, neuf témoins et variantes observées à distinguer |
| Release | **Non demandée** |

Installation terminée avec sauvegardes ; vérification finale de l'assembleur`verify-installed`
réussie pour l'override, vérificationAPI réussie pour le pack local. Les changements préexistants
du domaine animations sont préservés. L'installation locale a utilisé l'API AreaTest sans
`record_lock` ; aucune sélection QA historique ne qualifie automatiquement le nouveau candidat.

Restauration éventuelle, **jeu et InfinityLoader arrêtés**, depuis la racine du dépôt ; `$gameRoot`
désigne le jeu installé et `$py` le Python configuré. Les deux commandes restaurent leurs
transactions respectives ; le CLI AreaTest`restore` n'appelle pas`record_lock`.

```powershell
& pipeline/scripts/Restore-AreaOverrideAssets.ps1 `
  -BackupPath "backups/water/liquid-families-x4-20260923-v1/override/override-backup-20260923-014259" `
  -GameRoot $gameRoot
& $py -B pipeline/area-animation-area-test/area_animation_area_test.py restore `
  --backup-path "backups/water/liquid-families-x4-20260923-v1/local/AR3021-20260922T233851177160Z-a1a9aaba" `
  --game-root $gameRoot
```

Ne pas supprimer un namespace large ni restaurer un ancien lot sans contrôler l'état courant.
Aucun rollback demandé ou exécuté par la création de cette notice.

## Références

- [Recettes historiques et limites](VALIDATED_WATER_RECIPES.md).
- [Composition native et réparations](../WATER_REPAIR_RUNBOOK.md).
- [Suivi des états distincts](WATER_RELEASE_TRACKING.md).
- `areas.csv` : état général des décors, distinct de cette QA eau.
- `RUN/request.json`, `RUN/overlays-plan.json`, `RUN/bases-v4/base-repair-report.json` : périmètre,
  entrées et deltas de l'essai ; reçus et manifeste final ci-dessus décrivent l'état installé.
