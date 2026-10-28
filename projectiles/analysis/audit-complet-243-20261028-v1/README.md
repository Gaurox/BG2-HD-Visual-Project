# Audit complet des243PRO —2026-10-28

## Résultat

| État de la chaîne visuelle complète | PRO | Liste |
|---|---:|---|
| HD raccordée statiquement pour tous les composants identifiés |100|[noms](100-raccordes-HD.txt),[détails](100-raccordes-HD.csv)|
| Couverture partielle : au moins une route secondaire non démontrée |124|[noms](124-partiels.txt),[blocages](124-partiels.csv)|
| Natif/procédural, aucun nouveau travail image identifié |13|[noms](13-natifs.txt)|
| Images absentes |4|BGLRY,SPCL236,TRAPGLPN,TRAPGLYP|
| Contrat de traînée à examiner |1|LIGHTCHA|
| Dépendance source absente |1|LIGHTSTO|
| **Total exhaustif** |**243**|[une ligne par PRO](projectiles-243.csv)|

**« Raccordé statiquement » = source/alias, catalogue installé et chemin de résolution primaire ou VVC compatibles ; pas243acceptations visuelles ingame.** Les propriétés d'apparence (alpha/mélange, palettes/tint moteur, orientations et cadence réelle) conservent leurs QA propres. Les124routes non démontrées ne sont pas déclarées cassées : leur couverture HD n'est pas acquise. La présence d'une texture au catalogue ne prouve pas sa substitution dans chaque cellule native.

## Périmètre et méthode

- 243PRO stock : source KEY/BIF +override actif. **243/243conformes exactement** au stock +patchs documentés lot31/nuées ; aucun delta PRO inexpliqué.
- Toutes les ressources déclarées : source,vol,ombre,3traînées,explosion,spread,ring ; palettes comme métadonnées. Contrôleurs VEF/VVC développés récursivement depuis les fichiers actifs, y compris leurs alias et animations alpha.
- Fumées ANIMATE,fragments ANIMATE,particules SPRKCLR,21modes FIREBALL ; références secondaires/explosion/multiple-previous développées jusqu'à fermeture du graphe. Un défaut chez un enfant reste visible dans le verdict parent.
- Les deux champs SPL par défaut/succès sont vides pour les243PRO ; aucun sous-sort PRO oublié sur ces champs.
- Champs désactivés conservés dans `components.csv`, exclus du verdict actif. Conditions dépendantes du contexte runtime conservées de façon prudente. IDs moteur sans PRO rencontrés dans les chaînes consignés dans `engine_children`, sans inventer un BAM ou un job IA.
- Aucun état QA/intégration/installation/release de propriétaire promu par cet audit.

## Images déjà traitées

- Inventaire source existant :107BAM,175contextes source+palette ; **96BAM/164contextes réutilisables**,8masques natifs,3images sans sortie.80contextes ont une QA d'asset,84un pack de palette vérifié.
- Le primaire HD est présent pour189des195PRO déclarant un BAM de vol.5autres utilisent des masques natifs ; LIGHTSTO référence une source absente.48PRO n'ont pas de BAM primaire : ils restent inclus via leurs autres composants/enfants.
- Les49images de vol de la planche restent déjà produites ; elles ne constituent pas49nouveaux jobs.
- Les nouveaux raccords du28octobre sont pris en compte : **catalogue actif537ressources/62099backings**, et non le522du premier audit.

## Fumées,traînées,fragments,explosions

| Rôle local actif | Conclusion |
|---|---|
|29fumées|27utilisent le BAM déjà produit SPSMPUFF, via ANIMATE0300/0301 ; classe native d'animation distincte de la cellule projectile primaire. BGLRYU/SPCL236U sans sortie.|
|4PRO à fragments|TRAPSKUL/TSKULLNP : SKLH déjà produit +SPSHADOW natif ; route de classe animation non démontrée HD. TRAPGLPN/TRAPGLYP : SPGLYPHI sans sortie.|
|4références de traînée|SPCHLGT1/2/3 déjà produits ; route secondaire non démontrée. LIGHTCHA demande cycle9 de SPCHLGT3, absent des cycles du catalogue : vérifier le fallback natif, pas une preuve de crash ou d'image absente.|
|5ombres actives|4masques natifs à conserver ; CHROMORB→SPCHRORB produit, mais la cellule ombre ne possède pas de sélection HD distincte démontrée.|
|44feuilles d'explosion explicites|12viaVVC raccordées statiquement,28BAM d'aire avec scope non démontré,4masques natifs.|
|17feuilles spread|1viaVVC raccordée,15BAM d'aire avec scope non démontré,1masque natif.|
|26feuilles ring|17viaVVC raccordées,9BAM d'aire avec scope non démontré.|
|21modes FIREBALL|Le mode enum n'est pas une ressource BAM ; les champs explicites sont audités séparément. Aucun chemin de substitution global prouvé pour les effets natifs implicites ; ne pas transformer21modes en21jobs IA.|
|54routes sparks|Particules moteur conservées ; aucun upscale raster autonome.|

