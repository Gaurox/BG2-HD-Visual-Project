# Validation du bridge d'occlusion native — phase 1

Statut : jalon Phase 1 validé ingame le 2026-08-27 sur BG2EE `2.7.3.0`, pour une
animation de zone `CGameStatic` x4 et une créature `Character` xN dans AR0516. Cette
validation autorise la poursuite du développement du bridge ; elle ne constitue pas une
promotion en release ni une validation de toutes les familles de rendu.

## Décision

Le correctif retenu est global au niveau du moteur. Il ne contient aucun identifiant de map,
resref, occurrence, coordonnée ou forme de décor. Il réutilise, pour chaque objet éligible, le
résultat que le moteur vanilla calcule déjà à partir des polygones WED.

Un masque peint par animation ou par occurrence reste seulement un contournement local. Il ne
doit pas redevenir la solution générale. Une intervention map par map n'est justifiée que si la
map ne fournit pas une occlusion native correcte, ou si l'objet emprunte une famille de rendu qui
n'est pas encore raccordée au bridge.

## Processus validé

Le chemin vanilla compose d'abord l'objet dans une surface FX logique x1. Il appelle ensuite
`CInfinity::FXRenderClippingPolys`, qui applique les polygones d'occlusion WED à cette surface,
puis envoie le résultat natif vers le rendu final.

Le remplacement xN historique liait sa texture externe x2/x4 juste avant le
`CVidCell::RenderTexture` final. Cette texture arrivait donc après l'étape d'occlusion et
remplaçait les pixels natifs déjà découpés. Les polygones WED existaient et étaient exécutés, mais
leur résultat n'était plus présent dans le backing xN.

Le bridge Phase 1 restaure la composition dans cet ordre :

```text
surface FX logique avant occlusion
  -> CInfinity::FXRenderClippingPolys
surface FX logique après occlusion
  -> transfert de visibilité exact pre/post
  -> application GPU au backing x2/x4
  -> CVidCell::RenderTexture final d'origine
```

Le transfert mesure `alpha_après / alpha_avant` lorsque le RGB est inchangé. Il conserve aussi
les deux opérations natives vérifiées dans l'exécutable : effacement complet du pixel et dither
noir fixe `0x4F000000`. Toute mutation RGB inconnue, incohérence de surface, dimension non x2/x4,
erreur GL ou dépassement de borne fait échouer le bridge de manière fermée et conserve le rendu
xN précédent.

## Environnement et preuves

- Exécutable : `BaldurReal.exe` `2.7.3.0`, SHA-256
  `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`.
- DLL QA : SHA-256
  `6FAB82316454C882329119419BEDF2CE9C72682ECB8CEAA74F3E90A9AD53D377`.
- Rollback DLL : SHA-256
  `96F65BC0626B0172DC2D3D3495CDED39B39CDBD03925E8BCFE811CFF905E5D6E`.
- Sauvegarde chargée : `planar-test` ; aucune migration ni donnée de sauvegarde ajoutée.
- Zone et témoin : AR0516, `Search Square 105,117`, branche de premier plan traversant une
  occurrence `SPHINCT` et le personnage.

Captures de preuve :

| Session | Configuration utile | Capture | SHA-256 | Verdict |
|---|---|---|---|---|
| Phase 0 OFF | probe OFF, bridge OFF | `20260827145415_1.jpg` | `8806CC52EA596550BF52BA18D370B9166B5CDEBD5DC5DEB96865D7725FDCFACC` | Défaut présent |
| Phase 0 ON | probe ON, bridge OFF | `20260827150049_1.jpg` | `0BA4D48D69FFC03D4C58CD1A987D0215D7FB041777A5F4504B5C5C4D2521C157` | Même défaut ; probe visuellement neutre |
| Phase 1 zone | bridge ON, créatures xN OFF | `20260827150534_1.jpg` | `BA59FCA8C1892909B2A1457431172264793EBC8FF3F2B63173F0232DA29341E8` | La branche masque `SPHINCT` x4 |
| Phase 1 créature | bridge ON, créatures xN ON | `20260827150738_1.jpg` | `DBC836E2F3F911DF619986EF8F18679579F53A8A6A7D81FF575DD3DEF3AA9B38` | La même branche masque `Character` xN |

Les images OFF/ON ne sont pas comparées octet à octet : l'animation et le personnage changent de
frame. Le gate est l'identité du cadrage et du défaut statique, complétée par les traces natives.

Les traces de la session Phase 0 prouvent, pour les deux occurrences `SPHINCT` visibles :

- owner `CGameStatic` et subject encodant `SPHINCT` ;
- un appel `FXRenderClippingPolys` par occurrence ;
- `successful_clip_calls=1` et `result=1` ;
- dimensions finales logiques `160x120` ;
- remplacement final `area-registry`.

La session Phase 1 zone journalise ensuite :

- préparation et installation du hook Phase 1 ;
- activation du bridge avec masque logique `160x120` et backing x4 ;
- borne transitoire GPU de 64 Mio ;
- aucune erreur, incompatibilité de dimensions ou voie de repli.

La session créature installe les owners `Character` et `MonsterIcewind`. Lorsque le personnage
entre derrière la branche, ses appels passent de `successful_clip_calls=0` à
`successful_clip_calls=1`, avec remplacement final `creature-sprite`. La capture confirme que le
backing xN suit la même frontière que l'occlusion native. Les avertissements FBO de fin de session
proviennent de `gameoverlayrenderer64.dll` pendant la capture Steam et ne sont pas émis par le
bridge.

## Validation automatisée de clôture

