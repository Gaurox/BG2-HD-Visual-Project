# Installateur ciblé d'animation par zone — conception

Statut : implémenté. Les wrappers et le reçu v1 décrits ci-dessous sont actifs ; toute évolution
conserve ce contrat et ses tests transactionnels.

## Résultat attendu

Installer ou restaurer un pack complet d'une seule zone sans lire, hacher ni modifier les autres
zones installées. Le chemin de production reste l'installation complète ; cet outil sert aux essais
et à la QA ingame.

Invariants :

- jeu et InfinityLoader fermés ;
- pack source terminé `bg2-upscale-area-animation-runtime-pack-v2`, registre v2/v3, x4, sous budget ;
- `iee-assets/areas` déjà présent : ne jamais activer implicitement le mode par zone ;
- cible unique `iee-assets/areas/<AREA_ID>` ;
- DLL, INI, registre global, override, autorités, QA et release en lecture seule ;
- pack source = état complet désiré de la zone, pas un delta ;
- sauvegarde et restauration byte-identiques pour la zone ciblée ;
- aucune écriture en `-VerifyOnly`.

## Architecture retenue

| Fichier | Responsabilité |
|---|---|
| `pipeline/area-animation-area-test/area_animation_area_test.py` | validation, snapshots, reçu, installation, rollback et restauration |
| `pipeline/scripts/Install-AreaAnimation-AreaTest.ps1` | interface PowerShell d'installation ; aucun traitement métier |
| `pipeline/scripts/Restore-AreaAnimation-AreaTest.ps1` | interface PowerShell de restauration ; aucun traitement métier |
| `pipeline/tests/test_area_animation_area_test_transaction.py` | fixtures isolées, fault injection et garanties transactionnelles |

Le cœur Python permet de réutiliser `validate_v2_pack()` de
`run_animation_upscale_30fps_v2.py`, de tester les erreurs entre chaque étape et de suivre le modèle
fail-closed de `inject_build.py`. Les wrappers conservent l'interface PowerShell attendue.

Ne pas refactorer `inject_build.py` dans cette tâche : reprendre ses invariants, pas coupler les
transactions cartes et animations.

## Interfaces

### Installation

```powershell
.\pipeline\scripts\Install-AreaAnimation-AreaTest.ps1 `
  -AreaPack <split-root\ARxxxx> `
  [-GameRoot <fixture-test>] `
  [-BackupRoot <racine>] `
  [-VerifyOnly]
```

- `-AreaPack` : dossier feuille contenant `manifest.json`, le registre et tous les assets.
- `-GameRoot` : omis en production ; résolution par `config://bg2ee_game_root`. Autorisé pour les
  fixtures de test.
- `-BackupRoot` : défaut `backups/animations/area-tests`, déjà ignoré par Git. Refuser une racine
  située dans le pack source ou sous `iee-assets/areas`.
- `-VerifyOnly` : validations et plan uniquement ; aucun dossier, verrou, reçu ou staging créé.

### Restauration

```powershell
.\pipeline\scripts\Restore-AreaAnimation-AreaTest.ps1 `
  -BackupPath <transaction-ou-install-backup.json> `
  [-GameRoot <fixture-test>] `
  [-VerifyOnly]
