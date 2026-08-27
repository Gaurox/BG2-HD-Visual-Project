import sys, struct
from bg2lib import load_key, resolve_resource

bif_entries, res_entries = load_key()
are_list = [r for r in res_entries if r[1] == 0x03F2]
wed_by_name = {r[0].upper(): r for r in res_entries if r[1] == 0x03E9}

THRESH = 2000
selected = []
for name, rtype, locator in are_list:
    data, bif_name = resolve_resource(bif_entries, locator)
    if data[0:4] != b'AREA':
        continue
    area_type = struct.unpack_from('<H', data, 0x48)[0]
    outdoor = bool(area_type & 0x1)
    wr = wed_by_name.get(name.upper())
    if not wr:
        continue
    wdata, _ = resolve_resource(bif_entries, wr[2])
    if wdata[0:4] != b'WED ':
        continue
    num_overlays, num_doors, off_overlays = struct.unpack_from('<III', wdata, 8)
    ov_w, ov_h = struct.unpack_from('<HH', wdata, off_overlays)
    tile_area = ov_w * ov_h
    if outdoor or tile_area >= THRESH:
        selected.append((name, outdoor, ov_w, ov_h, tile_area))

selected.sort(key=lambda x: x[0])
print(f"Selected {len(selected)} areas")
with open("selected_areas.txt", "w") as f:
    for s in selected:
        f.write(f"{s[0]}\t{s[1]}\t{s[2]}\t{s[3]}\t{s[4]}\n")
print("Written to selected_areas.txt")
