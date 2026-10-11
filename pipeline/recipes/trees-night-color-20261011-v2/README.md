# Arbres T002/T003 — extension du correctif nocturne T005

- Demande utilisateur 2026-10-11 : correctif T005 « parfait » ; appliquer le même à deux autres arbres du screenshot `E:/Steam/userdata/5536307/760/remote/257350/screenshots/20261011185043_1.jpg`.
- Identification silhouettes : T002 = longues branches suspendues au-dessus de l'escalier ; T003 = grand tronc à droite. Ancres AR1400 : T0024556,203 / T0034815,259 ; AR1404 : T0024556,202 / T0034816,261 (`animations/index/occurrences.csv`).
- Delta : whitelist correction nocturne T005 → T002/T003/T005 ; log `AREA_TREE_NIGHT_COLOR` une fois par resref. Mêmes gains R×0.60/G×0.55/B×0.85 après transfert palette natif, même arrondi ; T005 validé inchangé.
- Gate identique : WED vivant AR1400+AR1400N ou AR1404+AR1404. Jour, T001/T004, état inconnu, alpha/centres/cycles et RGB source SeedVR inchangés.
- Parent exact : `animations/batches/1400t005-night-color-20261011-v1/.work/runtime-src`, DLL `275a3a3518f85d79909b2dc5560f5465525da0bf64af1c9eaf456411ffe86bb4` ; delta trois fichiers seulement, registre eau identique.
- Reproduction : `python pipeline/recipes/trees-night-color-20261011-v2/build_renderer.py` ; installation `python pipeline/recipes/trees-night-color-20261011-v2/install.py --run`. Jeu/InfinityLoader fermés requis.
- Autorités : `runtime.json`, `installation.json`, `runtime-delta.patch`, `build.log` ; restauration via reçu renderer. DLL seule modifiée en contenu ; INI et fichiers AR1400/AR1404/AR3000/vérou de packs conservés.
- Tests ciblés : T002/T003 même LUT/empreinte que T005, retour jour exact, T001/T004 exclus, état WED/alpha. Nouvelle teinte T002/T003 à vérifier ingame ; QA T005 acquise sur réglage précédent et conservée. Aucune release ni validation de visite exhaustive des occurrences.

## Validation finale

- Cinq arbres acceptés explicitement en l'état installé : « c'est tout bon ! valide ces assets en l'etat ! MAJ le suivi et committe ! » (2026-10-11).
- `accept.py` : vérifie DLL/INI/textures/registries installés ; fige les deux packs sans changer les octets ; écrit cinq wrappers/QA/sélections et index `validé-x4`/suivi alpha. Autorité `acceptance.json` ; contrat renderer/source SHA et politique nocturne liés à chaque wrapper final.
- Pack figé `animations/packs-par-zone/trees-seedvr-native-lighting-accepted-20261011-v1/{AR1400,AR1404}/` ; 5 assets/2 cartes/10 occurrences, aucune visite exhaustive déduite. Aucun fichier jeu ni release modifié par l'acceptation.
