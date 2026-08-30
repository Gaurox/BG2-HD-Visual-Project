#!/usr/bin/env python3
"""Offline validation of a game executable against the build manifests.

Implements the offline half of docs/new-build-validation.md (steps 1-5) and
emits the tables used by docs/validation/*-evidence.md:

    python tools/validate_build.py "<game>/Baldur.exe"

Exits non-zero if any required check fails, so it can gate a manifest change.
No third-party dependencies; parses the PE image directly.
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import sys

# Signatures shared by every validated 2.6.6.x / 2.7.3.x build so far.
PATTERNS = {
    "CInfGame::LoadArea": "40 55 53 56 57 41 54 41 55 41 56 41 57 48 8D AC 24 48 FD FF FF",
    "CVidTile::RenderTexture": "48 8B C4 44 89 48 20 48 83 EC 48 48 89 58 08 8B DA 48 89 68 10",
}

# Diagnostic-only target currently evidenced on the unified 2.7.3 image. It
# is intentionally not projected onto 2.6.6 without a matching binary audit.
PVR_DEMAND_PATTERN = (
    "48 89 5C 24 10 48 89 74 24 18 48 89 7C 24 20 41 56 "
    "48 83 EC 30 83 79 58 00"
)

# Phase 3e-B0 evidence on the unified 2.7.3 image. The wrapper adapts the
# engine's 32-bit Windows zlib lengths before calling the embedded zlib 1.2.11
# implementation. The consume window begins immediately after that call and
# proves that native code retains PVR field publication, upload and release.
PVR_UNCOMPRESS_PATTERN = (
    "40 53 48 83 EC 20 8B 02 48 8B DA 48 8D 54 24 38 89 44 24 38 "
    "E8 ? ? ? ? 8B 4C 24 38 89 0B 48 83 C4 20 5B C3"
)
PVR_CACHE_RELEASE_PATTERN = (
    "48 89 5C 24 08 57 48 83 EC 20 33 FF 48 8D 15 ? ? ? ? 48 8B D9 "
    "39 79 58 0F 84 ? ? ? ?"
)
CRES_FILE_OPEN_PATTERN = (
    "40 53 55 56 57 41 54 41 56 41 57 48 81 EC 80 02 00 00 "
    "48 8B 05 ? ? ? ? 48 33 C4 48 89 84 24 70 02 00 00"
)
PVR_CONSUME_WINDOW_OFFSET = 0x164
PVR_CONSUME_WINDOW_PATTERN = (
    "8B 4F 30 48 8D 57 34 44 8B 47 08 48 03 D1 44 8B 4C 24 40 "
    "44 89 43 5C 44 2B CA 8B 4F 1C 44 03 CF 89 4B 64 8B 47 18 "
    "89 43 68 8B 4F 1C 48 89 54 24 20 8B 57 18 E8 ? ? ? ? "
    "48 8B CF E8 ? ? ? ?"
)

# label, offset from CResPVR::Demand, exact target on the unified 2.7.3 image
PVR_PHASE_CALLS = [
    ("eviction texture delete", 0xA9, 0x413270),
    ("128-entry cache shift", 0xC1, 0x4FA710),
    ("CRes resource demand", 0xDC, 0x402A00),
    ("texture creation", 0x12E, 0x413350),
    ("texture bind", 0x138, 0x413140),
    ("native decoded-buffer allocation", 0x143, 0x502678),
    ("zlib uncompress handoff", 0x15F, 0x4000F0),
    ("compressed texture upload", 0x198, 0x413240),
    ("native decoded-buffer release", 0x1A0, 0x4FDAB8),
]

# Reference RVAs per known build, for shift reporting only.
REFERENCE_RVAS = {
    "2.6.6": {"CInfGame::LoadArea": 0x27E710, "CVidTile::RenderTexture": 0x4247E0},
    "2.7.3": {
        "CInfGame::LoadArea": 0x27EBD0,
        "CVidTile::RenderTexture": 0x4257C0,
        "CResPVR::Demand": 0x3F6DC0,
        "PVR zlib::uncompress wrapper": 0x4000F0,
        "CResPVR cache release": 0x3F70B0,
        "CRes file open": 0x408430,
    },
}

# name, intra-function offset from RenderTexture, expected opcode
CALLSITES = [
    ("CRes_Demand", 0x36, 0xE8),
    ("DrawBindTexture", 0x6E, 0xE8),
    ("DrawDisable", 0x7F, 0xE8),
    ("DrawColor", 0x89, 0xE8),
    ("DrawPushState", 0x91, 0xE8),
    ("DrawColorTone", 0xB6, 0xE8),
    ("DrawBegin", 0xC0, 0xE8),
    ("DrawTexCoord", 0xCD, 0xE8),
    ("DrawVertex", 0xDB, 0xE8),
    ("DrawEnd", 0x17A, 0xE8),
    ("DrawPopState", 0x1AD, 0xE9),
]

# mov rdi, [rcx+0x100]  -> CVidTile::pRes at RenderTexture+0x1D
PRES_PROBE_OFFSET = 0x1D
PRES_PROBE_BYTES = bytes([0x48, 0x8B, 0xB9, 0x00, 0x01, 0x00, 0x00])

# RuntimeOffsets members worth a disp32 census (skip small struct offsets).
CENSUS_OFFSETS = {
    "tisLinearTilesFlag": 0x1DC,
    "infGameVisibleArea": 0x6590,
    "infGameAreas": 0x6598,
    "infGameAreaMaster": 0x65F8,
}

IMAGE_SCN_MEM_EXECUTE = 0x20000000


def parse_pe(data: bytes) -> dict:
    if data[:2] != b"MZ":
        raise ValueError("not a DOS/PE image")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    coff = e_lfanew + 4
    machine, num_sections, _, _, _, size_opt, _ = struct.unpack_from("<HHIIIHH", data, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic != 0x20B:
        raise ValueError(f"expected PE32+ (0x20B), got {magic:#x}")
    image_base = struct.unpack_from("<Q", data, opt + 24)[0]

    sections = []
    sec_off = opt + size_opt
    for i in range(num_sections):
        base = sec_off + i * 40
        name = data[base:base + 8].rstrip(b"\0").decode("ascii", "replace")
        vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, base + 8)
        chars = struct.unpack_from("<I", data, base + 36)[0]
        sections.append({
            "name": name, "vaddr": vaddr, "vsize": vsize,
            "rawptr": rawptr, "rawsize": rawsize,
            "exec": bool(chars & IMAGE_SCN_MEM_EXECUTE),
        })
    return {"machine": machine, "image_base": image_base, "sections": sections}


def compile_pattern(pattern: str) -> list[int | None]:
    return [None if t in ("?", "??") else int(t, 16) for t in pattern.split()]


def find_pattern(buf: bytes, start: int, length: int, pat: list[int | None]) -> list[int]:
    hits: list[int] = []
    n = len(pat)
    if n == 0 or length < n:
        return hits
    first = pat[0]
    end = start + length - n
    i = start
    while i <= end:
        if first is not None:
            j = buf.find(bytes([first]), i, start + length)
            if j < 0 or j > end:
                break
            i = j
        if all(p is None or buf[i + k] == p for k, p in enumerate(pat)):
            hits.append(i)
        i += 1
    return hits


def rva_to_off(pe: dict, rva: int) -> int | None:
    for s in pe["sections"]:
        if s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            return s["rawptr"] + (rva - s["vaddr"])
    return None


def off_to_rva(pe: dict, off: int) -> int | None:
    for s in pe["sections"]:
        if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
            return s["vaddr"] + (off - s["rawptr"])
    return None


def exec_section_of(pe: dict, rva: int) -> str | None:
    for s in pe["sections"]:
        if s["exec"] and s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            return s["name"]
    return None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("executable", help="path to the game executable (Baldur.exe)")
    ap.add_argument("--reference", choices=sorted(REFERENCE_RVAS), default="2.7.3",
                    help="known build to report RVA shifts against (default: 2.7.3)")
    args = ap.parse_args(argv)

    with open(args.executable, "rb") as handle:
        data = handle.read()

    pe = parse_pe(data)
    failures: list[str] = []

    print("## Executable Identity\n")
    print(f"- Path: {args.executable}")
    print(f"- Size: {len(data):,} bytes")
    print(f"- SHA-256: `{hashlib.sha256(data).hexdigest()}`")
    print(f"- Image base `{pe['image_base']:#x}`, {len(pe['sections'])} sections")
    for s in pe["sections"]:
        if s["exec"]:
            print(f"- `{s['name']}` VA `{s['vaddr']:#x}`, size `{s['vsize']:#x}` (executable)")

    print("\n## Signature Scan (executable sections only)\n")
    print("| Target | Matches | RVA | Reference | Shift |")
    print("|---|---|---|---|---|")
    located: dict[str, int] = {}
    patterns = dict(PATTERNS)
    if args.reference == "2.7.3":
        patterns["CResPVR::Demand"] = PVR_DEMAND_PATTERN
        patterns["PVR zlib::uncompress wrapper"] = PVR_UNCOMPRESS_PATTERN
        patterns["CResPVR cache release"] = PVR_CACHE_RELEASE_PATTERN
        patterns["CRes file open"] = CRES_FILE_OPEN_PATTERN
    for label, pat_str in patterns.items():
        pat = compile_pattern(pat_str)
        hits: list[int] = []
        for s in pe["sections"]:
            if s["exec"]:
                hits.extend(find_pattern(data, s["rawptr"], s["rawsize"], pat))
        rvas = [off_to_rva(pe, h) for h in hits]
        ref = REFERENCE_RVAS[args.reference][label]
        if len(rvas) == 1 and rvas[0] is not None:
            located[label] = rvas[0]
            print(f"| `{label}` | 1 | `{rvas[0]:#x}` | `{ref:#x}` | `{rvas[0] - ref:+#x}` |")
        else:
            failures.append(f"{label}: expected exactly 1 match, got {len(rvas)}")
            print(f"| `{label}` | {len(rvas)} | - | `{ref:#x}` | - |")

    rt = located.get("CVidTile::RenderTexture")
    if rt is None:
        print("\nRenderTexture not uniquely located; cannot decode callsites.")
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    rt_off = rva_to_off(pe, rt)
    assert rt_off is not None

    print("\n## Render Callsite Decode (all 11 descriptors)\n")
    print("| Callsite | Offset | Opcode | Target RVA | Section |")
    print("|---|---|---|---|---|")
    for name, coff, expected_op in CALLSITES:
        p = rt_off + coff
        op = data[p]
        disp = struct.unpack_from("<i", data, p + 1)[0]
        target = rt + coff + 5 + disp
        sect = exec_section_of(pe, target)
        if op != expected_op:
            failures.append(f"{name}: opcode {op:#04x}, expected {expected_op:#04x}")
        if sect is None:
            failures.append(f"{name}: target {target:#x} outside any executable section")
        print(f"| {name} | +{coff:#x} | `{op:#04x}` | `{target:#x}` | {sect or 'OUTSIDE'} |")

    pvr_demand = located.get("CResPVR::Demand")
    pvr_uncompress = located.get("PVR zlib::uncompress wrapper")
    pvr_cache_release = located.get("CResPVR cache release")
    cres_file_open = located.get("CRes file open")
    if args.reference == "2.7.3":
        print("\n## PVR Decode Boundary (Phase 3e-B0)\n")
        print("| Native phase | Demand offset | Opcode | Target RVA | Exact 2.7.3 target |")
        print("|---|---|---|---|---|")
        if pvr_demand is None or pvr_uncompress is None:
            failures.append("PVR decode boundary cannot be checked without unique Demand and "
                            "uncompress signatures")
        else:
            pvr_off = rva_to_off(pe, pvr_demand)
            assert pvr_off is not None
            for name, call_offset, expected_target in PVR_PHASE_CALLS:
                call = pvr_off + call_offset
                op = data[call]
                disp = struct.unpack_from("<i", data, call + 1)[0]
                target = pvr_demand + call_offset + 5 + disp
                exact = op == 0xE8 and target == expected_target
                if not exact:
                    failures.append(
                        f"PVR {name}: got opcode {op:#04x} target {target:#x}, expected "
                        f"call {expected_target:#x}"
                    )
                print(f"| {name} | +{call_offset:#x} | `{op:#04x}` | `{target:#x}` | "
                      f"{'yes' if exact else 'NO'} |")
            handoff_target = next(
                pvr_demand + offset + 5 + struct.unpack_from("<i", data, pvr_off + offset + 1)[0]
                for name, offset, _ in PVR_PHASE_CALLS if name == "zlib uncompress handoff"
            )
            if handoff_target != pvr_uncompress:
                failures.append(
                    f"PVR handoff target {handoff_target:#x} differs from unique uncompress "
                    f"signature {pvr_uncompress:#x}"
                )

            consume_pattern = compile_pattern(PVR_CONSUME_WINDOW_PATTERN)
            consume_off = pvr_off + PVR_CONSUME_WINDOW_OFFSET
            consume_match = find_pattern(
                data, consume_off, len(consume_pattern), consume_pattern
            ) == [consume_off]
            if not consume_match:
                failures.append(
                    f"PVR native consume window mismatch at Demand+"
                    f"{PVR_CONSUME_WINDOW_OFFSET:#x}"
                )
            print(f"\n- Native post-decode field/upload/release window at "
                  f"`Demand+{PVR_CONSUME_WINDOW_OFFSET:#x}`: "
                  f"{'exact' if consume_match else 'MISMATCH'}.")
            print(f"- A consuming detour must fall back outside return RVA "
                  f"`{pvr_demand + 0x164:#x}` and must never bypass native cache, "
                  "allocation, upload or release.")

            print("\n## PVR Lifecycle Boundary (Phase 3e-B2c)\n")
            lifecycle_ready = pvr_cache_release is not None and cres_file_open is not None
            if not lifecycle_ready:
                failures.append("PVR lifecycle boundary requires unique cache-release and "
                                "CRes file-open signatures")
            else:
                cache_ref_offset = 0x19
                cache_ref = pvr_off + cache_ref_offset
                cache_ref_ok = data[cache_ref:cache_ref + 3] == bytes([0x4C, 0x8D, 0x35])
                cache_disp = struct.unpack_from("<i", data, cache_ref + 3)[0]
                cache_target = pvr_demand + cache_ref_offset + 7 + cache_disp
                cache_exact = cache_ref_ok and cache_target == 0x721B70
                if not cache_exact:
                    failures.append(
                        f"PVR cache reference: target {cache_target:#x}, expected 0x721b70"
                    )

                release_off = rva_to_off(pe, pvr_cache_release)
                assert release_off is not None
                release_ref_offset = 0x0C
                release_ref = release_off + release_ref_offset
                release_ref_ok = data[release_ref:release_ref + 3] == bytes([0x48, 0x8D, 0x15])
                release_disp = struct.unpack_from("<i", data, release_ref + 3)[0]
                release_target = pvr_cache_release + release_ref_offset + 7 + release_disp
                release_exact = release_ref_ok and release_target == 0x721B70
                if not release_exact:
                    failures.append(
                        f"PVR cache-release reference: target {release_target:#x}, "
                        "expected 0x721b70"
                    )

                resource_demand = next(
                    target for name, _, target in PVR_PHASE_CALLS
                    if name == "CRes resource demand"
                )
                resource_off = rva_to_off(pe, resource_demand)
                assert resource_off is not None
                file_open_offset = 0xE2
                file_open_call = resource_off + file_open_offset
                file_open_op = data[file_open_call]
                file_open_disp = struct.unpack_from("<i", data, file_open_call + 1)[0]
                file_open_target = resource_demand + file_open_offset + 5 + file_open_disp
                file_open_exact = file_open_op == 0xE8 and file_open_target == cres_file_open
                if not file_open_exact:
                    failures.append(
                        f"CRes file-open edge: opcode {file_open_op:#04x}, "
                        f"target {file_open_target:#x}, expected {cres_file_open:#x}"
                    )

                print("| Lifecycle edge | Reference | Target RVA | Exact |")
                print("|---|---:|---:|---|")
                print(f"| Demand cache array | `Demand+{cache_ref_offset:#x}` | "
                      f"`{cache_target:#x}` | {'yes' if cache_exact else 'NO'} |")
                print(f"| cache release array | `release+{release_ref_offset:#x}` | "
                      f"`{release_target:#x}` | {'yes' if release_exact else 'NO'} |")
                print(f"| CRes file open | `CRes::Demand+{file_open_offset:#x}` | "
                      f"`{file_open_target:#x}` | {'yes' if file_open_exact else 'NO'} |")

    print("\n## Runtime Offset Evidence\n")
    probe = data[rt_off + PRES_PROBE_OFFSET: rt_off + PRES_PROBE_OFFSET + len(PRES_PROBE_BYTES)]
    ok = probe == PRES_PROBE_BYTES
    if not ok:
        failures.append("CVidTile::pRes probe mismatch at RenderTexture+0x1D")
    print(f"- `RenderTexture+{PRES_PROBE_OFFSET:#x}`: `{' '.join(f'{b:02X}' for b in probe)}` "
          f"({'confirms' if ok else 'DIFFERS from'} `mov rdi, [rcx+0x100]`)")

    print("- disp32 census over executable sections:")
    for name, val in CENSUS_OFFSETS.items():
        needle = struct.pack("<I", val)
        total = 0
        for s in pe["sections"]:
            if not s["exec"]:
                continue
            start, end = s["rawptr"], s["rawptr"] + s["rawsize"]
            i = data.find(needle, start, end)
            while i >= 0:
                total += 1
                i = data.find(needle, i + 1, end)
        if total == 0:
            failures.append(f"{name} ({val:#x}) never appears as a disp32 constant")
        print(f"  - `{name}` `{val:#x}` x{total}")

    print("\n## Prologue Dumps\n")
    for label, rva in located.items():
        o = rva_to_off(pe, rva)
        assert o is not None
        print(f"- `{label}` @ `{rva:#x}`: `{' '.join(f'{b:02X}' for b in data[o:o + 24])}`")

    print()
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("Offline validation PASSED. In-game gates are still required before "
          "claiming support (see docs/new-build-validation.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
