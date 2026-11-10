# Quatre familles résiduelles corrigées/installées —2026-11-10

**État final : [2couleurs acceptées](../residual-four-colours-accepted-20261110-v1/README.md).** Palette/HD/masques/phasesimpaires observés pourSHWATER6 etSPBOOM67 ;trace désactivée,INI initial exact,DLL conservée.0nouvel essai demandé ;les instructions/mentions d'attente ci-dessous sont l'étape historique d'installation.

- **Courant : [2 observations de couleur](CLUA.md)**, `visual-tests.json`. SHWATER6 rouge via Baies magiques/SPPR207 ;SPBOOM67 doré via SPWM110 surcible jetable. Sources/opcodes/SHA contrôlés ;aucun helper installé. QA de ce nouveau contrat en attente,aucun drawHD live déduit de l'installation.
- Installation : `engine/InfinityEngine-Enhancer/installations/projectiles-residual-four-20261110-v1/installation.json`. DLL `ED9A5E4E…9132A844` ;seulecléINI `EnableEffectStreamingTrace=false→true`,temporaire. Jeu/loader arrêtés avant transaction ;backups immuables,manifeste/registre/PRO/carriers/shaders/sprites conservés.
-4entrées ajoutées au scope secondaire :SHWATER,FLMSTRK,SPDIMDR1,SPDIMDR2. SPBOOM déjà admis :ajout du transfert natif de palette. Aucune adresse/hook supplémentaire,aucune image/inférence/interpolation ni release modifiée.

## Palette / moteur

- `effect_residual_projectile_palettes.h` :2sources BAM RGB figées ;indices réellement utilisés prouvés :SHWATER1..214 (214RGB uniques),SPBOOM4..15 (12RGB uniques). `source-palettes.json` lie lesBAM etBMP natifs ;fixture CPU issue des7tables SHWATER etMPALETTE67/65/69.
- SHWATER :BMP217entrées,queue inutilisée exclue du calcul couleur/alpha/empreinte. Pas d'hypothèse sur des couleurs non dessinées. SPBOOM :seule range0 ;doublons des indices inutilisés exclus.1534nœudsRGB natifs vérifiés (214×7 +12×3),RGBA/BGRA,identité etalpha.
- `effect_indexed_palette.h` :2SourceKind ajoutés après lesanciens,empreintes historiques conservées ;calcul des couleurs intermédiaires corrigé pourclasser lesnœuds **de la bonne famille** (ancien classement utilisaitSHAREA pourtouteslesfamilles). Oracle CPU indépendant en recherche exhaustive surpoints non natifs pourAir/Earth/HolyMight/Water/Boom.
- PourWater/Boom,seulecopie d'upload GPU convertie selon le blend natif :premultiplied lumineux /straight normal ;empreintes distinctes etréversibles,source/cacheCPU inchangés. Tests pixels semi-transparents etcacheWGL. Autresfamilles conservent la politique de repli normal antérieure.
- SPBOOM neutre,palette identique/opacité255 :chemin antérieur conservé ;pas de recoloration gratuite. Palette invalide,alpha variable non supporté oucomposition indexée multicouche→repli natif complet. Aucune substitution de palette arbitraire.
- SPDIMDR :factory/update natifs inchangés,identité2→1→2 lue àchaque cellule ;les2packs conservent leursdessins/centres/cycles/timelines. FLMSTRK :mêmesource/contrat pour145 et66 ;le66,sanspilote scanné,est réconcilié par le raccord partagé.

## Contrôles

- `qualification.json` :208backings SHA exacts,5cycles natifs,600contrats (cycles/slots/phases/base+once/dimensions/centres/casse).
-5/5suites CPU/GPU passantes :surface-owner,occlusion,iee_tests,registry,texture-cache. Tests existants SHAREA/Air/Earth/HLY/COW/masques/prefixes conservés.
- `before-install-native-loader.log` +`installed-native-loader.log` :600contrats chacun ;`regression-loader.log` :31 668contrats du graphe complet,0lectureRGBA.
- États : `projectiles/analysis/owner-contracts-residual-four-20261110-v2/` ;**313/320 propriétaires qualifiés techniquement (97,8%)**,0famille active àcorriger,7écarts natifs sanspilote conservés.13IDs actifs corrigés +66 parréemploi FLMSTRK.11IDs de familles colorées liés àuncontrat techniquement qualifié dont2observations représentatives restent àfaire ;aucune promotion QA/release.
- Réconciliation antérieure conservée immuable. Les anciens13écarts etlescompteurs93,4% sont historiques.39PRO +10IDs gardent leursaccordsvisuels bornés ;aucune QA intégrale déduite.

## Suite exacte

1. Utilisateur :relancer viaInfinityLoader,faireR4-01/R4-02 seulement,quitter jeu/loader.
2. Agent :lire traces depuis `log-baseline.json`,enregistrer retourvisuel +portée HD/palette/phases,conserver leslimites observées.
3. Désactiver **seulement** EnableEffectStreamingTrace avec `pipeline/recipes/projectiles-residual-four-20261110-v1/install.py disable-trace` ;garder DLL. Ne pas relancer lesneutres/lots acquis ;ne pas déduire de release.
