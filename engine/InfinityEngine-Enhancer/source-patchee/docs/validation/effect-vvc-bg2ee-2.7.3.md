# Effets VVC — BG2EE 2.7.3

Statut : preuve statique complète ; gate ingame pending.

## Sources

- exécutable BG2EE 2.7.3.0 : SHA-256
  `b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57` ;
- EEex Docs commit `5c0b61b619ac1ad3a014cbd205d034677853d20e` : layout x64
  `CVEFVidCell`, taille `0x400`, `m_cVidCell` à `+0x248` ;
- EEex commit `204040502ac920161d60046d90b766b8d2d08152` : locator
  `CVEFVidCell::VFTable` dans `EEex/loader/InfinityLoader.db`.

## Résolution

| Élément | Valeur | Preuve |
|---|---:|---|
| `CVEFVidCell` vtable | RVA `0x59EAC0` | locator EEex résolu dans l'image |
| `CVEFVidCell::Render` | slot 19, RVA `0x254B00` | cible de vtable + désassemblage |
| `m_cVidCell` | `+0x248` | layout EEex Docs + lectures `[rsi+248h]` dans `Render` |
| `CInfinity::FXRenderClippingPolys` | RVA `0x29E4C0` | callsite `0x255098` |
| `CInfinity::FXRender` final | RVA `0x29DF60` | callsite `0x2550D7` |

Signature manifestée de `CVEFVidCell::Render` :

```text
4C 8B DC 55 56 41 57 49 8D 6B A1 48 81 EC D0 00 00 00 48 8B 05 ? ? ? ? 48 33 C4
```

## Contrat runtime

1. Le hook owner lit uniquement `m_cVidCell` via `safe_read`.
2. Le scope transporte `{instance, CVidCell*}` jusqu'au `FXRender` final.
3. `CVidCell::RenderTexture` résout resref, séquence, slot et dimensions dans le
   registre multi-resref.
4. Toute signature, lecture, géométrie, timeline ou texture divergente conserve le
   rendu natif.
5. `FXRenderClippingPolys`, shadow BAM et alpha BAM ne sont pas substitués isolément.

## Gate ingame

Pending pour `SPMINDAT`/Horreur : lancement propre, cast visible, logs de chaque
slot, preuve `x4-bound` ou manifeste `runtime-geometry`, pause/reprise 30 FPS,
fin d'effet, changement de zone, save/load et arrêt propre.
