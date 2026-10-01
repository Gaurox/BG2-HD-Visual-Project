# P4 — sonde de zoom et baseline x4 Nearest, 2026-10-01

- P3 : validée intégralement par l'utilisateur dans le chat ; anciennes preuves non réécrites.
- Runtime : `pipeline/runtime/manifests/iee-sprite-p4-probe-20261001-v1.json`.
- Baseline : catalogue commun `0x6100/0x6110` x4, SHA `637DBC809EAD7A9AD2A771BB760F5C0042109C5A4B6A19BE68A75CC41D50E0B8` ; Nearest.
- Installation P4 : DLL + `EnableCreatureSpriteP4Probe=true` + chemin CSV ; catalogue/shards/paramètres visuels inchangés. Reçu actif adopte ce runtime. Sauvegarde DLL/INI/reçu sous `ingame-probe/` ; historique intact.
- Sonde : aucune entrée souris/clavier, aucun nouvel offset/hook, aucun changement GL ; points de diagnostic ajoutés aux callbacks existants. Désactivée par défaut.
- CSV distinct par lancement dans `captures/p4-<UTC>-<microseconds>.csv`, flush toutes les ~1 s + arrêt normal, maximum 7 200 lignes ; absence de frame/viewport valide = données indisponibles, jamais zoom inventé.
- Zoom : `GL_VIEWPORT / viewWorldW,H` au premier dessin d'une texture HD reconnue de chaque frame ; FBO/échelle/MIN/MAG enregistrés. Transitions zoom/taille/FBO marquées `view_mixed` ; absence de monde rejetée.
- CPU : appels composites `0x6110` seulement, reconstruction/cache pixels, upload/setup GL ; durées imbriquées, **ne pas additionner**. Inclut soumission/stalls pilote, pas durée GPU. Chargement metadata à froid en amont hors timer composite.
- Mémoire : working set + private commit du processus entier. Octets uploadés = trafic RGBA réussi, pas VRAM résidente. FPS/p95 par fenêtre ; aucun p95 global reconstitué.
- Contrôles : `verification.json` ; première capture ingame attendue. Analyse uniquement après signal utilisateur, puis entrée CSV explicitement désignée ; jamais suivi/pilotage automatique.

## Manipulations utilisateur — première session

Même taille de fenêtre, même scène et personnage féminin `0x6110` utilisé en P3 (équipement visible). Jeu dépausé, aucun menu ouvert.

1. Lancer normalement, charger la sauvegarde ; attendre 10 s.
2. Zoom habituel, caméra fixe, personnage immobile : 20 s.
3. Dézoomer jusqu'à la butée minimum ; caméra fixe/personnage immobile : 20 s.
4. Zoomer jusqu'à la butée maximum ; caméra fixe/personnage immobile : 20 s.
5. Revenir au zoom habituel ; faire marcher le personnage visible, quelques allers-retours : 20 s.
6. Personnage immobile visible ; déplacer doucement la caméra dans les deux sens : 20 s.
7. Quitter normalement jeu + InfinityLoader, prévenir l'agent. Si un palier est raté, signaler lequel ; pas de capture d'écran ou console nécessaire.

## Commandes agent

Jeu/InfinityLoader fermés pour Install/Restore ; Verify en lecture seule.

```powershell
& pipeline/scripts/Set-Sprite-P4-Probe.ps1 -Mode Install
& pipeline/scripts/Set-Sprite-P4-Probe.ps1 -Mode Verify
& pipeline/scripts/Set-Sprite-P4-Probe.ps1 -Mode Restore

# Après signal utilisateur seulement ; nouvelle sortie, jamais écrasement.
$p4Python = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
& $p4Python -B pipeline/scripts/palette_p4_probe.py --input '<CSV session>' --output '<nouvelle analyse>.json'
```

Build/tests isolés : `build/sprite-p4-probe-20261001-v1/cmake`, VS2019 x64, dépendances locales épinglées P2 ; cibles DLL, `iee_tests`, `iee_palette_fraction_tests`, `iee_sprite_p4_probe_tests`. Lecteur : `python -B pipeline/tests/test_palette_p4_probe.py -v`. Aucun asset/release reconstruit.
