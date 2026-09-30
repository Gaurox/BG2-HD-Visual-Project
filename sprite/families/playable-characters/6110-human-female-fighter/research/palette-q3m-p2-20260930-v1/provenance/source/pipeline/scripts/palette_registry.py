"""IEECSXN V6 Character Q3m shards: checked writer, inspector and logical records.

LE: registry <8s6I> (32); resource <8s32sII> (48); frame
<HHhhBBBBI256H32sIB3x> (568), then I and optional F, then existing cycles.
The three bytes at frame offset9 are I codec, F-present bit0, zero.
Profile1=character-bg2ee-2.7.3.0; decode1=ramp-lerp-srgb8-v1. No B/packing.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import struct
import zlib

import numpy as np

import run_creature_sprite_x2 as registry
from palette_frac_encode import checked_u8, check_contract, dependency_mask, validate_planes

VERSION = registry.XN_FRACTION_REGISTRY_VERSION
CLASS_PROFILE_ID = 1
DECODE_RULE_ID = 1
HEADER_BYTES = 32
FRAME_BYTES = 568
FRAME = struct.Struct("<HHhhBBBBI256H32sIB3x")
assert FRAME.size == FRAME_BYTES


class _Codec:
    """Raw files remain portable; acquire the Windows codec only when used."""
    def __init__(self, compress):
        self.compress, self.value = compress, None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.value is not None:
            return self.value.__exit__(*args)

    def _get(self):
        if self.value is None:
            self.value = registry.WindowsXpressHuffCodec(compress=self.compress)
            self.value.__enter__()
        return self.value

    def encode(self, data):
        return self._get().encode(data)

    def decode(self, data, n):
        return self._get().decode(data,n)


def _require(ok, label):
    if not ok:
        raise RuntimeError(f"V6 {label}")


def _storage_valid(codec, stored, logical):
    return (codec == 0 and stored == logical) or (codec == 1 and 0 < stored < logical)


def _decode_plane(codec, data, logical, decoder):
    _require(_storage_valid(codec, len(data), logical), "invalid plane codec/size")
    return decoder.decode(data, logical) if codec == 1 else data


def _read_frame(stream, scale, read, decoder):
    header = read(stream, FRAME_BYTES, "frame header")
    width, height, cx, cy, transparent, ic, flags, zero, stored_i = struct.unpack_from("<HHhhBBBBI", header)
    dep = np.frombuffer(header, np.uint8, 32, 528)
    stored_f, fc = struct.unpack_from("<IB", header, 560)
    n = width * height * scale * scale
    _require(width > 0 and height > 0 and transparent == 0 and flags in (0, 1) and zero == 0
             and header[565:568] == bytes(3), "invalid geometry/transparency/flags")
    _require(0 < n <= registry.MAX_LAZY_FRAME_INDEX_BYTES and
             n * (1 + flags) <= registry.MAX_LAZY_FRAME_INDEX_BYTES, "decoded frame exceeds limit")
    _require(_storage_valid(ic, stored_i, n) and
             ((_storage_valid(fc, stored_f, n) if flags else stored_f == 0 and fc == 0)),
             "invalid plane storage")
    reps = np.frombuffer(header, "<u2", 256, 16)
    _require(np.all((reps == 0xffff) | (reps < width*height)), "invalid representative offset")
    ip = _decode_plane(ic, read(stream, stored_i, "I"), n, decoder)
    fp = _decode_plane(fc, read(stream, stored_f, "F"), n, decoder) if flags else b""
    i = np.frombuffer(ip, np.uint8).reshape(height*scale, width*scale)
    f = np.frombuffer(fp, np.uint8).reshape(i.shape) if flags else np.zeros_like(i)
    try:
        validate_planes(i, f)
        _require(np.array_equal(dep, dependency_mask(i, f)), "dependency mask is not exact")
    except ValueError as error:
        raise RuntimeError(f"V6 invalid I/F: {error}") from error
    return header, ip, fp, (width, height, cx, cy, transparent), reps.copy()


def inspect(path: Path, *, include_resource_records=False, include_frames=False):
    path = Path(path)
    size = path.stat().st_size
    _require(HEADER_BYTES < size <= registry.maximum_registry_bytes(4), "invalid file size")
    digest, crc = hashlib.sha256(), 0

    def read(stream, n, label):
        nonlocal crc
        _require(0 <= n <= size - stream.tell(), f"truncated {label}")
        data = stream.read(n)
        _require(len(data) == n, f"truncated {label}")
        digest.update(data)
        crc = zlib.crc32(data, crc)
        return data

    resources, records, frame_data = [], [], []
    totals = dict(frame_count=0, index_bytes=0, fraction_bytes=0, stored_index_bytes=0,
                  stored_fraction_bytes=0, compressed_frame_count=0, raw_frame_count=0,
                  compressed_fraction_count=0, fractional_frame_count=0)
    with path.open("rb") as stream, _Codec(compress=False) as decoder:
        before = os.fstat(stream.fileno())
        magic, version, scale, count, animation, profile, rule = struct.unpack("<8s6I", read(stream, HEADER_BYTES, "header"))
        _require(magic == registry.XN_REGISTRY_MAGIC and version == VERSION and scale in (2,4)
                 and 1 <= count <= registry.MAX_RESOURCES and animation == 0xffff
                 and (profile,rule) == (CLASS_PROFILE_ID,DECODE_RULE_ID)
                 and size <= registry.maximum_registry_bytes(scale), "unsupported header/profile")
        for _ in range(count):
            offset = stream.tell()
            rh = read(stream, 48, "resource")
            ref = rh[:8].split(b"\0",1)[0]
            _require(re.fullmatch(rb"[A-Z0-9_]{1,8}",ref) and rh[:8] == ref.ljust(8,b"\0"), "invalid resref")
            ref = ref.decode("ascii")
            _require(ref not in resources, "duplicate resref")
            nf,nc = struct.unpack_from("<II",rh,40)
            _require(1 <= nf <= registry.MAX_FRAMES_PER_RESOURCE and 1 <= nc <= registry.MAX_CYCLES_PER_RESOURCE, "invalid counts")
            logical, resource_i, resource_f = 48,0,0
            frames = []
            for _ in range(nf):
                h,ip,fp,geometry,reps = _read_frame(stream,scale,read,decoder)
                n = len(ip)
                logical += FRAME_BYTES+n+len(fp)
                resource_i += n
                resource_f += len(fp)
                totals["frame_count"] += 1
                totals["stored_index_bytes"] += struct.unpack_from("<I",h,12)[0]
                totals["stored_fraction_bytes"] += struct.unpack_from("<I",h,560)[0]
                totals["compressed_frame_count" if h[9] == 1 else "raw_frame_count"] += 1
                totals["compressed_fraction_count"] += int(h[10] and h[564] == 1)
                totals["fractional_frame_count"] += int(bool(fp))
                if include_frames:
                    frames.append(dict(geometry=geometry, representatives=reps, I=ip, F=fp, dep=h[528:560]))
            cycles = []
            for _ in range(nc):
                ch = read(stream,4,"cycle")
                slots = struct.unpack("<I",ch)[0]
                _require(slots <= registry.MAX_CYCLE_SLOTS,"cycle too large")
                lookup = read(stream,slots*4,"lookup")
                values = np.frombuffer(lookup,"<u4")
                _require(np.all(values < nf),"invalid cycle lookup")
                logical += 4+len(lookup)
                if include_frames:
                    cycles.append(values.tolist())
            resources.append(ref)
            totals["index_bytes"] += resource_i
            totals["fraction_bytes"] += resource_f
            _require(totals["index_bytes"]+totals["fraction_bytes"] <= registry.maximum_registry_bytes(scale),"decoded shard exceeds limit")
            records.append(dict(resref=ref,path=path,offset=offset,bytes=stream.tell()-offset,
                                logical_bytes=logical,storage_version=VERSION,scale=scale,
                                frame_count=nf,index_bytes=resource_i,fraction_bytes=resource_f,
                                class_profile_id=profile,decode_rule_id=rule))
            if include_frames:
                frame_data.append(dict(resref=ref,source_sha256=rh[8:40].hex(),frames=frames,cycles=cycles))
        _require(stream.tell() == size,"trailing bytes")
        after = os.fstat(stream.fileno())
    current = path.stat()
    _require(os.path.samestat(before,after) and os.path.samestat(after,current) and
             all(getattr(before,k)==getattr(after,k)==getattr(current,k)
                 for k in ("st_size","st_mtime_ns","st_ctime_ns")),"file changed during inspection")
    result = dict(version=VERSION,scale=scale,registry_magic="IEECSXN",animation_id="0xFFFF",
                  resources=resources,resource_count=count,registry_bytes=size,sha256=digest.hexdigest().upper(),
                  crc32=crc & 0xffffffff,index_storage_ratio=totals["stored_index_bytes"]/totals["index_bytes"],
                  class_profile_id=profile,decode_rule_id=rule,**totals)
    if include_resource_records:
        result["resource_records"] = records
    if include_frames:
        result["frame_data"] = frame_data
    return result


def write(path: Path, scale: int, resources: list[dict], *, compress=True, retain_zero_f=False):
    """Resources carry full native frames/cycles/source identity, not sampled tables.

    Each frame: geometry(w,h,cx,cy,transparent), representatives, I, optional F,
    optional guide/dep. Guide proves semantic classes; absent guide is index-only.
    """
    _require(scale in (2,4) and 1 <= len(resources) <= registry.MAX_RESOURCES,"invalid writer scope")
    path = Path(path)
    temporary = path.with_name(path.name+".part")
    _require(not path.exists() and not temporary.exists(),"output already exists")
    try:
        with temporary.open("xb") as stream, _Codec(compress=True) as codec:
            stream.write(struct.pack("<8s6I",registry.XN_REGISTRY_MAGIC,VERSION,scale,len(resources),0xffff,1,1))
            seen = set()
            for resource in resources:
                ref = resource["resref"]
                _require(re.fullmatch(r"[A-Z0-9_]{1,8}",ref) and ref not in seen,"invalid/duplicate resource")
                seen.add(ref)
                frames,cycles = resource["frames"],resource["cycles"]
                _require(1 <= len(frames) <= registry.MAX_FRAMES_PER_RESOURCE and
                         1 <= len(cycles) <= registry.MAX_CYCLES_PER_RESOURCE,"invalid writer counts")
                source = bytes.fromhex(resource["source_sha256"])
                _require(len(source)==32,"invalid source hash")
                stream.write(struct.pack("<8s32sII",ref.encode().ljust(8,b"\0"),source,len(frames),len(cycles)))
                for frame in frames:
                    w,h,cx,cy,tr = frame["geometry"]
                    _require(0 < w <= 65535 and 0 < h <= 65535 and -32768 <= cx <= 32767 and
                             -32768 <= cy <= 32767 and tr==0,"invalid writer geometry")
                    i = checked_u8(frame["I"],"I")
                    f = checked_u8(frame.get("F",np.zeros_like(i)),"F")
                    _require(i.shape == (h*scale,w*scale),"I geometry differs")
                    validate_planes(i,f)
                    if np.any(f):
                        _require("guide" in frame,"fractional writer requires semantic guide")
                    check_contract(frame.get("guide",i),i,f,frame.get("dep"))
                    reps = np.asarray(frame["representatives"])
                    _require(reps.shape==(256,) and np.issubdtype(reps.dtype,np.integer) and
                             np.all((reps>=0)&(reps<=65535)) and
                             np.all((reps==65535)|(reps<w*h)),"invalid writer representatives")
                    present = bool(np.any(f)) or retain_zero_f
                    n = i.size
                    _require(n*(1+int(present)) <= registry.MAX_LAZY_FRAME_INDEX_BYTES,"writer frame too large")
                    planes = [i.tobytes(),f.tobytes() if present else b""]
                    stored,codecs = [],[]
                    for payload in planes:
                        candidate = codec.encode(payload) if payload and compress else payload
                        use = len(candidate)<len(payload)
                        stored.append(candidate if use else payload)
                        codecs.append(int(use))
                    stream.write(FRAME.pack(w,h,cx,cy,tr,codecs[0],int(present),0,len(stored[0]),
                                           *reps.tolist(),dependency_mask(i,f).tobytes(),len(stored[1]),codecs[1]))
                    stream.write(stored[0]); stream.write(stored[1])
                for cycle in cycles:
                    _require(len(cycle)<=registry.MAX_CYCLE_SLOTS and all(isinstance(v,int) and 0<=v<len(frames) for v in cycle),"invalid writer cycle")
                    stream.write(struct.pack("<I",len(cycle)))
                    stream.write(struct.pack(f"<{len(cycle)}I",*cycle))
                _require(stream.tell() <= registry.maximum_registry_bytes(scale),"writer shard too large")
        inspect(temporary)
        temporary.rename(path)
        return inspect(path,include_resource_records=True)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def logical_chunks(record, decoder):
    """Compression-independent V6 record; profile IDs hashed by component caller."""
    with Path(record["path"]).open("rb") as stream:
        stream.seek(int(record["offset"]))
        end = stream.tell()+int(record["bytes"])
        def read(s,n,label):
            _require(n <= end-s.tell(),f"truncated logical {label}")
            data = s.read(n)
            _require(len(data)==n,f"truncated logical {label}")
            return data
        rh = read(stream,48,"resource")
        yield rh
        nf,nc = struct.unpack_from("<II",rh,40)
        logical = 48
        for _ in range(nf):
            h,ip,fp,_,_ = _read_frame(stream,int(record["scale"]),read,decoder)
            canonical = bytearray(h)
            canonical[9]=canonical[564]=0
            struct.pack_into("<I",canonical,12,len(ip))
            struct.pack_into("<I",canonical,560,len(fp))
            yield bytes(canonical)
            yield ip
            yield fp
            logical += FRAME_BYTES+len(ip)+len(fp)
        for _ in range(nc):
            ch = read(stream,4,"cycle")
            slots = struct.unpack("<I",ch)[0]
            _require(slots <= registry.MAX_CYCLE_SLOTS,"logical cycle too large")
            lookup = read(stream,slots*4,"lookup")
            yield ch+lookup
            logical += 4+len(lookup)
        _require(stream.tell()==end and logical==int(record["logical_bytes"]),"logical record length differs")


def write_catalog(directory: Path, scale: int, components: list[list[dict]], *,
                  animations=None, compress=True, retain_zero_f=False):
    """Write an isolated V2 catalog of homogeneous Character V6 components."""
    directory = Path(directory)
    _require(not directory.exists(),"catalog output already exists")
    directory.mkdir(parents=True)
    _require(components and all(c for c in components),"empty catalog component")
    if animations is None:
        animations = [dict(animation_id="0x6110",owner=1,component_indices=list(range(len(components))))]
    _require(all(a["owner"]==1 and registry.catalog_owner_matches_animation(1,int(a["animation_id"],16))
                 for a in animations),"catalog requires Character owners")
    infos,entries,component_rows,logical_digests = [],[],[],[]
    storage = dict(shard_registry_version=VERSION,stored_index_bytes=0,stored_fraction_bytes=0,
                   fraction_bytes=0,compressed_frame_count=0,raw_frame_count=0,
                   compressed_fraction_count=0,fractional_frame_count=0)
    for number, resources in enumerate(components):
        # One bounded shard/component is sufficient for the experimental pack.
        # A later production builder may partition while retaining this writer.
        resources = sorted(resources,key=lambda r:r["resref"])
        temporary = directory / f"component-{number:04d}.registry"
        info = write(temporary,scale,resources,compress=compress,retain_zero_f=retain_zero_f)
        final = directory / registry.catalog_shard_filename(info["sha256"])
        _require(not final.exists(),"duplicate shard in catalog")
        temporary.rename(final)
        info = inspect(final,include_resource_records=True)
        infos.append(info)
        entry = registry.catalog_shard_entry_bytes(info,final)
        entries.append(entry)
        component_rows.append(dict(index=number,digest=registry.catalog_component_digest(scale,[entry]),
                                   shard_start=number,shard_count=1,resource_count=info["resource_count"],
                                   frame_count=info["frame_count"],index_bytes=info["index_bytes"],registry_bytes=info["registry_bytes"]))
        logical_digests.append(registry.catalog_source_component_sha256(scale,info["resource_records"]))
        for key in storage:
            if key!="shard_registry_version":
                storage[key] += info[key]
    directory_rows = []
    for animation in animations:
        seen = set()
        for component in animation["component_indices"]:
            _require(0 <= component < len(infos),"invalid catalog membership")
            for ordinal,ref in enumerate(infos[component]["resources"]):
                _require(ref not in seen,"duplicate resref in animation scope")
                seen.add(ref)
                directory_rows.append(dict(animation_id=animation["animation_id"],resref=ref,
                                           component_index=component,shard_index=component,resource_ordinal=ordinal))
    path = directory / registry.XN_REGISTRY_CATALOG_FILENAME
    result = registry.write_registry_catalog_index(path,scale,animations,component_rows,infos,
                                                   directory_rows,logical_digests,storage)
    checked = registry.inspect_registry_catalog(path)
    _require(checked["logical_content_sha256"]==result["logical_content_sha256"],"catalog logical digest differs")
    return result
