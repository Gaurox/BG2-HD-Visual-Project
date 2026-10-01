"""P2 host fixtures and isolated 0x6110 Q0/Q3m experimental packs; never installs."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import time
import zlib

import numpy as np

import palette_registry as v6
import run_creature_sprite_x2 as registry
from palette_frac_encode import decode
import palette_frac_encode
from palette_oracle import read_bam_p8
from workspace_paths import get_path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "sprite/families/playable-characters/6110-human-female-fighter/research"
P1 = RESEARCH / "palette-q3m-p1-20260930-v1"
GOLDEN_SHA = "12171974b2df6423b928b880529fa277bf5ee7517e278d8d9554efa762910e4b"


def sha(path):
    with Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()


def golden():
    assert sha(P1/"decoder-golden.npz")==GOLDEN_SHA,"P1 golden fixture changed"
    with np.load(P1/"decoder-golden.npz",allow_pickle=False) as z:
        return tuple(z[k].copy() for k in ("palettes_rgba","I","F","expected_rgba"))


def _scalar_rgba(p,i,f):
    out=[]
    for primary,fraction in zip(i,f,strict=True):
        n,t=int(primary),int(fraction)
        terminal=n<=3 or (4<=n<88 and (n-4)%12==11) or (n>=88 and (n-88)%8==7)
        s=n if terminal else n+1
        out.append([((8-t)*int(p[n,c])+t*int(p[s,c])+4)//8 for c in range(3)]+[int(p[n,3])])
    return np.asarray(out,np.uint8)


def _unchecked_catalog(directory, raw, info, *, animation=0x6110, owner=1):
    """Only corruption fixtures bypass semantic inspection, with valid outer hashes."""
    directory.mkdir()
    info={**info,"sha256":hashlib.sha256(raw).hexdigest().upper(),"crc32":zlib.crc32(raw)&0xffffffff,
          "registry_bytes":len(raw)}
    leaf=directory/registry.catalog_shard_filename(info["sha256"])
    leaf.write_bytes(raw)
    component=dict(index=0,digest=registry.catalog_component_digest(info["scale"],[registry.catalog_shard_entry_bytes(info,leaf)]),
                   shard_start=0,shard_count=1,resource_count=info["resource_count"],frame_count=info["frame_count"],
                   index_bytes=info["index_bytes"],registry_bytes=len(raw))
    registry.write_registry_catalog_index(directory/registry.XN_REGISTRY_CATALOG_FILENAME,info["scale"],
        [dict(animation_id=f"0x{animation:04X}",owner=owner,component_indices=[0])],[component],[info],
        [dict(animation_id=f"0x{animation:04X}",resref="TEST",component_index=0,shard_index=0,resource_ordinal=0)],
        ["00"*32],dict(shard_registry_version=info["version"]))


def fixtures(output):
    inputs=[Path(__file__),Path(v6.__file__),Path(registry.__file__),
            Path(palette_frac_encode.__file__),P1/"decoder-golden.npz"]
    identity=hashlib.sha256("".join(sha(p) for p in inputs).encode()).hexdigest()
    output.mkdir(parents=True,exist_ok=True)
    root=output/identity[:16]
    if (root/"fixtures.json").is_file():
        proof=json.loads((root/"fixtures.json").read_text())
        for name,h in proof["sha256"].items():assert sha(root/name)==h
        (output/"ready.txt").write_text(root.name+"\n",encoding="utf-8")
        print("Reused immutable host fixtures",root)
        return
    assert not root.exists(),"Incomplete fixtures require a fresh output directory"
    root.mkdir()
    palettes,i,f,expected=golden()
    rng=np.random.default_rng(6110)
    extra=rng.integers(0,256,(32,256,4),dtype=np.uint8)
    extra[:,0]=0  # Rendering normalizes the transparent DWORD.
    extra_expected=np.stack([_scalar_rgba(p,i,f) for p in extra])
    all_p=np.concatenate((palettes,extra));all_e=np.concatenate((expected,extra_expected))
    (root/"golden.bin").write_bytes(struct.pack("<8s5I",b"IEEQ3G1\0",1,1,len(all_p),len(i),len(palettes))+
                                  i.tobytes()+f.tobytes()+all_p.tobytes()+all_e.tobytes())
    frame=dict(geometry=(228,2,-3,5,0),representatives=np.arange(256,dtype=np.uint16),
               I=i.reshape(4,456),F=f.reshape(4,456),guide=i.reshape(4,456))
    r=dict(resref="TEST",source_sha256="12"*32,frames=[frame],cycles=[[0,0],[]])
    valid={}
    for name,compress,zero,absent in (("raw",False,False,False),("compressed",True,False,False),
                                     ("absent",False,False,True),("zero-present",False,True,True)):
        resource=copy.deepcopy(r)
        if absent:resource["frames"][0]["F"].fill(0)
        info=v6.write(root/(name+".registry"),2,[resource],compress=compress,retain_zero_f=zero)
        raw=(root/(name+".registry")).read_bytes()
        valid[name]=(raw,info)
        _unchecked_catalog(root/name,raw,info)
    # Legacy V5 comparator, same I/geometry/palette and complete lookup.
    raw,info=valid["absent"]
    fh=80
    n=len(i)
    legacy=bytearray(raw[:24]);struct.pack_into("<I",legacy,8,5)
    legacy.extend(raw[32:80]);legacy.extend(raw[80:608]);legacy.extend(raw[648:648+n]);legacy.extend(raw[648+n:])
    _unchecked_catalog(root/"legacy-v5",bytes(legacy),{**info,"version":5})
    partial=copy.deepcopy(r);small=partial["frames"][0]
    small.update(geometry=(2,2,-3,5,0),I=np.full((4,4),4,np.uint8),F=np.full((4,4),3,np.uint8),guide=np.full((4,4),4,np.uint8))
    small["representatives"]=np.full(256,65535,np.uint16);small["representatives"][4]=0
    pi=v6.write(root/"partial.registry",2,[partial],compress=False)
    pr=(root/"partial.registry").read_bytes()
    _unchecked_catalog(root/"partial",pr,pi)
    zero_partial=copy.deepcopy(partial);zero_partial["frames"][0]["F"].fill(0)
    zi=v6.write(root/"partial-zero.registry",2,[zero_partial],compress=False,retain_zero_f=True)
    _unchecked_catalog(root/"partial-zero",(root/"partial-zero.registry").read_bytes(),zi)
    legacy_small = v5_from_raw_v6((root/"partial-zero.registry").read_bytes(), resref="LEGACY", half_transparent=True)
    for name, groups, animations in (
        ("mixed-components", [[0], [1]], None),
        ("mixed-component-bad", [[0, 1]], [dict(animation_id="0x6110", owner=1, component_indices=[0])]),
        ("mixed-owner-bad", [[0], [1]], [dict(animation_id="0x6110", owner=1, component_indices=[0, 1]),
                                      dict(animation_id="0x7000", owner=3, component_indices=[0])])):
        component_catalog(root/name, [(pr, pi), (legacy_small, {**zi, "version":5})],
                          groups=groups, animations=animations)
    component_catalog(root/"mixed-shared", [(pr, pi), (v5_from_raw_v6(
        (root/"partial-zero.registry").read_bytes(), resref="TEST"), {**zi, "version":5})],
        animations=[dict(animation_id="0x6110", owner=1, component_indices=[0]),
                    dict(animation_id="0x6115", owner=1, component_indices=[1])])
    # Five 32MiB I+F frames exceed the unchanged 128MiB lazy cache budget.
    # Scale4 permits the 160MiB decoded shard; each plane is highly compressible.
    large_i=np.full((4096,4096),4,np.uint8);large_f=np.full_like(large_i,3)
    large=dict(geometry=(1024,1024,0,0,0),representatives=small["representatives"],
               I=large_i,F=large_f,guide=large_i)
    eviction=dict(resref="TEST",source_sha256="12"*32,frames=[large]*5,cycles=[[0,1,2,3,4],[]])
    ei=v6.write(root/"eviction.registry",4,[eviction])
    _unchecked_catalog(root/"eviction",(root/"eviction.registry").read_bytes(),ei)
    # P3 complete x2: 80MiB I + 80MiB F, same bounded 32MiB frames/cache.
    x2=bytearray((root/"eviction.registry").read_bytes());struct.pack_into("<I",x2,12,2)
    cursor=80
    for _ in range(5):
        struct.pack_into("<HH",x2,cursor,2048,2048)
        cursor+=568+struct.unpack_from("<I",x2,cursor+12)[0]+struct.unpack_from("<I",x2,cursor+560)[0]
    (root/"eviction-x2.registry").write_bytes(x2)
    x2info=v6.inspect(root/"eviction-x2.registry")
    _unchecked_catalog(root/"eviction-x2",bytes(x2),x2info)
    # I-only 144MiB remains below the new 256MiB combined bound: this must
    # independently fail the unchanged 128MiB I bound, not an I+F overrun.
    frame_bytes=568+struct.unpack_from("<I",x2,92)[0]
    index_only=bytearray(x2[80:80+frame_bytes]);index_only[10]=0
    index_only[528:560]=bytes([1<<4])+bytes(31)
    struct.pack_into("<I",index_only,560,0);index_only[564]=0
    over=bytearray(x2[:80]);struct.pack_into("<I",over,72,9)
    over.extend(index_only*9);over.extend(x2[cursor:])
    _unchecked_catalog(root/"x2-index-budget",bytes(over),{**x2info,"frame_count":9,"index_bytes":9*4096*4096})
    del large_i,large_f,large,eviction
    cases=[(name,"ok",0x6110) for name in (*valid,"legacy-v5","partial","partial-zero","eviction","eviction-x2")]
    cases.append(("x2-index-budget","bad",0x6110))
    raw,info=valid["raw"]
    mutations=[("profile",24,struct.pack("<I",2)),("rule",28,struct.pack("<I",2)),
               ("version",8,struct.pack("<I",7)),("scale",12,struct.pack("<I",3)),
               ("animation",20,struct.pack("<I",0x6110)),("frames",72,struct.pack("<I",4097)),
               ("width",fh,b"\0\0"),("overflow",fh,struct.pack("<HH",65535,65535)),
               ("transparent",fh+8,b"\1"),("I-codec",fh+9,b"\2"),("B-flag",fh+10,b"\2"),
               ("reserved",fh+11,b"\1"),("I-size",fh+12,struct.pack("<I",n-1)),
               ("F-size",fh+560,struct.pack("<I",n-1)),("F-codec",fh+564,b"\2"),
               ("F-reserved",fh+565,b"\1"),("F-range",648+n,b"\x08"),
               ("F-special",648+n,b"\1"),("F-terminal",648+2*n-1,b"\1"),
               ("representative",fh+16,struct.pack("<H",456)),("lookup",len(raw)-8,struct.pack("<I",1))]
    corrupt={}
    for name,offset,value in mutations:
        bad=bytearray(raw);bad[offset:offset+len(value)]=value
        corrupt[name]=(bytes(bad),info)
    for name,size in (("prefix",20),("profiles-truncated",28),("frame-truncated",200),
                      ("I-truncated",650),("F-truncated",650+n),("cycle-truncated",len(raw)-1)):
        corrupt[name]=(raw[:size],info)
    corrupt["trailing"]=(raw+b"x",info)
    for name,bits in (("dep-missing",0x10),("dep-excess",0x70)):
        bad=bytearray(pr);bad[fh+528]=bits;corrupt[name]=(bytes(bad),pi)
    comp,ci=valid["compressed"]
    ni,nf=struct.unpack_from("<I",comp,fh+12)[0],struct.unpack_from("<I",comp,fh+560)[0]
    assert comp[fh+9]==comp[fh+564]==1,"Fixture must exercise real XPRESS on both planes"
    with registry.WindowsXpressHuffCodec(compress=True) as compressor:
        for plane,start,length,header_offset,payload in (("I",648,ni,fh+12,i.tobytes()),
                                                        ("F",648+ni,nf,fh+560,f.tobytes())):
            bad=bytearray(comp);bad[start:start+length]=bytes(length)
            corrupt[plane+"-xpress-corrupt"]=(bytes(bad),ci)
            replacement=compressor.encode(payload[:-1])
            bad=bytearray(comp[:start]+replacement+comp[start+length:])
            struct.pack_into("<I",bad,header_offset,len(replacement))
            corrupt[plane+"-decoded-length"]=(bytes(bad),ci)
    for name,(data,metadata) in corrupt.items():
        _unchecked_catalog(root/name,data,metadata)
        cases.append((name,"bad",0x6110))
    _unchecked_catalog(root/"owner",raw,info,animation=0xE400,owner=2)
    cases.append(("owner","bad",0xE400))
    (root/"cases.tsv").write_text("".join(f"{name}\t{status}\t{animation}\n" for name,status,animation in cases),encoding="utf-8")
    proof=dict(schema="bg2-upscale-palette-p2-host-fixtures-v1",p1_golden_sha256=GOLDEN_SHA,
               source_identity=identity,reference_palettes=18,synthetic_palettes=32,pairs=n,
               valid_cases=sum(s=="ok" for _,s,_ in cases),invalid_cases=sum(s=="bad" for _,s,_ in cases),
               sha256={p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob("*")) if p.is_file()})
    (root/"fixtures.json").write_text(json.dumps(proof,indent=2)+"\n",encoding="utf-8")
    (output/"ready.txt").write_text(root.name+"\n",encoding="utf-8")
    print(json.dumps({k:proof[k] for k in ("reference_palettes","synthetic_palettes","pairs","valid_cases","invalid_cases")},indent=2))


def v5_from_raw_v6(raw, *, resref="LEGACY", half_transparent=False):
    """Small uncompressed one-frame test fixture, independent physical layout."""
    if raw[89] or raw[644] or struct.unpack_from("<II", raw, 72) != (1, 2):
        raise ValueError("Fixture requires one raw frame with absent F and two cycles")
    count = struct.unpack_from("<I", raw, 92)[0]
    stored_f = struct.unpack_from("<I", raw, 640)[0]
    if any(raw[648 + count:648 + count + stored_f]):
        raise ValueError("Legacy fixture requires zero fractions")
    legacy = bytearray(raw[:24]); struct.pack_into("<I", legacy, 8, 5)
    legacy.extend(raw[32:80]); legacy[24:32] = resref.encode().ljust(8, b"\0")
    legacy.extend(raw[80:608]); legacy[82:84] = b"\0\0"
    legacy.extend(raw[648:648 + count]); legacy.extend(raw[648 + count + stored_f:])
    if half_transparent:
        legacy[24 + 48 + 528 + count // 2:24 + 48 + 528 + count] = bytes(count - count // 2)
        struct.pack_into("<H", legacy, 24 + 48 + 16, 2)
    return bytes(legacy)


def component_catalog(directory, leaves, *, groups=None, animations=None):
    """Authenticated catalog fixtures; deliberately permits invalid compositions."""
    directory.mkdir()
    groups = groups or [[n] for n in range(len(leaves))]
    animations = animations or [dict(animation_id="0x6110", owner=1, component_indices=[0, 1]),
                                dict(animation_id="0x7000", owner=3, component_indices=[1])]
    components, shards, resource_lists = [], [], []
    for number, group in enumerate(groups):
        start = len(shards)
        for n in group:
            raw, info = leaves[n]
            version = struct.unpack_from("<I", raw, 8)[0]
            ref = raw[32 if version == 6 else 24:40 if version == 6 else 32].rstrip(b"\0").decode()
            info = {**info, "sha256":hashlib.sha256(raw).hexdigest().upper(), "crc32":zlib.crc32(raw),
                    "registry_bytes":len(raw), "version":version, "index":len(shards)}
            leaf = directory / registry.catalog_shard_filename(info["sha256"])
            leaf.write_bytes(raw); shards.append(info); resource_lists.append([ref])
        selected = shards[start:]
        components.append(dict(index=number, shard_start=start, shard_count=len(group),
            digest=registry.catalog_component_digest(2, [registry.catalog_shard_entry_bytes(s, directory) for s in selected]),
            **{key:sum(s[key] for s in selected) for key in ("resource_count", "frame_count", "index_bytes", "registry_bytes")}))
    rows=[]
    for a in animations:
        for c in a["component_indices"]:
            component=components[c]
            for s in range(component["shard_start"], component["shard_start"] + component["shard_count"]):
                for n,ref in enumerate(resource_lists[s]):
                    rows.append(dict(animation_id=a["animation_id"], resref=ref, component_index=c, shard_index=s, resource_ordinal=n))
    return registry.write_registry_catalog_index(directory / registry.XN_REGISTRY_CATALOG_FILENAME,
        2, animations, components, shards, rows, ["00"*32]*len(components),
        dict(shard_registry_version=0, shard_registry_versions=[5, 6]))


def _pack_oracle(path,resources,palettes):
    count=sum(len(r["frames"]) for r in resources)
    with path.open("xb") as out:
        out.write(struct.pack("<8sII",b"IEEQ3P1\0",len(palettes),count))
        out.write(palettes.tobytes())
        for r in resources:
            lookup={}
            for sequence,cycle in enumerate(r["cycles"]):
                for slot,index in enumerate(cycle):lookup.setdefault(index,(sequence,slot))
            assert lookup,"No native slots for experimental resource"
            fallback=next(iter(lookup.values()))
            for index,frame in enumerate(r["frames"]):
                sequence,slot=lookup.get(index,fallback)
                if index not in lookup:sequence |= 0x80000000
                i=frame["I"];f=frame.get("F",np.zeros_like(i))
                out.write(struct.pack("<8s4I",r["resref"].encode().ljust(8,b"\0"),index,sequence,slot,i.size))
                for palette in palettes:
                    pixels=decode(i,f,palette)
                    out.write(hashlib.sha256(pixels.tobytes()).digest())


def packs(output,scales):
    """World subset only: full BAM tables, P1 sampled Q3m, xBR elsewhere."""
    from reboutcx_multipal import prepare_guides
    started=time.monotonic()
    assert not (output/"packs.json").exists(),"Completed P2 pack run is immutable"
    names=("CHFF4G11","CHFF4G12","WQNJ6G1","WQND3G1","WQNS1G1")
    experiment=json.loads((P1/"experiment.json").read_text())
    palettes,_,_,_=golden()
    sources,frames={},{}
    for ref in names:
        metadata=experiment["sources"][ref]
        path=ROOT/metadata["canonical_bam"]
        assert sha(path)==metadata["sha256"],f"Source changed: {ref}"
        bam=read_bam_p8(path.read_bytes());assert bam["cycles"]==metadata["cycles"]
        sources[ref]=bam
        for frame in bam["frames"]:
            i=frame["indices"];h,w=i.shape
            rgba=np.empty((h,w,4),np.uint8);rgba[:,:,:3]=bam["palette_rgb"][i]
            rgba[:,:,3]=np.where(i==bam["transparent"],0,255)
            key=f"{ref}_{frame['index']:04d}"
            frames[key]=registry.SourceFrame(ref,frame["index"],w,h,frame["center_x"],frame["center_y"],
                                             bam["transparent"],i,bam["palette_rgb"],rgba.tobytes())
    work=output/"work"
    (work/"guides").mkdir(parents=True,exist_ok=True)
    sampled=sorted(set(frames)&set(experiment["frames"]))
    for key in sampled:
        for scale in (2,4):
            path=work/"guides"/f"{key}-x{scale}.npz"
            original=P1/"guides"/path.name
            if not path.exists():shutil.copy2(original,path)
            assert sha(path)==sha(original),"Frozen P1 guide differs"
    keys=list(frames)
    context={}
    for start in range(0,len(keys),64):
        chunk=keys[start:start+64]
        context=prepare_guides({key:frames[key] for key in chunk},work)
        print(f"xBR fallback guides {min(start+64,len(keys))}/{len(keys)}",flush=True)
    reports=[]
    for scale in scales:
        common=[]
        for ref in names:
            bam=sources[ref]
            records=[]
            for index,src in enumerate(bam["frames"]):
                key=f"{ref}_{index:04d}";frame=frames[key]
                with np.load(work/"guides"/f"{key}-x{scale}.npz",allow_pickle=False) as z:guide=z["guide"].copy()
                reps=np.full(256,65535,np.uint16)
                values,offsets=np.unique(frame.indices,return_index=True)
                assert np.all(offsets<65535),"Source representatives do not fit u16"
                reps[values]=offsets
                record=dict(geometry=(frame.width,frame.height,frame.center_x,frame.center_y,frame.transparent),
                            representatives=reps,guide=guide,I=guide,key=key)
                records.append(record)
            common.append(dict(resref=ref,source_sha256=experiment["sources"][ref]["sha256"],
                               frames=records,cycles=[c["frame_indices"] for c in bam["cycles"]]))
        for method in ("Q0","Q3m-k6"):
            resources=[]
            for r in common:
                updated=[]
                for frame in r["frames"]:
                    frame=dict(frame)
                    if frame["key"] in sampled:
                        with np.load(P1/"encoded"/f"{frame['key']}-x{scale}.npz",allow_pickle=False) as z:
                            frame.update(I=z[f"{method}_I"].copy(),F=z[f"{method}_F"].copy(),dep=z[f"{method}_dep"].copy())
                    updated.append(frame)
                resources.append({**r,"frames":updated})
            label=f"x{scale}-{method.lower()}"
            directory=output/"packs"/label/"iee-assets/creature-sprites"
            info=v6.write_catalog(directory,scale,[resources])
            oracle=output/"packs"/label/"decoder-oracle.bin"
            _pack_oracle(oracle,resources,palettes)
            print(f"Experimental {label}: {info['total_frames']} frames, {info['total_registry_bytes']} registry bytes",flush=True)
            # Prove every reconstructed stream equals the exact input frame.
            physical=directory/registry.catalog_shard_filename(info["shards"][0]["sha256"])
            checked=v6.inspect(physical,include_frames=True)
            for original,readback in zip(sorted(resources,key=lambda r:r["resref"]),checked["frame_data"],strict=True):
                assert original["resref"]==readback["resref"] and original["cycles"]==readback["cycles"]
                assert original["source_sha256"]==readback["source_sha256"]
                for a,b in zip(original["frames"],readback["frames"],strict=True):
                    assert a["geometry"]==b["geometry"] and np.array_equal(a["representatives"],b["representatives"])
                    assert a["I"].tobytes()==b["I"]
                    f=a.get("F",np.zeros_like(a["I"]))
                    assert (f.tobytes() if np.any(f) else b"")==b["F"]
            reports.append(dict(method=method,scale=scale,assets=directory.relative_to(output).as_posix(),
                                decoder_oracle=oracle.relative_to(output).as_posix(),oracle_sha256=sha(oracle),
                                sampled_q3m_or_q0_frames=len(sampled),fallback_xbr_frames=len(frames)-len(sampled),
                                placeholders=sum(f.indices.shape==(1,1) and int(f.indices[0,0])==2 for f in frames.values()),
                                info=info))
    report=dict(schema="bg2-upscale-character-palette-p2-packs-v1",animation_id="0x6110",
                source_resrefs=list(names),source_frames=len(frames),sampled_frames=sampled,
                class_profile=experiment["class_profile"],decode_rule=experiment["decode_rule"],
                encoder=experiment["encoder"],k=6,boundary_mixing=False,guide_context=context,
                p1_golden_sha256=GOLDEN_SHA,scope="Small experimental world subset; no installation/release/P3; no new neural inference",
                runtime_alpha="neutral/synthetic oracle only; live effects still require P3",
                elapsed_seconds=time.monotonic()-started,packs=reports,
                source_sha256={ref:experiment["sources"][ref]["sha256"] for ref in names},
                p1_files_sha256={str(p.relative_to(P1)):sha(p) for key in sampled for scale in scales
                                for p in (P1/"encoded"/f"{key}-x{scale}.npz",P1/"guides"/f"{key}-x{scale}.npz")})
    (output/"packs.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    f=sub.add_parser("fixtures");f.add_argument("--output",type=Path,required=True)
    p=sub.add_parser("packs");p.add_argument("--output",type=Path,required=True)
    p.add_argument("--scale",type=int,choices=(2,4),action="append")
    args=parser.parse_args(argv)
    if args.command=="fixtures":fixtures(args.output)
    elif args.command=="packs":packs(args.output,args.scale or [2,4])


if __name__=="__main__":main()
