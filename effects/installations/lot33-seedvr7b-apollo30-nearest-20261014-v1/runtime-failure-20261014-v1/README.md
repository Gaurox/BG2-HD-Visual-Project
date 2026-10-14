# Échec runtime — 2026-10-14 22:43:56–22:44:02

- Source : journal jeu, lignes35650–35749 ; extrait `last-session.log`, constat `analysis.json`. Captures utilisateur22:44:29/22:44:41 : mosaïque de tuiles.
- 22:44:02.091 : préparation97effets/5407backings/3428013696octets, NEAREST/cache64 réussie. Catalogue personnages préparé ensuite. Cela ne prouve aucune activation du rendu.
- 22:44:02.202 : `MH_CreateHook failed`, `Failed to install hooks`, `Uninstalling all hooks`, `Hook cleanup complete`. Aucun `LoadArea hook created`, aucun `All hooks installed successfully`.
- Premier appel défaillant identifié par l'ordre réel : `src/iee/hooks.cpp:5046` crée LoadArea ; RenderTexture n'est pas atteint. `src/iee/core/hooking.h:34` masque le statut MinHook exact.
- `dll_main.cpp` : retour d'échec → FinalizeState → CleanupHooks ; suppression des interceptions, libération packeffets et cataloguepersonnages. Le jeu continue avec ses textures HD installées mais sans adaptation du renderer ; lecture native des atlas incompatible, mosaïque cohérente avec les captures. Effets/personnages x4 non actifs sur cette session.
- Avertissement prologueRenderTexture déjà présent dans les sessions antérieures réussies ; ne pas l'identifier comme cause. Aucun manque de mémoire signalé ; augmentation du pack et temps de démarrage ne prouvent pas une panne mémoire ni une course EEex.
- Régression constatée après nouvelle DLL `5207E625...` ; source renderer modifiée uniquement pour le plafond CPU2→4Gio. Cause interne MinHook indéterminée : le journal ne distingue pas mémoire, cible non exécutable, trampoline non supporté, hook déjà créé, etc. Le processus est fermé au diagnostic, pas de mémoire live disponible.
- Reçu vérifié : transaction limitée DLL/INI/iee-assets/effects ; aucun fichier de carte géré, INI identique. Ne pas retraiter les cartes ni les33images pour cet incident.
- Tests précédents : préparation pack, filtre GPU/cache et minification personnages ; ils ne couvraient pas l'installation complète des hooks sous EEex.
- Étape de diagnostic utile : journaliser opération + nom/adresse cible + `MH_StatusToString` + octets/protections, puis reproduire le démarrage. Aucun fichier jeu modifié pendant cette analyse ; QA assets et release inchangées.
