# SPDEATH3 — installation Bézier/fondu sigma4

```powershell
python -B pipeline/recipes/effects-spdeath3-soft4-install-20261018-v1/install.py derive
python -B pipeline/recipes/effects-spdeath3-soft4-install-20261018-v1/install.py prepare
python -B pipeline/recipes/effects-spdeath3-soft4-install-20261018-v1/install.py install
# Jeu et InfinityLoader fermés :
python -B pipeline/recipes/effects-spdeath3-soft4-install-20261018-v1/install.py restore
```

- Autorisation2026-10-18 : « ok on part sur sigma 4, installe SPDEATH3 ingame et redonne la clua pour tester ». Un seul asset, choix du comparatif soft4 ; aucune validation ingame implicite.
- Dérivé scellé actif : `effects/ressources/SPDEATH3/runs/spdeath3-bezier-soft4-20261018-v2/`, pack mono-BAM `spdeath3-7b-bezier-soft4-apollo30-20261018-v2`, lot `effects/batches/spdeath3-bezier-soft4-runtime-20261018-v2/`. v1 non scellée conservée : erreur de sérialisation int64 NumPy, aucun pack/installation ; corrigée par conversion des centres en entiers Python.
-124paires RGBA droit/prémultiplié identiques par SHA au comparatif `spdeath3-bezier-edgefade-preview-20261018-v1`, variante soft4 ; aucune nouvelle inférence/interpolation. Chronologie once+loop62phases/31/15s et centres monde conservés.
- Passage aperçu→runtime : canevas aligné54×94x1 +marge5x1 (=4x4 Bézier +16x4 Gaussian) ; sorties256×416x4, logical64×104, centre33,60.30frames BAM repaddées transparentes, indices/palette/cycles/lookup et coordonnées monde de chaque pixel source exacts. Ne jamais copier un raw d'aperçu avec les anciennes dimensions.
- Les nouvelles dimensions autorisent123backings distincts par encodage, contre122 auparavant ; reconstruire les IDs de stockage dans les tables, conserver les phases/durées. Deux nouvelles images `frame122` ;244backings remplacés,246actifs.320autres ressources/43111backings et tousVVC byte-identiques dans le manifest ;322RESREF/43357backings cumulés.
- Delta transactionnel250cibles :246RGBA +2carriers(SPDEATH3/X33N33) +registre/manifest. Backups ciblés, copies atomiques+hashées, rollback sur erreur ; collisions/état antérieur vérifiés. Jeu/InfinityLoader fermés. DLL/INI/shaders/profil personnages/exécutable/CLUA VVC inchangés. Index : seul SPDEATH3 production/interpolation puis reçu installation.
- Probe candidat+installé92632contrats natifs ; métadonnées20564362octets sous32Mio. `effects/installations/spdeath3-bezier-soft4-20261018-v1/{installation,transaction,scope-verification}.json`. Test normal inchangéZ33T33 (X33N33), boucleZ33P0182. Variantes explicites Z33B33/Z33N33 mises à jour par leurs BAM communs.
- `restore` rétablit les octets de cette transaction et le reçu installation précédent du seul SPDEATH3 ; production actuelle distincte, QA/release non modifiées. Jeu non lancé par l'agent, résultat visuel à confirmer.
