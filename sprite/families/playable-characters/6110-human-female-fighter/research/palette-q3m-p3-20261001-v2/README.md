# P3 Q3m K6 — catalogue complet, essai corrigé

État initial : **Q3m corrigé installé, QA en attente** ; `installation-verification.json`
confirme DLL, 833 shards, Nearest et profils x1 désactivés. Préparation hors jeu validée.
Pilotage BG2EE manuel. P3 non validée visuellement. Essai v1 et ses captures conservés.

## Correction et portée

- Parent P13 x2 : catalogue `CC91FA2EABBFCF5D63B94F3375C861DAE50862B787A000330B7E065148E9BFDC`.
- 195 animations ; 194 autres animations : mêmes routes/memberships/assets.
- `0x6110` garde ses 656 resrefs ; 5 remplacés seulement pour cette animation :
  CHFF4G11, CHFF4G12, WQNJ6G1, WQND3G1, WQNS1G1.
- 828 shards parents réutilisés ; 48 records résiduels V5 copiés sans réencodage ;
  feuille P2 Q0/Q3m réutilisée. Résultat : 813 composants / 833 shards ; aucun appel neural.
- Autres BAM `0x6110`, dont WQNMC/WQNJ8/WQNC2 : HD antérieur conservé.
  Ils ne deviennent pas Q3m. Verticale de quatre couches Q3m = équipement P1 exact.
- V5/V6 : composants homogènes, V6 Character uniquement ; nouvelle capability runtime
  obligatoire. Géométrie, cycles, interpolation, alpha/composition et plan B inchangés.
- SHA BAMC→BAM : contenu décompressé identique prouvé pour les cinq ressources.
  `generation/preservation.json` contient hashes, copies résiduelles et invariants.
- Profils fpSprite/fpSELECT x1 désactivés pendant l'essai ; CreatureHD actif et Nearest.
  Restauration catalogue/INI/DLL prévue ; aucune release ni production globale.

## Essai manuel

1. Lancer BG2EE comme habituellement. Rejouer d'abord la scène ayant échoué : vérifier
   corps + équipement HD, autres acteurs HD et absence du lissage x1 imposé par D7.
2. Pour comparer les quatre couches P1 : PLAT01 + HELM01 + ISHLD03 + SW1H04.
   Corps seul puis ajout des couches ; repos/marche, plusieurs directions, repos long.
3. Fermer jeu/InfinityLoader, archiver le log avant un nouveau lancement ; Q0 puis
   Q3m dans la même scène. Recolorations REF/DEFAULT/VAL05/VAL10 et effets : suite P3.
4. Une capture CPU réussie ne valide pas l'affichage. Exiger `Q3M_P3_DRAW` corrélé,
   `replacementBound=true`, couches complètes et QA utilisateur.

## Commandes

Depuis `G:\AI\BG2_Upscale`, jeu et InfinityLoader fermés pour installer/restaurer :

```powershell
$p3Run = 'sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p3-20261001-v2'
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $p3Run -Mode Q3m -TracePalettes
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $p3Run -Mode Q0 -TracePalettes
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $p3Run -Mode Restore
```

Capture bornée V6 uniquement ; coût CPU/log supplémentaire. Désactiver TracePalettes
pour mesurer FPS/p95. `Q3M_P3_UNRESOLVED` nomme les cellules manquantes/froides.

```powershell
$p3Python = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
& $p3Python -B pipeline/scripts/palette_p3.py verify-capture `
  --assets "$p3Run/x2-q3m-k6/generation/iee-assets/creature-sprites" `
  --log "$p3Run/captures/<cas>-q3m.log" --output "$p3Run/captures/<cas>-q3m.json"
```

Checker : routage du catalogue, identité V6, CRC/fingerprint CPU, corrélation avec
substitution native. Sans substitution HD : exit 1 ; `--cpu-only` pour diagnostic
explicite uniquement. Aucun GPU readback, aucune acceptation visuelle implicite.

## Preuves hors jeu

`preparation.json` : résultats Python/CTest, hashes DLL/catalogues/scripts et logs.
Tests natifs : ordres de chargement, owners mixtes, resrefs partagés avec memberships
disjointes, palettes par couche/acteur, pulsation/cache/reset, quarantaine composants.
Packs : 4230 frames × 18 palettes par mode, oracle P2 intact ; composition réelle
CHFF4G12 + WQNMCG1 + WQNJ8G1 + WQNC2G1 et conservation CHFF4G12 pour `0x6115`.
