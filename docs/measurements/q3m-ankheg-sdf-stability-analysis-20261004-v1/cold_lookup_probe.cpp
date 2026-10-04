#include <array>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <thread>
#include "iee/creature_sprite_x2.h"

namespace iee::probe {
void record_creature_texture_trace(unsigned,int,int,int,int,int,std::string_view) noexcept {}
}
namespace cs=iee::creature_sprite_x2;
int main(int argc,char** argv) {
  if(argc!=2 || !cs::prepare(std::filesystem::path(argv[1]))) return 1;
  const char* names[]={"MAKHDG1","MAKHDG1E","MAKHDG2","MAKHDG2E","MAKHDG3","MAKHDG3E",
                       "MAKHG1","MAKHG1E","MAKHG2","MAKHG2E","MAKHG3","MAKHG3E"};
  unsigned coldMisses=0,warmHits=0;
  for(const auto* name:names) {
    std::array<char,8> ref{};std::memcpy(ref.data(),name,std::strlen(name));cs::FrameHandle h{};
    const auto start=std::chrono::steady_clock::now();
    // Explicitly request existing Character wait: owner=9 still disallows it.
    const bool cold=cs::resolve_frame(0x3000,ref,0,0,h,cs::FrameResolveMode::WaitForCharacterMetadata);
    coldMisses+=!cold;
    bool warm=cold;
    while(!warm && std::chrono::steady_clock::now()-start<std::chrono::seconds(5)) {
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
      warm=cs::resolve_frame(0x3000,ref,0,0,h,cs::FrameResolveMode::NonBlocking);
    }
    if(!warm) {cs::release();return 2;}
    ++warmHits;
    std::cout<<"LOOKUP resref="<<name<<" cold="<<cold<<" warm="<<warm<<" ready_ms="
      <<std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()<<"\n";
  }
  cs::release();
  std::cout<<"{\"cold_misses\":"<<coldMisses<<",\"warm_hits\":"<<warmHits
    <<",\"requested_wait_mode\":\"WaitForCharacterMetadata\",\"native_owner\":9}\n";
  return coldMisses==12 && warmHits==12 ? 0 : 3;
}
