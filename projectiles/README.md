# Projectiles — source, production réutilisable, travail restant

- **Suivi courant : [validations manuelles](SUIVI_MANUEL.md)**. 29 PRO avec acceptation visuelle limitée aux composants observés ; 3 décisions historiques conservées séparément. États explicites `index/work-tracking.json:projectiles.<PRO>.qa` ; [32 décisions et sources figées](analysis/validations-manuelles-consolidees-20261028-v1/decisions.json). Pas de QA intégrale des243PRO déduite.
- **CourantV14 accepté : [preuve finale Projectile magique](analysis/projectile-magique-v14-valide-20261028-v1/README.md)**. 28dessinsHD/masqués,12phasesdistinctes,13dessinsimpairs,0rejet ;canevasnatifvariable64×79confirmé,0imageretraitée. Trace temporairedésactivée,jeu/loaderarrêtés ;DLLV14conservée. Aucun retestdemandé surlescomposantsobservésdecettesérie.
- **[V13 : éclairs et vol de Semence confirmés](analysis/validation-v13-20261028-v1/README.md)**. Trois traînées93dessinsHD/89masqués/50phasesimpaires ; SPFIRSE2 volHD+masque sur3dessins,phases0/2 seulement. Ne pas rejouercesdeuxessais. RéserveProjectilemagiqueV13 levée parvalidationfinaleV14.
- Matrice secondaire :37/37groupesrôle/asset avec preuve technique partagée aprèsV13, sansQAdechaquepropriétaire/palette/cycle ni fermetureglobale243. SPMAGMISV14confirmé ;contratspropriétairesnonexercés,nouveauxassetsmanquants et déplacementrestentdistincts.
- **100chaînes vérifiées statiquement** conservées séparément. [Audit243](analysis/audit-complet-243-20261028-v1/README.md) :100complètes,124partielles,13natives,4avec images manquantes,LIGHTCHAcontrat à examiner,LIGHTSTOdépendance absente. Cet audit historique ne constitue pas une QAingame générale.
- **Déplacement reporté** : [PROJ-MOTION-001](../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001), [étude](analysis/deplacement-generalise-etude-20261028-v1/README.md). Animation des images ≠ interpolation des coordonnées ; aucune position intermédiaire ajoutée.
- Preuves/anciennes corrections : [répertoire de reprise](REPRISE_LIAISONS124.md). Ne pas redemander les validations acquises ; conserver les limites de propriétaire/palette/cycle et les états production/QA/installation/release distincts.

- Entrée : [SUIVI.md](SUIVI.md) ; détail par PRO : [work-items.csv](index/work-items.csv).
- Demande2026-10-18 : analyser tous les projectiles, distinguer le vrai travail des images déjà produites ; ne pas lancer de production en double.
- `index/resources.csv`, `dependencies.csv`, `manifest.json` : inventaire source stock ; conservé.
- Les graphismes de projectile restent produits dans `effects/` ; pas de second pipeline ou de copie des mêmes textures sous `projectiles/`.

| État | Autorité / preuve |
|---|---|
| Source | KEY/BIF + source PRO/BAM/SHA ; `index/resources.csv` |
| Image produite/acceptée | Autorités effets, animations ou sprites ; liens explicites dans `contexts.json` |
| Intégration de chaque PRO | `index/work-tracking.json:projectiles.<RESREF>.integration` + référence locale |
| QA de chaque PRO | Même fichier, `.qa` + décision explicite/preuve ; aucune promotion depuis la QA d’un BAM |
| Installation | Même fichier, `.installation` + reçu propre au périmètre ; catalogue seul = observation distincte |
| Release | Même fichier, `.release` + référence explicite ; aucune déduction depuis les autres états |

## Anti-doublon

- Clé image : BAM décompressé canonique (pixels/palette/indices/centres/cycles) + SHA palette RGB réalisée pour le consommateur.
- Alias source exact : réutilisation ; exemple SPIPLARI/SPIPLAAI. Une égalité d’image ne valide pas le contrat de chaque propriétaire.
- Même BAM / plusieurs palettes : sorties explicites distinctes ou représentation dynamique ; ne pas figer une couleur pour tous les PRO.
- Un résultat spatial suffit à interdire un second job spatial identique ; reprendre temporalité/pack si nécessaire.
- PRO/VVC/VEF, tables de palettes, sons, vitesse/rayon, particules moteur : aucun upscale IA autonome.
- Masques noirs : conserver natifs ; les effets visibles entièrement noirs ne sont pas des images RGB à halluciner.
- Images natives identiques et ancrées repérées entre nouvelles sources et sorties déjà représentées : pistes explicites dans l’analyse ; pas d’équivalence inventée entre canevas d’inférence différents.

## Utilisation

```powershell
python -B pipeline/scripts/projectile_tracking.py status
python -B pipeline/scripts/projectile_tracking.py queue --action new-context-required
python -B pipeline/scripts/projectile_tracking.py queue --action reuse-existing-output
python -B pipeline/scripts/projectile_tracking.py refresh --snapshot AAAAMMJJ-vN
python -B -m unittest discover -s pipeline/tests -p test_projectile_tracking.py
```

- `status`/`queue` : lectures seules, sans jeu/GPU, ni scan de pixels.
- `refresh` : analyse source/autorités en lecture, écrit seulement un nouvel instantané `analysis/<id>/` + projections de ce domaine. Aucun worker d’inférence/compilation/installation lancé.
- Historique immuable ; nouveau nom obligatoire. `index/work-analysis-current.json` identifie la projection courante et ses SHA.
- Décisions manuelles dans `index/work-tracking.json`, pas dans les CSV régénérés. Espaces `projectiles.<RESREF>` et `engine_projectiles.<ID_décimal>`. Champs optionnels : `priority` (entier), `notes`, `historical_evidence` (liste), puis `integration`, `qa`, `installation`, `release` (objets `state`, `evidence`).
- Une valeur `not-assessed` marque l’absence de décision pour ce PRO, même si certaines images ont une QA acquise.
- `analysis/<id>/` : `analysis.json` (contrats natifs/entrées/SHA/limites), `contexts.json` (palettes/usages/candidats), dépendances développées, liens PRO, usages SPL/ITM, jobs de palette, IDs moteur et rapport figé.
- Les fichiers d’index effets peuvent évoluer pendant un lot : régénérer l’analyse après son avancement ; ne pas prendre un ancien snapshot pour un état temps réel.
- `status`/`queue` signalent les entrées modifiées depuis l’instantané et refusent les projections CSV modifiées manuellement. Aucun suivi interdomaines n’est réécrit.
- Les tâches par propriétaire listent les risques à résoudre pour un nouvel usage ; elles n’imposent ni une campagne de retests de 243 PRO ni une remise en cause des QA acquises.
