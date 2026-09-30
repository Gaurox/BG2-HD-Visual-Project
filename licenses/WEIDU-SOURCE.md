# WeiDU 249.00 — binary and corresponding source

| Item | Value |
|---|---|
| Unmodified binary | `releases/BG2-HD-Upscale/release-inputs/weidu/setup-bg2hd.exe` |
| Binary SHA-256 | `ad70f5897a6d0ba4b0d226f845a9b14cf345f56cc9697ca8d05cac9fe4932c1a` |
| Upstream | <https://github.com/WeiDUorg/weidu/tree/v249.00> |
| License | [Upstream GPL-2.0 COPYING](GPL-2.0.txt) |
| Corresponding-source archive | <https://codeload.github.com/WeiDUorg/weidu/tar.gz/refs/tags/v249.00> |
| Source SHA-256 | `c32725ce34d5b3f9d23094db79a5eede079eaf9e69622306f51b8cd5373b8595` |
| Package destination | `sources/weidu-v249.00.tar.gz` |
| Build instructions | Archive `README.md`, `sample.Configuration`, `Makefile`; [upstream README](https://github.com/WeiDUorg/weidu/blob/v249.00/README.md) |

The package builders include this source archive beside the separate WeiDU executable (GPL v2
section 3(a)). A bare upstream link is not used as a substitute for accompanying source.
The copier checks both hashes and refuses a different WeiDU binary until this source contract
is updated. No personal written-source offer is made.

Build requirements documented by upstream: OCaml 4.04–4.11 without forced safe strings,
platform C toolchain, make, Perl, Elkhound; optional documentation/archive tools. Copy
`sample.Configuration` to `Configuration`, set `OCAMLDIR`, then `make weidu` or the appropriate
platform packaging target. Requirements and instructions are preserved inside the source archive.

Offline build: pass `-WeiDUSourceArchive <local-copy-of-the-pinned-tar.gz>` to the package builder.
Otherwise the archive is downloaded from the URL above into the new package's temporary tree
and verified before checksums and ZIP creation. Old archives are not rewritten.
