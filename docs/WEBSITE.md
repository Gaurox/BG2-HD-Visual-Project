# Site public

## Autorité

| Élément | Valeur |
|---|---|
| Production | `https://bg2hd.gaurox.dev/` |
| Dépôt source unique | `https://github.com/Gaurox/bg2-hd-website.git` |
| Checkout local | `config://website_checkout` |
| Racine statique | racine du dépôt source, jamais un sous-dossier `website/` |

`config://website_checkout` est résolu par `config/workspace-paths.local.json` ou
`BG2HD_WEBSITE_ROOT`. Le dépôt BG2 principal reste l'autorité des inventaires, décisions, QA et
manifests ; le site contient seulement une présentation et des relevés copiés manuellement.

## Préflight obligatoire

```powershell
$siteRoot = python -c "from pipeline.scripts.workspace_paths import get_path; print(get_path('website_checkout', required=True))"
git -C $siteRoot rev-parse --show-toplevel
git -C $siteRoot remote get-url origin
git -C $siteRoot status --short
```

Attendus : checkout résolu, remote `Gaurox/bg2-hd-website`, état Git inspecté avant édition.

## Emplacements interdits

- `BG2_Upscale/website/` dans tout checkout du projet principal ;
- toute copie de site sous `H:` ;
- tout clone temporaire comme source de travail.

Le dépôt nu `H:/logiciels/BG2_Upscale/depot-git.git` est un historique du projet principal, pas
une source du site. Ne pas extraire son ancien répertoire `website/`.

## Modification et publication

1. Modifier uniquement le checkout `config://website_checkout`.
2. Conserver les pages EN/FR synchronisées et les URLs canoniques sans extension.
3. Lire `README.md` et `SEO_GOOGLE.md` dans le dépôt du site.
4. Ne jamais déduire les chiffres Progress : les recopier depuis les autorités du projet principal.
5. Aucun commit, push ou déploiement sans demande explicite.
6. Après publication, vérifier `/`, `/fr/`, `/progress`, `/fr/progress`, `/gallery`,
   `/fr/gallery`, `/robots.txt`, `/sitemap.xml` et une URL inexistante.

## Nettoyage du 5 septembre 2026

Les copies physiques `G:/AI/BG2_Upscale/website/`,
`H:/logiciels/BG2_Upscale/projet/website/` et le clone temporaire de publication ont été retirés
après comparaison avec le dépôt source. Elles ne doivent pas être recréées.
