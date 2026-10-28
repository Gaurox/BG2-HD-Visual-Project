# Six tests V3 + nuage opaque — 2026-10-28

- Preuves figées : `runtime.log`, `events.txt`, `evidence.json` ; recette `check.py`. Session10:49–10:50, DLL V3. Retour utilisateur : tout semble correct sauf nuage opaque ; ancien correctif rappelé. Aucun résultat visuel V4 déduit.

| Test | Trace observée | Limite conservée |
|---|---|---|
| Nuage mortel | Y31P069 + SPCLOUDK résolus/liaisonx4 ; SPCLOUDK masque0x20 | Retour visuel refusé : fond opaque ; ancienne variante binairealpha utilisée |
| Piège à crâne | SKLT géométrie24×52 rejetée,0x80000000/0x2 | Aspect jugé correct ; volHD non prouvé, aucun SKLH observé ; ne pas valider les fragments |
| Orbe chromatique | SPCHRORB géométrie56×60/57×59… rejetée | Aspect jugé correct, rendu composé encore natif |
| Insectes | X26PLAA + XIPLAUIN,0x8 puis0x20 | Résolution timeline0x4 ; pas de trace finale par phase ; quelques chargements0x10 |
| Tempête de glace | Y31P067 et COLDH0x8 ; COLDH0x20 | Enfants/fragments natifs non tous identifiés ; ne pas déduire la couverture de tout le dispatch |
| Éclairs en chaîne | SPCHLGT1/2/3 : séquence2,phase2,0x8 | Ne valide pas le cycle9 absent de SPCHLGT3 ; pas de mesure finale des phases |

- Ancienne solution retrouvée : `effects/installations/cloud-palettealpha-20261017-v1/README.md`, source du défaut `effects/research/black-cloud-backgrounds-20261017-v1/REPORT.md`. Les VVC de test utilisaient X58CLK ; le vrai PRO gardait SPCLOUDK et devenait maintenant effectivement HD via le pontFX, exposant l'ancien alpha binaire.
- Comparaison installation actuelle : SPCLOUDK/X58CLK425paires,605524352octets hashés ; RGB byte-identiques pour toutes ; alpha différent sur424paires. Cycles, timelines, tailles, centres, encodage straight et carriers natifs identiques. Échantillonframe212 : médianeA255→26,216324pixelsA255→0pixelsA255. Aucun calcul d'image ni copie d'asset nécessaire.
- Correction installée : `engine/InfinityEngine-Enhancer/installations/projectiles-cloud-alpha-20261028-v4/README.md`. Sélection HD interneSPCLOUDK→X58CLK, références natives intactes. **Retest visuel du nuage V4 en attente.** Ne pas promouvoir la QA des124/243 depuis ces tests.
