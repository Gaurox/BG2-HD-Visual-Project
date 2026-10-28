# V10 — Mur de brouillard, alias alpha natif existant

- Installé,transparenceingame àretester ; [analyse etpreuvedecorrespondance](../../../../projectiles/analysis/mur-brouillard-alpha-20261028-v1/README.md). DLL SHA B7F4C9DAB3CACE1DEA5023521D464D0AA4C9EC60E3A292A7184EDE2D38212B86 ;reçu `installation.json`.
- RouteBDWOFOGA→X58WFOG uniquementFXnormal ;Blended gardeBDWOFOGA.2683backings source+alias vérifiés (1342+1341),1344pairesRGB/géométrie/centres etprofils sémantiquementidentiques ; la différence d’indices provient deladéduplicationalpha.
- `tests.log` :3/3suites passantes ;probe2720contrats natifs passants avecbudgetmetadata32Mio inchangé. Aucunepreuveingame déduite decescontrôles.
- Aucun fichierimage/carrier/PRO/métadonnée/INI/shader/personnage/release modifié ;seuleDLLremplacée. Source : `core/effect_texture_alias.h`, `core/effect_secondary_scope.h`, `hooks.cpp` (tracealias),testsurfaceowner.
- `pipeline/recipes/projectiles-wall-fog-alpha-20261028-v10/install.py prepare|install` déjàexécuté ;nepasécraserlesreçus. `backups/` contient latransactionDLL/INI pourrestaurerV9.
- Rejouer4SPIN693pourtraces finales manquantes,puis2OHBWFOGpourtransparence ;1/3acquispourcomposantsobservés.
