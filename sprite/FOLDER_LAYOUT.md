# Sprite folder layout

`index/family-groups.csv` est l'autorité de classement. `sprite_layout.py` résout les chemins ; ne
pas les reconstruire depuis des noms de PNJ ou d'items.

```text
ressources/
  <RESREF>/sources/<source-sha256>/
    source.bam[c]               # octets stock
    source.bam                  # forme canonique ; même fichier si BAM non compressé
    source.json                 # provenance KEY/BIF, locator et hashes
families/
  monster-icewind/
    e4xx-goblins/
      e400-mgo1-goblin-axe/
        research/                 # comparisons and non-production trials
        source/                   # manifeste runner + hardlinks vers ressources/, non autorité
        runs/                     # immutable build, runtime, install and QA artifacts
        jobs/                     # mutable descriptors for this sprite only
  playable-characters/
    6102-dwarf-male-fighter/
      cdmb1/
        source/ runs/ jobs/       # source/ idem ; legacy local valide
        variants/<recipe>/
      <resref>-<bam-prefix>/
        source/ runs/ jobs/
    6110-human-female-fighter/
      <resref>-<bam-prefix>/
        source/ runs/ jobs/
    <id>-<character-type>/family-runs/<aggregate>/
catalogs/
  creature-x2-nearest/
    jobs/
    runs/
.work/
  cmake/                          # rebuildable caches; never a content source
index/
  family-groups.csv               # engine_section -> macro/dossier/bucket
  processing.csv                  # cycle de vie famille + variante
  extractions.csv                 # projection des sources matérialisées, si extraction exécutée
  sprite-layout.json              # current locations
  path-migrations.json            # legacy redirects for sealed artifacts
```

Naming:

- Monster family directory: `<high-byte>xx-<mob-plural>`; leaf: `<animation-id>-<bam-prefix>-<mob>`.
- Playable Character family directory: `<animation-id>-<character-type>`; leaf: one unique body or
  equipment sprite, normally `<resref>-<bam-prefix>`.
- Use lowercase `kebab-case`. Keep a run with the workspace that produced it; do not centralize
  unrelated runs.

Macro-groupes :

| Macro | Dossiers |
|---|---|
| `characters` | `playable-characters/`, `legacy-characters/` |
| `monsters` | `monsters/`, `monster-old/`, `monster-icewind/` |
| `composite-monsters` | `composite-monsters/<classe>/` |
| `ambient-static` | `ambient-static/<classe>/` |
| `large-flying` | `large-flying/<classe>/` |
| `effects` | `effects/` |

Créer seulement les feuilles nécessaires. `ressources/` conserve l'unique payload natif canonique.
`materialize_sprite_sources.py --run` crée dans `source/` des liens physiques vers ce payload ; il
ne copie pas les octets et ne produit aucun pixel. Une extraction locale historique valide reste
lisible et ne doit pas être réécrite.

Exception conservée : `playable-characters/6100-minsc/` est un workspace historique matérialisé.
Les nouvelles familles `0x6100` se résolvent sous `6100-human-male-fighter/`; ne pas déplacer ni
réécrire les artefacts Minsc scellés.

Migration invariant: mutable job descriptors use current paths. Immutable manifests keep their
original paths and are resolved through `index/path-migrations.json`; never rewrite their hashes.
The descriptor of an installed catalog is the sole temporary exception: keep its sealed payload
until the transaction is restored or superseded by a new generation.
