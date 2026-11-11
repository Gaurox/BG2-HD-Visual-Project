# Lot 6 — accès en jeu

Lancer par InfinityLoader habituel. Numéros identiques aux planches du chat.

| Nº | Ressource | Accès |
|---|---|---|
| 1 | GMPCARBD | Nouvelle partie / création de personnage → bouton **Créer un groupe** ; écran de préparation/import du groupe. |
| 2 | GUWPKPC0 | En partie → fiche personnage → **Réformer le groupe** ; regarder le panneau du bas puis annuler. |
| 3 | GUIINVHB | Menu principal de campagne → **Multijoueur** ; écran de connexion. |
| 4 | GUICONNB | Multijoueur → **Créer une partie**, ou options/permissions de la session ; grand cadre vertical. |
| 5 | GUICONN1 | Dans le salon multijoueur en tant qu’hôte, cliquer le joueur affecté à un emplacement de personnage 2–6 ; ouvre le choix du joueur. |
| 6 | GUIDCX | Fiche d’un personnage humain éligible → **Double classe** ; ouvrir le choix puis **Retour**, sans terminer le jumelage. |
| 7 | GUIDLC | Bouton DLC conditionné à `e:IsTouchUI()` dans START_MAIN, UI.menu:7401 ; pas d’accès normal sur l’interface PC. Ne pas modifier la configuration pour ce test. |
| 8 | GUIMOVB | Menu principal de la campagne → **Options → Cinématiques**. |
| 9 | GUISMBM | Écran des trois campagnes → **Crédits**. |
| 10 | START | Choisir SoA, ToB ou Black Pits II : fond du menu principal de campagne, avant de charger une partie. |

Sources : UI.menu `IMPORTPARTY`, `WORLD_PICKPARTY`, `CONNECTION`, `CONNECTION_CREATE`,
`MP_PICKPLAYER`, `CHARGEN_DUALCLASS`, `START_DLC`, `MOVIES`, `CREDITS`, `START_MAIN`.
Le choix du joueur est conditionné à hôte local / emplacement différent du premier / salon avant partie.
Les boutons sont natifs ; ces dix traitements portent sur les fonds/cadres.
