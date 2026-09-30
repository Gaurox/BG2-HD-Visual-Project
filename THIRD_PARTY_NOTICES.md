# Licensing scope and third-party notices

## Project material

- Original code, scripts, installer logic, configurations and original documentation contributed
  by Gaurox: [MIT](LICENSE), copyright (c) 2026 Gaurox. Commercial reuse and closed-source
  derivatives are permitted; retain the copyright and permission notice in copies or substantial
  portions. MIT does not require a visible UI credit or publication of modified source.
- Optional acknowledgement: `BG2 HD Visual Project — Gaurox — https://github.com/Gaurox/BG2-HD-Visual-Project`.
  This request is not an additional license condition.
- Contributions submitted for inclusion are provided under the license applicable to the files;
  disclose copied code, asset sources and their terms. Existing third-party notices take precedence
  for their material. No CLA or copyright transfer is required.
- Original procedural engine textures documented in
  `engine/InfinityEngine-Enhancer/source-patchee/assets/game-textures/README.md`: MIT for the
  project's original contributions. This does not cover replacements imported from another source.

## Engine and distributed tools

| Component / pinned reference | Terms and retained notice |
|---|---|
| [InfinityEngine-Enhancer](https://github.com/TheForgotten69/InfinityEngine-Enhancer) | MIT; copyright (c) 2025 Gabriel, GitHub TheForgotten69. [Text](licenses/INFINITYENGINE-ENHANCER-MIT.txt); original `engine/InfinityEngine-Enhancer/source-patchee/LICENSE` retained. Gaurox's original modifications: root MIT. |
| [Dshaders 0.3.5](https://github.com/dtiefling/dshaders/tree/4722673a8017c56ace4018b3db459392ecbb75a4) | MIT; copyright (c) 2023 dtiefling. [Text](licenses/DSHADERS-MIT.txt); engine notice retained. Covers Dshaders portions, not native game shaders. |
| [spdlog 1.15.3](https://github.com/gabime/spdlog/tree/6fa36017cfd5731d617e1a934f0e5ea9c4445b13) | MIT, Gabi Melman and contributors. [Text](licenses/SPDLOG-MIT.txt). |
| [fmt 11.2.0](https://github.com/fmtlib/fmt/tree/11.2.0) bundled by spdlog | MIT, Victor Zverovich and contributors. [Text](licenses/FMT-MIT.txt). |
| [MinHook 1.3.4](https://github.com/TsudaKageyu/minhook/tree/c3fcafdc10146beb5919319d0683e44e3c30d537) | BSD-2-Clause; includes HDE32/HDE64 notices. [Complete upstream text](licenses/MINHOOK-BSD.txt). |
| [zlib 1.3.2](https://github.com/madler/zlib/tree/da607da739fa6047df13e66a2af6b8bec7c2a498) | Zlib license. [Text](licenses/ZLIB.txt). |
| [WeiDU 249.00](https://github.com/WeiDUorg/weidu/tree/v249.00), `setup-bg2hd.exe` | GPL-2.0; [upstream COPYING](licenses/GPL-2.0.txt). Separate executable; not relicensed under MIT. A package containing this binary must include its corresponding source and build instructions; see [source contract](licenses/WEIDU-SOURCE.md). |
| [EEex / InfinityLoader](https://github.com/Bubb13/EEex) | External prerequisites, downloaded from upstream by the installation flow; never bundled or relicensed by this repository. |

Notices reflect current source dependencies. They do not establish the provenance of every
historical DLL. Before a public release, confirm the dependency versions of its frozen renderer
against its recorded source revision; retain all applicable notices.

## Development-only dependencies

These are used by local scripts; no Python environment, model, scalepix implementation or
commercial application is included in the mod archive.

| Dependency | Observed terms / handling |
|---|---|
| NumPy, SciPy, PyTorch, psutil | BSD family; retain exact installed-version notices if redistributing an environment. PyTorch also carries bundled-component notices. |
| Pillow | HPND / Pillow upstream terms; do not replace with MIT. |
| requests | Apache-2.0. |
| matplotlib | Matplotlib / PSF-derived terms; inspect bundled assets separately. |
| spandrel | MIT. |
| chainner-ext | MIT OR Apache-2.0; choose and comply with the relevant upstream option when redistributing. |
| [potracer 0.0.4](https://pypi.org/project/potracer/0.0.4/) (`potrace` imports) | GPL-2.0-or-later; used in `pipeline/scripts/build_spatial_spline_alpha.py` and `preview_water_contours.py`. Not bundled. A combined derivative distribution requires a separate GPL compatibility assessment. Root MIT does not override GPL. |
| Local scalepix, used by `pipeline/scripts/xbr2x_batch.js` | Third-party implementation outside Git: xBR (Josep del Rio), MMPX/EPX (Morgan McGuire), MIT portions; HQX LGPL-3.0-or-later. Preserve each embedded notice if importing; the wrapper is not a license grant for scalepix. |
| ReboutCX / SeedVR2 weights and other models | Weights outside Git; redistribution rights not established here. Tool or model-output availability is not a redistribution authorization. |
| Topaz, ComfyUI, chaiNNer, FFmpeg and other local tools | External tools, separately installed; their terms remain applicable. No blanket MIT grant. |

Research references in `sprite/Etudes_Sprite_codex_claude/` are outside root MIT:

| Copied source | Provenance / terms |
|---|---|
| NearInfinity Java references | `NearInfinityBrowser/NearInfinity`, revision `50021b834e0360c6400a6a818626b50edabdd868`; retain Jon Olav Hauglid's copyright and [upstream LGPL 2.1 text](licenses/NEARINFINITY-LICENSE.txt). |
| GemRB references | `gemrb/gemrb`, including revision `5552ade1d360fc487be0450eb2a4044fc969439b`; source headers declare GPL-2.0-or-later. Retain contributor notices and [GPL v2 text](licenses/GPL-2.0.txt). |
| EEex Lua references | `Bubb13/EEex`, revision `6c1f42b8184877d0222652a20c1ef89a1831db53`; root has no general LICENSE at this revision. No blanket redistribution grant is established here. Preserve source/README; settle permission before including these copies in a public distribution. |
| Local research libraries, if present | pefile MIT and Capstone BSD notices stay with their installed copies; not mod payload. |

The reference inventories record upstream paths, revisions and hashes. Original research prose
and scripts remain MIT only to the extent they contain original project contributions; copying
or adapting these references retains their applicable terms. They are not included in mod packages.

## Excluded material and mixed files

Root MIT grants rights only in the project's original material. It does not license:

- Original or transformed BG2EE/BGEE resources: TIS/PVRZ, BAM, WED, palettes, extracted tables,
  audio, video, sprites, portraits, UI, captures, comparison images, masks tied to game artwork,
  or HD derivatives. These remain subject to their respective rights holders' permissions.
- Native game shader portions in engine `assets/override/` and shader templates. A file combining
  native shader code, Dshaders and project changes has distinct provenance; MIT for a contribution
  does not clear the entire shader for redistribution.
- PPE portraits: see `portraits/mod-PPE/LISEZ-MOI.md` and the preserved upstream README. Credits
  alone do not authorize redistribution; no blanket permission is established.
- Copied community code, quotations, external reference documents and excerpts, including GemRB
  GPL material or vendored dependencies in sprite research. Keep their original notices; do not
  infer that a newly tracked research directory is wholly MIT.
- Generated data containing game resources, historical build binaries and archives: determine
  the rights of their contents; original metadata and analysis do not relicense embedded material.
- Trademarks, product names and logos belonging to others.

Purely factual identifiers or measurements need no new claim of ownership; their presence does
not extend MIT to the referenced resource. Original modding-guide prose is MIT; quotations and
copied implementations retain their source terms.

## Release and website

- [Release licensing](https://github.com/Gaurox/BG2-HD-Visual-Project/blob/main/releases/BG2-HD-Upscale/docs/LICENCES.md) separates permissive code from
  [HD asset distribution policy](https://github.com/Gaurox/BG2-HD-Visual-Project/blob/main/releases/BG2-HD-Upscale/docs/DISTRIBUTION_POLICY.md).
  The non-commercial fan-mod policy is not a grant of third-party rights and does not restrict
  reuse of MIT or other independently licensed components.
- A release-specific provenance record and pending rights/lifecycle decisions remain necessary.
  Adding licenses does not approve any existing archive for public distribution.
- Website source has its own licensing files in the separate
  [website repository](https://github.com/Gaurox/bg2-hd-website). Game media and fonts retain
  their own terms; website deployment is separate from this change.
