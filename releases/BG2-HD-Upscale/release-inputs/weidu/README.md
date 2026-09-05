# Frozen WeiDU input

`setup-bg2hd.exe` is WeiDU 24900, retained as the reproducible installer input.

- Size: `1,364,992` bytes
- SHA-256: `AD70F5897A6D0BA4B0D226F845A9B14CF345F56CC9697CA8D05CAC9FE4932C1A`

The Windows installer builder copies this exact binary and records its hash in
`BUILD-MANIFEST.json`. Replace it only through an explicit WeiDU upgrade and
rerun the complete dependency, lifecycle, AR0413 and archive gates.
