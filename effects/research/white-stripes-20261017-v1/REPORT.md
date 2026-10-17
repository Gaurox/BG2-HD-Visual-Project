# Bandes blanches à l'apparition d'effets — diagnostic 2026-10-17

## Conclusion

- Défaut renderer démontré hors jeu : restauration d'un état OpenGL **antérieur** à un flush natif, alors que le cache natif d'état appliqué décrit l'état **postérieur** au flush. Le prochain lot de dessins peut sauter une activation de shader/blending/scissor et utiliser l'état graphique erroné.
- Cause très probable des glitches signalés, commune aux effets ; corrélation avec une frame précise de la session non démontrée (pas de capture ni trace programme GL par draw). Aucun lancement du jeu, modification d'asset ou installation de correctif pendant cette recherche.
- Test réel WGL caché utilisant `ScopedEffectGlState` de production inchangé : bande blanche `[255,255,255]` au lieu du rouge attendu, **zéro erreur GL** ; garde capturée après flush : rouge correct `[255,0,0]`, cache cohérent, zéro erreur GL. Le cache natif est modélisé depuis le PE ; ce test ne charge/exécute pas le PE. `probe-result.json`, `host-reproduction.png`, `flush_coherence_probe.cpp`.

## Session observée / preuves figées

- Dernier démarrage :14:43:19.017 ; dernière ligne :14:52:11.965, horaires des logs du2026-10-17. 3368lignes : `session.log`, copies datées du fichier courant et de `.1.log`, empreintes dans `sources.json`.
- Pack221RESREF/27479backings/14587695872octets : lot58 +161précédents +2alias ; DLL active SHA256 `824A74D8FC107BE4C23D66A416C535199D217B11CC5CB6903B641ADEB33006D1`, inchangée depuis le build streaming du15octobre.
- GPU :14266draws,3188uploads,3124flushes ;64slots. `uploads - flushes = 64` : après les64allocations initiales, réemploi LRU avec flush. Première mesure avec flush :14:43:59.511 (72uploads/8flushes).
- Aucun drawMiss/cpuMiss/firstSubmitMiss, aucun refus scratch/horizon ; pic GPU114023808octets sous301989888. CPU7814lectures,5720évictions, zéro failure/miss/admissionFailure/deadlineMiss ; pic805306304 sous805306368. Ces compteurs attestent les chemins sélectionnés, pas la conformité visuelle des pixels.
- Une seule warning : prologue RenderTexture détourné EEex, cible récupérée par signature ; hooks installés ensuite. Aucun échec de lecture/backing/fallback signalé. `telemetry-summary.json`.

## Mécanisme vérifié

1. `engine/InfinityEngine-Enhancer/source-patchee/src/iee/effect_animation_x4_registry.cpp:397` : le garde GL est construit **avant** la lambda qui appelle `flush_native_locked` (L400–401). Réemploi de slot → flush (L437 environ) → upload → retour → destructeur du garde.
2. `src/iee/game/scoped_effect_gl_state.h:43,67` : capture puis restauration directe de `GL_CURRENT_PROGRAM`, ainsi que blend/scissor/textures. Aucun raccord au cache natif de l'état appliqué.
3. PE exact `BaldurReal.exe`, SHA256 `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57` ; lecture/désassemblage seulement. RVAs ci-dessous ; listings `*.asm`, identité `native-identity.json`.
4. `DrawFlush_GL` RVA42B350 :42B4F2 compare le premier état commandé au cache appliqué RVA2F73FE4 ;42B4F8 ajoute les bits sales RVA2F73FE8 ;42B5A0–42B5B1 n'active le programme que si ses bits bas diffèrent ;42BB7F publie le dernier état appliqué,42BB5E efface les bits sales. Restaurer matériellement un ancien programme après ce flush rend ce cache faux.
5. `DrawPushState/PopState` GL (42CDE0/42CDB0) sauvegardent/restaurent seulement le DWORD d'état logique courant RVA2F73F6C. Ils ne restaurent pas le cache appliqué RVA2F73FE4.
6. `DrawBindTexture` GL42A840 ne fait que changer les bits texture du DWORD logique ; l'hypothèse d'un simple bind GL manquant dans cette fonction n'est pas retenue. `TexImage` GL42D030 marque la texture sale (bit21), ce qui ne force pas les bits programme/blend/scissor à se réappliquer.
7. Les appels GL sont valides : mauvais état de rendu ≠ erreur API ; cela explique les compteurs HD réussis et l'absence d'erreur. [Sémantique officielle glUseProgram](https://wikis.khronos.org/opengl/GLAPI/glUseProgram).

## Correction ciblée à développer

- Faire le flush natif avant la capture du garde protégeant l'upload ; si le flush est décidé tardivement, terminer le garde précédent **avant** le flush, puis reconstruire une capture post-flush. Garder `DrawPushState/PopState` pour l'état logique souhaité. Examiner aussi le même ordre dans `release_gpu` (L1157).
- Préserver la synchronisation de la queue avant réemploi de descripteur/stockage : supprimer le flush exposerait les dessins différés à des images/dimensions remplacées.
- Étendre `tests/effect_texture_cache_tests.cpp` : son faux `flush()` actuel relie seulement les textures/lit leurs pixels et ne modélise ni changement de programme ni cache natif différentiel ; `verifyFrame()` relie explicitement la texture. Le test historique ne pouvait pas détecter cette incohérence.
- Pas de changement de modèle, RGB, alpha, cadence, pack ou budget nécessaire pour corriger ce défaut d'état. Installation/confirmation ingame du correctif = travail distinct de ce diagnostic.

## Reproduction hôte

```powershell
cmake -S effects/research/white-stripes-20261017-v1 -B build/effect-white-stripes-probe-20261017-v1 -G "Visual Studio 16 2019" -A x64
cmake --build build/effect-white-stripes-probe-20261017-v1 --config Release --parallel 1 -- /nodeReuse:false
# Exécuter l'EXE depuis un nouveau répertoire de sortie ; fenêtre WGL cachée.
G:/AI/BG2_Upscale/build/effect-white-stripes-probe-20261017-v1/Release/effect_flush_coherence_probe.exe
```

- Sonde hôte : deux ordres du même garde, politique différentielle native modélisée, dessin/lecture pixels réels ; exit0 = défaut reproduit + ordre post-flush cohérent.
- `native_disasm.py` : extraction statique des RVAs depuis les callsites et listings PE, aucun appel de fonctions du jeu. Conserver cette session/probe/identité ; nouveau dossier pour une nouvelle version de DLL ou session.