```

La restauration ne dépend pas du pack source. `-GameRoot` doit correspondre à la racine scellée
dans le reçu.

Les wrappers transmettent les arguments comme tableau, propagent le code retour Python et ne
résolvent aucun autre chemin machine.

## Prévalidation commune

Ordre obligatoire avant la première écriture :

1. Refuser `Baldur.exe`, `BaldurReal.exe` ou `InfinityLoader.exe`. Échouer si la vérification des
   processus échoue.
2. Résoudre la racine de jeu ; exiger `chitin.key`, une DLL et un INI ordinaires.
3. Exiger `iee-assets/areas` existant, non lié et non reparse.
4. Résoudre le pack source et refuser symlink, junction/reparse, enfant ou parent ambigu.
5. Exiger des types JSON stricts, sans coercition chaîne → entier/booléen.
6. Appeler `validate_v2_pack()`, puis renforcer le contrat ciblé :
   - `schema == bg2-upscale-area-animation-runtime-pack-v2` ;
   - `status == completed`, `scale == 4`, `registry_version in {2,3}` ;
   - `runtime_contract.registry_version == registry_version` ;
   - `runtime_budget_enforced is True` et total recalculé `<= 512 Mio` ;
   - `area_id` canonique `[A-Z0-9]{1,8}` et identique au nom du dossier feuille ;
   - inventaire plat exact : manifeste, registre et assets déclarés uniquement ;
   - registre reconstruit byte-identique, tailles et SHA-256 de tous les assets valides.
7. Dans `[Shaders]`, exiger une seule affectation active
   `EnableAreaAnimationX4 = true`; ignorer commentaires et espaces, refuser absent, faux, doublon ou
   affectation dans une autre section.
8. Hacher la DLL installée et l'INI pour le reçu. Ces fichiers ne sont jamais copiés ni modifiés.
9. Valider lexicalement puis physiquement que la cible directe est exactement
   `<areas>/<AREA_ID>`. Refuser tout composant reparse.
10. Photographier seulement la zone cible : présence du dossier, noms relatifs, tailles et SHA-256.
    Refuser sous-dossier, lien, reparse et collision de casse.

L'état « exact » couvre présence/absence du dossier, inventaire, noms et octets. ACL, timestamps et
attributs non fonctionnels sont hors contrat.

Si l'état cible est déjà identique au payload entrant, retourner `already-installed` sans écrire ni
créer de sauvegarde.

## Layout de transaction

```text
<BackupRoot>/
  area-animation-<AREA>-<UTC>-<UUID>/
    install-backup.json
    previous/                 # absent si la zone n'existait pas

<GameRoot>/iee-assets/areas/
  .bg2hd-<AREA>-<UUID>-incoming/
  .bg2hd-<AREA>-<UUID>-previous/   # transitoire pendant la bascule
  <AREA>/
```

Tous les noms transitoires proviennent d'un `AREA_ID` validé et d'un UUID. Avant suppression
récursive, exiger : chemin résolu, parent exact `areas`, préfixe exact, absence de reparse et identité
de transaction conforme au reçu.

Une transaction active par zone. La présence d'un transitoire pour cette zone fait refuser une
nouvelle installation et indique la restauration à exécuter.

## Reçu v1

Schéma : `bg2-upscale-area-animation-area-test-transaction-v1`.

| Champ | Contenu |
|---|---|
| identité | `schema`, `status`, `transaction_id`, timestamps UTC, `area_id` |
| chemins | racine jeu, racine `areas`, cible, pack source, sauvegarde et transitoires |
| pack | SHA-256/taille du manifeste, version registre, SHA-256 registre, inventaire entrant |
| runtime observé | DLL : chemin/taille/SHA-256 ; INI : chemin/taille/SHA-256 et résultat du contrôle |
| état précédent | dossier présent/absent, inventaire complet, empreinte agrégée |
| état installé | inventaire complet, empreinte agrégée |
| récupération | erreur initiale, erreur de rollback et chemins conservés si nécessaire |

Chaque fichier est décrit par `name`, `bytes` et `sha256`. L'empreinte agrégée encode aussi la
présence du dossier afin de distinguer dossier absent et dossier vide.

États autorisés :

```text
prepared -> switching -> installed -> restoring -> restored
                    \-> rolled-back
                    \-> recovery-required
