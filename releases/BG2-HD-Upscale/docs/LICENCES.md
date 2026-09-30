# Licences, attribution and redistribution status

## Scope / Périmètre

| Material | Terms / distribution status |
|---|---|
| Original Gaurox code, installers and documentation | Standard MIT, copyright (c) 2026 Gaurox. Commercial and closed-source reuse permitted with copyright and permission notice retained. |
| Original InfinityEngine-Enhancer | MIT, copyright (c) 2025 Gabriel / TheForgotten69; upstream notice preserved. Gaurox's original modifications also MIT. |
| Native linked libraries | spdlog / fmt: MIT; MinHook and HDE: BSD notices; zlib: Zlib. Ship their complete texts. |
| Dshaders portions | MIT, copyright (c) 2023 dtiefling. Native game shader portions remain outside this grant. |
| WeiDU 249.00 executable | Separate GPL-2.0 program; ship `licenses/GPL-2.0.txt`, corresponding `sources/weidu-v249.00.tar.gz` and build instructions. |
| EEex / InfinityLoader | External prerequisites; not bundled. |
| Game executables / Steam files | Never redistributed. |
| HD maps, animations, sprites, UI, audio/video, portraits and native shader portions | Third-party or derivative material; rights review and release-specific provenance required. The fan-mod policy is not a permission from their rights holders. |

MIT s'applique au code et aux documents originaux de Gaurox. La conservation de la notice est
obligatoire ; un crédit visible au projet est apprécié mais facultatif. MIT n'impose ni ouverture
des modifications ni interdiction commerciale. Les restrictions de la politique des assets HD
ne s'appliquent pas aux composants sous MIT ou sous une autre licence indépendante.

## Package files

- `LICENSE`: standard Gaurox MIT text.
- `THIRD_PARTY_NOTICES.md`: project scope, credits, dependencies and exclusions.
- `licenses/`: original engine, Dshaders, spdlog, fmt, MinHook/HDE, zlib, GPL-2.0 texts;
  `WEIDU-SOURCE.md` specifies binary/source hashes and build instructions.
- `sources/weidu-v249.00.tar.gz`: WeiDU corresponding source accompanying its executable.
- `bg2hd/manifests/licenses-and-exclusions.json`: release-specific machine record.
- `content.json`: file-level selection/provenance; inclusion alone does not establish permission.

In the source repository, central license files are in the project root (`../../../LICENSE`,
`../../../THIRD_PARTY_NOTICES.md`, `../../../licenses/`). `Copy-BG2HD-LicenseFiles.ps1` copies
them into future packages and verifies the WeiDU binary/source pair. Both package builders call
it before checksums and ZIP creation. Offline: `-WeiDUSourceArchive <pinned-source.tar.gz>`.
The engine's standalone CMake bundle/install carries its own MIT and dependency notices.

## Publication status

This alpha remains unpublished and blocked. License installation does not approve HD asset
rights, a frozen historical DLL's dependency provenance, or clean-install lifecycle validation.
Before public distribution: settle release-specific rights/provenance, check the frozen
renderer's dependency versions and notices, complete lifecycle validation, and publish a contact
route. Never rewrite historical builds merely to add notices; produce a new package when ready.

Forbidden content remains: saves, logs, personal paths, Steam account/configuration files, game
executables, development overrides, backups, captures, source previews, x2 comparison assets,
pending-QA maps and external EEex/InfinityLoader binaries.

See [HD asset distribution policy](DISTRIBUTION_POLICY.md).
