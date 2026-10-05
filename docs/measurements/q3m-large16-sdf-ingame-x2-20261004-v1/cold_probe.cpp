#include <array>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <iostream>
#include "iee/creature_sprite_x2.h"
namespace iee::probe {void record_creature_texture_trace(unsigned,int,int,int,int,int,std::string_view) noexcept {}}
namespace cs=iee::creature_sprite_x2;
#include "cold-cases.h"
int main(int argc,char** argv) {
  if(argc!=2 || !cs::prepare(std::filesystem::path(argv[1]))) return 1;
  unsigned hits=0,ankheg=0; double maximum=0;
  for(const auto& item:cases) {
      unsigned aid=item.aid;std::string name=item.name;
      std::array<char,8> ref{};std::memcpy(ref.data(),name.data(),name.size());cs::FrameHandle frame{};
      const auto start=std::chrono::steady_clock::now();
      bool ok=cs::resolve_frame(static_cast<std::uint16_t>(aid),ref,item.sequence,item.slot,frame,
        aid==0x3000u?cs::FrameResolveMode::WaitForAnkhegMetadata:cs::FrameResolveMode::WaitForLarge16Metadata);
      double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();maximum=(std::max)(maximum,ms);
      std::cout<<"LOOKUP id="<<std::hex<<aid<<std::dec<<" resref="<<name<<" cold_HD="<<ok<<" wait_ms="<<ms<<"\n";
      if(!ok){cs::release();return 2;}
      if(aid==0x3000u)++ankheg;else ++hits;
  }
  cs::release();std::cout<<"{\"passed\":true,\"Large16_cold_HD\":"<<hits<<",\"Ankheg_cold_HD\":"<<ankheg<<",\"cold_misses\":0,\"max_wait_ms\":"<<maximum<<"}\n";
  return hits==18 && ankheg==6 ? 0 : 3;
}
