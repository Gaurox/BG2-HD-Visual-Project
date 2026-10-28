# V14 — placement de SPMAGMIS sur canevas variable

- [Reçu actif](installation.json), [tests5/5](tests.log), [état précédent](before.json), [preuve et contrôle restant](../../../../projectiles/analysis/masque-capture-v14-20261028-v1/README.md).
- Source64×64 contenue ày7 danspack64×78 réutilisée enmémoire ; projection sur canevas natif réel64×78/88 avec bornes strictes,clécacheincluantcrop. Halo24×16 etcompositionsunsupported restent natifs. Masque parFX conservé depuisV12 ; aucun changement de WED/PRO/images/mouvement.
- Delta depuisV13 : DLL seule ;INItraceetQAfilesinchangés.5suitesCPU/GPU passantes,1048contrats chargeur. Acceptation visuelleV13 conservée dans son périmètre ; nouveau renduHDV14 enattente de contrôle.
- Après prochain tir : sauvegarder la session puis désactiver seulementla trace,jeu/loader arrêtés ; garderV14.
