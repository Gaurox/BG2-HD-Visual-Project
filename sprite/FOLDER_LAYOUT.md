# Sprite folder layout

```text
families/
  monster-icewind/
    e4xx-goblins/
      e400-mgo1-goblin-axe/
        research/                 # comparisons and non-production trials
        source/                   # native extraction
        runs/                     # immutable build, runtime, install and QA artifacts
        jobs/                     # mutable descriptors for this sprite only
  playable-characters/
    6102-dwarf-male-fighter/
      cdmb1/
        source/ runs/ jobs/
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
  sprite-layout.json              # current locations
  path-migrations.json            # legacy redirects for sealed artifacts
```

Naming:

- Monster family directory: `<high-byte>xx-<mob-plural>`; leaf: `<animation-id>-<bam-prefix>-<mob>`.
- Playable Character family directory: `<animation-id>-<character-type>`; leaf: one unique body or
  equipment sprite, normally `<resref>-<bam-prefix>`.
- Use lowercase `kebab-case`. Keep a run with the workspace that produced it; do not centralize
  unrelated runs.

Migration invariant: mutable job descriptors use current paths. Immutable manifests keep their
original paths and are resolved through `index/path-migrations.json`; never rewrite their hashes.
The descriptor of an installed catalog is the sole temporary exception: keep its sealed payload
until the transaction is restored or superseded by a new generation.
