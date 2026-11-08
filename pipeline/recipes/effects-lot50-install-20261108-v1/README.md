# Installation lot50 courant · 2026-11-08

- `install.py` reprend builderVVC/registrev3 du lot58 et transaction réversible du lot33 ; nouvelles constantes OUT/source courante, pas de modification des anciennes recettes.
- `prepare` : production50=`effects/batches/lot50-black-transparent-20261108-v1/production.json` ; append-only sur catalogue actif observé538/62500, snapshot hashes ; sources25SeedVR/25xBR, dernières7corrections alpha. Queue vide de cycles source conservée dans carrier, omise uniquement du registre. Matrices once+loop/native/phase vérifiées par probe existant.
-100ressources =50premult natifs+50droits X50Nxx ;300VVC =50principales Z50Txx+150profils Z50Pxxxx+100comparaisons Z50Bxx/Nxx. Principaux boucle0≥4s ;7corrigés noir en normal, flammes/énergie majoritairement lumineux ; choix de test, pas contrat propriétaire mesuré.
- `install` : contrôle processus fermés, baselines, sauvegarde des2catalogues remplacés, copies atomiques et hashes de4294cibles, snapshots DLL/INI/personnages/cartes conservés, probe20kcontrats installé ; rollback en cas d'erreur. Écritures jeu uniquement sur demande explicite ; exécution hors sandbox requise pour tasklist et dossier Steam.
- `finish` : installation CSV50lignes seulement ; QA/production/release indépendantes. Reçu final `effects/installations/lot50-current-20261108-v1/installation.json`.
- `restore` : rollback via reçu, restaure seulement colonnes installation des lignes encore liées au reçu. Jeu/InfinityLoader fermés.

```powershell
python -B pipeline/recipes/effects-lot50-install-20261108-v1/install.py prepare
python -B pipeline/recipes/effects-lot50-install-20261108-v1/install.py install
```
