"""Only representative new colours; source-native drivers, no helper installed."""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from workspace_paths import get_path
OUT = ROOT / 'projectiles/analysis/residual-four-20261110-v1'


def main():
    assert not (OUT / 'visual-tests.json').exists()
    bifs, entries = load_key()
    key = {(n.upper(),t):loc for n,t,loc in entries}
    game = get_path('bg2ee_game_root', required=True)
    tests = []
    for code, spell, kind, ident, expected_opcodes, target in [
        ('R4-01','SPPR207',26,138,{122,174,141,61},'Myself'),
        ('R4-02','SPWM110',32,142,{170,141},'NearestEnemyOf(Myself)')]:
        over = game / 'override' / (spell+'.spl')
        raw = over.read_bytes() if over.exists() else resolve_resource(bifs,key[spell,1006])[0]
        offset = struct.unpack_from('<I',raw,0x6a)[0]
        effects = [dict(offset=hex(p),opcode=struct.unpack_from('<H',raw,p)[0],target=raw[p+2],
            parameter1=struct.unpack_from('<I',raw,p+4)[0],parameter2=struct.unpack_from('<I',raw,p+8)[0],
            timing=raw[p+12],duration=struct.unpack_from('<I',raw,p+14)[0],
            resource=raw[p+20:p+28].split(b'\0')[0].decode('ascii')) for p in range(offset,len(raw)-47,48)]
        assert {e['opcode'] for e in effects} == expected_opcodes
        assert any(e['opcode']==141 and e['parameter2']==kind for e in effects)
        assert not any(e['opcode'] in {12,13,55,68,124,151,168} for e in effects)
        tests.append(dict(id=code,spell=spell,projectl_id=ident,opcode141_type=kind,
            source_sha256=hashlib.sha256(raw).hexdigest().upper(),effects=effects,
            command=f'C:Eval(\'ForceSpellRES("{spell}",{target})\',0)',
            inspect='New native colour, obvious clipping/opaque rectangle only; no replay of old assets.',
            status='prepared-not-observed'))
    (OUT / 'visual-tests.json').write_text(json.dumps(dict(manual_tests=tests,manual_test_count=2,
        policy='One representative per new palette family, not each alias or every colour. All native knots/BMP variants/normal+additive cache paths tested automatically.',
        automated_instead_of_manual=['FLMSTRK unchanged image/native cycles/centres','SPDIMDR1/2 native update and2->1->2 identity switch; both packs qualified',
            'All7 SHWATER palettes on214 used native indices','All3 SPBOOM range0 colours on12 used indices'],
        new_helpers_installed=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Two native colour drivers source-checked, no damage/teleport/removal/summoning opcodes; no helper installed.')


if __name__=='__main__':
    main()
