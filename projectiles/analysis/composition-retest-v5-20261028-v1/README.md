# Crâne/orbe V5 — preuve runtime ciblée

- Session28octobre14:17, DLLV5 SHA36541C5F212077AD247658DC60CBC6998D4594414D9E4028CDCA4F8DACE80CF5. `runtime-session.log` figé ; mesures et SHA dans `verification.json`.
- SKLT :15dessins finauxx4,phases0/2–15 dont7impaires,texture96×208 pour canevas24×52,source24×24. Intervalles des phases successives32,738–33,858ms,médiane33,223ms ; cible30/1.
- SPCHRORB :16dessins finauxx4,phases2–17 dont8impaires,canevas57×59→228×236 puis géométrie variable respectée ; source29×27 initiale,offset13,0. Intervalles32,298–33,832ms,médiane33,376ms ; cible30/1.
- Les deux : `layers=2 nativePrefix=true nativeOpacity=255`, aucun rejet composition/géométrie ni repli masque observé. Le blocage du volHD des surfaces composées n'est plus observé sur ce test. Le préfixe, dont les ombres, conserve ses pixels natifs ; seule la dernière couche utilise les images HD existantes.
- Extension effective : fragmentsSKLH aussi résolus/timeline0x4,bindHD0x8 etmasque0x20. Présence d'un chargement transitoire0x10 ; pas de mesure finale par phaseSKLH, ne pas déduire tous les dessins HD ni l'acceptation de tous les fragments.
- Décision : preuve technique ciblée acquise ; utilisateur demande lecture des logs, aucune acceptation visuelle V5 explicite déduite. TSKULLNP reste opportunité statique non testée. Pas de validation générale124/243, aucune release/image/installation modifiée pendant cette lecture.
