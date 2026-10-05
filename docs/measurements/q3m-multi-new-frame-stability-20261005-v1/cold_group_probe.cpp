#include <array>
#include <chrono>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include "iee/creature_sprite_x2.h"
namespace iee::probe {
void record_creature_texture_trace(unsigned,int,int,int,int,int,std::string_view) noexcept {}
}
namespace cs = iee::creature_sprite_x2;
struct Group {unsigned id; std::vector<std::array<char,8>> refs;};
int main(int argc, char** argv) {
  if (argc != 4) return 1;
  const bool baseline = std::string(argv[3]) == "baseline";
  std::ifstream input(argv[2]); std::string line;
  std::vector<Group> groups;
  while (std::getline(input,line)) {
    std::istringstream row(line); Group group{}; row >> std::hex >> group.id;
    std::string name;
    while (row >> name) {
      if (name.size()>8) return 2;
      std::array<char,8> ref{}; std::memcpy(ref.data(),name.data(),name.size());
      group.refs.push_back(ref);
    }
    if (group.refs.size() != (group.id == 0x1300 ? 4 : 9)) return 3;
    groups.push_back(group);
  }
  if (groups.empty() || !cs::prepare(std::filesystem::path(argv[1]))) return 4;
  unsigned misses=0, resources=0, warmMisses=0, guardFailures=0;
  double maxGroupMs=0;
  for (const auto& group:groups) {
    auto start=std::chrono::steady_clock::now();
    for (const auto& ref:group.refs) if (!cs::contains_resource(group.id,ref)) return 5;
    bool selected=true;
    for (const auto& ref:group.refs) {
      cs::FrameHandle handle{};
      bool ok=cs::resolve_frame(group.id,ref,0,0,handle,
        baseline ? cs::FrameResolveMode::NonBlocking : cs::FrameResolveMode::WaitForMultiNewMetadata);
      selected &= ok;
      if (!ok && baseline)
        ok=cs::resolve_frame(group.id,ref,0,0,handle,cs::FrameResolveMode::WaitForMultiNewMetadata);
      if (!ok || !cs::ensure_frame_payload_available(handle)) {
        std::cerr<<"FAILED id="<<std::hex<<group.id<<" ref="<<std::string(ref.data(),8)<<"\n";
        cs::release(); return 6;
      }
      ++resources;
      cs::FrameHandle warm{};
      warmMisses += !cs::resolve_frame(group.id,ref,0,0,warm,cs::FrameResolveMode::WaitForMultiNewMetadata);
      cs::FrameHandle invalid{};
      guardFailures += cs::resolve_frame(group.id,ref,0,100000,invalid,cs::FrameResolveMode::WaitForMultiNewMetadata);
    }
    misses += !selected;
    auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
    if (ms>maxGroupMs) maxGroupMs=ms;
  }
  std::array<char,8> absent{'N','O','S','U','C','H'};cs::FrameHandle invalid{};
  guardFailures += cs::resolve_frame(0x1207,absent,0,0,invalid,cs::FrameResolveMode::WaitForMultiNewMetadata);
  guardFailures += cs::resolve_frame(0x1300,absent,0,0,invalid,cs::FrameResolveMode::WaitForMultiNewMetadata);
  // This owner-5 wait mode must not change other families' cold lookup contract.
  std::array<char,8> ankheg{'M','A','K','H','G','1'};
  guardFailures += cs::resolve_frame(0x3000,ankheg,0,0,invalid,cs::FrameResolveMode::WaitForMultiNewMetadata);
  cs::release();
  std::cout<<"{\"mode\":\""<<(baseline?"baseline-nonblocking":"fixed-owner5-wait")
    <<"\",\"groups\":"<<groups.size()<<",\"resources\":"<<resources
    <<",\"cold_native_fallback_groups\":"<<misses<<",\"warm_misses\":"<<warmMisses
    <<",\"guard_failures\":"<<guardFailures<<",\"max_group_ms\":"<<maxGroupMs<<"}\n";
  return warmMisses || guardFailures || (!baseline && misses) || (baseline && !misses) ? 7 : 0;
}
