"""Publish current installation pointers only after all installed-byte checks pass."""
from install import ROOT, OUT, load, save

v = load(OUT/'installation.json')
assert v['status'] == 'installed-offline-verified' and v['contracts'] == 33548
assert v['character_files_byte_identical'] and not v['qa_accepted']
p = ROOT/'effects/README.md'
s = p.read_text(encoding='utf-8')
old = 'Pack d’effets installé :'
if old not in s: old = "Pack d'effets installé :"
assert old in s
s = s.replace(old, '''Pack actif : [`lot64-7b-x4-nearest30-20261015-v1`](installations/lot64-7b-x4-nearest30-20261015-v1/installation.json).
161 ressources : 97 précédentes (RGBA/cycles identiques) +64 nouveaux effets7B x4/NEAREST/Apollo30 ; 226cycles natifs,228profils de ce lot. Taille monde/durée natives conservées ; 97carriers BAM (33anciens+64nouveaux), aucun VVC modifié.
Registrev3 : variantes ponctuelles SPFLESHS/SPMETSWA routées depuis l'owner natif ; CPU8Gio pour8208516864octets, GPU64. 33548contrats natifs toutes phases/modes sur candidat puis installation ; personnages NearestRGB-SilhouetteAlphaAA identiques par SHA256. Correction d'arrondi des seuils au rafraîchissement, essais30/60/120Hz et pause/reprise ; QA ingame64 et mesure de cadence réelle encore attendues. [Recette](../pipeline/recipes/effects-lot64-install-20261015-v1/README.md), [CLUA et variantes](installations/lot64-7b-x4-nearest30-20261015-v1/CLUA.md).

Installation précédente du lot33 :''', 1)
s = s.replace('Renderer diagnostique courant :', 'Renderer diagnostique précédent, trace SPIMPFR conservée :')
s = s.replace('Chargeur CPU borné à4Gio (packretimed3.51Gio), cache GPU64 inchangé ; profil personnages conservé octet pour octet.',
              'Historique lot33 : plafond CPU4Gio ; installation lot64 ci-dessus portée à8Gio, cache GPU64 et profil personnages conservés.')
s = s.replace('Aucune installation ni QA acquise ; profil personnages préservé.',
              'Lot64 installé par le reçu actif ci-dessus ; aucune QA ingame ni intégration release déduite ; profil personnages préservé.')
p.write_text(s, encoding='utf-8')
p = ROOT/'pipeline/PROBLEMES_A_RESOUDRE.md';s = p.read_text(encoding='utf-8')
s = s.replace('Scheduler non corrigé ; aucune nouvelle interpolation nécessaire pour ce symptôme.',
              'Correctif installé avec lot64 : seuil intermédiaire arrondi au rafraîchissement observé, clamp au slot natif, phase monotone et pause/reprise conservée ; tests30/60/120Hz réussis. Nouvelle mesure ingame SPIMPFR encore attendue ; phases initiales0–1 non corrigées par ce changement. Aucune nouvelle interpolation nécessaire pour ce symptôme.')
p.write_text(s, encoding='utf-8')
p = ROOT/'engine/InfinityEngine-Enhancer/source-patchee/README.md';s=p.read_text(encoding='utf-8')
s=s.replace('registre multi-resref v1/v2, scopes projectile + VVC', 'registre multi-resref v1/v2/v3 (profils ponctuels/bouclés), scopes projectile + VVC')
p.write_text(s, encoding='utf-8')
(OUT/'README.md').write_text('''# Lot64 — installation locale

- Autorisation : installer64 effets SeedVR7B x4/NEAREST/30FPS, taille native ; personnages avec AA actuel ; lancement et contrôle du jeu exclusivement utilisateur.
- `installation.json` : reçu final après validation transactionnelle et chargeur natif sur fichiers installés.161 ressources cumulées ;97 anciennes ressources RGBA/cycles identiques ;97carriers BAM ; cartes/VVC/shaders personnages non modifiés.
- `before.json`, `backups/*/renderer-install-receipt.json` : état antérieur et restauration transactionnelle ; aucune validation ingame déduite.
- `ctest.log` :7/7 tests ciblés réussis ;19 tests Python installer/compositeur réussis. `native-profile-offsets.json` : vérification des offsets owner dans l'exécutable exact.
- `runtime-contracts.tsv`, `candidate-native-loader.log`, `installed-native-loader.log` :33548 contrats (20028 nouveaux64), tous slots/phases/cycles/profils/casse/dimensions/backings ; filtre NEAREST et cacheGPU64.
- [CLUA](CLUA.md) :64 commandes principales et tous contrôleurs natifs alternatifs ; `clua.json` relie chaque BAM au VVC réel.
- Recette : `pipeline/recipes/effects-lot64-install-20261015-v1/README.md`. QA64 et cadence réellement présentée à confirmer par l'utilisateur ; release non modifiée.
''', encoding='utf-8')
save(OUT/'test-summary.json', {'cpp_targeted_passed':7, 'python_installer_composer_passed':19,
    'native_contracts_candidate':33548, 'native_contracts_installed':33548,
    'new_assets':64, 'new_native_cycles':226, 'new_profiles':228, 'new_asset_contracts':20028,
    'character_profile_byte_identical':True, 'native_geometry_and_durations_preserved':True,
    'game_controlled_by_agent':False, 'ingame_validation':'pending-user'})
print('Installation pointers updated; QA and release unchanged.')
