import sys
sys.path.insert(0, r"C:\Users\Adrien\AppData\Local\Temp\claude\E--Steam-steamapps-common-Baldur-s-Gate-II-Enhanced-Edition\71779e0c-679b-4df8-972c-c96a4e15d86c\scratchpad")
from bg2lib import load_key, resolve_resource
import struct

bif_entries, res_entries = load_key()
mos = [r for r in res_entries if r[1] == 0x03EC]
print(f"Total MOS: {len(mos)}")

versions = {}
errors = 0
for name, rtype, locator in mos:
    result = resolve_resource(bif_entries, locator)
    if result is None:
        errors += 1
        continue
    data, bif_name = result
    sig = data[0:4]
    if sig == b"MOSC":
        ver = data[4:8]
        real_ver = b"(compressed)" + ver
    elif sig == b"MOS ":
        real_ver = data[4:8]
    else:
        real_ver = b"UNKNOWN:" + sig
    versions[real_ver] = versions.get(real_ver, 0) + 1

print("Version breakdown:", versions)
print("Errors:", errors)
