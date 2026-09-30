# InfinityEngine-Enhancer — notices and scope

| Material | License / notice |
|---|---|
| Original engine by Gabriel / [TheForgotten69](https://github.com/TheForgotten69/InfinityEngine-Enhancer) | [MIT, copyright (c) 2025 Gabriel](LICENSE); preserved upstream notice. |
| Original BG2 HD changes by Gaurox | [MIT, copyright (c) 2026 Gaurox](licenses/BG2HD-MIT.txt). |
| Dshaders 0.3.5 portions, commit `4722673a8017c56ace4018b3db459392ecbb75a4` | [MIT, dtiefling](licenses/DSHADERS-MIT.txt). |
| spdlog 1.15.3, `6fa36017cfd5731d617e1a934f0e5ea9c4445b13` | [MIT](licenses/SPDLOG-MIT.txt). |
| fmt 11.2.0, bundled in spdlog | [MIT](licenses/FMT-MIT.txt). |
| MinHook 1.3.4, `c3fcafdc10146beb5919319d0683e44e3c30d537` | [BSD-2-Clause and embedded HDE notices](licenses/MINHOOK-BSD.txt). |
| zlib 1.3.2, `da607da739fa6047df13e66a2af6b8bec7c2a498` | [Zlib](licenses/ZLIB.txt). |

Ship `LICENSE`, this notice and `licenses/` with the DLL and retain notices in source copies.
The CMake bundle/install targets copy these files. Dependency updates require matching notices.

Original procedural `iee-textures/` material documented by its README is covered by the project
MIT contribution notice. Game-derived bridge video/audio, effect images, native shader portions
and other game resources are excluded from that grant. Dshaders attribution covers only its
own portions; it does not establish rights to the entire mixed shader suite. Redistribution of
these assets requires its own provenance and permissions assessment.

EEex / InfinityLoader are external prerequisites, not included in this engine bundle.
The full project scope is documented in
[BG2 HD third-party notices](https://github.com/Gaurox/BG2-HD-Visual-Project/blob/main/THIRD_PARTY_NOTICES.md).
MIT permits commercial and closed-source reuse of covered code with retained notices.
Visible credit to BG2 HD Visual Project / Gaurox is appreciated but optional.
