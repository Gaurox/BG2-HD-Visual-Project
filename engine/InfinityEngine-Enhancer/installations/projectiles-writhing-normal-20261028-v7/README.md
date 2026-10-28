# Brouillard putride — WRITHING normal-alpha, V7

- **Installé, retest visuel/runtime attendu.** `installation.json` ; DLL SHA CFE479943BC70B7387705A3060EE6D6FCF2C2EE1486A1A0BAB50E51606284003 ; manifeste SHA6E11B00001E4EFA49BE9D00E411B2647F97C024FB416996FE11D05B5A876215B ;538ressources/62500backings.
- Source du défaut : testSPPR250 appelleWRITHING,flags30080(non-Blended),mais chargeait les images prémultipliées à masque binaire. Le même run scellé `effects/ressources/WRITHING/runs/writhing-apollo30-retimed-strict-20261017-v1/` contient déjà les companions straight à alpha palette natif (`normal_alpha_policy=native-palette-temporal-nearest4-inner12`). Aucune nouvelle production.
- AliasX28WRTH :401backings/218616000octets copiés exactement depuis ces companions, SHA de chaque fichier vérifié contre le manifeste du run ; géométrie/centres/cycles/durée/30FPS conservés ; seuls les index de déduplication sont recalculés par l'assembleur existant. Échantillon temporalframe210 : médianeA255→43.
- Portée moteur : `core/effect_texture_alias.h`, `hooks.cpp`. WRITHING→X28WRTH seulement dans les passages FX normaux (bitBlended0x8 absent), contexte sauvegardé/restauré autour deFXRenderBam/FXRender. Les usages Blended conserventWRITHING et leurs octets/contrat ; anciens3aliasnuages et compositionsV5 conservés. Nouvelle cible dans whitelist et trace finale, aucune nouvelle adresse/hook.
- Données : ancien corps du registre conservé byte-identique après l'en-tête, enregistrement ajouté ;537descripteurs/62099frames JSON initiaux et contrôleursVVC inchangés ; carrier alias byte-identique àWRITHING natif installé,aucunPRO/SPL changé. Ni écrasement d'anciennes images, ni release.
- Recette transactionnelle : `pipeline/recipes/projectiles-writhing-normal-20261028-v7/repair.py prepare|verify|install`, déjà exécutée ; ne pas relancer sur ces reçus. `before.json`, `before/` et `transaction.json` contiennent les états V6 à restaurer si nécessaire ; rollback automatique sur échec d'installation. Les recettes V1–V6 à catalogue537 ne conviennent plus à l'installation courante.
- Tests3/3passants : `build/iee-projectile-secondary-links-20261028-v1/writhing-normal-v7-tests-final.log`,0,79s. Distinction normal/Blended, whitelist/idempotence, suites moteur/registre. `git diff --check` passé.
- Chargeur natif :840contrats alias (slots/phases,6cycles/once-loop/casse) passants candidat etinstallation ; `candidate-native-loader-metadata32.log`, `installed-native-loader.log`. Zéro lectureRGBA au probe,metadata26820516octets<budget32Mio déjà configuré ; aucun budget jeu augmenté. Le premier probe avec son défaut historique16Mio a refusé le catalogue, d'où option CLI `--metadata-mib` ajoutée au test pour refléter l'INI actuel.
- Installation après vérification hors sandbox BG2/InfinityLoader fermés ; snapshot préservé INI/exécutable/WRITHING natif/shaders/personnages/tousPRO overrides. Le préflight initial sans dossier `before/` s'est arrêté avant mutation, puis corrigé/repris ; transaction finale installée.
- **Retest seul à faire après relance InfinityLoader** :

```lua
C:Eval('ForceSpellRES("SPPR250",Player2)',0)
```

- Attendu : fond opaque disparu, contours/transparence cohérents ; `EFX_TEXTURE_ALIAS native=WRITHING runtime=X28WRTH` puis `EFX_BOUND_PHASE resref=X28WRTH` x4/phases impaires. Pas d'acceptation visuelle inventée depuis les probes.
- Feu spirituel/Aube illusoire/Comète jugés corrects par utilisateur et bindsHD observés : `projectiles/analysis/validation-vague2-writhing-20261028-v1/evidence.json`. Ne pas les redemander pour ce correctif.
