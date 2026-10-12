# Registre eau — cohérence des patches renderer

- Autorité : `pipeline/water/route2-registry-current.json`, registre référencé + SHA-256 normalisé LF.
- Récidive AR3000 2026-10-13 : DLL `6E0FDE1C…` du correctif effets ; cache CMake explicitement v2/1 entrée malgré l'autorité v3/188. Les 16 pages RGB validées étaient intactes.
- `generate_water_route2_registry.py resolve_input` : compare aussi les inputs explicites/cachés ; drift refusé par défaut, à configuration **et** génération.
- Cache ancien : `cmake -S <source> -B <build> -U IEE_WATER_ROUTE2_REGISTRY` ; l'input vide suit l'autorité courante.
- Changement volontaire du registre eau : `IEE_WATER_ROUTE2_ALLOW_REGISTRY_CHANGE=ON` / `--allow-registry-change` ; installation eau avec le registre explicitement déclaré. Cette option ne dispense pas du contrôle DLL/registre.
- PE : export `IEE_WaterRegistryBuildContract()` référence `IEE_WATER_ROUTE2_V1:<sha256_lf>:<version>:<entries>` ; conservé avec optimisation, vérifié sans charger la DLL.
- `install_renderer_candidate.py` : installation refusée avant sauvegarde/mutation si l'empreinte ne correspond pas à l'autorité courante ; restaurations historiques restent explicites.
- `Install-WaterRuntime.ps1` : DLL candidate comparée au registre déclaré ; changement de hash de la DLL live accepté seulement si son empreinte prouve le même registre courant.
- Vérification : `python -B tools/generate_water_route2_registry.py --check-dll <dll>`.
- Régressions : `pipeline/tests/test_water_registry_default.py`, `test_renderer_candidate_transaction.py` ; cache v2 refusé, DLL non identifiée/v2 refusée avant écriture.
- Récupération installée : `pipeline/water/manifests/ar3000-runtime-contract-recovery-20261013-v2.json` ; 21 tests Python + 3 suites natives ; [QA utilisateur AR3000](../../../../pipeline/water/manifests/ar3000-active-area-recovery-user-qa-20261013-v1.json).

## Carte chargée avant le suivi runtime

- Symptôme complémentaire : session `2026-10-13 01:34:47`, registre v3 `188/188` valide, aucun `Loaded WED`, dessins eau `wed=-` ; registre restauré seul insuffisant, tuiles toujours visibles selon utilisateur.
- `AppContext::infGame` provenait exclusivement de `LoadArea`. Un chargement non observé laisse le suivi eau vide ; le rafraîchissement render existant retourne immédiatement sans propriétaire.
- `hooks.cpp detour_game_area_render` : si propriétaire absent et hors chargement natif, lire `CGameArea::m_pGame` ; `game/active_area_runtime.h` exige aller-retour propriétaire → carte active chargée → objet rendu exact. Publication atomique sans écraser `LoadArea` concurrent ; préparation WED CPU avant rendu, upload GL dans le passage natif existant.
- Résolveur visible/master/fallback existant conservé ; offsets du manifeste + layouts x64 curés ; aucun champ moteur/sauvegarde modifié.
- `tests/iee_tests.cpp test_rendered_area_owner_recovery` : carte déjà chargée sans callback, carte inactive, propriétaire absent/illisible, chargement incomplet, transition visible, fallback master.
- QA positive : session `2026-10-13 01:42:32`, `Loaded WED AR3000`, masque `0x1E`, `nativeAlpha=128 drawAlpha=160`, slots 1–4 temporels 30 FPS ; utilisateur « Elles ont disparu ». Cette session suit `LoadArea` normalement ; la branche de récupération est couverte par les tests natifs, sans trace ingame de son déclenchement.
