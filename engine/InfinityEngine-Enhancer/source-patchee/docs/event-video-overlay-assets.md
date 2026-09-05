# Transition vidéo AR1300 / BRIDGE01

Le runtime actuel est spécifique à AR1300. Il ne lit pas de manifeste générique et ne constitue
pas un pipeline réutilisable par simple ajout d'assets. Une nouvelle transition exige une nouvelle
fonction moteur, un manifeste de build et ses propres preuves.

## Contrat codé

| Élément | Valeur |
|---|---|
| Zone / objet | `AR1300` / `BRIDGE01` |
| Rectangle monde x1 | `(2848, 1984)`, `512 × 512` |
| Média | `2048 × 2048` BGRA, 124 frames, 24 fps |
| File décodée | 8 frames maximum |
| Activation | `EnableBridgeTransitionPreview=false` par défaut |
| Implémentation | `src/iee/bridge_transition.*` |
| Assets | `assets/bridge-transition/` |

Fichiers attendus, dont les noms sont codés dans `bridge_transition.cpp` :

```text
BRIDGE01-classic-2048-audio.mp4
BRIDGE01-classic-2048-reverse.mp4
BRIDGE01-classic-audio.wav
BRIDGE01-classic-audio-reverse.wav
BRIDGE01-classic-2048-closed.bgra
BRIDGE01-classic-2048-open.bgra
```

CMake copie ce dossier vers `iee-assets/bridge-transition/` dans `release_bundle` et à
l'installation.

## Signal et lecture

- Le hook observe les indices finaux de tuiles primaire/secondaire réellement rendus, pas le clic
  du levier ; scripts et chargements de sauvegarde suivent ainsi le même chemin.
- Les cellules persistantes/ambiguës sont ignorées et un état identique ne redéclenche pas la
  transition.
- Une inversion en cours reprend depuis la phase logique courante dans la vidéo opposée.
- Les endpoints BGRA lossless évitent un flash pendant le seek ou au repos.
- Media Foundation décode sur un worker borné ; MCI lit les WAV avant/arrière séparés.
- Le rendu se fait après le map flush dans la cible active, avant la composition HUD/menus.
- Les objets GL appartiennent au thread de rendu et sont recréés au changement de contexte.

La correction colorimétrique, le gain spatial 8×8 et le feather de bord sont eux aussi codés dans
`bridge_transition.cpp`; changer l'asset sans les revalider est interdit.

## Modifier correctement

1. Produire un nouveau jeu de six fichiers hors du dossier scellé et fixer leurs hashes/provenance
   dans le run de production.
2. Vérifier dimensions, cadence, endpoints, sens et audio.
3. Modifier ensemble constantes, assets et tests ; ne pas présenter le changement comme une simple
   mise à jour de contenu.
4. Construire un candidat renderer transactionnel et utiliser un reçu neuf.
5. QA : ouverture, fermeture, inversion live, chargement dans chaque état, zoom/dézoom, pause,
   HUD, inventaire et menus plein écran.
6. Intégrer au bundle release uniquement après décision explicite.

Le média livré est actuellement le resize classique 2048. Une variante SeedVR n'est pas approuvée
par déduction et doit suivre le cycle complet ci-dessus.
