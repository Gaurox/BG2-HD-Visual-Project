# Corrections lot31 —2026-10-19

- Entrée immuable : `effects/batches/lot31-projectiles-7b-apollo30-20261018-v1/` ; sortie d'essai : `effects/batches/lot31-corrections-preview-20261018-v1/`.
- `prepare.py` : groupes exacts27/95 ; refuse d'écraser le plan. `rebout.py` :41palettes natives, modèle ReboutCX x4 FP16, exécuter avec Python chaiNNer configuré (`config://chainner_python`).
- `masks.py` : Potrace SPDEATH3 +fondu Gaussian adaptatif aux traits fins, cache24BAM. `correct.py` : RGB/alpha séparés, Apollo, chrono native12/20/30, noir neutre12/14/20 ;2workers, reprend les `results/` terminés.
- `verify.py` : vérification des candidats/parents et durées ; attend les résultats encore en cours, cache par SHA du résultat+vérificateur. `--job <JOB>` pour diagnostic ciblé. Répare seulement les fichiers d'aperçu intermédiaires interrompus, jamais les parents.
- `review.py` :31cartes/99contextes,3vues synchronisées vanilla/avant/après, palettes/profils/zoom/alpha. Attend les99résultats ; aucune production requise pour conserver un parent inchangé.
- `contact.py` :4planches poses visibles. `finalize.py` : synthèse etREADME après99vérifications réussies ; aucune autorité de production/QA/install/release modifiée.
- Reprise d'une exécution interrompue compatible : `python -B .../correct.py`, puis `verify.py`, `review.py`, `contact.py`, `finalize.py`. Résultat déjà livré/accepté : nouvelle version, pas de réécriture.
- Service de revue : `python -m http.server 8794 --bind 127.0.0.1 --directory effects/batches/lot31-corrections-preview-20261018-v1/review` ; vérifier port libre et titreHTTP, ne pas remplacer les serveurs historiques.
- Géométrie candidate : marge20px x4, centre+5x1 ; pas directement substituable à l'ancien pack/carrier sans dérivation runtime explicite. Base15FPS héritée, pas de mesure réelle supplémentaire.
