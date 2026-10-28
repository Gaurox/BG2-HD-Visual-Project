# FIREBAT V3 — preuve runtime, 2026-10-28

- Session : démarrage09:29:08, test09:29:34–35 (horodatages du log). `runtime.log` figé ; `evidence.txt` extraits numérotés ; `summary.json` SHA et mesures.
- DLL active SHA2370067272AC3CA909D86D05CF90656A24A5C0E84719049DF4817DC54DB67E7B = V3 installée.
- **Vol FIREBAT x4/interpolé confirmé au dessin final** : 14 `EFX_BOUND_PHASE`, phases2–15, backings25–38 distincts ; canevas69×78→texture276×312, source69×65 conservée. Phases impaires3/5/7/9/11/13/15 effectivement dessinées. Cible30/1 ; intervalle médian33,359ms (31,891–34,310ms).
- Masque : étape0x20 (occlusion liée) ; aucun `EFX_MASK_FALLBACK FIREBAT` ni étape0x40 dans cette session. Le repli provoqué par le mélange halo/vol observé en V2 n'est plus observé.
- Les rejets FIREBAT24×16 concernent le passage distinct du halo ; ils ne contredisent pas les preuves finales du vol69×78. Ne pas forcer ces surfaces à prendre la texture du projectile.
- SPSMPUFF : phases finales0,2–11, x4, cible30/1, opacité native127 ; SPFIREPI/SPFLAMES : étapes0x8 et0x20. Des étapes0x10 (indisponibilités transitoires au chargement) existent pour ces ressources ; ne pas annoncer zéro fallback universel ni une couverture de chaque image.
- Décision : correction **technique du vol confirmée pour le test**. Utilisateur indique test refait ; pas de nouvelle appréciation visuelle explicite V3. Pas de QA générale des124PRO ni de release. Lecture seule du jeu, aucune image retraitée.
