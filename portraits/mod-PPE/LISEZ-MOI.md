# Portraits du mod « Portraits Portraits Everywhere » (PPE)

## Origine

- Mod : **Portraits Portraits Everywhere**, par Smeagolheart et bob_veng
- Dépôt : https://github.com/smeagolheart/Portraits-Portraits-Everywhere
- Dernière mise à jour du dépôt : 24 juillet 2021
- Récupéré par `git clone --sparse`, en ne prenant que `PPE/Portraits` et
  `PPE/RandomPortraits`. Le mod complet (installeur WeiDU, scripts, dialogues)
  n'a **pas** été téléchargé et **rien n'a été installé dans le jeu**.
- **Aucun fichier de licence** n'accompagne le dépôt. Ces portraits sont l'œuvre
  de tiers : à usage personnel, et à créditer en cas de rediffusion.

Le mod couvre BG1EE, Siege of Dragonspear, BG2EE, IWDEE et EET. Une partie des
portraits ne concerne donc pas BG2EE.

## Contenu

| Dossier | Portraits | Description |
|---|---|---|
| `par-creature/` | 2018 | Un portrait par créature parlante, nommé d'après le resref de son CRE |
| `par-categorie/` | 876 | Portraits génériques, classés par type (47 catégories) |

Total : **2894 portraits**, tous en **169×266** (taille moyenne du jeu). Le mod
ne fournit pas les tailles grande et petite : son installeur les dérive.

Chaque portrait est présent sous deux formes : le **BMP d'origine** copié tel
quel, et une conversion **PNG sans perte**.

## Inventaire

`inventaire.csv` — ensemble, catégorie, ressource, nom affiché, dimensions,
empreinte SHA-256.

Le nom affiché a été résolu en lisant les 4735 fichiers CRE de BG2EE et leur
chaîne de nom dans `dialog.tlk`. **1011 des 2018 portraits nommés** (50 %)
correspondent à une créature de BG2EE ; les autres visent les autres jeux
couverts par le mod, et leur colonne `nom` est vide.

`_apercu-categories.png` donne un représentant de chacune des 47 catégories
avec son effectif.

## À ne pas confondre

- `portraits/pnj-rencontres/` — portraits **d'origine du jeu**, extraits des
  ressources, pour les PNJ non recrutables.
- `portraits-recrutables/` — portraits **d'origine du jeu** des 30 compagnons.
- `portraits/mod-PPE/` — ce dossier, portraits **ajoutés par un mod tiers**.
