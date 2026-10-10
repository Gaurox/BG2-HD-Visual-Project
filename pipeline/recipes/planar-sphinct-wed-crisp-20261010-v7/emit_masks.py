from pathlib import Path
import sys,numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
OUT=ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v7';RUN=ROOT/'animations/ressources/SPHINCT/runs/planar-sphinct-wed-crisp-20261010-v7'
checks=v2.load_json(OUT/'checks.json');selected=sorted([c for c in checks['occurrences'] if c['area']=='AR0516'],key=lambda c:tuple(c['position']))
text=['#pragma once\n#include "iee/core/native_occlusion_probe.h"\n#include <array>\n#include <vector>\n#include <string_view>\n#include <stdexcept>\nnamespace iee::core {\n']
for i,c in enumerate(selected):
 mask=np.array(Image.open(RUN/c['mask'])).ravel();breaks=np.r_[0,np.flatnonzero(mask[1:]!=mask[:-1])+1,len(mask)]
 runs=[(int(b-a)<<8)|int(mask[a]) for a,b in zip(breaks[:-1],breaks[1:])]
 assert np.array_equal(np.concatenate([np.full(v>>8,v&255,np.uint8) for v in runs]),mask)
 text.append(f'// {c["area"]} @ {c["position"]}; mask SHA256 {c["mask_sha256"]}\ninline constexpr std::array<std::uint32_t,{len(runs)}> kPlanarMask{i} = {{\n')
 for j in range(0,len(runs),12):text.append(','.join(str(v)+'u' for v in runs[j:j+12])+',\n')
 text.append('};\n')
text.append('inline int planar_sphinct_mask_index(const NativeOcclusionSample& s,std::string_view area,int w,int h) noexcept {\n if(area!="AR0516" || w!=160 || h!=120 || s.owner!=NativeOcclusionOwner::AreaAnimation || s.draw.replacement!=NativeOcclusionReplacement::AreaRegistry || s.subjectId!=0x0054434E49485053ull || s.lastClippingCall.dither!=0 || s.successfulClippingCallCount==0) return -1;\n')
for i,c in enumerate(selected):text.append(f' if(s.lastClippingCall.x=={c["position"][0]} && s.lastClippingCall.y=={c["position"][1]}) return {i};\n')
text.append(' return -1;\n}\ninline std::vector<std::uint8_t> decode_planar_mask(int index) {\n std::vector<std::uint8_t> result;result.reserve(640*480*4);\n const auto append=[&](const auto& runs){for(auto packed:runs){const auto count=packed>>8;const auto value=static_cast<std::uint8_t>(packed&255);if(result.size()+count*4ull>640*480*4ull) throw std::runtime_error("planar mask overflow");for(std::uint32_t j=0;j<count;++j){result.push_back(value);result.push_back(0);result.push_back(0);result.push_back(255);}}};\n switch(index){case 0:append(kPlanarMask0);break;case 1:append(kPlanarMask1);break;case 2:append(kPlanarMask2);break;default:return {};}\n if(result.size()!=640*480*4) throw std::runtime_error("planar mask size");return result;\n}\n} // namespace iee::core\n')
target=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/planar_sphinct_world_masks.h';assert not target.exists();target.write_text(''.join(text),encoding='utf-8')
v2.write_json(OUT/'embedded-masks.json',dict(passed=True,source_masks=selected,RLE_roundtrip_exact=True,header_sha256=v2.sha256_file(target)))
print('Embedded 3 exact coverage masks; RLE roundtrip passed')
