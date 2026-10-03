"""Verify the pinned BG2EE creature vtables/Render signatures against the engine manifest."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import struct
from palette_oracle import pe_rva, EXE_SHA256
from workspace_paths import get_path

ROOT = Path(__file__).resolve().parents[2]
KNOWN = {
    'character':(1,0x5aac20,0x32c240,0x33eea0),
    'character_old':(6,0x5aae10,0x32c910,0x33f250),
    'monster':(3,0x5a98b0,0x32d770,0x33f990),
    'monster_old':(7,0x5a9ab0,0x330180,0x340df0),
    'monster_icewind':(2,0x5a9ca0,0x32e360,0x33fee0),
    'monster_quadrant':(4,0x5aa460,0x3305a0,0x341010),
    'multi_new':(5,0x5ab000,0x32fd20,0x340bc0),
    'monster_layered':(8,0x5aa650,0x32ee90,0x3403f0),
    'monster_ankheg':(9,0x5aaa30,0x32dd70,0x33fcd0),
    'monster_large':(10,0x5a9e90,0x32eab0,0x340250),
    'monster_large16':(11,0x5aa080,0x32eab0,0x3400b0),
    'ambient':(12,0x5a96c0,0x32ba40,0x33ea60),
    'ambient_static':(13,0x5a94d0,0x32be60,0x33ec40),
    'town_static':(14,0x5a92e0,0x3309b0,0x341250),
    'flying':(15,0x5a90f0,0x32d390,0x33f7c0),
}


def analyze():
    raw = (get_path('bg2ee_game_root',required=True)/'BaldurReal.exe').read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXE_SHA256: raise ValueError('unidentified executable')
    pe = struct.unpack_from('<I',raw,0x3c)[0]; base = struct.unpack_from('<Q',raw,pe+48)[0]
    manifest = (ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/build_manifest.cpp').read_text()
    families = []
    for family,(owner,vtable,render,parser) in KNOWN.items():
        pointers = struct.unpack('<62Q',pe_rva(raw,vtable,62*8))
        if pointers[38] != base+render or pointers[61] != base+parser: raise ValueError('native vtable differs: '+family)
        # INI parser's LEA RIP-relative reference must identify this native subclass.
        code = pe_rva(raw,parser,384); references = []
        for match in re.finditer(rb'\x48\x8d[\x0d\x15\x35\x3d]',code):
            loc = match.start(); target = parser+loc+7+struct.unpack_from('<i',code,loc+3)[0]
            try: value = pe_rva(raw,target,32).split(b'\0')[0].decode('ascii')
            except (ValueError,UnicodeDecodeError): continue
            if value == family: references.append(hex(parser+loc))
        if not references: raise ValueError('native INI parser family differs: '+family)
        if owner >= 6:
            pattern = re.search(r'\{(0x[0-9a-f]+), (0x[0-9a-f]+), '+str(owner)+r', [^\n]+"([0-9A-F ]+)"\}',manifest)
            if owner == 11: pattern = re.search(r'\{(0x[0-9a-f]+), (0x[0-9a-f]+), 10, (0x[0-9a-f]+), 11, [^\n]+"([0-9A-F ]+)"\}',manifest)
            if not pattern: raise ValueError('manifest family missing '+family)
            values = pattern.groups(); expected = bytes.fromhex(values[-1])
            native_table = int(values[2] if owner == 11 else values[1],16)
            if int(values[0],16) != render or native_table != vtable or pe_rva(raw,render,len(expected)) != expected: raise ValueError('manifest vtable/signature differs '+family)
        families.append(dict(family=family,owner=owner,vtable_rva=hex(vtable),render_rva=hex(render),render_virtual_slot=38,ini_parser_rva=hex(parser),ini_parser_virtual_slot=61,ini_name_instructions=references,render_prefix_sha256=hashlib.sha256(pe_rva(raw,render,32)).hexdigest()))
    # Dragon [multi_new] can use the MonsterMulti implementation; both are hooked.
    if struct.unpack('<Q',pe_rva(raw,0x5aa270+38*8,8))[0] != base+0x32f8d0: raise ValueError('MonsterMulti alternate path differs')
    rows = list(csv.DictReader((ROOT/'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig')))
    header = (ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/sprite_family_owners.h').read_text()
    canonical = sorted((int(r['animation_id'],16),KNOWN[r['engine_section']][0]) for r in rows if r['engine_section'] in KNOWN)
    declared = [(int(i,16),int(o)) for i,o in re.findall(r'\{(0x[0-9a-f]+), (\d+)\}',header)]
    if declared != canonical: raise ValueError('engine integration owner table differs from inventory')
    return dict(schema='bg2-q3m-native-families-analysis-v1',executable_sha256=EXE_SHA256,image_base=hex(base),family_count=15,animation_ids=len(canonical),families=families,alternate_multi_new=dict(native_class='MonsterMulti',vtable_rva='0x5aa270',render_rva='0x32f8d0'),proof='native vtable slots + INI parser LEA + exact additional-hook manifest signatures; no game launched',ingame_validated=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args();report=analyze()
    if args.output:
        if args.output.exists(): raise ValueError('choose a new immutable analysis destination')
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(families=report['family_count'],animation_ids=report['animation_ids'],passed=True)))
