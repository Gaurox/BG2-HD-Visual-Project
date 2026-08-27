# Pipeline jour/nuit — méthode validée

Le préflight détecte les paires de WED `ARxxxx` / `ARxxxxN`. Elles utilisent deux jeux d'assets
PVRZ peints et colorés séparément : une variante nuit n'est ni une LUT ni une dérivation de la
variante jour.

**État : méthode validée, référence AR0700/AR0700N (2026-08-17).** Le préflight ne bloque plus une
zone pour la seule présence d'une variante nuit ; `day-night` est une route `required` comme les
autres (alpha, secondaire, eau), pas un arrêt. Traiter jour et nuit comme deux jeux indépendants
reste obligatoire (voir ci-dessous) : ce n'est plus une garde expérimentale, c'est la procédure.

## Outillage (points 2 à 4 de la validation)

`build_upscaled_area.py` et `verify_upscaled.py` sont génériques par resref — ils résolvent le WED
et le tileset uniquement par le code passé en argument, sans jamais supposer qu'il fait 6
caractères. **Le WED nuit `ARxxxxN` fonctionne donc tel quel comme argument `AREA` de ces deux
scripts**, sans mode nuit dédié : il lit sa propre géométrie d'overlay et référence son propre
tileset nuit, et produit son propre `ARxxxxN.TIS` + PVRZ au préfixe dérivé du resref nuit (ex.
`AR0700N` → préfixe PVRZ `A0700N`). Seul
`run_seedvr_comfyui.py` avait besoin d'un ajout : `--tile-kind` accepte
`tuiles-principales-nuit` et `tuiles-secondaires-nuit`, qui résolvent la source dans
`rendus-x1/tuiles-*-nuit/ARxxxxN-...-x1.png` et nomment les sorties avec le code nuit.

### ⚠️ La variante nuit plafonne à 100 pages PVRZ

**C'est la contrainte la plus facile à sous-estimer de tout le pipeline jour/nuit**, et une
version antérieure de ce document affirmait à tort que le préfixe nuit tenait « dans les limites
du format ».

Un resref fait **8 caractères** (`CResRef` est un type de 8 octets dans l'ABI du moteur). Le nom
d'une page PVRZ vaut `préfixe + numéro`, et le `N` de la variante nuit coûte un caractère de plus :

| Variante | Préfixe | Longueur | Chiffres restants | Pages maximum |
|---|---|---:|---:|---:|
| Jour `AR0900` | `A0900` | 5 | 3 | 1 000 |
| **Nuit `AR0900N`** | `A0900N` | **6** | **2** | **100** |

En x4 une page de 2 048 px ne porte que **49 tuiles** (cellule 264 px) : une grande zone nuit
dépasse donc 100 pages dès ~4 900 tuiles, ce qui arrive couramment sur les zones 80×60 avec
secondaires. Le nom devient alors inexprimable et **le jeu plante à l'affichage** (`0xC0000005`,
confirmé sur AR0900N ; AR0300N, AR0500N et AR1000N étaient exposées sans avoir encore planté).

`build_upscaled_area.py` gère ce cas seul : il passe la page à 4 096 **uniquement** quand 2 048
dépasse le plafond du préfixe, et **refuse le build** si 4 096 ne suffit pas, plutôt que d'écrire
un fichier invalide. Rien à faire manuellement — mais lire le compte rendu, qui indique la taille
retenue et le plafond du préfixe.

Deux corollaires à ne pas enfreindre :

- **Ne pas forcer 4 096 sur une variante nuit qui tient en 2 048** (`AR0800N` à 34 pages,
  `AR0400N` à 61 pages restent en 2 048) : la page plus grande ne change rien à l'image.
- **Ne pas reconvertir une variante déjà installée et valide en 2 048.** Seules les variantes
  réellement au-dessus du plafond ont été rebuildées (`AR0300N` 109, `AR0500N` 108, `AR1000N` 101,
  `AR0900N` 118). `AR0900` **jour** fait exception : installée en 4 096 alors qu'elle tenait en
  2 048, héritage du test de validation du correctif — **ne pas la retoucher**.

Règle complète de pagination : [`README.md`](README.md) étape 4. Détail du défaut :
[`PROBLEMES_A_RESOUDRE.md`](PROBLEMES_A_RESOUDRE.md).

## Vérification systématique du catalogue

Chaque zone déjà extraite est vérifiée pour une variante nuit, et ses rendus x1 sont extraits et
contrôlés dans la même arborescence que les rendus jour :

- `areas.csv`, colonnes `has_night_variant`, `x1_tuiles_principales_nuit`,
  `x1_tuiles_secondaires_nuit`, `runs_nuit`, `build_nuit`, `status_nuit` — régénérées par
  `pipeline/scripts/refresh_area_catalog.py` (les trois dernières sont manuelles, comme leurs
  équivalents jour `runs`/`build`/`status`).
- `maps/<AREA>/rendus-x1/tuiles-principales-nuit/<AREA>N-tuiles-principales-x1.png` et
  `tuiles-secondaires-nuit/<AREA>N-tuiles-secondaires-x1.png` — extraits par
  `pipeline/scripts/batch_extract.py --night` et
  `pipeline/scripts/batch_extract_secondary.py --night`, qui ignorent silencieusement
  toute zone sans WED nuit (pas un échec).
- Intégrité contrôlée par `pipeline/scripts/validate_x1_masters.py --all --confirm-all --night`
  (ou `--area ARxxxx --night`), au même sens que pour le jour : recalcul depuis `chitin.key` et
  comparaison octet à octet.

