# Frozen WeiDU input

`setup-bg2hd.exe` is WeiDU 24900, retained as the reproducible installer input.

- Size: `1,364,992` bytes
- SHA-256: `AD70F5897A6D0BA4B0D226F845A9B14CF345F56CC9697CA8D05CAC9FE4932C1A`

The Windows installer builder copies this exact binary and records its hash in
`BUILD-MANIFEST.json`. Replace it only through an explicit WeiDU upgrade and
rerun the complete dependency, lifecycle, AR0413 and archive gates.

Corresponding source retained for local alpha packaging: `weidu-v249.00.tar.gz`,
755,016 bytes; SHA-256 `C32725CE34D5B3F9D23094DB79A5EEDE079EAF9E69622306F51B8CD5373B8595`.
Origin: official WeiDUorg/weidu tag `v249.00`; `Copy-BG2HD-LicenseFiles.ps1` verifies both pins.
