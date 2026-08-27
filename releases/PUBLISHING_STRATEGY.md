# Strategie de publication BG2 HD

## Etat au 17 aout 2026

La session locale Phase 5B a valide le Core WeiDU, le lancement normal Steam,
le raccourci HD et les zones x4 de l'alpha. Cette preuve ne vaut pas encore
publication : l'installation contenait des assets x2 de developpement et ne
remplace pas la derniere matrice sur une copie Steam distincte.

## Decision

Publier le **contenu HD et le Core Steam** comme mod WeiDU a composants, mais
garder le **renderer** comme prerequis Windows distinct tant qu'il depend d'EEex
et est verrouille sur des empreintes de `Baldur.exe`.

Cette separation est essentielle : les TIS/PVRZ sont des ressources `override` statiques, donc WeiDU sait les installer, sauvegarder et retirer. Le renderer est du code natif charge par EEex ; il ne doit ni etre ecrase aveuglement par le TP2 ni pretendre fonctionner sur une nouvelle version du jeu.

La politique adoptee est celle d'un mod communautaire gratuit et non
commercial : archive intacte, copie legitime du jeu requise, credits/provenance
et canal de retrait, sans executables du jeu, EEex ni InfinityLoader. Elle ne
remplace pas les derniers controles de provenance et de compatibilite avant la
premiere publication.

| Element | Test actuel | Release publique |
| --- | --- | --- |
| Cartes HD | manifeste et staging reversibles | composants WeiDU (`setup-bg2hd.exe`) |
| Core Steam | helper transactionnel valide en Phase 5B | composant WeiDU Core avec rollback et documentation |
| Renderer | bundle fige teste localement | prerequis versionne, checksums, changelog et licence MIT, sous reserve de droits |
| EEex | prerequis externe | prerequis externe, lien vers sa release officielle |
| Project Infinity / WeiDU Install Tool | facultatif | consommateurs possibles du `.tp2`/`.ini`, pas format de publication |
| Assets IA | manifestes, hashes et run source | provenance, licence et changelog par version |

## Ordre et compatibilite

Installer les correctifs officiels puis le renderer/EEex. Pour une installation moddee, installer les gros mods qui modifient les zones avant les composants graphiques BG2 HD ; les cartes HD doivent etre **dernieres parmi les mods qui ecrivent les memes ressources `ARxxxx.TIS`/`PVRZ`**. Chaque mise a jour officielle EE peut effacer les mods : travailler sur une copie dediee et reinstalller/verifier avant de reprendre une sauvegarde.

Le mod est incompatible avec un autre remplacement de la meme carte au meme nom de ressource. Il est intentionnellement cible BG2EE 2.7.3.0 Steam tant que le renderer n'a pas ete revalide sur une autre build/distribution. Il ne prend pas en charge Android, iOS, macOS ni Linux aujourd'hui.

## Checklist avant une alpha publique

1. Verifier chaque payload : 0 tuile hors limite, PSNR du pipeline, hashes SHA-256 et installation/desinstallation propre.
2. Revalider l'archive complete et le renderer sur une installation Steam vierge distincte : chargement, transition, portes, sauvegarde/rechargement, changement de resolution, sortie propre, Steam Verify puis Repair ; publier les preuves nettoyees et les gates qui passent.
3. Licences : ne distribuer aucun fichier du jeu. Conserver licence MIT/attribution du renderer, licence de chaque dependance et provenance des images/IA. Une source recuperable dans un autre mod n'est pas automatiquement redistribuable.
4. Produire un `README` bilingue, changelog, known issues, matrice de compatibilite, hashes et procedure de rapport (capture + logs + `weidu.log`).
5. Ajouter CI de paquetage WeiDU : archives Windows et `.iemod`, a partir d'un tag, avec le packaging maintenu par InfinityTools. Ne publier un installateur multi-plateforme que lorsque le renderer est reellement multi-plateforme.

## Sources consultees

- WeiDU est l'outil standard de developpement/distribution/installation des mods Infinity Engine et documente `COPY_LARGE`, utile pour les PVRZ volumineux : <https://weidu.org/~thebigg/README-WeiDU.html>.
- Le format des ressources concernes (TIS, WED, MOS, BAM, PVRZ compresse) est documente par l'IESDP : <https://burner1024.github.io/iesdp/file_formats/index.htm>.
- G3 distribue ses mods EE avec un installateur WeiDU et rappelle que les mises a jour EE effacent l'etat modde : <https://gibberlings3.github.io/Documentation/readmes/readme-eefixpack.html>.
- Project Infinity est un organisateur d'installations complexes, pas un format necessaire pour un mod simple : <https://kgo.mycenius.com/wp-content/uploads/Mycenius_Using_Project_Infinity_For_The_First_Time_v0-91.pdf>.
- La communaute fournit aussi un front-end WeiDU moderne, qui peut lire les metadonnees `.ini` : <https://github.com/InfinityTools/WeiduInstallTool>.
- Le packageur InfinityTools peut construire automatiquement archives Windows et `.iemod` depuis une release GitHub : <https://github.com/InfinityTools/WeiduModPackager>.
