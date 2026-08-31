# Corrections locales d'occlusion WED

Ce dossier conserve les spécifications reproductibles des corrections de données WED validées.
Il ne remplace pas le bridge moteur global : une correction locale n'est autorisée qu'après avoir
prouvé que le runtime xN passe bien par le bridge et que le premier plan attendu est absent, faux
ou décalé dans le WED natif.

## Processus

1. Vérifier dans les traces que l'objet atteint `FXRenderClippingPolys` et que le bridge produit
   une composition xN active.
2. Comparer l'alpha logique de la ressource xN au BAM vanilla. Une extension réelle du sprite se
   corrige dans l'animation ; elle ne justifie pas un polygone WED.
3. Extraire les polygones, wall groups et sommets du WED source KEY/BIF. Mesurer leur intersection
   exacte avec l'alpha de l'objet au lieu de déduire leur rôle depuis leur boîte englobante.
4. Si la donnée WED manque réellement, produire un canevas monde xN de la carte seule. Le masque
   d'authoring est aplati, opaque et monochrome : blanc conserve l'objet, noir désigne le décor de
   premier plan.
5. Convertir ce masque en coordonnées logiques x1 avec
   `pipeline/scripts/build_wed_mask_polygon_patch.py`. Le builder exige le hash WED source, les
   octets exacts d'un slot vide et la plage lookup attendue du wall group. Toute divergence échoue
   fermée.
6. Contrôler le contour quantifié sur la carte, l'intersection réelle avec toutes les phases, les
   différences binaires du WED puis demander « tests ciblés / tous / aucun » avant toute suite
   Python ; voir [`../../docs/TEST_SELECTION.md`](../../docs/TEST_SELECTION.md).
7. Installer uniquement jeu et InfinityLoader fermés avec
   `pipeline/scripts/Install-AreaOverrideAssets.ps1`, puis valider ingame. Conserver le backup de
   restauration et ne promouvoir ni staging ni manifeste de release sans accord distinct.

Le PNG peint sert à authorer la géométrie ; il n'est pas cuit dans le BAM et n'est pas chargé au
runtime. La spécification validée conserve les sommets WED x1 définitifs, les hashes et le verdict
QA afin que le correctif reste reproductible sans Photoshop.

Pour une sélection release, conserver le WED validé dans un dossier versionné sous la correction,
puis l'épingler depuis `animation-release-candidates.json` avec hash, destination, preuve QA, clé
INI et composant map. Le générateur de contenu refuse toute divergence.

## Quand revalider

Une QA locale doit être rejouée si le hash du WED source change, si un mod remplace la zone, si les
sommets ou wall groups sont modifiés, ou si le bridge change sa politique de composition. Une
nouvelle validation globale du bridge n'est nécessaire que pour un changement moteur, une nouvelle
famille de rendu ou une nouvelle version de l'exécutable.

Ces interventions restent donc **au cas par cas pour les cartes dont les données WED sont
défectueuses**. Elles ne demandent pas de traiter tous les premiers plans du jeu un par un.
