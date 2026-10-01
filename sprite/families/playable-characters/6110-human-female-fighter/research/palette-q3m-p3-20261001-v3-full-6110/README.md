# Q3m K6 x2 — couverture complete humaine guerriere 0x6110

Etat final a lire dans `verification.json` et `installation-verification.json`.
Essai experimental pour controle manuel ; `visual_qa_accepted=false`.

## Perimetre et contrat

- Animation unique `0x6110` : 656 BAM / 178 360 frames natives, cycles complets.
- Corps/armures CHFB1, CHFB2, CHFB3, CHFF4 : 92 BAM.
- Casques : 252 BAM ; boucliers : 60 BAM ; armes : 252 BAM.
- 65 familles avec sources ; `scope.json` detaille 805 items compatibles et 66 familles
  indexees. WINGS01B / YW / WQNYW n'a aucun BAM source : absence native conservee.
- Q3m K=6, F 0..7 u8/pixel, x2 ; six palettes P1 REF/DEFAULT/LATIN1..4, poids identiques ;
  fixed86 FP16 q32, reduction BOX x4->x2 ; aucun tramage/melange B.
- Toutes les frames encodees ; les frames nulles/transparentes gardent naturellement F=0.
  Les 144 echantillons P1 x2 restent identiques en I/F/dep_mask ; les 84 du petit
  pack P2 sont inclus, avec les 60 poses/armures supplementaires du corpus P1.
- Geometrie/centres x1, cycles/slots, ombres/reserves et composition preserves.
  Catalogue parent P13 reutilise ; 194 autres animations et leurs routes inchangees,
  y compris les BAM partages par d'autres acteurs. Inventaire/paperdoll hors perimetre.
- V6 : I+F cumules x2 jusqu'a 256 Mio/shard ; I seul/fichier/cache resident jusqu'a
  128 Mio. Capability DLL explicite obligatoire au-dela des 128 Mio cumules initiaux.
- Corps et chaque equipement presents dans le catalogue utilisent V6 ; repli d'erreur
  = BAM natif. Aucune seconde feuille Q0/xBR automatique ni changement de release.

## Preuves et fichiers

- `recipe.json` : sources SHA, palettes et contrat inference P1 ; seule difference
  AST autorisee = loader MPALETTE non appele, calcul pixel identique.
- `coverage.json` : 656 ressources, fractions, roundtrip, oracles et P1 byte identity.
- `x2-q3m-k6/generation/preservation.json` : equivalence BAMC/BAM, sources,
  memberships, reutilisation des shards parents et conservation hors 0x6110.
- `verification.json` : tests Python/CTest, lecture native de toutes les frames avec
  18 palettes, SHA par image depuis oracle scalaire independant, hashes sources/DLL.
- `index-budget-verification.json` : controle I seul, F absent ; 128 Mio admis en
  Python, 144 Mio rejetes en Python/C++ malgre le budget cumule de 256 Mio.
- `catalog-working-set-verification.json` : une frame par BAM dans une meme session,
  656 BAM sous 128 Mio de metadonnees ; premier BAM recharge apres eviction, identite
  sous 18 palettes ; quatre couches V6 et BAM partage de 0x6115 V5 preserves.
- Lecture native de validation via `build/p3-6110-v3-native/creature-sprites` : liens
  physiques vers les memes fichiers. Chemins originaux de 267 caracteres trop longs
  pour le flux CRT de prefixe C++ ; vue courte de 151 caracteres, installation jeu courte.
- `installation-verification.json` : DLL/catalogue/shards/INI effectivement installes.
- `candidate/`, `work/`, `captures/`, etats transactionnels : locaux, ignores par Git.
  Les anciens runs P1/P2/P3 v1/v2 restent immuables.

## Controle demain

Lancer le jeu comme habituellement ; pilotage utilisateur. Le test installe utilise
CreatureHD + Nearest, fpSprite/fpSELECT x1 desactives, trace palettes desactivee.
Verifier les quatre niveaux d'armure, puis les casques/boucliers/armes voulus :
repos, marche, combat, plusieurs directions et changements de couleurs/equipement.
Comparer aussi les autres acteurs de la scene ; leurs assets HD restent ceux du parent.

Les tests hote prouvent le decodeur CPU et les contrats ; ils ne valident pas
palettes vivantes/effets reels, upload GL, FPS ou aspect visuel. Regression REF P1
toujours +6,10 % x2 / +11,59 % x4 ; aucune correction de poids ou K ici.

Depuis `G:\AI\BG2_Upscale`, jeu et InfinityLoader fermes :

```powershell
$p3Run = 'sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p3-20261001-v3-full-6110'
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $p3Run -Mode Q3m
# Trace bornee pour une session de diagnostic ; archiver le log avant relancement.
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $p3Run -Mode Q3m -TracePalettes
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $p3Run -Mode Restore
```

Le mode Q0 complet n'est pas produit par ce run. Une comparaison Q0 implique un pack
explicite separe ; ne pas utiliser un job absent comme repli automatique.

## Production locale

```powershell
$p3Python = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
& $p3Python -B pipeline/scripts/palette_complete.py --output <nouveau-run> --runtime <manifeste-DLL-compatible>
```

Reprise `--resume` uniquement avant publication de `coverage.json`, avec recette
strictement identique. Toute regeneration d'un resultat final exige un nouveau run.
