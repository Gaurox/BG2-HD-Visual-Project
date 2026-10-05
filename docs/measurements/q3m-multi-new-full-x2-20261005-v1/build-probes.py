"""Build only verification executables, linked to the acquired runtime core."""
import json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
old=ROOT/'sprite/.work/q3m-monster-quadrant-full-x2-20261004-v1'
work=WORK/'probe-src';work.mkdir(parents=True,exist_ok=True)
source=(old/'runtime-src/tests/palette_partner_tests.cpp').read_text()
assert 'nr<=256' in source;source=source.replace('nr<=256','nr<=8192')
(HERE/'palette_probe.cpp').write_text(source,encoding='utf-8')
source=(HERE.parent/'q3m-monster-quadrant-full-x2-20261004-v1/composite_probe.cpp').read_text()
source=source.replace('manifest->get().areaAnimations.monsterQuadrantRender==0x3305a0','manifest->get().areaAnimations.multiNewRender==0x32fd20 && manifest->get().areaAnimations.monsterMultiRender==0x32f8d0')
source=source.replace('native Quadrant hook differs','native owner-5 hooks differ').replace('count==4','(count==4 || count==9)').replace('native four quadrants','native four/nine parts').replace('metadata[0]),4','metadata[0]),5')
helper='''
// Native MonsterMulti submits nine independent cells; it never uses the
// eight-layer Character/equipment compositor. Assemble its actual cell decodes.
bool ordered_native_cells(const cs::CompositeLayer* layers,std::size_t count,
                          std::vector<std::uint32_t>& pixels,cs::CompositeBounds& bounds){
  std::vector<std::vector<std::uint32_t>> cells(count);
  std::vector<cs::CompositeBounds> boxes(count);
  for(std::size_t i=0;i<count;++i){
    if(!cs::reconstruct_composite_pixels(layers+i,1,cells[i],boxes[i]))return false;
    if(i==0)bounds=boxes[i];else{
      bounds.left=std::min(bounds.left,boxes[i].left);bounds.top=std::min(bounds.top,boxes[i].top);
      bounds.right=std::max(bounds.right,boxes[i].right);bounds.bottom=std::max(bounds.bottom,boxes[i].bottom);
    }
  }
  const auto width=bounds.logical_width()*2,height=bounds.logical_height()*2;
  pixels.assign(std::size_t(width)*height,0);
  for(std::size_t i=0;i<count;++i){
    const auto w=boxes[i].logical_width()*2,h=boxes[i].logical_height()*2;
    const auto x=(boxes[i].left-bounds.left)*2,y=(boxes[i].top-bounds.top)*2;
    for(int cy=0;cy<h;++cy)for(int cx=0;cx<w;++cx){
      const auto pixel=cells[i][std::size_t(cy)*w+cx];
      if(pixel)pixels[std::size_t(y+cy)*width+x+cx]=pixel;
    }
  }
  return true;
}
'''
source=source.replace('int main(int argc,char** argv)',helper+'\nint main(int argc,char** argv)')
source=source.replace('cs::reconstruct_composite_pixels(layers.data(),layers.size(),pixels,bounds)','ordered_native_cells(layers.data(),layers.size(),pixels,bounds)')
(HERE/'composite_probe.cpp').write_text(source,encoding='utf-8')
tree=ET.parse(old/'runtime-build/iee_palette_partner_tests.vcxproj');ns={'m':'http://schemas.microsoft.com/developer/msbuild/2003'}
includes=next(e.find('m:ClCompile/m:AdditionalIncludeDirectories',ns).text for e in tree.findall('m:ItemDefinitionGroup',ns) if "'Release|x64'" in e.get('Condition','')).split(';')[:-1]
libs=[old/'runtime-build/Release/iee_common.lib',old/'runtime-build/_deps/spdlog-build/Release/spdlog.lib',old/'runtime-build/_deps/zlib-build/Release/zs.lib']
quote=lambda p:'"'+str(p).replace('\\','/')+'"'
cmake='cmake_minimum_required(VERSION 3.20)\nproject(MultiNewProbes LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 20)\nset(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)\n'
for name in ('palette','composite'):
    cmake+=f'add_executable({name}_probe {quote(HERE/(name+"_probe.cpp"))} {quote(old/"runtime-src/src/iee/creature_sprite_x2.cpp")} {quote(old/"runtime-src/src/iee/game/opengl_types.cpp")})\n'
    cmake+=f'target_compile_definitions({name}_probe PRIVATE NOMINMAX SPDLOG_COMPILED_LIB)\n'
    cmake+=f'target_compile_options({name}_probe PRIVATE /utf-8)\n'
    cmake+=f'target_include_directories({name}_probe PRIVATE '+ ' '.join(map(quote,includes))+')\n'
    cmake+=f'target_link_libraries({name}_probe PRIVATE '+' '.join(map(quote,libs))+' opengl32 Cabinet bcrypt version psapi)\n'
(work/'CMakeLists.txt').write_text(cmake,encoding='utf-8')
subprocess.run(['cmake','-S',str(work),'-B',str(WORK/'probe-build'),'-G','Visual Studio 16 2019','-A','x64'],check=True)
subprocess.run(['cmake','--build',str(WORK/'probe-build'),'--config','Release','--parallel','2'],check=True)
write_json(HERE/'probe-build.json',dict(role='test-only-no-runtime-rebuild',acquired_common=dict(path=libs[0].relative_to(ROOT).as_posix(),sha256=file_sha(libs[0])),executables=[dict(path=(WORK/'probe-build/Release'/(name+'_probe.exe')).relative_to(ROOT).as_posix(),sha256=file_sha(WORK/'probe-build/Release'/(name+'_probe.exe'))) for name in ('palette','composite')]))
