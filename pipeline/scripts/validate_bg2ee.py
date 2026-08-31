"""Offline validation of the InfinityEngine-Enhancer manifest against BG2EE.

Mirrors docs/new-build-validation.md steps 1-5 and the evidence format used in
docs/validation/bgee-2.7.3-evidence.md.
"""
import hashlib
import struct
import sys

from workspace_paths import get_path

EXE = str(get_path("bg2ee_game_root") / "Baldur.exe")

# Patterns from the BGEE 2.7.3.x manifest (identical to 2.6.6.x).
PATTERNS = {
    "CInfGame::LoadArea": "40 55 53 56 57 41 54 41 55 41 56 41 57 48 8D AC 24 48 FD FF FF",
    "CVidTile::RenderTexture": "48 8B C4 44 89 48 20 48 83 EC 48 48 89 58 08 8B DA 48 89 68 10",
}

# BGEE 2.7.3 reference RVAs, for comparison only.
BGEE273_RVA = {"CInfGame::LoadArea": 0x27EBD0, "CVidTile::RenderTexture": 0x4257C0}

CALLSITES = [
    ("CRes_Demand",     0x36,  0xE8),
    ("DrawBindTexture", 0x6E,  0xE8),
    ("DrawDisable",     0x7F,  0xE8),
    ("DrawColor",       0x89,  0xE8),
    ("DrawPushState",   0x91,  0xE8),
    ("DrawColorTone",   0xB6,  0xE8),
    ("DrawBegin",       0xC0,  0xE8),
    ("DrawTexCoord",    0xCD,  0xE8),
    ("DrawVertex",      0xDB,  0xE8),
    ("DrawEnd",         0x17A, 0xE8),
    ("DrawPopState",    0x1AD, 0xE9),
]

RUNTIME_OFFSETS = {
    "vidTileResource":       0x100,
    "tisLinearTilesFlag":    0x1DC,
    "tisHeaderTileDimension": 0x14,
    "infGameVisibleArea":    0x6590,
    "infGameAreas":          0x6598,
    "infGameAreaMaster":     0x65F8,
}

IMAGE_SCN_MEM_EXECUTE = 0x20000000


def parse_pe(data):
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    assert data[e_lfanew:e_lfanew + 4] == b"PE\0\0", "not a PE file"
    coff = e_lfanew + 4
    machine, num_sections, _, _, _, size_opt, _ = struct.unpack_from("<HHIIIHH", data, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    assert magic == 0x20B, f"expected PE32+ (0x20B), got {magic:#x}"
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
            "rawptr": rawptr, "rawsize": rawsize, "chars": chars,
            "exec": bool(chars & IMAGE_SCN_MEM_EXECUTE),
        })
    return {"machine": machine, "image_base": image_base, "sections": sections}


def compile_pattern(pattern):
    toks = pattern.split()
    out = []
    for t in toks:
        out.append(None if t in ("?", "??") else int(t, 16))
    return out


def find_pattern(buf, start, length, pat):
    hits = []
    n = len(pat)
    first = pat[0]
    i = start
    end = start + length - n
    while i <= end:
        if first is not None:
            j = buf.find(bytes([first]), i, start + length)
            if j < 0 or j > end:
                break
            i = j
        ok = True
        for k in range(1, n):
            p = pat[k]
            if p is not None and buf[i + k] != p:
                ok = False
                break
        if ok:
            hits.append(i)
        i += 1
    return hits


def rva_to_off(pe, rva):
    for s in pe["sections"]:
        if s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            return s["rawptr"] + (rva - s["vaddr"])
    return None


def off_to_rva(pe, off):
    for s in pe["sections"]:
        if s["rawptr"] <= off < s["rawptr"] + s["rawsize"]:
            return s["vaddr"] + (off - s["rawptr"])
    return None


def in_exec_section(pe, rva):
    for s in pe["sections"]:
        if s["exec"] and s["vaddr"] <= rva < s["vaddr"] + max(s["vsize"], s["rawsize"]):
            return s["name"]
    return None


