# Sprites — résolution CVidCell commune — 2026-10-07

- Portée : **15 familles /331 IDs installés**, corps/armures/équipements/parties spatiales ; aucune inférence GPU, **0 sprite recalculé**. Q3m V6 Character et V7 autres familles, x2/Nearest, palettes et géométrie acquis inchangés.
- Cause observée : `Character 0x6110 /CHFF4G1 /sequence15 /slot12` ; cycle natif de12 slots, ancienne résolution Strict refuse12. Loop/Clamp natifs sélectionnent ici frame575. [Session/diagnostic](analysis.json), [log ciblé](last-session-evidence.txt).
- Correction commune : `CVidCell+0x11C` lu pour chaque cellule ; slots signés Loop/Clamp et séquence hors plage→0 comme jeu natif. Attente de la métadonnée de la ressource exacte sur tout owner authentifié, délai5s existant ; payloads toujours paresseux. Strict reste le défaut des appels hors hook. Ressource absente, cycle vide, lookup invalide, palette incompatible : refus conservé ; aucune frame arbitraire substituée.
- Diagnostic : premier échec par ID (ancien avertissement unique global masquait les autres IDs), playback natif inclus.
- Source successeur : fork du runtime MFIE v3 acquis ; **3 fichiers seulement**. Essais Character V10 stock non introduits. [Delta](runtime-delta.patch), [provenance DLL/sources](runtime.json).
- [Tests](runtime-verification.json) : instructions x64 natives émulation231 cas ; chaque cycle et slot valide des14370 combinaisons feuille/ressource/owner, limites int16/Loop/Clamp/Strict, aliases63029, tous331 IDs. Oracles tirés des BAM natifs ; déduplication des feuilles partagées. Oracle pixels G2 réutilisé avec le nouveau décodeur natif (11774 frames, K6×3 formats). Nombre exact de contrôles dans le JSON.
- Installation : **DLL seule**, sauvegarde parent et rollback ; catalogue et14330 feuilles SHA vérifiés avant/après. [Candidat](current-generation.json), [reçu figé](installation-verification.json). QA historiques immuables ; aucune nouvelle QA visuelle déduite. Deux octets G2 Monster précédemment en attente restent à confirmer, dont attaque MFISG2 non observée dans la session.
- Reprise : `build_runtime.py` → `prepare_oracle.py` → `verify_runtime.py` → `prepare_install.py` → `install.ps1` → `finish.py`. Preuves finales immuables ; nouveau run pour successeur. `restore.ps1` restaure uniquement la DLL parent, jeu/InfinityLoader fermés ; ensuite actualiser le pointeur runtime du suivi.
- Confirmation ingame : guerrière humaine/compagnon humain (repos, marche, clic, attaque, dégâts, fins de cycles), puis attaque QMON7313 ; vérifier nouveaux logs. Aucun lancement automatique du jeu, aucune release modifiée.

```lua
C:CreateCreature("QMON7313")
```

```lua
C:Eval('ActionOverride("QMON7313",Enemy())')
```

```lua
C:Eval('ActionOverride("QMON7313",Attack(Player1))')
```
