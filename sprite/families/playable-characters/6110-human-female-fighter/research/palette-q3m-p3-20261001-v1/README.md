# P3 Q3m K6 — premier essai en jeu

État initial : **Q3m x2 installé, QA en attente**. Pilotage BG2EE manuel choisi par
l'utilisateur. Aucun lancement ingame effectué par l'agent. Aucun verdict visuel acquis.

## Portée et identités

- `0x6110` uniquement ; `CHFF4G11`, `CHFF4G12`, `WQNJ6G1`, `WQND3G1`, `WQNS1G1`.
- Packs P2 réutilisés sans réencodage : 4230 frames, 84 samples P1 Q0/Q3m K6,
  4146 frames xBR communes. Aucun changement de K, de géométrie ou de plan B.
- Première étape = smoke test + capture de palettes + A/B des samples. La verticale
  entière n'est pas couverte : autres BAM/mouvements restent au repli natif.
- DLL P3 : `candidate/InfinityEngine-Enhancer.dll`, SHA256
  `9445d59137f97da60ae748a4f21a61a0fa7a4b9ffea9b7d1a939ca821ae45143`.
  Diff P2 = capture bornée `EnableCreatureSpritePaletteTrace`, off par défaut.
- Catalogue Q3m : `4ef3187cac1ac86ce8f90083360165e8d23198582d7a321f292aa0ea84ebeef0`.
- Runtime/installation/QA distincts : `runtime.json`, reçus sous `ingame-runtime/`
  et `<pack>/ingame-installation/`, décisions QA futures séparées.
- Pas de production globale, paperdoll, intégration release ou commit demandé.

## Premier essai manuel

1. Lancer BG2EE normalement, puis charger une sauvegarde de test avec une guerrière
   humaine `0x6110` ; utiliser une copie pour conserver la partie habituelle.
2. Équiper `PLAT01` (corps CHFF4). Commencer corps seul, puis ajouter les couches
   exactement couvertes : `HELM01` (J6), `ISHLD03` (D3), `SW1H04` (S1).
   Items vérifiés dans `sprite/index/sprite_items.csv`. `HELM03` est J8,
   `SHLD05` est C2 et `SW1H01` est S0 : ils ne ciblent pas ce pack.
3. Console Ctrl+Espace, si nécessaire :

```lua
C:CreateItem("PLAT01")
C:CreateItem("HELM01")
C:CreateItem("ISHLD03")
C:CreateItem("SW1H04")
```

4. Observer repos/marche sur plusieurs directions et le repos long G12, au zoom joué.
   Capturer les éventuels liserés, ombres incorrectes, flashs ou couches manquantes.
5. Fermer BG2EE et InfinityLoader ; conserver le log avant le prochain lancement.
   L'agent peut lire le log pour vérifier les palettes et le décodage sans piloter le jeu.
6. Rejouer la même scène en Q0 pour l'A/B. Ne conclure que sur les frames couvertes.

## Installation / A-B / restauration

Commandes depuis `G:\AI\BG2_Upscale`, **jeu et InfinityLoader fermés** :

```powershell
$p3Run = 'sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p3-20261001-v1'
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $p3Run -Mode Q3m -TracePalettes
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $p3Run -Mode Q0 -TracePalettes
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $p3Run -Mode Restore
```

Le switch restaure d'abord le catalogue/INI précédent puis installe l'autre pack.
`Restore` rétablit aussi la DLL originale ; shards adressés par hash laissés inertes.
Sauvegardes : `ingame-runtime/previous-InfinityEngine-Enhancer.dll` et
`<pack>/ingame-installation/backups/<transaction>/`.

Pour les mesures FPS/p95, installer sans `-TracePalettes`. La capture ajoute une
reconstruction CPU et des écritures log ; ses timings ne valent pas pour la performance.
`PerformanceLogs=true` existe déjà ; attendre les lignes `Frame presentation perf`.

## Preuves automatiques de capture

`Q3M_P3_PALETTE` : palette native brute 256 DWORDs après Realize, format/type, cell,
couche, generation, resref, cycle/slot/frame, flags/transparence, pixels CRC32 et
empreinte du décodeur C++. Maximum 1024 couples uniques cell/frame/palette/encoding
par thread/session. Indice transparent normalisé ensuite comme CVidCell.

Archiver le log dans `captures/<cas>-<mode>.log`, puis :

```powershell
$p3Python = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
& $p3Python -B pipeline/scripts/palette_p3.py verify-capture `
  --assets "$p3Run/x2-q3m-k6/generation/iee-assets/creature-sprites" `
  --log "$p3Run/captures/<cas>-q3m.log" --output "$p3Run/captures/<cas>-q3m.json"
```

Le checker utilise des intervalles de classes explicites, sans helper de décodage
de production. Contrôles : CRC/taille, table native cycle/slot, empreinte sur le
dep_mask. Rapport = samples capturés uniquement ; aucune preuve GPU readback.
`records_with_nonzero_F>0` nécessaire pour constater le passage effectif par Q3m.

## Suite P3 à réaliser

- A/B REF, DEFAULT, VAL05, VAL10 : lignes exactes dans `p1-palette-plan.json`.
  Recoloration via menu/effets EEex ; API installée vérifiée, comportement encore à observer.
- Couleurs canal par canal, opcodes pulsés 8/9, ombre/alpha, pause/invisibilité/flou,
  deux acteurs même BAM aux couleurs opposées ; captures de scènes explicitement nommées.
- Logs `Composing creature sprite ... layer n/n`, remplacement/fallback explicites.
- Redémarrage/contexte WGL, équipement/couleur, sauvegarde/rechargement, FPS/p95
  avec capture désactivée. Aucune preuve runtime déduite des tests hôte.
- Arbitrage utilisateur obligatoire pour REF (+6,10% x2 P1), recoloration et rendu.
- Compléter les BAM nécessaires avant de déclarer la verticale entière acquise.

## Vérifications de préparation

- Build MSVC19.29/v142 x64, SDK10.0.19041 ; deux suites ciblées `iee_tests` et
  `iee_palette_fraction_tests` PASS.
- Checker P3 : 65 664 pixels RGBA/BGRA égaux aux octets de la fixture P1.
- DLL/catalogue/shard installés vérifiés par empreinte ; Nearest et trace activés.
- Sources et preuves P0/P1/P2 conservées. `preparation.json` décrit cet état initial.
