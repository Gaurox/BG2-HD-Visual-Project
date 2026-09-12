# Aide rapide — upscaling

Ce fichier est un index facultatif. Il n'est ni un préflight, ni une checklist, ni une condition de
démarrage ou de clôture. Consulter uniquement la ligne utile au problème courant.

| Situation | Repère utile |
|---|---|
| Changements locaux possibles | `git status --short`, puis préserver ce qui est hors périmètre |
| Autorité d'une carte | `areas.csv` |
| Autorité d'une animation | `animations/index/` |
| Autorité d'un sprite | `sprite/index/` |
| Recette déjà tentée | `docs/DECISIONS.md` |
| Problème encore ouvert | `pipeline/PROBLEMES_A_RESOUDRE.md` |
| Format BG2EE inconnu | `BG2EE_Documentation_Modders_FR/INDEX.md` |
| Validation ingame finale | Enregistrer la décision exacte dans l'autorité du domaine |
| Intégration release | Traiter seulement après demande explicite |

Conseils, à utiliser seulement s'ils apportent quelque chose au cas présent :

- garder les sorties finales reproductibles et associer leurs entrées utiles ;
- créer une nouvelle version plutôt que réécrire une preuve finale ;
- vérifier un risque local par le contrôle le plus court capable de le révéler ;
- éviter les audits globaux, reconstructions, tests ou inventaires sans besoin concret.

Les anciens signaux d'erreur (`animation-pack-p3-drift`, run sans asset, QA non prise en charge,
totaux codés en dur) sont des pistes de diagnostic, pas des contrôles systématiques.
