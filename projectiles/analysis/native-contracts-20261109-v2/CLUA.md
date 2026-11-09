# Projectiles — tests ingame préparés, 2026-11-09

- **Lot immédiat : QA01→QA05.** Ressources natives déjà disponibles ;aucune installation nécessaire. `tests-ready.json` lie les capacités et les SHA des SPL/ITM actifs.
- Partie de test non enregistrée ;IA du groupe désactivée. Player1 lanceur,Player2 visible à distance ;dépauser pour l'animation. Un essai à la fois ;attendre sa fin ou recharger entre effets persistants.
- Retours attendus par numéro : aspect,couleur,transparence/contour,vol→impact→dispersion,disparition. Un lancement/objet créé ne prouve pas un dessin ou un tir réussi.
- Trace détaillée `EnableEffectStreamingTrace=false` conservée : retour visuel possible, aucune preuve technique HD/masque/phases déduite automatiquement.

## QA01 — Boule de feu : accord à confirmer après les correctifs

```lua
C:Eval('ForceSpellRES("SPWI304",Player2)',0)
```

- SPWI304→PFIRE2 ;observer le vol FIREBAT puis l'explosion. Le retour positif historique précède les correctifs du rendu ;pas de remise en cause des images acceptées.

## QA02 — Piège à crâne : vol et déclenchement

```lua
C:Eval('ForceSpellRES("SPWI313",Player2)',0)
```

- SPWI313→TRAPSKUL ;observer SKLT/crâne posé. Un piège qui attend ne valide pas ses fragments :pour déclencher,utiliser une cible ennemie vivante à proximité.
- Variante sur ennemi :curseur à distance du groupe,créer l'ennemi puis lancer immédiatement :

```lua
C:CreateCreature("OGRE01")
C:Eval('ForceSpellRES("SPWI313",NearestEnemyOf(Myself))',0)
```

- Observer aussi SKLH à l'explosion. Recharge entre variantes pour éviter l'empilement des pièges.

## QA03 — Orbe chromatique : couches et transparence

```lua
C:Eval('ForceSpellRES("SPWI118",Player2)',0)
```

- SPWI118→CHROMORB ;observer SPCHRORB sur le vol/l'impact,absence de rectangle opaque et disparition. LIGHTSTO n'est pas utilisé par ce pilote ;son enfant est SKYBOLT22, pas CHROMORB23.

## QA04 — Anneau202 : vraie route propriétaire/palette

Curseur à distance du groupe ;créer une cible ennemie avant le sort (pétrification possible) :

```lua
C:CreateCreature("OGRE01")
C:Eval('ForceSpellRES("SPWM157",NearestEnemyOf(Myself))',0)
```

- SPWM157 capacité0→SPKLARST ;champ secondaire0x214=202→PROJECTL202→SHAREA+SHAREA2. SHA/capacité vérifiés dans tests-ready.json.
- Observer l'anneau et sa couleur/transparence sur le fond. Le sort interne de magie sauvage peut avoir un effet de jeu ;recharger après l'observation.
- Ce pilote remplace SPIN560/SPWM162→SPKLARRE201/SHAREA6 :ils ne testent pas202. Les autres palettes déjà observées gardent leur QA.

## QA05 — TSKULLNP : tirer le crâne de Jan

- Correction après retour utilisateur :BOLT07 est le crâne «Flasher Master Bruiser Mate»,munition spéciale de Jan ;la consigne initiale «arbalète compatible» était insuffisante. Lanceur exact **XBOW12** («Flasher Launcher»),présent avecBOLT07 dansJAN8/JAN10/JAN12.CRE natifs.
- Utiliser Jan dans le groupe. S'il est absent :place libre dans le groupe,curseur sur terrain libre,`C:CreateCreature("JAN10")`,puisfermer la console etCtrl+Q en pointant Jan pour le recruter dans cette partie de test.
- Sélectionner Jan seul avant de créer les objets ;ou lui transférer le crâne déjà créé :

```lua
C:CreateItem("XBOW12")
C:CreateItem("BOLT07",5)
```