```

Le reçu est écrit atomiquement par fichier temporaire + `os.replace`. Toute restauration vérifie
son schéma, ses agrégats, ses sauvegardes et la racine de jeu avant écriture.

## Installation

1. Prévalider la totalité de la source et photographier la cible.
2. Copier la cible précédente vers `<transaction>/previous`; vérifier chaque hash.
3. Copier le payload entrant, sans `manifest.json`, dans le staging frère ; vérifier inventaire et
   hashes.
4. Écrire/publier le reçu `prepared` seulement après sauvegarde et staging valides.
5. Rephotographier la cible ; refuser si elle a changé depuis l'étape 1.
6. Passer le reçu à `switching`.
7. Si la cible existe, la renommer vers le dossier transitoire `previous`.
8. Renommer le staging vers `<AREA_ID>` avec `os.replace` sur le même volume.
9. Vérifier l'inventaire installé complet.
10. Passer le reçu à `installed`, puis supprimer prudemment le transitoire précédent.

Toute exception après `prepared` déclenche le rollback depuis la sauvegarde vérifiée. Succès du
rollback : `rolled-back`. Échec : `recovery-required`, sans supprimer reçu, sauvegarde ni
transitoires utiles.

La bascule n'est pas un échange atomique de deux dossiers Windows. La combinaison staging complet,
renommages même volume, reçu préalable et reprise depuis les états avant/installé fournit la
garantie transactionnelle.

## Restauration

1. Refuser les processus actifs.
2. Charger et valider le reçu et toutes les sauvegardes sans source externe.
3. Exiger la même racine de jeu et la même cible canonique.
4. Pour `installed`, exiger que la zone courante corresponde exactement à l'état installé du reçu ;
   toute dérive est refusée sans écriture.
5. Pour `prepared`, `switching`, `restoring` ou `recovery-required`, accepter seulement un état
   complet reconnu : avant, installé ou absence transitoire décrite par le reçu.
6. Construire et vérifier un staging frère depuis `previous`, ou un staging d'absence.
7. Passer à `restoring`, basculer par renommages et vérifier l'état précédent complet.
8. Passer à `restored`, puis nettoyer les transitoires validés.

Une seconde restauration d'un reçu `restored` est idempotente : vérifier l'état précédent et ne
rien écrire. DLL et INI peuvent avoir changé depuis l'installation ; les signaler sans les restaurer.

## Tests obligatoires

Créer uniquement des fixtures temporaires ; ne jamais lire ni écrire le vrai jeu.

| Groupe | Cas minimaux |
|---|---|
| lecture seule | install/restore `-VerifyOnly` : arbre complet byte-identique, aucun backup/staging |
| installation | zone absente ; zone existante ; état entrant déjà présent |
| isolation | zone témoin inchangée ; aucune énumération/hash des autres zones par le cœur |
| source | manifest, registre ou asset corrompu ; extra/manquant ; mauvais `area_id` ; hors budget |
| runtime | INI absent/faux/dupliqué ; DLL absente ; processus actif |
| restauration | état précédent exact ; zone précédemment absente ; idempotence |
| fail-closed | reçu/backup altéré ; autre racine jeu ; cible modifiée après installation |
| rollback | échec injecté avant la première bascule, entre les deux renommages et après publication |
| reprise | reçus `prepared`, `switching`, `restoring`, `recovery-required` avec états reconnus |
| chemins | traversal, collision de casse, sous-dossier, symlink/junction/reparse, cible hors `areas` |
| wrappers | appels PowerShell install/verify/restore et propagation des codes retour |

L'injection de panne est un callback privé du cœur Python ; aucune option de panne n'est exposée par
les wrappers de production.

## Fichiers à modifier pendant l'implémentation

1. Ajouter le cœur Python, les deux wrappers et le module de tests ci-dessus.
2. Ajouter `area_animation_area_test.py` à `ANIMATION_SCRIPTS` et le module de tests au groupe
   `animations` dans `pipeline/scripts/test_changed.py`.
3. Étendre `pipeline/tests/test_test_changed.py` pour le routage du cœur et des wrappers.
4. Mettre à jour `pipeline/ANIMATION_PACKS_PAR_ZONE.md` : outil ciblé = QA ; outil complet =
   intégration complète ; rappeler qu'un pack feuille remplace toute la zone.
5. Mettre à jour `pipeline/scripts/README.md` avec install, verify et restore.
6. Ne modifier aucune autorité animation, donnée de production, QA ou release.

## Critères d'acceptation

- Les tests prouvent tous les cas obligatoires, dont trois points de panne.
- Aucun chemin d'installation/restauration ne touche une autre zone.
- `-VerifyOnly` ne modifie ni filesystem ni reçu.
- Une restauration refuse toute dérive de la cible installée.
- Une interruption laisse un reçu et un état récupérable, jamais une zone partiellement copiée.
- Le pack, la DLL et l'INI restent byte-identiques.
- La commande AR2300 ne traite que 7 fichiers runtime/~15,7 Mio au lieu de
  8 671 fichiers/~2,65 Gio.

## Commandes AR2300 après implémentation

```powershell
$pack = 'G:\AI\BG2_Upscale\animations\packs-par-zone\combined-20260905-active-plus-fall2-7b-ingame-test\AR2300'

.\pipeline\scripts\Install-AreaAnimation-AreaTest.ps1 -AreaPack $pack -VerifyOnly
.\pipeline\scripts\Install-AreaAnimation-AreaTest.ps1 -AreaPack $pack

# Utiliser le chemin affiché par l'installation.
.\pipeline\scripts\Restore-AreaAnimation-AreaTest.ps1 -BackupPath '<backup>' -VerifyOnly
.\pipeline\scripts\Restore-AreaAnimation-AreaTest.ps1 -BackupPath '<backup>'
```

Avant l'installation réelle : fermer BG2EE et InfinityLoader. L'installation ne vaut ni QA ingame,
ni sélection, ni intégration release.
