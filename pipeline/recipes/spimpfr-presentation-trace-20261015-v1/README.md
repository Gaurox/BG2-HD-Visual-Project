# SPIMPFR — mesure effective de la cadence, 2026-10-15

- Demande : logs pour contrôler les30FPS ingame sans répétitions anormales ; l'utilisateur seul lance/contrôle le jeu.
- Aucun changement de scheduler, pack, BAM, dimensions, filtre, shader ou antialiasing personnages. DLL diagnostique +INI identique.
- `core/effect_presentation_trace.h` : buffer render-thread sans allocation/I/O/GLreadback ; SPIMPFR uniquement ;8occurrences/processus,2048swaps/occurrence. Identité instance+génération+séquence ; nouvelle capture après fin/réutilisation de pointeur/recul de slot. Dépassement explicite => résultat incomplet.
- Owner observé dans VVC/ProjectileBAM ; draw observé après le dernier choix de remplacement/masquage et après retour du RenderTexture natif, avant restauration de texture ; inclut les fallbacks natifs.
- Row publiée seulement au retour du vrai SDL_GL_SwapWindow / SwapBuffers, avec epoch conservé avant incrément de `frame_count`, QPC après swap, slot natif, phase, backing, texture logique, dimensions, pause, HD/masquage, nombre de draws, conflit et résultat swap. SDL a un retourvoid ; GDIfalse => swapOk=false.
- Capture terminée après250ms sans owner en jeu actif ; pas de clôture automatique pendant pause. Logs groupés uniquement après disparition de tous les owners SPIMPFR suivis, afin de ne pas mesurer les flush INFO du diagnostic lui-même. L'heure murale des lignes est l'heure de publication différée : utiliser exclusivement QPC/frequency pour la cadence.
- Préfixes : `SPIMPFR_PRESENT_BEGIN`, `SPIMPFR_PRESENT_ROW`, `SPIMPFR_PRESENT_END`. Pas de preuve de scanout moniteur, ni de hash des pixels GPU après occlusion ; les118backings CPU distincts restent liés au manifeste installé et à son reçu.
- Analyse : phase/backing réellement soumis après occlusion +swap retourné ; moyenne des changements de contenu en temps actif ; répétitions normales au-dessus de30Hz distinguées des longs maintiens. Pauses exclues ; phases manquantes/sautées, retours arrière, fallback, no-draw, conflit, swap échoué et captures tronquées conservés séparément. Pas de conclusion30FPS sur capture incomplète ou <30transitions observables.
- Seuil longs maintiens : période30FPS +1,25×intervalle médian des présentations ; cadence moyenne observée tolérance±3%. Couverture complète des118phases rapportée séparément (un premier draw natif au slot1 peut commencer à la phase2).

```powershell
python -B -m unittest discover -s pipeline/recipes/spimpfr-presentation-trace-20261015-v1 -p test_analyze.py
python -B pipeline/recipes/spimpfr-presentation-trace-20261015-v1/install.py
# Après test utilisateur ; sortie stdout sans écriture par défaut.
python -B pipeline/recipes/spimpfr-presentation-trace-20261015-v1/analyze.py
```

- Test utilisateur : charger une carte, lancer `C:Eval('CreateVisualEffectObject("SPIMPFR",Player1)',0)`, fermer console/reprendre le jeu ; laisser l'effet finir (~4s), attendre1s, laisser le jeu ouvert pour lecture du log. Répéter2–3fois si utile ;8captures max par lancement.
- Reçu : `engine/InfinityEngine-Enhancer/installations/spimpfr-presentation-trace-20261015-v1/installation.json` ; payload97/33effets7Bx4NEAREST30FPS et profil personnages préservés par hash ; aucune QA visuelle déduite des tests hors jeu.

## Résultat runtime — session00:18:16, 2026-10-15

- Preuve immuable : `engine/InfinityEngine-Enhancer/installations/spimpfr-presentation-trace-20261015-v1/runtime-session-20261015T001816-v1/{session.log,analysis.json}`.
- 4captures complètes, 29.8327–29.8636 changements/s, x4/timeline toujours actifs, zéro fallback/mauvais backing/saut intérieur. Chaque capture commence au slot1/phase2 ; phases0–1 absentes,116/118phases présentées.
- **Cadence moyenne30 ≠ cadence régulière.** Sur460durées entièrement mesurées :228≈33ms,118≈50ms,114≈16.7ms ; alternance3/1rafraîchissements à60Hz, biais phases paires longues/impaires courtes. Le seuil « long hold » initial54ms et `cadence_30_confirmed_for_observed_segment` ne détectent pas ce défaut de régularité ; ne pas interpréter ce booléen comme validation de fluidité.
- Cause probable : `core/area_animation_timeline.cpp::select` réinitialise `slotStartTicks=sample.clockTicks` à chaque changement de slot15FPS, puis `calculate_phase` applique floor à30FPS ; observations proches du seuil33.33ms déplacent la phase intermédiaire au troisième rafraîchissement (~50ms). Correction à porter au scheduler runtime, avec test régressif3/1 ; aucune nouvelle interpolation nécessaire. Jeu utilisateur resté ouvert, aucune installation pendant cette analyse.
