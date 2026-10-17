# Lot26 — dérivation SDF sans retrait / installation delta

```powershell
python -B pipeline/recipes/effects-lot26-sdf-install-20261017-v1/derive.py
python -B pipeline/recipes/effects-lot26-sdf-install-20261017-v1/install.py prepare
python -B pipeline/recipes/effects-lot26-sdf-install-20261017-v1/install.py install
# Retour ciblé, jeu et InfinityLoader fermés :
python -B pipeline/recipes/effects-lot26-sdf-install-20261017-v1/install.py restore
```

- Ne pas réexécuter les étapes sur les résultats scellés : gardes d’existence ; nouvelle version si remplacement nécessaire.
- `derive.py` : huit dérivés de la v2, RGBA droits exacts du comparatif SDF8787/inset0 ;404phases, autres18 identiques v2. RGB existants/centres/carriers/durées conservés, extension du matériau aux nouveaux bords uniquement ; prémultiplication unique des packs par défaut.
- `install.py` : réutilise le constructeur de ressources du lot58 ; delta sparse,225anciennes ressources/30229backings et octets des anciens enregistrements conservés ; +28RESREF =26sources +SPIPLARI canonique +X26PLAA normal.
- 15ressources exclusivement normales en RGB droits ; quatre exclusivement lumineuses et six PRO en prémultiplié. SPIPLAAI/SPIPLARI prémultipliés, X26PLAA droit ; seuls les8octets de référence BAM des VVC normaux ICINHIT/ICINTRAV changent.
- 26contrôleurs Z26T01..Z26T26 +60profils Z26P0001..Z26P0060 ; cycles,15FPS natifs, durées et géométrie conservés ; sorties30FPS. Les tests isolés ne reproduisent pas les chemins PRO.
- Catalogue :253RESREF/32927backings,70888contrats natifs ; métadonnées17224952octets. INI : seul `EffectMetadataMiB = 16`→`32`. DLL/shaders/profil personnages préservés par SHA.
- `native_probe.cpp` : copie du test catalogue canonique, budget explicite32Mio ; binaire isolé `build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe`. Aucun rebuild ni changement de DLL déployée.
- Avant écriture : jeu/InfinityLoader arrêtés ; backups ciblés ; copies atomiques/hashées ; rollback ciblé sur échec. `before.json`, `plan.json`, `transaction.json`, `installation.json` dans `effects/installations/lot26-sdf-no-inset-20261017-v1/`.
- `restore` restaure les octets de la transaction ; le CSV d’installation doit ensuite être réconcilié avec l’état restauré. QA/release indépendantes, aucune acceptation implicite.
