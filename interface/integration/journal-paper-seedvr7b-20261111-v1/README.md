# Journal — feuille QUESTBG 7B x4

- Constat : premier lot traitait `QUESTBAK` uniquement ; feuille superposée `QUESTBG` restée native.
- Capture utilisateur en mode Quêtes. Dans `UI.menu`, boutons notes (`PAPERBUT`) activés seulement en mode Journal/édition ; bouton événements récents commenté nativement, bug20368.
- Audit : `../../analysis/journal-controls-20261111-v1/` ; aucune intersection des premières modifications avec `QUESTBG`, `XBUTT`, `PARROW`, `PCHEV`, `PAPERBUT`.
- Correction : 2 frames complètes `QUESTBG`, SeedVR2 7B x4 LAB, seed959948902156062 ; même pipeline que les quatre fonds retenus ; alpha natif nearest x4 séparé.
- Sorties/workflows : `../../experiments/journal-paper-seedvr7b-20261111-v1/`.
- Patch seulement pages254/255 ; page254 conserve exactement les autres blocs du premier lot, dont `QUESTBAK`.
- Page255 : fallback natif x4 sans recompression hors rectangles feuille ; nouvelle entrée runtime au flag existant `EnableGameplayMenusX4`.
- 9 pages gameplay / 7 sélecteur : test format/taille/hash/isolation réussi. 7 autres fichiers d’atlas du lot initial vérifiés inchangés.
- Reçu : `installed-20261111-v1.json` ; sauvegarde : `backups/20261111T000047Z/receipt.json`.
- Trois autres menus : retour utilisateur positif enregistré dans `../four-menus-seedvr7b-20261111-v1/qa-three-menus-20261111-v1.json`.
- Journal à retester : onglets Quêtes puis Journal, boutons notes, croix et flèches ; pas de nouvelle QA ingame déduite.

Retour au lot précédent, jeu/InfinityLoader fermés :

```powershell
python -B interface/integration/journal-paper-seedvr7b-20261111-v1/install.py --restore interface/integration/journal-paper-seedvr7b-20261111-v1/backups/20261111T000047Z/receipt.json
```

Restaure DLL/page254, retire page255 ajoutée ; garde les quatre fonds précédents. Pour restaurer
ensuite l’état antérieur aux quatre fonds, utiliser leur reçu après ce retour intermédiaire.

Validation utilisateur 2026-11-11 : « finalement c’est ok » ; `qa-accepted-20261111-v1.json`. Journal accepté sur le rendu observé, release indépendante.
