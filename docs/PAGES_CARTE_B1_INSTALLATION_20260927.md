# B1 — installation de test, 2026-09-27

- Autorisation utilisateur : « installe » ; candidat [B1.1 + B1.2](PAGES_CARTE_B1_CANDIDAT_20260927.md).
- Installation : **2026-09-27 01:09 Europe/Paris** ; jeu et InfinityLoader fermés, contrôle assuré par l'installateur.
- État : DLL/INI B1 installés et vérifiés ; **aucune validation ingame déduite**. Cet état remplace l'état « non installé » du document de préparation.
- Reçu : [`backups/renderer/20260926T230906729301Z-eeee7a15/renderer-install-receipt.json`](../backups/renderer/20260926T230906729301Z-eeee7a15/renderer-install-receipt.json).
- DLL installée SHA256 : `05F1C2AC1F7811A39795D24A33F6F954D06738DC25B7307BD4DD9A562A97C143`.
- INI installé SHA256 : `92ADEA786228C2782875CE629DE98BC68F8DE32429D0F7C665FE1940E867F960` ; ajout activation B1 + chemin du cache, paramètres antérieurs conservés.
- Cache : `engine/InfinityEngine-Enhancer/source-patchee/build-map-prepare-b1-20260927-v1/private-cache-ar0900-v1` ; 27 copies indépendantes vérifiées par SHA256, chemin référencé par l'INI. À conserver pendant l'essai.
- Sauvegarde A1 : sous-dossier `before/` du reçu ; DLL SHA256 `10FBD4652DC6E6AD8BFA0FE5CB8F4950352970E438BC2FBBC47D554B28BD1FD2`, INI `47979DA9D49EF826014B675D4B0F495842509EED95A6574AFDF71D72B4204B08`.
- Vérification après transaction : `verify` réussi, reçu/candidat/sauvegardes/fichiers installés cohérents. Deux fichiers gérés ; assets et release inchangés.
- Essai utilisateur : même sauvegarde AR0900 **jour**, carte immédiatement après chargement, puis après quelques secondes, puis réouvertures. Corréler logs `Map page B1` et `Map wide-view burst telemetry`.

Retour A1, jeu et InfinityLoader fermés, depuis la racine du dépôt :

```powershell
.tmp/water-python/Scripts/python.exe engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py restore backups/renderer/20260926T230906729301Z-eeee7a15/renderer-install-receipt.json
```