def main():
    with open(EXE, "rb") as f:
        data = f.read()

    print("=" * 78)
    print("EXECUTABLE IDENTITY")
    print("=" * 78)
    print(f"Path       : {EXE}")
    print(f"Size       : {len(data):,} bytes")
    print(f"SHA-256    : {hashlib.sha256(data).hexdigest()}")

    pe = parse_pe(data)
    print(f"Machine    : {pe['machine']:#x} (0x8664 = x64)")
    print(f"Image base : {pe['image_base']:#x}")
    print(f"Sections   : {len(pe['sections'])}")
    for s in pe["sections"]:
        flag = "X" if s["exec"] else " "
        print(f"  [{flag}] {s['name']:<8} VA {s['vaddr']:#010x}  vsize {s['vsize']:#010x}  raw {s['rawptr']:#010x}")

    print()
    print("=" * 78)
    print("SIGNATURE SCAN (executable sections only)")
    print("=" * 78)
    found = {}
    for label, pat_str in PATTERNS.items():
        pat = compile_pattern(pat_str)
        all_hits = []
        for s in pe["sections"]:
            if not s["exec"]:
                continue
            hits = find_pattern(data, s["rawptr"], s["rawsize"], pat)
            all_hits.extend(hits)
        rvas = [off_to_rva(pe, h) for h in all_hits]
        print(f"\n{label}")
        print(f"  pattern : {pat_str}")
        print(f"  matches : {len(all_hits)}")
        for r in rvas:
            print(f"    -> RVA {r:#x}   (VA {pe['image_base'] + r:#x})")
        ref = BGEE273_RVA[label]
        if len(rvas) == 1:
            shift = rvas[0] - ref
            print(f"  BGEE 2.7.3 RVA {ref:#x} -> shift {shift:+#x}")
            found[label] = rvas[0]
        else:
            print(f"  !! expected exactly 1 match")

    if "CVidTile::RenderTexture" not in found:
        print("\nRenderTexture not uniquely located; cannot decode callsites.")
        return 1

    rt_rva = found["CVidTile::RenderTexture"]
    rt_off = rva_to_off(pe, rt_rva)

    print()
    print("=" * 78)
    print("RENDER CALLSITE DECODE (11 descriptors)")
    print("=" * 78)
    print(f"{'Callsite':<18}{'Offset':>8}  {'Opcode':<8}{'Target RVA':>12}  {'Section':<10}Status")
    ok_count = 0
    for name, coff, expected_op in CALLSITES:
        p = rt_off + coff
        op = data[p]
        disp = struct.unpack_from("<i", data, p + 1)[0]
        target_rva = rt_rva + coff + 5 + disp
        sect = in_exec_section(pe, target_rva)
        good = (op == expected_op) and (sect is not None)
        if good:
            ok_count += 1
        status = "OK" if good else f"MISMATCH(op={op:#04x} exp={expected_op:#04x})"
        print(f"{name:<18}{'+' + hex(coff)[2:]:>8}  {op:#04x}    {target_rva:>#12x}  {str(sect):<10}{status}")
    print(f"\n{ok_count}/11 callsites valid")

    print()
    print("=" * 78)
    print("RUNTIME OFFSET EVIDENCE")
    print("=" * 78)
    probe = data[rt_off + 0x1D: rt_off + 0x1D + 7]
    print(f"Bytes at RenderTexture+0x1D : {' '.join(f'{b:02X}' for b in probe)}")
    expect = bytes([0x48, 0x8B, 0xB9, 0x00, 0x01, 0x00, 0x00])
    print(f"Expected (mov rdi,[rcx+0x100]): {' '.join(f'{b:02X}' for b in expect)}")
    print(f"CVidTile::pRes = 0x100 -> {'CONFIRMED' if probe == expect else 'DIFFERS'}")

    print("\nPrologue dump (24 bytes) for each target:")
    for label, rva in found.items():
        o = rva_to_off(pe, rva)
        print(f"  {label} @ {rva:#x}")
        print(f"    {' '.join(f'{b:02X}' for b in data[o:o + 24])}")

    print("\ndisp32 constant census over executable sections (4-byte LE occurrences):")
    for name, val in RUNTIME_OFFSETS.items():
        if val < 0x100:
            continue
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
        print(f"  {name:<24} {val:#07x}  x{total}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
