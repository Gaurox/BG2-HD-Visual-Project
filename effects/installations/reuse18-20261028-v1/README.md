# Réemplois18 —2026-10-28

- Demande : lier9effets+5animations existants, rapprocher4alias déjà installés ; aucune inférence ni nouvelle interpolation.
- Installé hors session ; jeu/InfinityLoader fermés ;18lignes de suivi actualisées,36descripteurs de réemploi scellés. QA des nouvelles liaisons non déduite ; aucune sélection/QA/release historique modifiée.
- `installation.json`, `transaction.json`, `plan.json`, `before.json`, `bindings.json`, `target-baselines.json` ; `tracking-verification.json` :18lignes seules changées,18checks ciblés passent.
- Actif537RESREF/62099backings,139748contrats natifs testés sur candidat puis jeu ; metadata26692163octets<32Mio ; manifest SHA256 `3477E7211680CF1CF7F067A471A003EBC0A2ECAA4C994136ED257A3AA59A872A`.
-522anciennes ressources/blocs et59699backings conservés ; ajout15ressources=14liaisons+1compagnon normal.2429cibles copiées/hashées ; sauvegardes sous `before/`, transaction restaurable avec le helper. DLL/INI/shaders/catalogue personnages et tous registres AREA préservés par hash.
-9effets clonés depuis leurs ressources installées : RGB/alpha/cycles/tables identiques.5animations depuis les packs sélectionnés : placement sans redimensionnement sur canevas transparent commun ; pixels RGBA et positions monde exacts (`checks/*.json`), sources indexées/palettes/cycles conservés dans carriers.
- SPARMOUR : consommateurs lumineux conservés ; SPARM2 normal rerouté par référence BAM seule vers `R18ARMN`. Conversion d'encodage depuis OHNVIS1 prémultiplié, alpha identique ; re-prémultiplication diffère≤1octet. Aucun upscale/lissage.
- BDFORCEW : décalage spécifique du décor OH8100 non propagé aux appels VVC ; ancrage BAM natif conservé.
- Suivi : `effects/ressources/<RESREF>/runs/<ref>-reuse-{spatial,interpolation}-20261028-v1/` référence les productions existantes et l'installation, pas une génération fictive. États `produced`,installation `installed`,QA/release inchangées. Les4déjà installés n'ont pas eu leurs pixels remplacés.
- Reste165RESREF non commencés/162ensembles visuels distincts dans l'inventaire élargi (pas162sorts). Audit183 historique conservé ;3paires internes toujours à produire une fois chacune.

| Liaison | Source réutilisée |
|---|---|
|SPARMOUR|OHNVIS1|
|SPFDETH3|SPFDEATH|
|SPFIRIMP|FIREH|
|SPFLMSTI|FLMSTRK|
|SPHLHI01|SPHLEFT|
|SPHLHI02|SPHRIGHT|
|SPICEIMP|COLDH|
|SPILUSIO|SPILLUS|
|SPSDRBUR|SPSDBUR|
|BDFORCEW/OHDLPORT/OHHNECR/OHRSGATE/SPDIMNDR|Sélections animations homonymes, détails `checks/`|
|BURNHAND/SPIPLARI/SPPRISM3/SPPRISMT|Déjà installés ; suivi uniquement|

[14CLUA](CLUA.md). Recette `pipeline/recipes/effects-reuse18-20261028-v1/install.py` ; ne pas relancer sur cette installation finale. Logs `candidate-native-loader.log`, `installed-native-loader.log` : catalogue seulement,zéro lecture RGBA par le probe ; intégrité des cibles vérifiée par transaction. Jeu non lancé ; nouveaux chemins à tester visuellement.
