# Contrat des profils shader

Autorité unique des valeurs, bornes, défauts, composants et recettes :
`shader-suite-contract-v1.json`.

- `shader-suite-contract-v1.schema.json` décrit la structure sans recopier de valeur métier.
- `ENGINE/tools/shader_suite_profile.py` valide l'autorité et matérialise un profil.
- Toute représentation C++, GLSL ou INI doit être générée ou vérifiée contre cette autorité.
- Modifier le numéro de contrat pour tout changement incompatible ; ne pas réécrire une preuve de run scellée.