État au 2026-08-17 : **31 zones** ont une variante nuit : AR0020, AR0041, AR0045, AR0046, AR0300,
AR0400, AR0500, AR0700, AR0800, AR0900, AR1000, AR1400, AR1900, AR2000, AR2800, AR2807, OH4000,
OH4100, OH4200, OH4101, OH5100, OH5200, OH5300, OH6000, OH6100, OH6200, OH6400, OH6500, OH8200,
OH8300, OH8400. Les 31 × 2 rendus (principal et secondaire) jour et nuit sont extraits et
**`OK`** à `validate_x1_masters.py`.

**Zones déjà traitées : lire `areas.csv`** (colonnes `status_nuit` / `runs_nuit`). Ne pas
maintenir de liste ici, elle serait fausse au premier build. Les autres se traitent avec la
procédure ci-dessous.

`render_area()` (`area_decode.py`) refuse une demande de rendu nuit sur une zone qui n'a pas de
WED `ARxxxxN` (erreur explicite) au lieu de retomber silencieusement sur le rendu jour.

## Procédure de production

Séquence par zone à variante nuit — le run nuit est **strictement séparé** du run jour (sa propre
correction LAB par morceau, sans référence croisée à l'autre variante) :

```powershell
python pipeline/scripts/audit_area_preflight.py ARxxxx <run-nuit>/00_preflight/ARxxxx-preflight.json
python pipeline/scripts/run_seedvr_comfyui.py --area ARxxxx --run <run-nuit> --preflight <run-nuit>/00_preflight/ARxxxx-preflight.json --tile-kind tuiles-principales-nuit --split-grid <col> <lig> --scale 4 --expected-scale 4
python pipeline/scripts/run_seedvr_comfyui.py --area ARxxxx --run <run-nuit> --preflight <run-nuit>/00_preflight/ARxxxx-preflight.json --tile-kind tuiles-secondaires-nuit --split-grid <col> <lig> --scale 4 --expected-scale 4 --append
python pipeline/scripts/build_upscaled_area.py ARxxxxN <principale-nuit-x4.png> <run-nuit>/05_build <secondaire-nuit-x4.png>
python pipeline/scripts/verify_upscaled.py ARxxxxN <run-nuit>/05_build <principale-nuit-x4.png>
```

Découpe : même politique que le jour ([`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md)), sur
la surface x1 du rendu **nuit** (généralement identique à celle du jour, à vérifier zone par
zone). `--allow-blocked-test` n'est plus requis pour le seul motif jour/nuit ; il reste nécessaire
si un autre bloqueur du préflight est présent par ailleurs (ex. une route eau ou secondaire non
validée sur cette zone précise).

Intégration (jeu fermé, comme au jour) : sauvegarder `ARxxxxN.TIS` + ses PVRZ actifs de
`override\`, copier le build, comparer les SHA-256, ne jamais toucher aux overlays globaux
partagés entre jour et nuit (ex. `WTPOOL`/`WPOOL00` sont référencés par les deux WED sur AR0700 et
ne doivent être écrasés par aucun des deux builds). Faire quatre captures en jeu par variante,
idéalement à la même position jour et nuit, classées dans `06_qa/screenshots/` de chaque run.

Puis proposer la mise à jour du catalogue comme au jour ([`README.md`](README.md) étape 8) —
l'utilisateur confirme, puis écrire `runs_nuit`, `build_nuit`, `status_nuit` dans `areas.csv`, en
plus des colonnes jour.

## Référence — AR0700 / AR0700N (2026-08-17)

Première zone traitée en entier sur les deux variantes, jour et nuit :

- Jour (`AR0700`, run `seedvr2-7b-int8-lab-grid-2x5-x4-jour`) et nuit (`AR0700N`, run
  `seedvr2-7b-int8-lab-grid-2x5-x4-nuit`) upscalés **séparément**, tuiles-principales et
  tuiles-secondaires, grille 2×5, `0 resampled` sur les deux.
- Build + `verify_upscaled.py` : `0 OOB` sur les deux, jour PSNR 34,19 dB, nuit PSNR 36,79 dB
  (round-trip de la primaire uniquement : `verify_upscaled.py` ne rejoue pas la substitution des
  portes, une inspection visuelle en jeu reste nécessaire pour celles-ci).
- Injection : jeu fermé, backups horodatés dans `backups/maps/AR0700-*/` et
  `backups/maps/AR0700N-*/` (ce dernier vide, `AR0700N` n'était pas encore installé), copie des
  deux builds, **0 divergence SHA-256** sur 202 fichiers (101 par variante), overlay partagé
  `WTPOOL`/`WPOOL00` non touché.
- **QA en jeu validée jour et nuit** : zone confirmée par l'utilisateur. C'est cette validation qui
  a levé le bloqueur du préflight.

Ce bloc documente la **méthode validée sur ce cas**, pas l'état courant de la zone : pour savoir
ce qui est installé aujourd'hui, lire `areas.csv`.

## Incident AR0700 (référence pour ne pas répéter l'erreur)

Le 2026-08-15, un run de production antérieur à cette méthode a upscalé `AR0700` (jour seul) en
7B/LAB x4 en ignorant le bloqueur jour/nuit alors actif du préflight, sans utiliser
`--allow-blocked-test` ni documenter la décision dans le run. `AR0700N` n'avait jamais été traité.
Le résultat a été jugé « probablement mal fait » et refait proprement, ce qui a mené à la méthode
ci-dessus. Retenir : passer outre un bloqueur doit toujours être une décision explicite et tracée,
jamais un contournement silencieux d'un run qui échoue autrement.
