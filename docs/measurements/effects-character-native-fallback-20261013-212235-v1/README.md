# Audit dernière session — 2026-10-13 21:22:35

- Fenêtre log : 21:22:35.552–21:24:42.073 ; source lignes 29682–30872.
- Aucun changement installation/INI ; défaut moteur/installeur suspendu sur demande utilisateur.
- À 21:24:25.204–.304 : composites Character 0x6010/0x6210/0x6110 -> natif ; 0x6000 à 21:24:33.841.
- FDAWNX : 39 slots refusés ; slot0 pack31x32/draw31x76. Refus géométrique distinct des échecs de création texture.
- Hypothèse saturation slots : cache effets sans éviction, table moteur512 ; allocation effective non journalisée => causalité non démontrée.
- Traces stage uniques par resref/session ; x4-bound ≠ toutes frames validées. Ne pas interpréter le suffixe textuel générique « x4Bound confirms » des lignes fallback comme succès.

| BAM | VVC | Observation |
|---|---|---|
| ABJURH | ABJURH | x4 observé, aucun fallback signalé |
| OHRSHFIE | OHRSHFIE | x4 observé, aucun fallback signalé |
| SPGFLSH1 | SPGFLSH1 | x4 observé, aucun fallback signalé |
| BDFAVSPI | BDFAVSPI | x4 observé, aucun fallback signalé |
| BDRSPIRI | BDRSPIRI | x4 observé, aucun fallback signalé |
| SPRAISEI | ICRAISEI | x4 observé, aucun fallback signalé |
| COLDH | COLDH | x4 observé, aucun fallback signalé |
| FIREH | FIREH | x4 observé, aucun fallback signalé |
| MMAGICH | ICMAGICH | x4 observé, aucun fallback signalé |
| SPSHKIMP | SPSHKIMP | x4 observé, aucun fallback signalé |
| FDAWNX | FDAWNX | retour natif confirmé, aucun x4 observé |
| GRNDGLOW | FIRECOLD | x4 puis retour natif |
| SPCCMDSI | ICCCMDSI | retour natif confirmé, aucun x4 observé |
| SPUNHOLY | SPUNHOLY | aucune trace dans cette session |
| SPDISPMA | SPDISPMA | aucune trace dans cette session |
| SPHEALIN | SPHEALIN | aucune trace dans cette session |
| SPHOLLYW | SPHOLY | aucune trace dans cette session |
| BDSPLOCK | BDSPLOCK | aucune trace dans cette session |
| CSHIELDH | CSHIELDH | aucune trace dans cette session |
| CURSEH | CURSEH | aucune trace dans cette session |
| SPBLESHI | ICBLESAI | aucune trace dans cette session |
| GARMORH | 1WDGARMR | aucune trace dans cette session |
| SARMORH | 1WDSARMR | aucune trace dans cette session |
| SPARMORI | ICARMOR | aucune trace dans cette session |
| PARALH | PARALH | aucune trace dans cette session |
| SPDHRMNY | SPDHRMNY | aucune trace dans cette session |
| SPCHMPSI | ICCHMPSI | aucune trace dans cette session |
| SPSTRENI | ICSTRENI | aucune trace dans cette session |
| SPSTRONE | ICSTRONE | aucune trace dans cette session |
| SPPOWATK | SPPOWATK | aucune trace dans cette session |
| SPSDIMPA | SPSDIMPA | aucune trace dans cette session |
| SPTRUSEE | SPTRUSEE | aucune trace dans cette session |
| SPUSEANY | SPUSEANY | aucune trace dans cette session |
| SPFDEATH | SPDEATH3 | aucune trace dans cette session |
| ASUMM1X | ASUMM1X | aucune trace dans cette session |
| BDSHSUM | BDSHSUM | aucune trace dans cette session |
| MSUMM1X | MSUMM1X | aucune trace dans cette session |
| SPFRACTI | ICFRACTI | aucune trace dans cette session |
| BDSPWARD | BDSPWARD | aucune trace dans cette session |
| SPROTECT | SPROTECT | aucune trace dans cette session |
| SPFLSRIN | SPFLSRIN | aucune trace dans cette session |
| SPSETTIH | SPSETTIH | aucune trace dans cette session |
| OHRDARK | OHRDARK | aucune trace dans cette session |
| SPPOWWRD | SPPOWWRD | aucune trace dans cette session |
| BDETHER | BDETHER | aucune trace dans cette session |
| SHAREAW | SHAREAW | aucune trace dans cette session |
| BDSPCLAR | BDSPCLAR | aucune trace dans cette session |
| EXALTAH | EXALTAH | aucune trace dans cette session |
| GLDUSTH | GLDUSTH | aucune trace dans cette session |
| OHRMJAR | OHRMJAR | aucune trace dans cette session |
| SPNWCHRM | SPNWCHRM | aucune trace dans cette session |
| SPHLYBLS | SPHLYBLS | aucune trace dans cette session |
| SPPLANAR | SPPLANAR | aucune trace dans cette session |
| SPSPMAZE | SPSPMAZE | aucune trace dans cette session |

- `audit.json` : faits, lignes originales, limites ; `last-session.log` : snapshot ; `effects.csv` : couverture54.
- Session précédente21:11:42–21:15:26 : SPUNHOLY supplémentaire en fallback ; même bascule simultanée Character/effets.
