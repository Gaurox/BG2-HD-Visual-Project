# Lot33 — installé pour test2026-10-18

Acceptation ultérieure : [33/33 validés ingame avec SPDEATH3 final sigma4](../../batches/lot33-impacts-accepted-20261018-v1/README.md). Les reçus conservent l'état de cette transaction avant QA et avant le correctif SPDEATH3.

- Autorisation : « installe ingame et donne les clua ». Entrée : `effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1/`,33productions7Bx4/Apollo30,5244phases/182profils ; doublons retirés, durée des cycles natifs conservée sur base15FPS de compatibilité.
- **Installé et vérifié hors jeu** : [`installation.json`](installation.json), [`transaction.json`](transaction.json).322RESREF/43355backings cumulés,278productions ; ajout36noms natifs +33alias droits de test,10428backings/6384386752octets. Les253anciennes ressources/32927backings/contrôleurs/carriers sont conservés ; [`scope-verification.json`](scope-verification.json).
- [33CLUA principales](CLUA.md), [182cycles/modes](CLUA-tous-profils.md), [66comparaisons normal/lumineux](CLUA-transparence.md). Relancer via InfinityLoader, console Ctrl+Espace ; une commande à la fois, sans dégâts. Profils par défaut identiques à la galerie8789 ; boucles bornées à au moins4s.
- Modes des tests principaux : feu/froid/lumière et SPHORPUF en Blended/prémultiplié ; autres fumées/matériaux/sang en normal/RGB droit via `X33Nxx`. Choix de test par famille, pas une observation des flags natifs. Versions explicites `Z33Bxx`/`Z33Nxx` disponibles pour les33 ; aucun masque/RGB de production retouché, aucune suppression automatique du noir.
- Alias natifs BURNHAND→SPBRNHND, SPPRISM3/SPPRISMT→SPPRISM2 ; mêmes productions. Originaux prémultipliés, compagnons normaux séparés.
- Vérification : tous les10780fichiers cibles copiés atomiquement et hashés ; sauvegarde ciblée des deux autorités remplacées. Probe natif candidat+installation :92632contrats de résolution slot/phase/cycle/once,0lecture RGBA au chargement catalogue. Métadonnées20563754octets sous32Mio. [`controls-verification.json`](controls-verification.json) :281VVC, signature/référence/cycle/boucle/FPS/encodage vérifiés.
- DLL/INI/shaders/profil personnages/exécutable identiques par SHA ; budgets inchangés. Jeu/InfinityLoader fermés pendant la transaction.36lignes de suivi installation mises à jour, toutes les autres colonnes conservées ; aucune QA/release modifiée. Jeu non lancé par l'agent.
- **Limite d'intégration** : ces VVC utilisent un owner pris en charge. Leur rendu ne prouve pas le remplacement HD, la cadence ou le mélange des appels natifs directs des vrais sorts ; restent à observer. [Audit avant installation](../../research/lot33-transparency-20261017-v1/REPORT.md). Transparence visuelle ingame en attente de test utilisateur, aucune acceptation déduite.
- Recette/restauration : `pipeline/recipes/effects-lot33-install-20261018-v1/README.md` ; `install.py restore`, jeu/InfinityLoader fermés. Backups locaux ignorés `before/`, état restauré ultérieur dans `restoration.json` ; productions scellées et anciens reçus conservés.

```text
manifest 227EBB21D9DE49B60CEAAAA842493830F1778EDED285E1EDEEDC5C1BA8CD9F65
DLL      FEA4B2B153653461D465B67EB9CC5A762CC97785E511EEBBF5C776348268C246
```
