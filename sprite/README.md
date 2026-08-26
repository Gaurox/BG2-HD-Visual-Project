# Sprite workspace

Source of truth for a sprite location:

1. `index/manifest.json`: game and inventory snapshot.
2. `index/sprite-layout.json`: current physical workspace and job locations.
3. `index/path-migrations.json`: legacy-path redirects for immutable manifests only.
4. `FOLDER_LAYOUT.md`: placement rules for a new asset.

```text
sprite/
  families/
    monster-icewind/<code-family>/<animation-id>-<prefix>-<mob>/
      research/ source/ runs/ jobs/
    playable-characters/<animation-id>-<character-type>/<unique-sprite>/
      source/ runs/ jobs/
  catalogs/creature-x2-nearest/
    jobs/ runs/
  index/
  .work/
  docs/
```

Rules:

- One physical workspace per unique sprite. Keep its native extraction in `source/`, test material in
  `research/`, and every build/runtime/QA artifact in `runs/`.
- Keep aggregate Character work in `family-runs/` below its Character family. Keep global catalog
  runs under `catalogs/`.
- Never edit a file inside an existing `runs/` directory. Historic paths inside sealed manifests are
  resolved by `index/path-migrations.json`.
- The currently installed catalog descriptor keeps its sealed legacy payload until that ingame
  transaction is restored or replaced by a new catalog generation; its physical file is still in
  `catalogs/creature-x2-nearest/jobs/`.
- Create future family jobs through `pipeline/scripts/generate_sprite_family_append.py`; it creates
  only `families/.../jobs/x2-nearest-vN.json` and `catalogs/.../jobs/append-...-vN.json`.
- `.work/` is rebuildable tooling state, never a content source. `docs/archive/` is historical and
  not an operational source of truth.
- Do not create sprite assets under `maps/` or global `animations/` directories.

## Operational routing

1. Read `index/README.md`, then verify `index/manifest.json` before selecting an animation.
2. Resolve the animation, family, BAM resources and optional ITM through the CSV files in `index/`.
3. Require `runtime_supported=yes`, `pipeline_ready=yes`, an empty `blocker`, and an empty
   `override_collision` before a production build.
4. Use `docs/archive/SPRITE_FAMILY_CATALOG_APPEND_PIPELINE.md` for every new family append. The
   other archived runbooks describe retained contracts and historical procedures; resolve their
   legacy paths through `index/path-migrations.json`.
5. Regenerate and test the inventory after a change to the game snapshot, schema, classification,
   runtime limits or palette mapping:

```powershell
python pipeline/scripts/build_sprite_inventory.py
python -m unittest pipeline.tests.test_sprite_inventory pipeline.tests.test_creature_sprite_x2_pipeline
```

`pipeline_ready=yes` proves only that known automated prerequisites pass. It is not a build,
installation or ingame validation result.

## Politique de QA ingame pilotée

The runner and PowerShell transaction scripts never launch or close the game. Before any install,
restore or sampling change, require the game and InfinityLoader processes to be stopped. Do not
alter an active transaction while either process is running.

After an authorized install, the operator launches the game, exercises every animation and every
representative prefix in the sealed QA contract, checks composition, palette, equipment layers,
orientations and transitions, then closes the game. Automated build gates still cover every catalog
resource. The agent runs `qa-log` only against that completed post-install session. Record a pass
with `record-qa` only when all automated gates pass and the user explicitly accepts the visual
result. `LINEAR`, `pending-qa`, partial sessions, captures, saves, `override` files and temporary
directories are never `validated-installed` evidence.

QA validation does not authorize release integration. Updating the release manifest, staging,
`content.json` or the archive requires a separate affirmative user decision.
