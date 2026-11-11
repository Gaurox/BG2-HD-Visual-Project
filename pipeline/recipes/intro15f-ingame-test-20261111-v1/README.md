# INTRO15F — installation locale30 et console, 2026-11-11 v1

- Demande :4INTRO15F finales acceptées → installer, donner commandes par langue, committer le travail vidéo. QA visuelle : `video/index/qa-decisions/INTRO15F/20261111-four-apollo30-assemblies-accepted-v1.json` ; QA ingame reste à faire.
- Entrées : `video/final/intro-30fps-20261111-v1/INTRO15F/{default,de_DE,it_IT,pl_PL}/intro15f.wbm` ; manifeste technique `video/index/intro-finals30-20261111-v1.json` ; VP8/Vorbis natif,1920×1080/30fps,5148images (PL5147),audio PCM/PTS vérifiés,SSIM échantillonné >0.99.
- `python -B pipeline/recipes/intro15f-ingame-test-20261111-v1/install.py prepare` : vérifie jeu/InfinityLoader fermés,SHA sources/absences alias, sauvegarde les4fichiers effectivement installés dans `video/installations/intro15f-apollo30-20261111-v1/before/` ; reçu `installation.json`,état `prepared`.
- `.../install.py install` : vérifie à nouveau sauvegardes/sources/destinations,jeu fermé avant chaque remplacement ; copies temporaires vérifiées puis `os.replace`, SHA des8destinations vérifiés après installation. Recette limitée aux4INTRO15F et4alias ; aucune modification des3INTRO existantes, profil utilisateur ou release.
- Cibles canoniques `config://bg2ee_game_root/` : `movies/intro15f.wbm`, `lang/de_DE/movies/intro15f.wbm`, `lang/it_IT/movies/intro15f.wbm`, `lang/pl_PL/movies/INTRO15F.wbm`.
- Alias neufs dans `movies/` : `HD15EN.wbm`, `HD15DE.wbm`, `HD15IT.wbm`, `HD15PL.wbm` ; copies hash-identiques de la variante correspondante. Index installation courant : `video/index/intro15f-ingame-test-20261111-v1.json` ; copie du reçu final sous `metadata/installation.json`.

## Test console

- Charger une partie puis **Ctrl+Espace** ; console déjà activée (`Program Options/Debug Mode=1`), profil inchangé. Une commande à la fois ; aucun changement de langue/rechargement nécessaire entre vidéos :

```lua
C:PlayMovie("HD15EN") -- défaut/anglais
C:PlayMovie("HD15DE") -- allemand
C:PlayMovie("HD15IT") -- italien
C:PlayMovie("HD15PL") -- polonais
```

- `C:PlayMovie("INTRO15F")` joue la variante résolue selon la langue du jeu. Pas de version française séparée disponible ; le défaut correspond au fichier commun anglais.
- Les3INTRO précédentes restent testables avec `HDINEN`, `HDINDE`, `HDINPL` ; reçu précédent `video/installations/intro-locales-seedvr-20261111-v1/installation.json` inchangé.
- Référence raccourci/commande : https://gibberlings3.github.io/iesdp/appendices/clua/bgee.htm . Ne pas déduire une validation ingame de l’installation ou de l’acceptation MP4.

## Restauration ciblée

- Fermer jeu/InfinityLoader ; suivre uniquement les8entrées du reçu. Vérifier le SHA actuel égal à `after_sha256` avant de modifier une cible.
- Si `existed_before=true` : recopier `backup` vers `resolved_target`, vérifier `before_sha256`. Sinon : retirer uniquement l’alias désigné après vérification du SHA. Garder reçu/sauvegardes historiques immuables ; ne pas substituer une source vanilla à la sauvegarde réelle.
