# Lot33 — transparence du noir, audit2026-10-17

## Résultat

- Périmètre : `effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1/`,33productions/36codes/5244phases. Demande : vérifier les fonds noirs servant de transparence ingame.
- **Alpha exporté vérifié33/33 ; transparence ingame de tous les chemins non garantie.** Aucun des33 n'est installé dans le manifest actif ; aucune capture du mélange natif de ce lot.
- **20sources contiennent du noir/presque noir opaque** (`max(R,G,B)≤8`, index transparent exclu). Ce critère repère les cas sensibles ; il ne prouve pas que chaque pixel sombre est un fond à supprimer.8sources contiennent du noir exact opaque.
- Normal alpha : un pixel noir/A255 masque le terrain. Mélange lumineux : le noir RGB peut être neutre. Le choix appartient au consommateur natif, pas au seul BAM ; conserver alpha et prémultiplication ne suffit donc pas à garantir ce résultat.
- **Ne pas convertir globalement le noir en alpha et ne pas forcer tous les33 en mode normal.** Risques : perte de détails sombres, modification de l'intensité/du tint/du halo. Les deux encodages déjà produits restent disponibles ; routage à déterminer par consommateur observé.
- Aucun fichier installé, production scellée, décision QA ou release modifié par cet audit.

## Preuves fichiers

Autorité : [`audit.json`](audit.json), producteur [`audit.py`](audit.py). Tous les5244couples RGBA prémultiplié/droit relus et SHA256 comparés aux manifestes :

| Propriété | Résultat |
|---|---|
| RGB nuls lorsque A=0, deux encodages | 5244/5244 |
| Alpha identique des deux encodages | 5244/5244 |
| RGB prémultiplié≤A ; reconstruction droit×A | 5244/5244 ; erreur≤1/255 |
| Alpha effectif des entrées palette utilisées hors index transparent | 255 pour33/33 |
| Alpha palette natif gradué1..254 utilisé | aucun |
| Productions du lot présentes dans le manifest installé | 0/33 |
| Mélange natif observé lors d'un vrai draw de ce lot | 0/33 |

L'absence d'alpha palette gradué distingue ce lot des4nuages corrigés : [`../black-cloud-backgrounds-20261017-v1/REPORT.md`](../black-cloud-backgrounds-20261017-v1/REPORT.md). A0/255 palette signifie opaque par compatibilité, index transparent toujours prioritaire : `pipeline/scripts/bam_export.py:native_palette_alpha`. Le fond noir interne reste potentiellement opaque en composition alpha normale malgré l'extérieur correctement transparent.

### Cas sensibles à conserver dans le contrat d'intégration

Noir exact opaque dans la source :

`SPMETSWM SPRDRASI SHAREA SHEARTH SHWATER SPPRISM2 SPSPARKS SPSMPUFF`

Presque noir opaque dans la source, sans noir exact :

`SPCCOLDL SPICESTM SPSCORIC HLYMITE SPGENHLA SPHLYSM2 SPHLYSM3 SPUNHBL2 SPUNHBL3 SPCSPRA2 SPCSPRA3 SPHORPUF`

13sources sans pixel opaque≤8 :

`SPBOOM SPBRNHND SPBURN SPRING SPSMKJET STNKCLDD BLOODCR BLOODL BLOODM BLOODS SPBLOOD SPCHUNKS SPDEATH3`

Ce dernier groupe n'exonère pas du respect du mélange natif. SPBRNHND compte15pixels de sortie presque noirs/A≥240 sur120phases, malgré zéro source≤8 ; statistique de diagnostic, pas un fond noir démontré. Inversement l'unique pixel noir natif SPSMPUFF ne subsiste pas en presque noir opaque dans l'export. Alias à suivre sans inférence séparée : BURNHAND→SPBRNHND ; SPPRISM3/SPPRISMT→SPPRISM2.

### Diagnostic visuel

[`blend-diagnostic.png`](blend-diagnostic.png) : six exemples, alpha normal sur terrain vs **simulation mathématique lumineuse**, pas une capture ni une reproduction prouvée du mélange moteur. Formule illustrative RGB prémultiplié `P` et fond `B` : `P+B*(1-P)` ; noir→fond. Elle démontre pourquoi un aperçu alpha normal peut montrer un fond absent sous un autre mélange ; elle ne choisit pas le mode natif.

Sonde des noyaux noirs exacts natifs, distance>2pixels x1 et intersection des deux poses sources : [`spmetswm-black-core.json`](spmetswm-black-core.json), [`spmetswm-black-core.png`](spmetswm-black-core.png). SPMETSWM picRGB121 à phase74 dans cette intersection ; énergie localisée, pas un aplat gris global observé. Les mouvements interpolés peuvent traverser une zone noire dans les deux poses clés : cette mesure seule ne démontre pas une fuite, ni une correction alpha nécessaire. Autres noyaux : pic≤3. Cette sonde n'évalue pas tous les fonds presque noirs et ne remplace pas la comparaison ingame.

## Moteur : limites de couverture

- `engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp:2830–2934` : contexte d'effet depuis `CProjectileBAM::Render` / `CVEFVidCell::Render`, puis finalisation FX. `:4065` : substitution HD exige ces contextes et l'absence de scope créature prioritaire. `x4-bound` réel nécessaire pour exclure un simple affichage natif correct.
- Shader installé `override/fpDraw.glsl`, branche ordinaire : texture×couleur/tint ; aucune conversion générale noir→alpha. La neutralité du noir ne peut pas être déduite du shader seul.
- [`native-references.json`](native-references.json) :71références statiques exactes aux codes,9fragments natifs. Une référence statique ne prouve pas le chemin effectivement exécuté.
- Constructeur natif RVA30ACE0 : cellules CVidCell+CE0/+E18, vtable5A8F00 ; [`ctor-0030ACE0.asm`](ctor-0030ACE0.asm), fragments30ADCB/30B45E. Vtable slot38→RVA32D020 : [`native-effect-render-full-0032D020.asm`](native-effect-render-full-0032D020.asm). Ce rendu compose ses flags depuis les champs+5F4/+5F5/+5F6/+F80 avant FXRender. Ces chemins supplémentaires ne sont pas prouvés couverts par les deux owners effects actuels ; **risque d'absence de substitution HD à vérifier séparément du noir**.
- `RenderTexture` RVA4257C0 →`DrawBegin`4130B0 : début de primitive, pas une preuve du choix de mélange. Le facteur GL précis n'a pas été capturé ; aucune attribution systématique « additif » aux33.

## Décision pour l'intégration

Pour le vrai usage de chaque cas sensible : identifier owner/flags/mélange et encodage adapté ; observer `x4-bound` sur ce chemin ; comparer terrain visible/halo/tint au natif. Un VVC de test normal ne constitue pas une preuve pour un appel natif lumineux, ni l'inverse. Si plusieurs consommateurs exigent des contrats différents, appliquer des alias ciblés comme les variantes déjà acceptées ; ne pas écraser l'encodage utilisé par les autres consommateurs.

**État final : production inchangée, audit terminé ; transparence ingame et couverture HD encore non observées.** Pas d'acceptation implicite.

Hashes du contexte lus pendant l'audit :

```text
manifest actif 44A63CBDDC7609D9C89921C0BEBE148A577847AB28D2B400DB8AEDF91C34E924
DLL active     FEA4B2B153653461D465B67EB9CC5A762CC97785E511EEBBF5C776348268C246
BaldurReal.exe B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57
```