- Équiper XBOW12 dans un emplacement d'arme etBOLT07 dans un emplacement de munitions ;sélectionner explicitement les crânes comme munition active (Jan possède aussi des carreaux ordinaires).
- Curseur à distance du groupe :`C:CreateCreature("OGRE01")` ;sélectionner Jan,attaquer l'ogre avecXBOW12,dépauser etobserver le tir.8Force requise par le lanceur ;ne pas utiliser une arbalète générique pour ce test.
- BOLT07 capacité0 brut240→PROJECTL239 TSKULLNP ;observer vol SKLT,impact/fragments SKLH. Ne pas compter la création de l'objet comme un tir.
- La QA de TRAPSKUL ne suffit pas à valider ce propriétaire ;aucune nouvelle production nécessaire.

## Autres essais préparés

### QA08 — alias natif du carreau enflammé, disponible

```lua
C:CreateItem("XBOW15")
```

- Équiper l'arbalète,choisir sa capacité de tir et tirer sur ennemi vivant. Ses capacités0/1 emploient brut14 ;le moteur normalise14→4→ARROWFLM.
- Observer Y31P056 et fuméeSPSMPUFF ;pas de texture «BOLT_FLAMING» supplémentaire à produire.

### QA07 — propriétaire FIRESTOR, essai complémentaire optionnel

```lua
C:Eval('ForceSpellRES("SPWI399",Player2)',0)
```

- Sort interne→FIRESTOR→enfant37 FIREBALL. La donnée0x21a=38 est numérotée à partir de1, pas PROJECTL38 :le graphe corrigé ne passe pas par ICE_FRAGMENTS.
- SPWI399 n'est pas le sort standard Tempête de feu ;ce pilote sert à observer cette branche précise.

### QA06 — Appel de la foudre : attendre le raccord SKYBOLT pour sa QA HD

```lua
C:Eval('ForceSpellRES("SPPR302",Player2)',0)
```

- Extérieur ;cible visible. Capacités selon niveau→IDs80..83→enfantSKYBOLT22. Cet essai peut montrer le natif aujourd'hui ;ne pas l'accepter comme preuve de substitutionHD avant le raccord.
- Ne pas rejouer LIGHTCHA pour réexaminer «cycle9» :cette réserve était une erreur de lecture des périodes d'émission.

## Pilotes réservés après les10raccords

**Pas à lancer comme campagne de validation HD maintenant.** `tests-after-links.json` : SHA et capacités de chaque pilote vérifiés. Les sorts internes peuvent avoir des conditions de cible/zone ;une absence de dessin se diagnostique avant de conclure sur l'image.

| BAM/route à observer | Pilote CLUA après raccord |
|---|---|
| HLYMITE65 | `C:Eval('ForceSpellRES("SPPR214",Player2)',0)` |
| SHAIR130 +paletteSHAIR4 | `C:Eval('ForceSpellRES("SPIN835",Player2)',0)` |
| SHEARTH137 +paletteSHEARTH6 | `C:Eval('ForceSpellRES("SPIN782",Player2)',0)` |
| SKYBOLT via contrôleur80..83 | `C:Eval('ForceSpellRES("SPPR302",Player2)',0)` |
| SPBOOM / modeSTORM3 | `C:Eval('ForceSpellRES("SPWI404",Player2)',0)` |
| SPFDEATH207 | `C:Eval('ForceSpellRES("SENDAIF1",Player2)',0)` |
| SPGENHLA254 | `C:Eval('ForceSpellRES("SPPR412",Player2)',0)` |
| SPGFLSH1 / modeENTANGLE9 | `C:Eval('ForceSpellRES("SPPR105",Player2)',0)` |
| SPSCORIC190 | `C:Eval('ForceSpellRES("SPWI015",Player2)',0)` |
| SPWRDFLD / modeWEIRD8 | `C:Eval('ForceSpellRES("SPWI421",Player2)',0)` |

- SPWI404 ci-dessus :observer uniquement les nouveaux composants raccordés ;leurs composants déjà acceptés gardent leur QA.
- LIGHTSTO :aucun essai normal préparé ;MAGMIS manque mais aucun pilote dans le graphe SPL/ITM/PRO courant. Pas de remplacement arbitraire ni d'asset synthétique installé.
