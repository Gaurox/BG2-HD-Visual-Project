# Transaction de candidat shader-suite

## Contrat

`tools/install_shader_suite_candidate.py` gère uniquement une liste explicite parmi :

```text
override/fpSprite.glsl
override/fpSELECT.glsl
override/fpDraw.glsl
override/fpTone.glsl
override/fpFONT.glsl
override/fpSEAM.glsl
override/fpYUV.glsl
override/fpYUVGRY.glsl
```

Le candidat D3 contient les huit fichiers. Aucun glob du répertoire jeu `override/` n’est géré.
Le manifeste scelle le hash candidat et l’état initial attendu de chaque cible. Un fichier inattendu,
une casse non canonique, un lien ou un hash divergent bloque l’installation ; aucune fusion.

## Préparation D3

Depuis la racine du dépôt, avec `ENGINE=engine/InfinityEngine-Enhancer/source-patchee` :

```powershell
python ENGINE/tools/install_shader_suite_candidate.py prepare `
  ENGINE/assets/override `
  sprite/catmull-rom/runs/<run-id>/candidate/shaders `
  --baseline-override sprite/catmull-rom/runs/d2-20260909-shader-suite-capture/initial/override
```

Le répertoire candidat doit être nouveau. Le baseline D2 contient le `fpSEAM.glsl` IEE réellement
installé avant D3 ; l’absence des sept autres fichiers est donc explicite. Relire l’état live avant
usage : ce baseline ne donne aucune autorisation d’écraser une modification ultérieure.

Sortie :

```text
candidate/shaders/
  shader-candidate.json
  override/<liste explicite>
```

## Installation, vérification, restauration

Fermer BG2EE et InfinityLoader. Prévalidation obligatoire :

```powershell
python ENGINE/tools/install_shader_suite_candidate.py install <candidate/shaders> --verify-only
```

Installation :

```powershell
python ENGINE/tools/install_shader_suite_candidate.py install <candidate/shaders>
```

Le reçu, les payloads et sauvegardes sont autonomes sous `backups/shader-suite/<transaction>/`.
Conserver ce répertoire jusqu’à restauration vérifiée.

```powershell
python ENGINE/tools/install_shader_suite_candidate.py verify <reçu-ou-transaction>
python ENGINE/tools/install_shader_suite_candidate.py restore <reçu-ou-transaction>
python ENGINE/tools/install_shader_suite_candidate.py verify <reçu-ou-transaction>
```

Un échec de publication déclenche un rollback compensatoire. Une cible modifiée par un tiers reste
intacte et place/refuse la transaction en récupération. La restauration retire un shader absent
initialement seulement s’il correspond encore au hash candidat.

## Ordre avec le renderer

1. Prévalider transaction shader et transaction DLL/INI.
2. Installer les shaders.
3. Installer DLL/INI.
4. Vérifier les deux reçus avant lancement.
5. Après QA, fermer jeu/loader ; restaurer DLL/INI, puis shaders.
6. Vérifier les états initiaux des deux reçus.

Deux reçus coordonnés ne constituent pas une transaction disque atomique unique. Si la seconde
installation échoue, restaurer immédiatement la première. Installation de développement, QA et
intégration release restent trois décisions distinctes.
