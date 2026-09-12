# Eau BG2EE — solutions runtime/procédurales (voie 2)

Index facultatif. La voie 2 peut être examinée directement lorsqu'une eau est statique, peu lisible
ou manque de mouvement. Aucun audit préalable de toute la voie 1, aucune gate et aucun ordre de
lecture ne sont requis.

## Quand cette voie aide

| Symptôme | Piste route2 |
|---|---|
| Eau propre mais visuellement figée | activer l'identité exacte avec matériau adapté et q mesuré |
| Cycle de tuiles encore saccadé | 36 phases/15 Hz côté WED/TIS + blend 30 FPS côté renderer |
| Effet absent | comparer WED, TIS, page, hash et nom GL live à l'entrée du registre |
| Effet sur une autre carte | restreindre le matcher aux identités/hashes propriétaires |
| Teinte fausse/intermittente | vérifier la résolution slot PVRZ→nom GL avant les assets |
| Pluie non traitée | enregistrer l'identité alternative météo exacte |

## Composition et repli

```text
U2 = mix(overlay_natif, matériau_procédural, q)
sortie = alpha_art_local * art_local + (1-alpha_art_local) * U2
```

- Le matériau modifie le RGB de l'overlay ciblé ; alpha, teinte auteur et passe secondaire restent
  disponibles.
- `q=0` sert de repli natif pour une identité absente, divergente ou ambiguë.
- Le dosage validé courant est `q=0.70` pour les identités listées dans les recettes ; l'ancien
  essai AR0900 q1.00 est historique.
- Le dosage est remis à zéro autour de chaque draw afin d'éviter une fuite entre ressources.

## Identité utile du registre

Une entrée peut utiliser les champs suivants selon ce que le matcher consomme réellement :

```text
WED + variante + hash WED
base TIS + hash + tile count
slot overlay + overlay TIS + hash + tile count
page PVRZ + hash + dimensions
matériau + q + éventuelle ressource météo
```

La précision du registre sert à borner l'effet, pas à créer une procédure de preuve. Lors d'un ajout,
les autres identités courantes sont conservées pour ne pas désactiver leurs eaux.

## Matériaux observés

| ID | Famille | q validé |
|---:|---|---:|
| 1 | WTLAKE et WTPOOL AR1000 | 0.70 |
| 4 | WTSEW AR0404 | 0.70 |
| 5 | WTSWAM AR1607/AR1800 | 0.70 |

Lave, huile, goo et eaux intérieures n'ont pas de généralisation validée.

## AR1000 jour

La voie 1 non générative a supprimé le quadrillage, mais q0 a été jugé figé. La solution validée v5
combine WTPOOL2 bilinéaire périodique, 36 phases/15 Hz, blend 30 FPS, matériau 1 et q0.70. Elle est
bornée à AR1000 jour ; AR1000N reste hors périmètre.

Références :

- `water/manifests/ar1000-wtpool-route2-validated-20260912-v5.json`
- `water/manifests/ar1000-wtpool-route2-installed-20260912-v5.json`
- `scripts/build_ar1000_wtpool_route2_candidate.py`

## Outils moteur disponibles

Build Windows, seulement lorsqu'une nouvelle DLL est nécessaire :

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 `
  -DIEE_BUILD_WINDOWS_DLL=ON -DBUILD_TESTING=OFF
cmake --build build --config Release --target release_bundle
```

Installation transactionnelle d'un candidat, jeu et InfinityLoader fermés :

```powershell
python tools/install_renderer_candidate.py install <candidate-dir>
python tools/install_renderer_candidate.py verify <receipt-or-transaction-dir>
python tools/install_renderer_candidate.py restore <receipt-or-transaction-dir>
```

Ces commandes ne sont pas des gates. Aucun test, rebuild global, packaging ou changement release
n'est impliqué par défaut.
