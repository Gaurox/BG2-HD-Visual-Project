# BG2EE 2.7.3 Manifest Evidence

Status: offline validation complete (2026-08-13); in-game gates pending.
Runbook: [new-build-validation.md](../new-build-validation.md)

## Why A Separate Manifest

Beamdog ships a **unified engine image**: the same executable code serves BGEE,
BG2EE and IWDEE, and the game is selected at runtime by `engine.lua`:

```lua
engine_name = "Baldur's Gate II - Enhanced Edition"
engine_mode = 1 -- 0 = BGEE, 1 = BG2EE, 2 = IWDEE
```

The BG2EE 2.7.3.0 image therefore carries the same `.text` as BGEE 2.7.3 — the
scan below finds both hook targets at the *same* RVAs with the *same* callsite
targets. Only the version resource distinguishes the products, so BG2EE needs
its own manifest entry rather than a product-name addition, and identity
selection must match on version **and** product name (see
`find_manifest_for_identity`). Before that change `detect_manifest` took the
first version match, which for 2.7.3 was always the BGEE entry.

## Executable Identity

- Game: Baldur's Gate II: Enhanced Edition (Steam, app 257350)
- Fixed file version: `2.7.3.0`
- ProductName / FileDescription: `Baldur's Gate II: Enhanced Edition`
- SHA-256: `b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57`
- Size: 7,202,696 bytes
- Image base `0x140000000`, `.text` VA `0x1000`, size `0x588510`, 7 sections
  (identical to the BGEE 2.7.3 image)

## Signature Scan (executable sections only)

| Target | Pattern | Matches | BG2EE 2.7.3 RVA | BGEE 2.7.3 RVA | Shift |
|---|---|---|---|---|---|
| `CInfGame::LoadArea` | unchanged 2.6.6 pattern | exactly 1 | `0x27EBD0` | `0x27EBD0` | `+0x0` |
| `CVidTile::RenderTexture` | unchanged 2.6.6 pattern | exactly 1 | `0x4257C0` | `0x4257C0` | `+0x0` |
| `CResPVR::Demand` | diagnostic 25-byte prologue | exactly 1 | `0x3F6DC0` | `0x3F6DC0` | `+0x0` |
| PVR zlib `uncompress` wrapper | Phase 3e-B0 37-byte pattern | exactly 1 | `0x4000F0` | `0x4000F0` | `+0x0` |

Prologue dumps (24 bytes):

```
CInfGame::LoadArea      @ 0x27EBD0
  40 55 53 56 57 41 54 41 55 41 56 41 57 48 8D AC 24 48 FD FF FF 48 81 EC
CVidTile::RenderTexture @ 0x4257C0
  48 8B C4 44 89 48 20 48 83 EC 48 48 89 58 08 8B DA 48 89 68 10 48 89 70
CResPVR::Demand         @ 0x3F6DC0
  48 89 5C 24 10 48 89 74 24 18 48 89 7C 24 20 41 56 48 83 EC 30 83 79 58
```

The `CInfTileSet` path calls this target at RVA `0x2A46C3`, then reads the resulting texture name
from `CResPVR+0x58` before dispatching `CVidTile::RenderTexture`. Inside `CResPVR::Demand`, the
2.7.3 call sequence creates/binds the engine texture, prepares the PVR payload and invokes the
compressed upload. The diagnostic times those existing phases but does not alter them.

### Phase 3e-B0 decoded-PVR boundary

The 2026-08-30 static audit validated the complete native chain from resource demand through
decoded-buffer release. `CResPVR::Demand+0x15F` calls the unique zlib wrapper at `0x4000F0`; the
native post-decode window at `Demand+0x164` then publishes format/size, uploads the DXT payload and
releases the engine-allocated destination. The C++ manifest carries both exact signatures and the
offline validator decodes all nine phase calls. See
[`map-page-offframe-phase3b0.md`](map-page-offframe-phase3b0.md) for ownership, cache and fallback
evidence. No consuming hook is enabled by this manifest addition.

## Render Callsite Decode (all 11 descriptors)

Every descriptor decoded at the expected intra-function offset with the
expected opcode, and every rel32 target resolves inside `.text` — at the same
addresses recorded for BGEE 2.7.3:

| Callsite | Offset | Opcode | Target RVA | Section |
|---|---|---|---|---|
| CRes_Demand | +0x36 | E8 | 0x3F6D50 | .text |
| DrawBindTexture | +0x6E | E8 | 0x413140 | .text |
| DrawDisable | +0x7F | E8 | 0x413290 | .text |
| DrawColor | +0x89 | E8 | 0x413200 | .text |
| DrawPushState | +0x91 | E8 | 0x413450 | .text |
| DrawColorTone | +0xB6 | E8 | 0x413220 | .text |
| DrawBegin | +0xC0 | E8 | 0x4130B0 | .text |
| DrawTexCoord | +0xCD | E8 | 0x413580 | .text |
| DrawVertex | +0xDB | E8 | 0x4135A0 | .text |
| DrawEnd | +0x17A | E8 | 0x4132D0 | .text |
| DrawPopState (tail) | +0x1AD | E9 | 0x413430 | .text |

11/11 valid.

## Runtime Offset Evidence

- `CVidTile::pRes = 0x100`: bytes at `RenderTexture+0x1D` are
  `48 8B B9 00 01 00 00` (`mov rdi, [rcx+0x100]`), identical to BGEE 2.6.6/2.7.3.
- disp32 constant census over executable sections — counts match the BGEE 2.7.3
  census exactly, which is strong evidence `.text` is unchanged between the two
  products: `0x6590` ×434, `0x6598` ×464, `0x65F8` ×56, `0x1DC` ×77.
- Final layout proof remains the in-game gate: the runtime probes every offset
  through fail-closed `safe_read` paths.

## Native Occlusion Phase-0 Target

Read-only inspection of the same official executable resolves
`CInfinity::FXRenderClippingPolys` at RVA `0x29E4C0`. Its prologue is:

```text
40 57 41 55 48 81 EC 18 01 00 00 48 8B 05 06 65 3C 00 48 33 C4
```

The manifest wildcard covers only the RIP-relative displacement. Disassembly of callers,
including `CGameStatic::RenderBam` at callsite `0x1F2EEF`, confirms the eight-argument x64 call
shape recorded in [the phase-0 protocol](../native-occlusion-phase0.md). The wildcarded prologue
occurs exactly once in the 7,202,696-byte executable (file offset `0x29D8C0`, which maps to RVA
`0x29E4C0`). This evidence authorizes only an opt-in metadata probe; it does not validate a visual
correction.

## Reproducing

`tools/validate_build.py` reproduces every table above against an arbitrary
game executable:

```text
python tools/validate_build.py "<game>/Baldur.exe"
```

## In-Game Gates

**PENDING.** Per the runbook this manifest must not be advertised as supported
until a clean-install session passes: standard tileset, every authored scale
present, one water area, area transition, resize/fullscreen, save/load, and a
clean `ShutdownBindings` shutdown, with verbose + performance logs captured
here.

Note for that session: on BGEE 2.7.3 the first launch found `RenderTexture`
detoured by EEex (a `jmp qword ptr [rip+2]` prologue). The detour-tolerant
`confirm_pattern_with_patched_prologue` path handles it, and BG2EE is expected
to behave identically since EEex hooks the same function.
