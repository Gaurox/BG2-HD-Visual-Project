# Topaz Gigapixel — correction locale des cartes

Périmètre : source CGI sous masque pour cartes. L'interface utilise le preset distinct décrit dans
[`../interface/README.md`](../interface/README.md).

## Preset autorisé

```powershell
. .\pipeline\scripts\WorkspacePaths.ps1
$topazExe = Resolve-BG2WorkspacePath -Key topaz_gigapixel_exe -RequireExisting

& $topazExe -m cgi --scale 2 `
  -i <source.png> -o <dossier-sortie> --cf -f png `
  --pc 4 --bd 8 --cs preserve -p 1 -d 0 `
  --suffix '-x2-topaz-gigapixel-v8.4.1-cgi-neutre'
```

Avec Gigapixel 8.4.1, `--dn` et `--sh` acceptent `1..100`; `0` est invalide. Pour les valeurs
neutres du modèle, omettre les deux options. Ne pas activer gamma ni Face Recovery.

Le PNG CGI n'est jamais installé seul : il est redimensionné à la cible, composé avec la sortie
SeedVR sous masque utilisateur (blanc = CGI, noir = SeedVR), puis fondu avec le rayon prévu par le
run.

## Contrôles

- commande : `-m cgi --scale 2`, options neutres omises ;
- sortie : dimensions exactes, PNG RGB 8 bits ;
- provenance : commande, version, SHA-256 d'entrée et de sortie dans `run.json` ;
- état : source intermédiaire, sans valeur de QA ni de release.

Valeurs recommandées dans le manifeste :

```json
{
  "denoise": "modèle par défaut neutre (option omise)",
  "sharpen": "modèle par défaut neutre (option omise)"
}
```
