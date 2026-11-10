"""Read-only stock+active-override usage scan for seven unresolved native owners."""
from pathlib import Path
from collections import Counter
from functools import lru_cache
import csv
import hashlib
import json
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'pipeline/recipes/projectiles-secondary-links-20261028-v1')]
from bg2lib import load_key,resolve_resource
from workspace_paths import get_path
from projectile_tracking import ids_entries,ability_projectiles,parse_pro,projectile_child_id
from native import PE

TARGETS={21:'SPBRNHND',24:'SPBRNHND',25:'SPBRNHND',44:'SPSMKJET',92:'MAGMIS',96:'COLRSPRY',241:'SPHOLYMT'}
NAMES=set(TARGETS.values())|{'LIGHTSTO'}
EXT={1:'bmp',1000:'bam',1005:'itm',1006:'spl',1007:'bcs',1008:'ids',1009:'cre',1010:'are',1011:'dlg',1016:'eff',1017:'bs',1018:'chr',1013:'gam',1019:'vvc',1020:'vef',1021:'pro',1012:'2da'}


def digest(raw):return hashlib.sha256(raw).hexdigest().upper()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out=ROOT/sys.argv[1];assert not out.exists();out.mkdir(parents=True)
    game=get_path('bg2ee_game_root',required=True);bifs,entries=load_key();key={(n.upper(),t):loc for n,t,loc in entries}
    stock_only='--stock-only' in sys.argv
    active=dict(key)
    if not stock_only:
        for t,ext in EXT.items():
            for p in (game/'override').glob('*.'+ext):active.setdefault((p.stem.upper(),t),None)
    inputs={};counts=Counter();effectcounts=Counter();refs=[];metadata=[];assetrefs=[];actioncounts=Counter();scripts=[];warnings=[];savedtraps=[];dialog_lightning=[]

    @lru_cache(None)
    def read(n,t):
        over=game/'override'/(n+'.'+EXT[t])
        if not stock_only and over.exists():raw=over.read_bytes();origin='config://bg2ee_game_root/override/'+over.name
        elif (n,t) in key:raw=resolve_resource(bifs,key[n,t])[0];origin=f'KEY://{n}.{t}'
        else:return None
        inputs[origin]=digest(raw);return raw

    projectl=ids_entries(read('PROJECTL',1008));action=read('ACTION',1008).decode('latin1')
    action_sigs={}
    for line in action.splitlines():
        m=re.match(r'\s*(\d+)\s+(.*)',line)
        if m:action_sigs.setdefault(int(m[1]),[]).append(m[2])
    projectile_actions=[line for line in action.splitlines() if re.search('projectile|missile',line,re.I)]
    save(out/'action-signatures.json',dict(direct_projectile_signatures=projectile_actions,
        visual_and_lightning={str(k):v for k,v in action_sigs.items() if any(re.search('VisualEffect|CallLightning',x,re.I) for x in v)}))
    def hit(owner,kind,ident,offset,**extra):
        if ident in TARGETS:refs.append(dict(owner=owner,kind=kind,PROJECTL=ident,offset=hex(offset),**extra))
    op141={4*s+k:118+3*s+k for s in range(8) for k in range(3)}
    op141.update({32:142,33:143,34:144,35:145,36:146,37:147,38:109,39:207})
    def effect(owner,raw,pos,v2=False,header=True):
        # EFF V2 file vs CRE EFF V2 without 8-byte header.
        base=pos-(0 if header else 8)
        if v2:
            op=struct.unpack_from('<I',raw,base+0x10)[0];p1,p2=struct.unpack_from('<II',raw,base+0x1c)
            prov=struct.unpack_from('<I',raw,base+0xa0)[0]
            if (prov&65535) in TARGETS:metadata.append(dict(owner=owner,offset=hex(base+0xa0),value=prov,PROJECTL_low16=prov&65535,opcode=op))
        else:op=struct.unpack_from('<H',raw,pos)[0];p1,p2=struct.unpack_from('<II',raw,pos+4)
        effectcounts[op]+=1
        if op==140:
            if p2==0:
                # Both conventions retained until native binding checked; a negative scan is conservative.
                hit(owner,'opcode140-direct',p1-1,pos,parameter1=p1,parameter2=p2)
                hit(owner,'opcode140-direct-conservative-native-index',p1,pos,parameter1=p1,parameter2=p2)
        elif op==141:hit(owner,'opcode141',op141.get(p2),pos,parameter1=p1,parameter2=p2)
        elif op==327:
            # Actual native call1cab3e: ((p2&0xfff)+0x1000)+1. Cannot launch these IDs<255.
            hit(owner,'opcode327', (p2&0xfff)+4096,pos,parameter1=p1,parameter2=p2)
        elif op==339:
            hit(owner,'opcode339-conservative-direct',p2,pos,parameter1=p1,parameter2=p2)
            hit(owner,'opcode339-conservative-onebased',p2-1,pos,parameter1=p1,parameter2=p2)

    def cre(owner,raw):
        if raw[:8]!=b'CRE V1.0':warnings.append(dict(owner=owner,kind='unknown-CRE-version',signature=repr(raw[:8])));return
        offset,count=struct.unpack_from('<II',raw,0x2c4);v2=raw[0x33]==1;size=0x108 if v2 else 48
        assert not count or offset+count*size<=len(raw),(owner,offset,count,len(raw))
        for i in range(count):effect(owner,raw,offset+i*size,v2,False)
        counts['CRE_effects']+=count

    # Every physical data resource with projectile-generating fields, not only currently referenced spells.
    for (n,t) in sorted(active):
        if t not in (1005,1006,1009,1010,1016,1021,1007,1017,1018,1013,1011,1019,1020,1012):continue
        raw=read(n,t);owner=n+'.'+EXT[t];counts[EXT[t]]+=1
        if t in (1005,1006):
            for ability,offset,rawid in ability_projectiles(raw,EXT[t].upper()):
                if rawid:hit(owner,'ability',rawid-1,offset,raw_id=rawid,ability=ability)
            offset=struct.unpack_from('<I',raw,0x6a)[0]
            if offset:
                assert (len(raw)-offset)%48==0,owner
                for p in range(offset,len(raw),48):effect(owner,raw,p)
        elif t==1016:
            if raw[:8]==b'EFF V2.0':effect(owner,raw,0,True)
            else:warnings.append(dict(owner=owner,kind='unknown-EFF-version',signature=repr(raw[:8])))
        elif t==1009:cre(owner,raw)
        elif t==1018:
            assert raw[:8]==b'CHR V2.0',owner
            offset,size=struct.unpack_from('<II',raw,0x28)
            assert offset+size<=len(raw),owner
            cre(owner+':embedded',raw[offset:offset+size]);counts['CHR_embedded_CRE']+=1
        elif t==1013:
            # Header signatures additionally cover CRE blobs embedded in stock GAM,
            # never player savegame directories. Counts/bounds validated by CRE reader.
            for m in re.finditer(re.escape(b'CRE V1.0'),raw):
                cre(owner+f':embedded@{m.start():x}',raw[m.start():]);counts['GAM_embedded_CRE']+=1
        elif t==1010:
            assert raw[:8]==b'AREAV1.0',owner
            offset,count=struct.unpack_from('<II',raw,0xcc)
            assert not count or offset+count*0x1c<=len(raw),owner
            for i in range(count):
                p=offset+i*0x1c;name=raw[p:p+8].split(b'\0')[0].decode('ascii').upper();value=struct.unpack_from('<H',raw,p+0xe)[0]
                savedtraps.append(dict(owner=owner,offset=hex(p),resource=name,raw_id=value))
                hit(owner,'saved-area-trap-onebased',value-1,p+0xe,raw_id=value)
                hit(owner,'saved-area-trap-conservative-direct',value,p+0xe,raw_id=value)
            actor_offset,actor_count=struct.unpack_from('<IH',raw,0x54)
            for i in range(actor_count):
                p=actor_offset+i*0x110;co,cs=struct.unpack_from('<II',raw,p+0x88)
                if co and cs:
                    assert co+cs<=len(raw),(owner,'embedded-CRE')
                    cre(owner+f':actor{i}',raw[co:co+cs]);counts['embedded_CRE']+=1
        elif t==1021:
            p=parse_pro(raw)
            if p.get('area_flags',0)&16:hit(owner,'secondary-PRO',projectile_child_id('secondary-projectile',p['secondary_raw']),0x214)
            if p.get('explosion_projectile_raw'):hit(owner,'explosion-PRO',projectile_child_id('explosion-projectile',p['explosion_projectile_raw']),0x21a)
            if p['extended_flags']&1024:warnings.append(dict(owner=owner,kind='multiple-previous-native-branch'))
        elif t in (1007,1017):
            text=raw.decode('latin1')
            found=0
            for m in re.finditer(r'(?:^|\n)AC\r?\n(\d+)OB\r?\n(.*?)AC(?=\r?\n|$)',text,re.S):
                aid=int(m[1]);body=m[2];found+=1;actioncounts[aid]+=1
                tail=re.split(r'OB\r?\n',body)[-1];strings=re.findall(r'"([^"\r\n]*)"',tail)
                if aid in (68,272,273) or any(s.upper() in NAMES for s in strings):
                    scripts.append(dict(owner=owner,offset=m.start(),action=aid,signature=action_sigs.get(aid,[]),tail=tail.strip(),strings=strings))
            expected=len(re.findall(r'(?:^|\n)AC\r?\n\d+OB\r?\n',text))
            assert found==expected,(owner,'unparsed script action',found,expected)
        elif t==1011:
            for m in re.finditer(rb'(?i)\bCallLightning\s*\(',raw):dialog_lightning.append(dict(owner=owner,offset=hex(m.start())))
        # Exact asset names are separate leads, never automatically interpreted as projectile IDs.
        for name in NAMES:
            for m in re.finditer(rb'(?<![A-Z0-9_])'+name.encode()+rb'(?![A-Z0-9_])',raw.upper()):
                assetrefs.append(dict(owner=owner,name=name,offset=hex(m.start()),context=repr(raw[max(0,m.start()-25):m.end()+25])))
        if sum(counts[k] for k in EXT.values())%2500==0:print('Scanned',dict(counts),flush=True)
    save(out/'references.json',refs);save(out/'effect-provenance-matches.json',metadata);save(out/'asset-name-references.json',assetrefs)
    save(out/'script-actions.json',scripts);save(out/'saved-area-traps.json',savedtraps);save(out/'inputs.json',inputs)
    save(out/'dialogue-lightning-actions.json',dialog_lightning)
    save(out/'summary.json',dict(scope='Stock KEY only;no save or override content' if stock_only else 'Stock KEY overlay plus all active relevant overrides;no save/third-party installation inferred',
        counts=dict(counts),opcode_counts={str(k):effectcounts[k] for k in [140,141,327,339]},
        effect_provenance_matches=len(metadata),target_projectile_references=len(refs),asset_name_leads=len(assetrefs),
        script_action_counts={str(k):actioncounts[k] for k in [68,272,273]},dialogue_CallLightning=len(dialog_lightning),all_script_actions=sum(actioncounts.values()),warnings=warnings))
    print((out/'summary.json').read_text(encoding='utf-8'),flush=True)


if __name__=='__main__':main()
