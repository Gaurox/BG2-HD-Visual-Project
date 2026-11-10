# Lot31 — projectiles, manifestations et contrôle

- Autorisation2026-10-18 :31BAM, SeedVR7B x4/Apollo30, doublons condensés avec durée conservée, palettes/alpha natifs.
- Batch : `effects/batches/lot31-projectiles-7b-apollo30-20261018-v1/`. `batch.json` :31assets primaires +99jobs de palettes (68variantes supplémentaires), même source native par BAM.
- `prepare.py` :31sources intactes ; PRO travel bit0 →7rampes MPALETTE12 +mélanges natifs ; sinon BMP externe si déclarée, sinon palette BAM. Palettes complètes dédupliquées par SHA ; consommateurs/flags conservés.99contextes,15BAM à palettes.
- `verify_palettes.py` : tous les champs de leurs PRO redécodés/SHA ; mélanges comparés au fragment natif isolé validé P0 (`palette_oracle.NativeMix`), BMP/source exacts. Aucun appel au jeu ni écriture installée.
- `verify_model_inputs.py` après spatial :2032fichiers RGB/alpha réels et leur padding relus ; couleurs visibles comparées à chaque palette native, masque d'entrée exact.1991inférences distinctes/41réemplois exacts.
- `spatial.py` : producteur canonique7B INT8/LAB x4 adapté en mémoire (aucun script partagé modifié). Exports par palette explicite, alpha binaire séparé pour compatibilité lumineuse ; alpha normal gradué reconstruit ensuite. Cache d'inférence RGB identique lié au workflow exact/échelle/padding/LAB ; SHA des sorties vérifié avant réemploi. Source native, géométrie, cycles/indices intacts ; instantané du producteur/palette lié à chaque run.
- `temporal.py` : recette lot33 padding Apollo min128/multiple32, crop exact ; une variante once et loop par cycle/palette, fréquences VVC connues ou base15FPS de compatibilité. Poses RGBA ancrées distinctes avant Apollo, phases réparties sur durée rationnelle native. Cycles constants conservés ; alpha interpolé sans génération par IA. GaussianRGB1.2 habituel, feather0 pour tous : traits fins conservés, aucun retrait/fondu universel.
- Chaque contexte : run spatial/interpolation/pack distinct, carrier palette/indices natifs inchangés ; alpha droit natif et RGB prémultiplié conservés séparément. Seul p01 alimente la production courante CSV ; toutes les variantes secondaires scellées dans `batch.json`/résultat, aucune sélection QA implicite.
- `verify.py --wait` : source/carrier redécodés, palette réalisée à chaque entrée modèle, RGB/RGBA/timings par phase, alpha normal reconstruit indépendamment, absence de doublons visibles hors cycles constants, tables du pack.
- `review.py --wait` :31cartes, sélecteur palette puis cycle/mode, natif et résultat, WebP lossless alpha droit/fonds réglables. Teinte/éclairage runtime non simulés.
- `finalize.py` : requiert99contextes vérifiés/31cartes/99palettes, crée `production.json` une fois seulement. Aucune installation/QA/release déduite ; dispatch des palettes par owner à intégrer avant tests ingame.

```powershell
python -B pipeline/recipes/effects-lot31-projectiles-20261018-v1/prepare.py
python -B pipeline/recipes/effects-lot31-projectiles-20261018-v1/verify_palettes.py
python -B pipeline/recipes/effects-lot31-projectiles-20261018-v1/spatial.py
python -B pipeline/recipes/effects-lot31-projectiles-20261018-v1/verify_model_inputs.py
python -B pipeline/recipes/effects-lot31-projectiles-20261018-v1/run_temporal.py
python -B pipeline/recipes/effects-lot31-projectiles-20261018-v1/verify.py --wait
python -B pipeline/recipes/effects-lot31-projectiles-20261018-v1/review.py --wait
python -B pipeline/recipes/effects-lot31-projectiles-20261018-v1/finalize.py
```

- Spatial requiert accès localhost hors sandbox (`require_escalated`), serveur explicitement fourni par utilisateur. Workers temporels2 bornés ; reprises par asset/job scellé sans réécriture. Un échec non scellé peut être repris à paramètres identiques ; changement de recette ⇒ nouveau run/dossier versionné.
- Résultat final :31/31BAM,99/99contextes,9968phases/658profils,4248524864octets de packs. Contrôles99sans échec,31lignes production seules changées ; QA/install/release et autres lignes conservées. Galerie8793, liste palettes/cycles ; installation et dispatch natif non effectués.
