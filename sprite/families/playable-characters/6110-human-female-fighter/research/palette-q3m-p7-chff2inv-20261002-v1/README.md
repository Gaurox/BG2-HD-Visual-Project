# P7 — corps cuir CHFF2INV Q3m K6 x2

- Périmètre : guerrière humaine `0x6110`, corps cuir `CHFF2INV` seul ; aucune couche équipement supplémentaire.
- Source vanilla vérifiée contre KEY/GUIIcon courant : `source-verification.json`, SHA `d7f3e636…e2a23672` ; deux moitiés 66×64/65×75, centres −24,−16/−25,0 ; cycle `[0,0,1,1]`.
- Recette héritée : ReboutCX P12 x4 float → BOX x2 → Q3m K6 (REF/DEFAULT/LATIN1–4), sans tramage ; 12 cibles, ≈12,24 s total.
- Contrôles producteur : fuite de classe 0, spéciaux inchangés, masque exact ; 36 décodages RGBA conformes à l'oracle indépendant, répétition GPU delta0. `result.json` + deux plans NPZ.
- Aperçus : `comparison.png` natif nearest/Q3m sur même palette DEFAULT et placement ; aucun verdict visuel ingame déduit.
- [Pilote installé](../palette-q3m-p7-chff2inv-ingame-20261002-v1/README.md) ; QA utilisateur en attente.
- Reproduction : nouveau dossier frère, `render.py` avec `config://chainner_python` ; source/modèle/scalepix épinglés par hashes du résultat. Aucune réécriture de run historique.
