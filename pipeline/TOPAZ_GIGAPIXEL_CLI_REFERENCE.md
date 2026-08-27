# Référence impérative — Topaz CGI pour corrections masquées

> **Périmètre : les cartes de zone uniquement.** Cette fiche ne s'applique pas à l'interface.
> Les menus et le HUD utilisent un autre preset validé — **Recovery v2, Detail 50, x4, couleurs
> préservées** — décrit dans [`../interface/README.md`](../interface/README.md). Ne pas transposer
> les règles ci-dessous à ce domaine.

Cette fiche est la source de vérité pour Topaz Gigapixel AI dans le flux désormais validé pour les
**cartes** : **CGI neutre comme source locale sous masque utilisateur**. Les autres modèles et
paramètres testés sont archivés dans `archive/tests-upscale/AR0602/ECHECS_PARAMETRES_MODELES.md`
et ne sont pas des réglages de production.

## Règle bloquante : valeurs neutres de débruitage et netteté

Avec Gigapixel AI `8.4.1`, les options CLI `--dn` et `--sh` n'acceptent que les entiers de `1` à
`100`. La valeur `0` est invalide et le CLI refuse le lancement sans produire de rendu.

| Intention | Commande correcte | Commande interdite |
|---|---|---|
| Conserver le réglage neutre par défaut du modèle | **Omettre** `--dn` et `--sh` | `--dn 0 --sh 0` |
| Imposer une valeur de débruitage ou de netteté | utiliser une valeur entière `1..100` | utiliser `0`, une valeur négative ou supérieure à `100` |

Ne jamais écrire « débruitage 0 / netteté 0 » comme paramètres effectifs d'un run. Employer :
« valeurs neutres par défaut du modèle ; `--dn` et `--sh` omis ».

## Preset autorisé : CGI neutre ×2, source de masque

```powershell
& 'C:\Program Files\Topaz Labs LLC\Topaz Gigapixel AI\gigapixel.exe' `
  -m cgi --scale 2 `
  -i <source.png> -o <dossier-sortie> --cf -f png --pc 4 --bd 8 --cs preserve -p 1 -d 0 `
  --suffix '-x2-topaz-gigapixel-v8.4.1-cgi-neutre'
```

Ce preset signifie :

- modèle CGI : `-m cgi` ;
- échelle `×2` ;
- débruitage et netteté : valeurs par défaut neutres car `--dn` et `--sh` sont absents ;
- gamma désactivée : ne pas ajouter `--gc` ; Face Recovery désactivé : ne pas ajouter d'option de
  récupération faciale ;
- sortie PNG 8 bits, couleurs préservées, compression PNG `4`, une image en parallèle, GPU `0`.

Le PNG CGI n'est pas installé seul : il est composé à la même taille avec SeedVR2 7B à l'aide du
masque utilisateur, blanc = CGI, noir = SeedVR, puis un flou gaussien de rayon `32 px` est appliqué
au masque avant composition.

## Pré-vol obligatoire

Avant de lancer une commande Topaz :

1. Vérifier qu'elle contient `-m cgi --scale 2`.
2. Rechercher explicitement `--dn` et `--sh` dans la commande. S'ils sont présents, vérifier que
   chacun est dans `1..100`; s'ils sont absents, documenter « valeur neutre par défaut ».
3. Après le rendu, valider les dimensions exactes, le PNG RGB et l'empreinte SHA-256 avant de
   classer le fichier.

## Journalisation

Chaque `run.json` doit stocker les paramètres neutres ainsi :

```json
"denoise": "modèle par défaut neutre (option omise ; 0 est refusé par le CLI)",
"sharpen": "modèle par défaut neutre (option omise ; 0 est refusé par le CLI)"
```

Cette formulation évite de confondre le résultat souhaité (neutre) avec une valeur CLI invalide
(`0`).
