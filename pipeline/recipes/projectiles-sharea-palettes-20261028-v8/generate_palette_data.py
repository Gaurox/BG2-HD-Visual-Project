"""Read native SHAREA/BMP palettes; emit only C++ constants, never image output."""
from pathlib import Path
import hashlib,struct,zlib,sys,json
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bg2lib import load_key,resolve_resource
bifs,entries=load_key();key={(n.upper(),t):v for n,t,v in entries}
raw=(ROOT/'effects/ressources/SHAREA/source.bam').read_bytes();b=zlib.decompress(raw[12:]);po=struct.unpack_from('<I',b,16)[0]
def rgb(data):return [int.from_bytes(data[i:i+3],'little') for i in range(0,1024,4)]
source=rgb(b[po:po+1024]);assert len(set(source[1:]))==255 and source[1]==0
base=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
def arr(values):return ',\n'.join('  '+','.join('0x%08xu'%x for x in values[i:i+8]) for i in range(0,len(values),8))
(base/'src/iee/core/effect_sharea_source_palette.h').write_text('#pragma once\n#include <array>\n#include <cstdint>\nnamespace iee::core::effect_indexed_palette {\n// Native SHAREA BGRA palette. Source BAM SHA256 '+hashlib.sha256(raw).hexdigest().upper()+'\ninline constexpr std::array<std::uint32_t,256> source{\n'+arr(source)+'\n};\n}\n',encoding='utf-8')
palettes=[source];proof={'SHAREA.bam':hashlib.sha256(raw).hexdigest().upper()}
for n in ['SHAREA1','SHAREA2','SHAREA3','SHAREA4','SHAREA5','SHAREA6']:
 data=resolve_resource(bifs,key[n,1])[0];assert data[:2]==b'BM' and struct.unpack_from('<H',data,28)[0]==8
 palettes.append(rgb(data[54:1078]));proof[n+'.bmp']=hashlib.sha256(data).hexdigest().upper()
(base/'tests/effect_sharea_palette_fixtures.h').write_text('#pragma once\n#include "iee/core/area_animation_lighting.h"\n// Native KEY/BIF fixtures from generate_palette_data.py; default then BMP1..6.\ninline constexpr std::array<iee::core::area_lighting::Palette,7> shareaPalettes{{\n'+',\n'.join(' {\n'+arr([v|0xff000000 for v in p])+'\n }' for p in palettes)+'\n}};\n',encoding='utf-8')
(Path(__file__).parent/'source-palettes.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
