# INTRO — installation locale et tests CLUA, 2026-11-11 v1

- Demande : installer les3INTRO validées pendant le calcul d'INTRO15F, permettre le test de chaque langue, puis committer avant la fin du calcul long.
- `runtime.py prepare` : défaut/DE issus de `video/assembly/intro-locales-seedvr-1080-20261111-v1/`, PL du master30 accepté `video/assembly/intro-polish-master30-20261111-v1/` ; sorties `video/intro/runs/intro-locales-ingame-20261111-v1/<locale>/intro.wbm`.
- VP8/libvpx,1920×1080/30000/1001,CRF4,b:v30M,qmax12,cpu-used2,2threads par encodage,2encodages maximum simultanés. Aucune interpolation ; Vorbis natif copié, PCM/PTS vérifiés ; SSIM source→runtime >0.99 ;3347/3345/3440images.
- `runtime.py install` : sauvegarde préalable et remplacement atomique de `config://bg2ee_game_root/{movies/intro.wbm,lang/de_DE/movies/intro.wbm,lang/pl_PL/movies/INTRO.wbm}` ; jeu/InfinityLoader fermés avant chaque remplacement. Aucun INTRO15F touché.
- Alias de test neufs dans `movies/` : `HDINEN.wbm`, `HDINDE.wbm`, `HDINPL.wbm` ; copies hash-identiques des3runtimeWBM. Reçu/sauvegardes : `video/installations/intro-locales-seedvr-20261111-v1/installation.json` et `before/`.
- État : installation locale pour test utilisateur ; ne pas déduire une QA ingame ni une intégration release.

## Tester sans changement de langue

- Console déjà activée dans le profil utilisateur (`Program Options/Debug Mode=1`) ; aucun changement du profil.
- Charger une partie, **Ctrl+Espace**, puis une commande à la fois :

```lua
C:PlayMovie("HDINEN") -- fichier commun/défaut
C:PlayMovie("HDINDE") -- allemand
C:PlayMovie("HDINPL") -- polonais, cadence30 du master
```

- Commandes canoniques selon la langue active : `C:PlayMovie("INTRO")` ; les alias évitent un changement d'interface/langue ou le démarrage d'une nouvelle partie.
- Référence des commandes et du raccourci : https://gibberlings3.github.io/iesdp/appendices/clua/bgee.htm ; la lecture effective reste à confirmer par l'utilisateur.
- Si changement de langue souhaité : jeu fermé, paramètre `SetPrivateProfileString('Language','Text','fr_FR')` du `Baldur.lua` utilisateur ; `de_DE`/`pl_PL` pour DE/PL, puis relancer. Le profil courant est français ; il reste inchangé ici.

## Restauration

- Fermer jeu/InfinityLoader ; suivre chaque entrée du reçu : recopier son `backup` vers `target` si `existed_before=true`, puis vérifier `before_sha256` ; retirer seulement les3alias créés, après vérification de leur `after_sha256`.
- Sauvegardes immuables ; ne pas substituer une source vanilla du dépôt au fichier réellement sauvegardé. Aucune suppression d'autres vidéos ni modification du staging, TP2 ou manifeste release.
