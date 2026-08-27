"""List the area's BAM animations: these are sprites, not tiles."""
import struct
import sys
from bg2lib import load_key, resolve_resource

AREA = sys.argv[1] if len(sys.argv) > 1 else "AR0602"

bif, res = load_key()
are_by = {r[0].upper(): r for r in res if r[1] == 0x03F2}
bam_by = {r[0].upper(): r for r in res if r[1] == 0x03E8}

data, _ = resolve_resource(bif, are_by[AREA][2])
assert data[0:4] == b"AREA"
count = struct.unpack_from("<I", data, 0xAC)[0]
off = struct.unpack_from("<I", data, 0xB0)[0]
print(f"{AREA}: {count} area animations at {off:#x}\n")

print(f"{'name':<24}{'BAM':<10}{'x':>6}{'y':>6}{'cell':>10}{'seq':>5}{'frame':>6}  flags")
rows = []
for i in range(count):
    b = off + i * 76
    name = data[b:b + 32].split(b"\0")[0].decode("cp1252", "replace")
    x, y = struct.unpack_from("<hh", data, b + 0x20)
    bam = data[b + 0x28:b + 0x30].split(b"\0")[0].decode("ascii", "replace")
    seq, frame = struct.unpack_from("<HH", data, b + 0x30)
    flags = struct.unpack_from("<I", data, b + 0x34)[0]
    rows.append((name, bam, x, y, seq, frame, flags))
    print(f"{name:<24}{bam:<10}{x:>6}{y:>6}{f'({x//64},{y//64})':>10}{seq:>5}{frame:>6}  {flags:#010x}")

bams = sorted({r[1].upper() for r in rows})
print(f"\ndistinct BAM resources: {len(bams)}")
for b in bams:
    entry = bam_by.get(b)
    if not entry:
        print(f"  {b}: not found in the key")
        continue
    d, _ = resolve_resource(bif, entry[2])
    sig, ver = d[0:4], d[4:8]
    if sig == b"BAMC":
        import zlib
        d = zlib.decompress(d[12:])
        sig, ver = d[0:4], d[4:8]
    nframes, ncycles = struct.unpack_from("<HB", d, 8)[:2] if sig == b"BAM " else (0, 0)
    print(f"  {b}: {sig.decode(errors='replace')}{ver.decode(errors='replace')}  frames={nframes}")
