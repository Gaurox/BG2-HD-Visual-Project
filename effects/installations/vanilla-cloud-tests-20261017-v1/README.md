# Nuages isolés sur vanilla — 2026-10-17

- Autorisation : utilisateur veut tester les4animations seules sur sa copie vanilla ; les vrais sorts fonctionnent, les4appels BAM directs n'affichent rien.
- État faisant autorité : [`installation.json`](installation.json), champ `status`. QA visuelle utilisateur distincte de l'installation/vérification technique.
- Cible résolue depuis `C:/Users/Adrien/Desktop/BG2EE VANILLA.lnk` : `G:/AI/BG2_Vanilla_23534562/Baldur.exe`.
- Intervention : **4nouveaux VVC seulement**, `override/{BDWOFOGA,SPCLOUDK,SPCLOUDS,SPDFOGA}.vvc`. Le moteur choisit désormais le contrôleur VVC du même nom avant le BAM. Aucun fichier préexistant remplacé ; BAM/SPL/PRO/BIF d'origine conservés, pas d'EEex/renderer HD installé.
- Source : copies octet identiques des4contrôleurs Z58 du candidat lot58 installé, renommées uniquement au niveau du fichier ; chaque référence BAM reste native. Même cycle,15FPS, mêmes flags normaux/non-Blended que le test HD. Les effets ne déclenchent ni sort ni dégâts ni dispersion PRO.
- Vérification préparation : chaque BAM présent dans le KEY vanilla, absence de VVC homonyme dans KEY/override, absence de BAM override, cycles/slots/index natifs valides, VVC492octets/version/référence/flags/FPS contrôlés. SHA256 VVC/BAM et fichiers de base conservés dans le reçu.

| Animation | Cycle natif | Slots | Commande HD équivalente |
|---|---:|---:|---|
| BDWOFOGA |4, boucle bornée|82|`C:Eval('CreateVisualEffectObject("Z580269",Player1)',0)`|
| SPCLOUDK |2, une fois|33|`C:Eval('CreateVisualEffectObject("Z580278",Player1)',0)`|
| SPCLOUDS |2, une fois|33|`C:Eval('CreateVisualEffectObject("Z580290",Player1)',0)`|
| SPDFOGA |1, une fois|66|`C:Eval('CreateVisualEffectObject("Z580300",Player1)',0)`|

## Vanilla : Ctrl+Espace, une commande à la fois

```lua
-- Brouillard putride
C:Eval('CreateVisualEffectObject("BDWOFOGA",Player1)',0)
-- Nuage mortel
C:Eval('CreateVisualEffectObject("SPCLOUDK",Player1)',0)
-- Nuage puant
C:Eval('CreateVisualEffectObject("SPCLOUDS",Player1)',0)
-- Brume mortelle
C:Eval('CreateVisualEffectObject("SPDFOGA",Player1)',0)
```

Laisser le jeu défiler après fermeture de la console si la pause était active. Les deux nuages33slots durent2,2s ; SPDFOGA4,4s, BDWOFOGA~5,47s. Ne pas comparer leur dispersion à un vrai sort : ces tests affichent un élément isolé.

## Vérification / retrait

Recette : `pipeline/recipes/effects-vanilla-cloud-tests-20261017-v1/install.py`. `prepare --game-root <cible_du_raccourci>` déjà exécuté ; ne pas recréer le reçu.

```powershell
python -B pipeline/recipes/effects-vanilla-cloud-tests-20261017-v1/install.py verify
# Retrait réversible, jeu/InfinityLoader fermés : suppression des4seuls VVC,
# uniquement si leurs octets correspondent encore au reçu.
python -B pipeline/recipes/effects-vanilla-cloud-tests-20261017-v1/install.py restore
```

Format : https://gibberlings3.github.io/iesdp/file_formats/ie_formats/vvc_v1.htm ; priorité VVC/BAM : https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm#273 .
