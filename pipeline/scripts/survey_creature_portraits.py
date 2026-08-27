"""Recense les portraits cités par les créatures du jeu.

Parcourt tous les CRE, relève leurs références de portrait et le nom affiché,
puis regroupe par base de portrait. Sert à distinguer les portraits déjà
exportés (compagnons) de ceux des PNJ simplement rencontrés.
"""
from __future__ import annotations

import struct
from collections import Counter, defaultdict
from pathlib import Path

from bg2lib import load_key, resolve_resource
from extract_joinable_portraits import (BMP, CRE, SIZES, TLK, joinable_npcs,
                                        load_tlk, portrait_base, tlk_string)


def main() -> None:
    bif, resources = load_key()
    bmp_index = {r[0].upper(): r for r in resources if r[1] == BMP}
    cre_index = {r[0].upper(): r for r in resources if r[1] == CRE}
    tlk = load_tlk(TLK) if TLK.exists() else None
    print(f"{len(cre_index)} CRE, {len(bmp_index)} BMP")

    users: dict[str, Counter] = defaultdict(Counter)   # base -> noms affiches
    creatures: dict[str, set] = defaultdict(set)       # base -> resrefs CRE
    for name, entry in cre_index.items():
        data, _ = resolve_resource(bif, entry[2])
        if data[0:4] != b"CRE ":
            continue
        strref = struct.unpack_from("<i", data, 8)[0]
        label = tlk_string(tlk, strref) if (tlk and strref > 0) else ""
        for offset in (0x34, 0x3C):
            ref = data[offset:offset + 8].split(b"\0")[0].decode("ascii", "replace").strip().upper()
            if len(ref) > 1 and ref[-1] in "LMS":
                base = ref[:-1]
                creatures[base].add(name)
                if label:
                    users[base][label] += 1

    # bases reellement presentes en BMP
    available = {b: [s for s, _ in SIZES if (b + s) in bmp_index] for b in creatures}
    available = {b: v for b, v in available.items() if v}

    joinable_bases = set()
    for npc in joinable_npcs(bif, resources):
        base, _ = portrait_base(bif, cre_index, npc)
        if base:
            joinable_bases.add(base)

    others = {b: v for b, v in available.items() if b not in joinable_bases}
    print(f"\nbases citees par des CRE et presentes en BMP : {len(available)}")
    print(f"  dont compagnons deja exportes : {len(available) - len(others)}")
    print(f"  autres PNJ rencontres         : {len(others)}")

    sizes_hist = Counter(len(v) for v in others.values())
    print(f"  repartition des tailles : "
          + ", ".join(f"{n} taille(s) : {c}" for n, c in sorted(sizes_hist.items())))

    print("\nexemples (base, tailles, nb de creatures, nom le plus frequent) :")
    ranked = sorted(others, key=lambda b: -len(creatures[b]))
    for base in ranked[:25]:
        top = users[base].most_common(1)
        print(f"  {base:<10} {''.join(available[base]):<4} {len(creatures[base]):>4} CRE   "
              f"{top[0][0] if top else '(sans nom)'}")

    unnamed = [b for b in others if not users[b]]
    print(f"\nbases sans aucun nom affiche : {len(unnamed)}")


if __name__ == "__main__":
    main()