- build Debug de `iee_tests` et `iee_bridge_worker_tests` : réussi ;
- CTest Debug : 2/2 tests réussis ;
- build du bundle Release : réussi ;
- DLL Release reconstruite : SHA-256
  `6FAB82316454C882329119419BEDF2CE9C72682ECB8CEAA74F3E90A9AD53D377`, identique à la DLL QA
  testée ingame ;
- suite Python commune : 166/166 tests réussis ;
- `git diff --check` : aucune erreur.

Une première exécution de la suite Python a correctement refusé ses tests d'installation pendant
que `BaldurReal.exe` et `InfinityLoader.exe` étaient encore ouverts. Après fermeture manuelle par
l'utilisateur, la même suite a réussi intégralement. Ce refus est un gate de sécurité attendu, pas
une régression.

## Portée acquise et limites

Le jalon valide le mécanisme commun, pas chaque contenu du jeu :

- `CGameStatic` registry-backed x4 : validé ingame sur AR0516 ;
- `Character` xN : validé ingame sur AR0516 ;
- `Monster` et `MonsterIcewind` : raccordés structurellement, validation d'occlusion ingame encore
  requise ;
- packs v1/v2 et v3 non liés à une occurrence : éligibilité couverte par tests hôte, matrice ingame
  encore requise ;
- le contrat de hash source des jobs sprite inclut le probe et le bridge : un job existant doit
  rafraîchir son runtime et son manifeste après ce commit, mais ses shards et pixels xN n'ont pas
  à être régénérés ;
- v3 lié à une occurrence avec masque de premier plan déjà baked : bypass volontaire pour éviter
  un double masquage ; le masque Photoshop AR0517 reste donc inchangé pendant cette phase ;
- x1, objets non enregistrés, WBM/PVRZ de zone, effets et overlays hors owners modélisés : chemin
  natif inchangé ;
- mémoire : bornes CPU/GPU vérifiées par le code et les tests, mais endurance et pic réel en zone
  chargée encore à mesurer ; la limite existante de pack de 512 Mio n'est pas modifiée.

Le `SPHINCT` inférieur d'AR0516 a ensuite fourni le premier cas résiduel classé : bridge actif,
mais polygone WED attendu absent. L'ajout local d'un polygone `Cover animations` dérivé d'un masque
monde a été validé ingame. Cette exception confirme la frontière de responsabilité du bridge ;
elle ne remet pas en cause son caractère global. Voir
[`native-occlusion-ar0516-wed-correction.md`](native-occlusion-ar0516-wed-correction.md).

## Quand revalider globalement

Une nouvelle matrice représentative est obligatoire après :

1. changement de version ou de hash de l'exécutable, de RVA, signature ou layout des surfaces FX ;
2. modification du hook, du calcul pre/post, du shader, de la restauration d'état GL ou de la
   durée de vie des textures transitoires ;
3. ajout d'une famille de rendu, d'une échelle autre que x2/x4 ou d'un nouveau format de registre ;
4. modification du composite `Character`, de la réalisation de palette ou des overlays
   d'équipement ;
5. promotion d'un pack v3 lié, changement de la politique des masques baked ou retrait du masque
   local AR0517 ;
6. changement de backend graphique, incompatibilité pilote démontrée, ou activation d'une option
   qui possède le viewport/FBO, notamment le SSAA2x plein écran ;
7. préparation d'une release.

Cette revalidation reste une matrice par classes et scénarios représentatifs : elle ne demande pas
de parcourir toutes les branches de toutes les maps.

## Quand examiner un cas individuellement

Un défaut restant doit être classé au cas par cas uniquement si l'un des signaux suivants apparaît :

- `native_clip=absent`, `result=0` ou flag ARE `No Wall` alors qu'un premier plan est attendu ;
- polygone WED absent, incorrect, décalé ou modifié par un mod ;
- objet rendu par une classe non raccordée au bridge ;
- ressource v3 liée qui conserve volontairement un masque baked ;
- mismatch de surface/dimensions, mutation RGB non supportée, rejet des 64 Mio ou erreur GL ;
- différence entre le comportement x1 natif et la frontière attendue par le décor.

Dans ces cas, l'ordre de décision est : vérifier d'abord le chemin et les données WED/ARE,
étendre ensuite le bridge par famille de rendu si nécessaire, et ne retenir un masque manuel que
comme exception locale documentée.

## Gates restant avant release

- Monster et MonsterIcewind derrière une occlusion partielle ;
- `Character` avec équipement complet et dither partiel ;
- packs v1/v2/v3 avec hashes inchangés, dont bypass v3 lié ;
- absence de changement sur map x1, objet non enregistré et ARE `No Wall` ;
- sauvegarde/rechargement, transitions de zones, pause, zoom, resize et plein écran ;
- endurance en zone chargée, mesure des temps GPU et des pics mémoire processus/GPU ;
- rollback puis réactivation sur redémarrage complet ;
- bundle renderer alpha.7 figé avec les marqueurs d'occlusion et toutes les gates ci-dessus.

## Réactivation AR0516 du 2026-08-31

La combinaison DLL `9FCE57D1...FCC98`, registre AR0516 et WED corrigé a été réactivée
transactionnellement avec `EnableNativeOcclusionBridge=true`, puis validée ingame par
l'utilisateur sur `planar-test`. L'intégration manifeste du WED et l'exigence d'un nouveau bundle
renderer compatible ont été approuvées. Voir
[`native-occlusion-reactivation-20260831.md`](native-occlusion-reactivation-20260831.md).

## Rollback

Le rollback fonctionnel est `EnableNativeOcclusionBridge = false` puis redémarrage complet. La
DLL antérieure et son INI ont aussi été sauvegardés sous
`iee-qa-backups/native-occlusion-20260827-1437/` dans l'installation locale. Aucun asset, WED,
ARE, registre Windows, format de sauvegarde ou manifeste de release n'est migré par le bridge.