- **Preuve nouvelle dans BaldurReal.exe installé** : masque `0xf00`, branche0300→`0x30b207`→SPSMPUFF ;0301 partage cette branche.0400→SKLH etSPSHADOW. Dumps `native-animation-entry.txt`,`native-animation-dispatch.txt`,`native-xrefs.txt`.
-0410 utilise l'INI actif→SPGLYPHI. Le vieux fallback GLPHWRDH du binaire n'est pas la source effective lorsque cet INI est présent.
- Smoke: les couleurs PRO et le profil d'animation restent à respecter. Réutiliser SPSMPUFF ne signifie pas figer arbitrairement toutes les fumées dans une palette.
- `hooks.cpp:2830` mémorise la cellule primaire ; `hooks.cpp:2873` couvre la celluleVVC ; `hooks.cpp:4064` sélectionne la texture depuis cette cellule seulement. Ombre/animation smoke ou fragment ne peuvent pas être déduites du primaire. Pour les BAM d'aire, sans instanceVVC démontrée, le résultat est explicitement non prouvé.
- **Correction de lecture utilisée par cet audit** : `PRO[0x14e/150/152]` sont des numéros de séquence des traînées, pas des périodes temporelles. Voir [IESDP PRO](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/pro_v1.htm). Le champ `trailing_periods` de l'ancien parseur garde un nom historique ; l'audit lui applique la sémantique de séquence et n'élimine pas un cycle0.

## Cas à traiter

| PRO | Manque ou décision |
|---|---|
|BGLRY|Fumée BGLRYU : produire seulement ce manque puis raccorder la classe d'animation. Primaire BGLRYT déjà traité.|
|SPCL236|Fumée SPCL236U : même distinction avec primaire SPCL236.|
|TRAPGLPN,TRAPGLYP|Fragments SPGLYPHI : une production commune, deux propriétaires. Primaires déjà traités.|
|LIGHTCHA|Traînées déjà produites ; vérifier cycle9 de SPCHLGT3 et le chemin effectif de rendu.|
|LIGHTSTO|MAGMIS absent de KEY/BIF et du catalogue ; ne pas remplacer par SPMAGMIS par supposition.|
|124partiels|Liste exacte des causes et des enfants dans `124-partiels.csv`. Reprendre le raccord moteur/contrat, sans relancer les images déjà disponibles.|

## Vérifications physiques et moteur

- Manifest actif SHA256 `3477E7211680CF1CF7F067A471A003EBC0A2ECAA4C994136ED257A3AA59A872A`, inchangé entre début et fin du contrôle ; registreSHA conforme.
- **169ressources runtime concernées**,21207textures/10021360128octets : SHA256et tailles vérifiés,0écart. **163carriers BAM** : SHA256vérifiés,0écart. Les ressources sans carrier listé utilisent leur source native ; aucun carrier supplémentaire inventé.
- **139748contrats** de slots/dimensions/phases passent avec le probe natif sur le catalogue actif. Ce probe ne mesure pas des draws ingame.
- DLL/INI/exécutable/shaders conformes au reçu actif ; INI streaming/X4activés. Dernier journal ingame :522ressources chargées et hooks projectile/VVC/FX installés avant les15ajouts réutilisés ; le catalogue537 est vérifié hors jeu, sans inventer une session ingame537.
- Historique acquis préservé : missile magique,assets acceptés et nuées27octobre. Ne pas l'étendre automatiquement à chaque propriétaire/branche.

## Fichiers

- `projectiles-243.csv` : verdict global après parcours des enfants, primaire, images manquantes,scopes douteux,IDs moteur.
- `components.csv` : chaque feuille locale/activité/source/état/chemin/cycle. Les feuilles sont des usages, pas des jobs d'inférence distincts.
- `projectile-links.csv`,`controllers.csv` : arêtes PRO et contrôleurs effectivement lus.
- `summary.json`,`physical-checks.json`,`native-route-evidence.json`,`native-catalogue-current.log` : compteurs,SHA,INI actifs,identité DLL/exécutable,probe.
- `audit.py` : recette de lecture ; aucune installation ni inférence. Instantané source détaillé : `../20261028-v2/`.
