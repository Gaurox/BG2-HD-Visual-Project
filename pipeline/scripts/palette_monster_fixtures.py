"""Synthetic native-reader fixtures only; not source assets, inference results or production packs."""
from __future__ import annotations
import argparse
import copy
from pathlib import Path
import struct

import numpy as np

from palette_monster_contract import get_profile
from palette_p2 import component_catalog
import palette_registry as v6


def make_resource(pid, fractional=True):
    p=get_profile(pid);ref=next(iter(p.sources))
    i=np.concatenate((np.arange(3,dtype=np.uint8),np.repeat(np.arange(3,256,dtype=np.uint8),8),np.array([2],np.uint8))).reshape(2,1014)
    f=np.concatenate((np.zeros(3,np.uint8),np.tile(np.arange(8,dtype=np.uint8),253),np.zeros(1,np.uint8))).reshape(i.shape)
    if not fractional: f.fill(0)
    reps=np.full(256,65535,np.uint16)
    frame=dict(geometry=(507,1,-3,5,0),representatives=reps,guide=i.copy(),I=i,F=f,dep=p.dependency_mask(i,f))
    return dict(resref=ref,source_sha256=p.sources[ref]["canonical_sha256_registered"],frames=[frame],cycles=[[0,0],[]])


def golden(path, pid, frame):
    p=get_profile(pid)
    palettes=list(p.fitting.copy())
    partial=p.fitting[0].copy();partial[:,3]=128;partial[0]=0;partial[1,3]=64;palettes.append(partial)
    opaque=p.fitting[0].copy();opaque[:,3]=255;opaque[0]=0;palettes.append(opaque)
    rng=np.random.default_rng(pid);arbitrary=rng.integers(0,256,(256,4),dtype=np.uint8)
    arbitrary[:,3]=200;arbitrary[0]=0;arbitrary[1,3]=100;palettes.append(arbitrary)
    i,f=frame["I"].reshape(-1),frame["F"].reshape(-1)
    with path.open("xb") as stream:
        stream.write(struct.pack("<4I",pid,2,len(palettes),len(i)))
        for palette in palettes:
            palette[0]=0  # Native reader normalizes the transparent DWORD.
            stream.write(palette.tobytes())
            expected=[]
            for n,t in zip(i,f):
                n,t=int(n),int(t);s=int(p.succ[n])
                expected.extend([((8-t)*int(palette[n,c])+t*int(palette[s,c])+4)//8 for c in range(3)]+[int(palette[n,3])])
            stream.write(bytes(expected))


def fixtures(output):
    output=Path(output)
    if output.exists(): raise ValueError("new fixture directory required")
    output.mkdir(parents=True)
    cases=[];valid={}
    def catalog(name,raw,info,animation,*,animations=None):
        animations=animations or [dict(animation_id=f"0x{animation:04X}",owner=3,component_indices=[0])]
        component_catalog(output/name,[(raw,info)],animations=animations)
    for pid in range(2,8):
        p=get_profile(pid);animation=int(next(iter(p.animation_ids)),16)
        for label,compress,frac in (("raw",False,True),("compressed",True,True),("zero",False,False)):
            name=f"p{pid}-{label}";r=make_resource(pid,frac)
            leaf=output/(name+".registry")
            info=v6.write(leaf,2,[r],class_profile_id=pid,decode_rule_id=2,compress=compress)
            raw=leaf.read_bytes();catalog(name,raw,info,animation)
            golden(output/(name+".bin"),pid,r["frames"][0])
            cases.append((name,"ok",animation,r["resref"]))
            if label=="raw": valid[pid]=(raw,info,animation,r)
    raw,info,animation,r=valid[4]
    # Keep outer shard SHA/CRC and routing valid: failures must come from the V6 reader.
    mutations=(("unknown-profile",24,99),("wrong-rule",28,1),("wrong-profile",24,5),
               ("wrong-scale",12,4))
    for name,offset,value in mutations:
        bad=bytearray(raw);struct.pack_into("<I",bad,offset,value)
        catalog(name,bytes(bad),info,animation);cases.append((name,"bad",animation,r["resref"]))
    for name,offset in (("source-hash",40),("dependency",80+528),("special-fraction",648+2028),
                        ("fraction-eight",648+2028+3)):
        bad=bytearray(raw);bad[offset]=8 if name=="fraction-eight" else bad[offset]^1
        catalog(name,bytes(bad),info,animation);cases.append((name,"bad",animation,r["resref"]))
    catalog("wrong-owner-animation",raw,info,0x7f07)
    cases.append(("wrong-owner-animation","bad",0x7f07,r["resref"]))
    catalog("shared-wrong-owner",raw,info,animation,animations=[dict(animation_id="0x7F30",owner=3,component_indices=[0]),
            dict(animation_id="0x7F07",owner=3,component_indices=[0])])
    cases.append(("shared-wrong-owner","bad",animation,r["resref"]))
    small=dict(resref="CHAR",source_sha256="12"*32,cycles=[[0,0],[]],frames=[dict(geometry=(2,2,-3,5,0),
        representatives=np.full(256,65535,np.uint16),I=np.full((4,4),4,np.uint8),F=np.full((4,4),3,np.uint8),guide=np.full((4,4),4,np.uint8))])
    ci=v6.write(output/"character.registry",2,[small],compress=False)
    component_catalog(output/"mixed",[(raw,info),((output/"character.registry").read_bytes(),ci)],
        animations=[dict(animation_id="0x7F30",owner=3,component_indices=[0]),dict(animation_id="0x6110",owner=1,component_indices=[1])])
    (output/"cases.tsv").write_text("".join(f"{n}\t{s}\t{a}\t{ref}\n" for n,s,a,ref in cases),encoding="utf-8")
    print(f"synthetic fixtures: {len(cases)} cases + mixed Character/Monster catalog")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",required=True,type=Path)
    fixtures(parser.parse_args().output)
