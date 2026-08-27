"""Find the largest area in the game.

Grid size alone ties at the engine's ceiling, so ties are broken by how much of
the grid actually carries painted tiles (non-black), which is the meaningful
"biggest playable surface".
"""
import struct
from bg2lib import load_key, resolve_resource, resolve_tileset_resource

bif, res = load_key()
are_list = [r for r in res if r[1] == 0x03F2]
wed_by = {r[0].upper(): r for r in res if r[1] == 0x03E9}
tis_by = {r[0].upper(): r for r in res if r[1] == 0x03EB}

rows = []
for name, _t, loc in are_list:
    adata, _ = resolve_resource(bif, loc)
    if adata[0:4] != b"AREA":
        continue
    outdoor = bool(struct.unpack_from("<H", adata, 0x48)[0] & 0x1)
    wr = wed_by.get(name.upper())
    if not wr:
        continue
    w, _ = resolve_resource(bif, wr[2])
    if w[0:4] != b"WED ":
        continue
    _n, _d, oo = struct.unpack_from("<III", w, 8)
    ov_w, ov_h = struct.unpack_from("<HH", w, oo)
    tileset = w[oo + 4:oo + 12].split(b"\0")[0].decode("ascii", "replace")
    tm, lut = struct.unpack_from("<II", w, oo + 0x10)

    painted = None
    te = tis_by.get(tileset.upper())
    if te:
        try:
            td, tcount, esize, _ = resolve_tileset_resource(bif, te[2])
            if esize == 12:
                painted = 0
                for cell in range(ov_w * ov_h):
                    s, _c, _sec, _f = struct.unpack_from("<HHHB3x", w, tm + cell * 10)
                    tid = struct.unpack_from("<H", w, lut + s * 2)[0]
                    if tid < tcount:
                        page = struct.unpack_from("<I", td, tid * 12)[0]
                        if page != 0xFFFFFFFF:
                            painted += 1
        except Exception:
            painted = None
    rows.append((name, outdoor, ov_w, ov_h, ov_w * ov_h, painted))

print(f"zones analysees : {len(rows)}")
maxcells = max(r[4] for r in rows)
print(f"grille maximale : {maxcells} cellules\n")

top = sorted(rows, key=lambda r: (-r[4], -(r[5] or 0)))
print(f"{'zone':<9}{'grille':>10}{'pixels':>14}{'tuiles peintes':>16}{'remplissage':>13}  type")
for name, outdoor, w, h, cells, painted in top[:15]:
    fill = f"{100*painted/cells:.0f}%" if painted else "?"
    print(f"{name:<9}{f'{w}x{h}':>10}{f'{w*64}x{h*64}':>14}"
          f"{(painted if painted is not None else -1):>16}{fill:>13}  "
          f"{'exterieur' if outdoor else 'interieur'}")

print("\n--- classement par surface reellement peinte ---")
best = sorted((r for r in rows if r[5]), key=lambda r: -r[5])
for name, outdoor, w, h, cells, painted in best[:10]:
    print(f"{name:<9}{f'{w}x{h}':>10}{f'{w*64}x{h*64}':>14}{painted:>16}"
          f"{100*painted/cells:>12.0f}%  {'exterieur' if outdoor else 'interieur'}")
