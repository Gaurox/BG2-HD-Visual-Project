# Prêtres humains Q3m K6 x2 — 2026-10-02

- Portée monde : homme `0x6000`, femme `0x6010` ; inventaire exclu.
- Résultat : 188 212 traitements uniques ; 183 054 réutilisés ; 5 158 nouveaux, 30 948 cibles neurales.
- Reprise guerrière : 90 250 résultats importés ; cache guerrier masculin déjà disponible.
- Bilan figé : `production.json`. Cache I/F/dep partagé ignoré par Git ; namespace x2 `15e582a92931128f728d9532113ba86a8a5958361d2989caadb7fbcb6dd20ae2`.
- Plan existant : `sprite/index/palette-work-plan.json` ; aucun nouvel audit exécuté.
- État : encodé ; assemblage natif, installation et QA ingame restent à faire.
- Journal local : `sprite/.work/q3m-human-clerics-x2-20261002-v1/production.log`.

```powershell
$clericPython = (Get-Content -LiteralPath 'config/workspace-paths.local.json' -Raw | ConvertFrom-Json).paths.chainner_python
& $clericPython -u -B pipeline/scripts/palette_playable.py run --scale 2 --animation-id 0x6000 --animation-id 0x6010
```
