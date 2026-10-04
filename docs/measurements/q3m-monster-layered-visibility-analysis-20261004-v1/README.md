# Monster_layered — visibilité, session 2026-10-04 19:40:54

- Preuve : `analysis.json` (hashes CRE/ITM, paramètres effets, lignes log).
- Volo `QLYR2100` : clone `ENDVOLO`; état=0, translucency=0; effets EFFv2 268 + **271**, timing=1 (permanent), mode=0. Opcode 271 masque avatar+cercle et bloque actions ordinaires. Aucun rendu UVOL/2100 dans la session. Erreur de fixture : retirer scripts/dialogue n’a pas retiré l’effet finaliste.
- Alternative stock : `C:CreateCreature("SARVOLO")`; animation=0x2100, état=0, translucency=0, aucun effet CRE. Scripts natifs conservés; visibilité ingame de cette alternative non encore constatée.
- Ogre mage `OGREMA01` : état=0, translucency=0, aucun effet CRE; **MAGE01** équipé en index slot CRE 5, effet opcode **20** (invisibilité). MAGE3 lance ses sorts natifs; pas de sort d’invisibilité mémorisé nécessaire. Q3m confirmé 19:41:34.643 : replacements=1, layers=2, incomplete=false. Premier passage cold lookup 33 ms avant : retour natif, pas panne persistante.
- Les six autres IDs du lot ont un témoin Q3m complet dans la session; Volo doit encore être testé avec un consommateur visible. Aucune QA famille déduite.
- Périmètre : lecture jeu seulement; aucun asset/DLL/CRE installé modifié; run précédent intact.
- Références : https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op271 ; https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op20
