# Projectiles — source, production réutilisable, travail restant

- **Suite active : [validation des productions existantes](analysis/validation-produits-suite-20261028-v1/README.md)**.100chaînes complètes validées techniquement sans retests systématiques ; seules les parties déjà produites des128autresPRO concernés sont à poursuivre. Suite active : [trois variantes produites](analysis/writhing-v7-valide-20261028-v1/next-tests.json), SPWI953/SPCL239/SPDD03 ; vagues1–2 acquises pour les composants observés.
- [Vague1 terminée, nuages transparents confirmés](analysis/nuages-v6-valides-20261028-v1/README.md) : quatre effets jugés corrects pour les composants observés ; V6installée,0image retraitée. Vague2 également terminée pour les composants observés.
- [Vague2 jouée](analysis/validation-vague2-writhing-20261028-v1/README.md) : Feu spirituel/Aube illusoire/Comète satisfaisants ; **V7courante538ressources**,Brouillard putride réutilise401companions normal-alpha déjà produits viaX28WRTH,aucune inférence. **[SPPR250 accepté en V7](analysis/writhing-v7-valide-20261028-v1/README.md)** ; anciennes537ressources préservées.
- Audit complet243PRO, branches et installation active2026-10-28 : [résultat et listes](analysis/audit-complet-243-20261028-v1/README.md).100chaînes HD statiquement raccordées,124partielles,13natives,4avec images manquantes,LIGHTCHA à vérifier,LIGHTSTO incomplet ; aucune QA ingame générale déduite.
- Corrections des124en cours : [reprise courante](REPRISE_LIAISONS124.md),[124candidats](analysis/liaisons124-20261028-v1/124-candidate-routes.csv). **V5installée** : [préfixe natif + dernière coucheHD](../engine/InfinityEngine-Enhancer/installations/projectiles-native-underlay-20261028-v5/README.md), généralisé aux compositions compatibles ; [vol crâne/orbe x4/interpolé confirmé dans les logs](analysis/composition-retest-v5-20261028-v1/README.md). Correctifs FIREBAT et nuage conservés ;0inférence,octets images/PRO conservés. Ne pas promouvoir124QA depuis ces tests.
- [Contrôles ciblés et6tests ingame](analysis/verifications-ciblees-20261028-v1/README.md) : continuité243PRO,13ressources/39images échantillonnées intactes ; manques connus conservés, tests supplémentaires en attente.
- [Résultats des6tests et correction du nuage](analysis/six-tests-cloud-alpha-20261028-v1/README.md) : V4installée,SPCLOUDK réutiliseX58CLK/alpha natif existant,0image retraitée. [Nuage accepté visuellement, x4/phases interpolées confirmés dans les logs](analysis/nuage-valide-v4-20261028-v1/acceptance.json). Crâne/orbe : aspect correct mais repli natif encore observé ; pas de validationHDglobale.

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
