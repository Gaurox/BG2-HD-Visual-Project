"""Preserve native Matroska declared duration, including its existing Vorbis tail convention."""
from pathlib import Path
import struct,zlib

def vint(data,offset,is_id=False):
    first=data[offset];length=1
    while not first & (1 << (8-length)):length+=1
    value=int.from_bytes(data[offset:offset+length],'big')
    if not is_id:value &= (1 << (7*length))-1
    return value,offset+length

def elements(data,start,end):
    p=start
    while p<end:
        ident,q=vint(data,p,True);size,r=vint(data,q)
        yield ident,p,r,r+size
        p=r+size

def set_duration(path,seconds):
    path=Path(path)
    with path.open('r+b') as file:
        data=bytearray(file.read(65536))
        segment=next(x for x in elements(data,0,len(data)) if x[0]==0x18538067)
        info=next(x for x in elements(data,segment[2],len(data)) if x[0]==0x1549A966)
        children=list(elements(data,info[2],info[3]))
        scale=next((int.from_bytes(data[a:b],'big') for ident,_,a,b in children if ident==0x2AD7B1),1000000)
        crc=next((x for x in children if x[0]==0xBF),None)
        byteorder=None
        if crc:
            old=zlib.crc32(data[info[2]:crc[1]]+data[crc[3]:info[3]])
            byteorder=next(order for order in ('little','big') if int.from_bytes(data[crc[2]:crc[3]],order)==old)
        duration=next(x for x in children if x[0]==0x4489)
        size=duration[3]-duration[2];assert size in (4,8)
        data[duration[2]:duration[3]]=struct.pack('>d' if size==8 else '>f',seconds*1e9/scale)
        if crc:
            new=zlib.crc32(data[info[2]:crc[1]]+data[crc[3]:info[3]])
            data[crc[2]:crc[3]]=new.to_bytes(4,byteorder)
        file.seek(info[1]);file.write(data[info[1]:info[3]])
