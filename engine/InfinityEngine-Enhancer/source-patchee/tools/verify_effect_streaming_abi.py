"""Read-only check of manifested effect lifecycle starts on the reference PE.

Reads one executable and its existing identity receipt; never loads its code,
touches installed files, or reads RGBA. RVAs/signatures come from build_manifest.cpp.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = Path(__file__).resolve().parents[1]


def verify(executable: Path) -> dict:
    raw = executable.read_bytes()
    receipt = json.loads((ROOT / "effects/installations/lot64-7b-x4-nearest30-20261015-v1/"
                         "native-profile-offsets.json").read_text(encoding="utf-8-sig"))
    digest = hashlib.sha256(raw).hexdigest().upper()
    if digest != receipt["executable_sha256"]:
        raise ValueError("executable differs from the statically analysed reference")
    if raw[:2] != b"MZ":
        raise ValueError("not a PE")
    pe, = struct.unpack_from("<I", raw, 0x3C)
    if raw[pe:pe + 4] != b"PE\0\0" or struct.unpack_from("<H", raw, pe + 4)[0] != 0x8664:
        raise ValueError("not an AMD64 PE")
    count, = struct.unpack_from("<H", raw, pe + 6)
    size, = struct.unpack_from("<H", raw, pe + 20)
    sections = [struct.unpack_from("<8sIIII", raw, pe + 24 + size + i * 40)
                for i in range(count)]

    def read(rva: int, length: int) -> bytes:
        for _, _, va, physical, offset in sections:
            if va <= rva and rva + length <= va + physical:
                return raw[offset + rva - va:offset + rva - va + length]
        raise ValueError(f"RVA outside physical sections: {rva:#x}")

    pdata = next(section for section in sections if section[0].startswith(b".pdata"))
    starts = {struct.unpack_from("<I", raw, pdata[4] + offset)[0]
              for offset in range(0, pdata[3] - 11, 12)}
    text = (SOURCE / "src/iee/game/build_manifest.cpp").read_text(encoding="utf-8-sig")
    block = text.split("// EFFECT_STREAMING_ABI_BEGIN", 1)[1].split("// EFFECT_STREAMING_ABI_END", 1)[0]
    rvas = [int(value, 16) for value in re.findall(r"0x[0-9A-Fa-f]+", block.split("// Exact", 1)[0])]
    signatures = re.findall(r'"([0-9A-F? ]+)"', block)
    names = ("cellConstruct", "cellDestruct", "vvcConfigure", "vvcSequence", "destroyGame")
    if len(rvas) != len(names) or len(signatures) != len(names):
        raise ValueError("cannot unambiguously extract central streaming manifest")
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    results = []
    for name, rva, signature in zip(names, rvas, signatures):
        pattern = signature.split()
        actual = read(rva, max(len(pattern), 32))
        if rva not in starts or any(token != "?" and actual[i] != int(token, 16)
                                    for i, token in enumerate(pattern)):
            raise ValueError(f"invalid function start/signature: {name} {rva:#x}")
        length = 0
        for instruction in decoder.disasm(actual, rva):
            length += instruction.size
            if instruction.mnemonic.startswith(("ret", "jmp")) and length < 14:
                raise ValueError(f"unexpected short hook prologue: {name}")
            if length >= 14:
                break
        if length < 14:
            raise ValueError(f"undecodable prologue: {name}")
        results.append({"name": name, "rva": hex(rva), "whole_instruction_bytes": length})
    return {"executable_sha256": digest, "checked": results, "executed_game": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path)
    args = parser.parse_args()
    executable = args.executable
    if executable is None:
        sys.path.insert(0, str(ROOT / "pipeline/scripts"))
        from workspace_paths import get_path
        executable = get_path("bg2ee_game_root", required=True) / "BaldurReal.exe"
    print(json.dumps(verify(executable), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
