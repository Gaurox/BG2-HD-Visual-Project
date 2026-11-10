# Deux couleurs acceptées —2026-11-10

- Accord utilisateur :«ok les 2 tests sont bons, valide-les, maj le suivi et committe» ;`acceptance.json`. R4-01 SHWATER6 rouge/ID138 etR4-02 SPBOOM67 doré/ID142 acceptés sur DLL `ED9A5E4E…9132A844`. Commandes réellement testées archivées dans `CLUA-tested.md` ;aucun nouvel essai demandé.
- `trace-summary.json`, `trace-selected.txt.gz` :SHWATER66drawsHD,dont31masqués et34phasesimpaires ;SPBOOM41drawsHD,tous41masqués,dont19phasesimpaires. Palette native réalisée liée au GPU pourles2ressources. SHWATER :1repliCpuNotReady au démarrage,puisHD ;pas un rejetdepalette.
- `outcome=0`=HD,`outcome=1`=CpuNotReady ;`ok=false` surdraw ne signifie pas échec. Traces échantillonnées,ni touscycles/couleurs ni mouvement natif intégralement mesurés. FLMSTRK etSPDIMDR1/2 conservent leur qualification statique etQA images antérieure,sansnouveau drawlive revendiqué.
- QA directe ajoutée **uniquement** auxIDs138/142. Autresvariants :preuve commune réutilisée àcontratcompatible +qualification CPU/GPU,aucune acceptation visuelle individuelle inventée. Anciensaccords etétats installation/release conservés.
- `trace-cleanup.json` :jeu/loader arrêtés,trace désactivée,INI initial retrouvé exactement (`AB4A3C30…AD6D8B0D`),DLL conservée ;images/PRO/registre/shaders/sprites inchangés.
- Autorité technique : `projectiles/index/owner-reconciliation-current.json` → `owner-contracts-residual-four-accepted-20261110-v3/`.313/320contrats techniques (97,8%),0famille active àcorriger,0test manuel restant ;7écarts natifs sanspilote statique conservés.39PRO +12IDs moteur ont uneQA descomposants observés ;pas uneQA globale deschaînes gameplay.
- Déplacement PROJ-MOTION-001 reporté ;aucune release/inférence/production nouvelle déduite.
