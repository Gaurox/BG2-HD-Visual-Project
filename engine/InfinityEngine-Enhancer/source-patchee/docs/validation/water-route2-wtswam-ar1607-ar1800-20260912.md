# Route2 WTSWAM AR1607/AR1800 — 2026-09-12

Sélection courante : `pipeline/water/manifests/wtswam-rain-installed-20260912-v4.json`.
V2/v3 rejetées sous pluie : variante TIS WTSWAMR omise, pas seulement un problème fpTone.
Paire sec/pluie x4 isolée et matcher des ressources alternatives natives ; état installé validé.
QA utilisateur : `pipeline/water/manifests/wtswam-ar1607-ar1800-validated-20260912-v1.json` ; q0.70.
Cause/preuves/QA : `pipeline/water/WTSWAM_RAIN_RESOURCE_REPAIR_20260912.md`. Historique ci-dessous.

## Contrat initial — QA rejetée

| Champ | Valeur |
|---|---|
| Identités | `AR1607/WTSWAM/slot1`, `AR1800/WTSWAM/slot1` |
| Matériau | `WaterMaterialMode::Swamp`, `material_id=5` |
| Intensité | `q=0.70` |
| Animation | 36 phases à 15 Hz, interpolation linéaire renderer à 30 FPS |
| Gate shader | modes 1 eau, 4 égouts et 5 marais uniquement |
| Fallback | identité absente/divergente : `q=0`, rendu natif |
| DLL | SHA-256 `32D519D11FC0E1628D0157E3326BC750710DD48D3DA55AE1D3ABBEF153FAF90B` |
| `fpSEAM.glsl` | SHA-256 `A63D1FCDAC49CDAA09B191FC08800E79A38069165927E549C47877B956FD8472` |
| Tests | Non exécutés, choix utilisateur |
| QA | En attente sur les deux cartes |

Registre compilé :
`maps/technical-overlays/WTSWAM/runs/seedvr2-none-apollo8-x4-15hz-route2-render30-q070-ar1607-ar1800-20260912/registry-v3.json`,
17 entrées, SHA-256 `B37AC8176CDFAB633790FCFF9271C70EDDB5CA9D303F1026D52A48432ADB3222`.

Preuve d'installation et reçus :
`pipeline/water/manifests/wtswam-ar1607-ar1800-pilot-installed-20260912-v1.json`.

## Reprise v2 installée — pas encore validée ingame

- Sélection : `pipeline/water/manifests/wtswam-ar1607-ar1800-repair-installed-20260912-v2.json`.
- Registre : `maps/water-batches/runs/wtswam-ar1607-ar1800-repair-20260912-v2/registry-v3.json` ;
  SHA256 `877BC199CB31B70F2A5D31EDAF77E19E55D8556819B493797CAD8CF46BC854C5`.
- DLL SHA256 `8F2D0CF39B6FB89F717C8F4EAD7501D8ABD24721B006801EC3FD6970CC5F0010`.
- Shader SHA256 `763CCBD16733CFC17AEEBA72A8F31D3204E96C918753CA6FB5A49519410E4D6C`.
- Voie1 : alpha natif100 AR1607/128 AR1800 et raccords RGB repris ; références bases mises à jour.
- Matériau5 : shallow RGB `(0.30,0.48,0.37)`, spec0.40 ; autres modes inchangés, q0.70.
- Diagnostics : `Match.wed`, budgets identity/draw par WED, rejet/identité/alpha natif tracés.
  Règles de matching/fallback inchangées. Les anciens logs ne prouvaient pas une panne de routage
  sur ces cartes : budget épuisé sur AR0900. Activation réelle des deux cibles encore à confirmer.
- Build : `build/iee-wtswam-repair-20260912-v2`, Release x64, `BUILD_TESTING=OFF`.
  Tests non exécutés ; jeu non lancé ; hashes des696 ressources du registre installées vérifiés.
- Procédure QA : `pipeline/water/WTSWAM_AR1607_AR1800_PILOT_20260912.md`, section Reprise v2.
