# BDFORCEW — WED trop rogné, correctif installé

- Déclencheur : capture utilisateur `E:/Steam/userdata/5536307/760/remote/257350/screenshots/20261010163527_1.jpg`, extrémité de la seconde occurrence OH8100 trop coupée ; OHHPORT explicitement validé.
- Centres/positions inchangés (frames et logs avant/après : `(2286,820)`, `(2350,866)` ; final_draw `(302,3)`, `(366,49)`). Cause : v1 garde4px x4 + feather16px x4 sur masque WED ; perte de lumière sur le bout du second faisceau.
- Correction v2 : garde4 conservée contre fuite hors masque ; feather16→4px x4 ; transfert natif R/G/B exact. Alpha SplineFit1/frames/cycles/centres inchangés ; aucun pack map réécrit.
- Scope : même branche BDFORCEW/AreaRegistry/dither0/transfert binaire. Sources héritées de la DLL installée `c1bc43f8070b5b47115b54f786891573f9c7c3827036e54faaff5edee9d9c13e` ; seuls helper de coverage + test ciblé changés.
- Comparaison GPU sur WED180/frame50/occurrence2 : perte lumineuse due au feather WED 4.15→1.91% ; cœur p95 7.03→3.33%. Simulation ≠ QA ingame ; aucun pixel natif masqué révélé. Artefacts : `animations/batches/bdforcew-wed-edge-20261010-v2/edge-diagnosis.json`, `BDFORCEW-instance-{1,2}-coverage-comparison.png`.
- Validation : C++ tests ciblés ; coverage réelle byte-identique à la simulation GPU sur les deux occurrences ; shader et headers générés eau/version identiques à v1.
- Installation : `animations/batches/bdforcew-wed-edge-20261010-v2/installation.json` → reçu/backup renderer ; DLL `66f6a4f051597f02e84cd9902cb98851954d677b30fcf72385a5e01a250dd896` ; INI exact ; 393frames + 2registries AR0811/OH8100 exacts avant/après ; BDFORCEW en attente de retest utilisateur ; release hors périmètre.
- OHHPORT : décision immuable `animations/index/qa-decisions/OHHPORT/2026-10-10-accepted-ohhport-xbr-apo8-backgroundfix-v1.json` ; bytes installés conservés.
