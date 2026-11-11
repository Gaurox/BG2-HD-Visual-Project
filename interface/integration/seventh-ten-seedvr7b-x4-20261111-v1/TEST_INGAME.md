# Accès du lot 7 — usage non établi

Audit : `route-audit.json`. Les dix resrefs n'ont aucune référence statique dans UI.menu actif,
ni occurrence de leur nom exact dans les exécutables à la racine du jeu. Cela ne prouve pas
l'absence d'une construction dynamique du nom ; aucune route actuelle n'est établie.

Les titres des planches décrivaient les visuels, pas un accès ingame confirmé. Ne pas annoncer
qu'un écran actuel affiche une de ces variantes à partir de sa seule ressemblance.

| Nº | Ressource | Route actuelle |
|---|---|---|
| 1 | GMPCARBB | Ancien fond de groupe ; accès non établi. |
| 2–4 | GMWMSGA0 / GMWMSGA9 / GMWMSGB0 | Anciens panneaux de dialogue ; accès non établi. |
| 5 | GUICGPR | Variante de création ; accès non établi. |
| 6 | GUIAPBR | Variante personnage ; accès non établi. |
| 7 | GUICHISE | Variante histoire ; accès non établi. |
| 8 | GUICPORB | Variante portrait ; accès non établi. |
| 9–10 | GUICUSTP / GUICUSTX | Variantes personnalisation ; accès non établi. |

Interfaces actives proches déjà traitées, distinctes du lot7 :
- Nouvelle partie → création : GUICGB.
- En partie → fiche personnage → Personnaliser : GUICUSTB.
- Personnaliser → Biographie : GUICHISD.
- Personnaliser → Apparence : GUIAPB.

Installation du lot7 : textures x4 disponibles sous le flag existant EnableGameplayMenusX4.
Aucun routage UI.menu, écran, logique Lua ou contrôle modifié pour forcer les variantes.
QA retenue : validation des planches seulement ; observation ingame à établir séparément.
