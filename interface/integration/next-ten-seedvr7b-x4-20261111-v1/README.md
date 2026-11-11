# Dix assets UI — SeedVR2 7B x4 installés

- Ressources : `INVSTATS`, `GUIINVHI`, `GUIMGX`, `GUIMGB`, `GUIPRB`, `GUIMGCP`, `GUICUSTB`, `GUICHISD`, `GUITUTB`, `GUILOAD`.
- Sorties exactes retenues : `../../experiments/next-ten-seedvr7b-x4-20261111-v1/selected-20261111-v1.json` ; aucune nouvelle inférence.
- État : installé pour QA ingame, pas encore accepté en jeu ; release inchangée.
- Reçu : `installed-20261111-v1.json` ; sauvegarde exacte : `backups/20261111T003037Z/receipt.json`.
- 16 fichiers : DLL, INI (activation déjà présente), 14 atlas.

## Contrat

- Pages115/116/125/126/138/139/140/148/149/150/154/168/169/181.
- MOS181 : base installée contenant sélecteur et inventaire validés ; seuls les blocs INVSTATS changent.
- MOS140 : réutilise l’entrée historique `HUD-MOS0140`, désormais aussi sous `EnableGameplayMenusX4`. Hors GUILOAD : DXT5 natif x4 sans perte ; anciens boutons HD non réactivés.
- Autres nouvelles pages : fallback DXT5 natif x4 sans perte, puis copie des seuls rectangles des dix compositions.
- Aucun BAM/MOS/PVRZ natif modifié ; géométrie logique x1 ; blocs non sélectionnés byte-identiques à la base.
- `assets.json` : source FNV1a/SHA256, rectangles, baseline et résultat.

## Vérifications

- 14 pages : rectangles des dix ressources disjoints ; INVSTATS n’empiète pas sur les blocs INVENTOR validés.
- Fallbacks décodés identiques au nearest x4 natif ; hors rectangles sélectionnés conservé exactement.
- Test runtime : 22 pages gameplay / 7 sélecteur ; isolation, hash/format/dimensions invalides, désactivation et INI.
- CTest `iee_tests` : passé.
- Jeu/InfinityLoader fermés, copie transactionnelle ; tous les fichiers installés et anciennes pages non remplacées vérifiés par SHA256.

## Test utilisateur

Lancer par InfinityLoader habituel, puis vérifier détails/statistiques inventaire, descriptions et
capacités d’objets, livres mage/prêtre, contingences, personnalisation/biographie, sous-menus
options et chargement. Boutons/icônes superposés restent natifs.

## Retour au lot précédent — jeu/InfinityLoader fermés

```powershell
python -B interface/integration/next-ten-seedvr7b-x4-20261111-v1/install.py --restore interface/integration/next-ten-seedvr7b-x4-20261111-v1/backups/20261111T003037Z/receipt.json
```

Refus si les fichiers installés ont changé depuis le reçu. Restaure DLL/page181/HUD140 antérieurs
et retire seulement les nouveaux fichiers absents avant ce lot. Les quatre premiers menus et le
complément du journal sont conservés.

Validation utilisateur 2026-11-11 : « validé » ; `qa-accepted-20261111-v1.json`. Dix assets acceptés sur le rendu observé, sans extrapoler tous les états/variantes.
