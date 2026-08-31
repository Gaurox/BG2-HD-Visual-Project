# Test natif des futures sauvegardes HD vers vanilla

Ce protocole valide les nouvelles chaines de sauvegarde creees avec le garde
save-neutral. Il ne tente pas de reparer les anciennes sauvegardes contenant
deja des blocs prives EEex `X-BIV1.0`.

## Preparer la base vanilla

1. Fermer BG2EE, InfinityLoader et Steam.
2. Verifier que le jeu cible est vanilla : `Baldur.exe` officiel et aucun
   `BaldurReal.exe`.
3. Avec Steam, commencer une nouvelle partie et creer un slot, par exemple
   `VANILLA-BASE`. Fermer completement le jeu.
4. Extraire le contenu de l'archive BG2HD directement a la racine de ce jeu,
   la ou se trouvent `Baldur.exe` et `chitin.key`.
5. Lancer `Install-BG2HD.exe`. Si EEex est absent, installer ses deux
   composants dans ce meme dossier, puis installer le Core et le contenu HD.

Apres installation, Steam et l'icone HD lancent tous deux la version HD. Il
n'existe pas de version vanilla parallele dans cette variante de l'installeur.

## Creer et scanner la sauvegarde HD

1. Lancer le jeu par Steam ou l'icone HD.
2. Charger `VANILLA-BASE`, changer de zone, combattre ou faire apparaitre
   plusieurs creatures, puis creer `HD-SAVECOMPAT-TEST`.
3. Fermer completement le jeu.
4. Demander le choix « tests ciblés / tous / aucun » défini dans
   [`../../../docs/TEST_SELECTION.md`](../../../docs/TEST_SELECTION.md). Si ce test ciblé est
   autorisé, depuis le dossier du jeu, executer :

```powershell
.\tools\Test-BG2HD-FutureSaveCompatibility.ps1 -ReleaseRoot . -SaveDirectory "C:\chemin\vers\HD-SAVECOMPAT-TEST"
```

Le resultat attendu annonce `GAM=0` et `SAV=0`. Le scanner est en lecture
seule : il decompresse en memoire pour rechercher `X-BIV1.0` et ne modifie pas
le slot.

## Revenir vraiment en vanilla

1. Lancer `Uninstall-BG2HD.exe` depuis la racine du jeu.
2. Choisir le **retour vanilla complet**. Cette option retire BG2HD, les
   composants EEex actifs, restaure l'executable officiel sous `Baldur.exe` et
   supprime le layout `BaldurReal.exe`.
3. Ne pas renommer les executables a la main et ne pas utiliser directement
   `BaldurReal.exe` comme substitut de test.
4. Verifier que `Baldur.exe` est officiel, que `BaldurReal.exe` a disparu et
   que Steam lance sans InfinityLoader.

Si EEex etait present avant BG2HD ou si son origine est inconnue, le programme
affiche un avertissement supplementaire : son retrait peut affecter d'autres
mods qui en dependent.

## Validation vanilla decisive

1. Lancer le jeu avec le bouton Steam.
2. Charger `HD-SAVECOMPAT-TEST`.
3. Changer de zone, creer un troisieme slot, le recharger, puis fermer le jeu.
4. Refaire le scanner sur ce troisieme slot ; le resultat doit toujours etre
   `GAM=0` et `SAV=0`.

Le test reussit seulement si le chargement, la sauvegarde et le rechargement
vanilla ne provoquent aucun crash et si les deux scans trouvent zero bloc
`X-BIV1.0`.

En cas d'echec, conserver les slots de test et relever l'etape exacte, le
resultat du scanner et le chemin du nouveau dump. Ne jamais publier un dump ou
une sauvegarde sans retirer les donnees personnelles.
