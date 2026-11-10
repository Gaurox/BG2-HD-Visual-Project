#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <stdexcept>
#include <vector>

namespace iee::core {
// Exact registry binding avoids any ambiguity between logical frame orders.
// Header: IEEFXS1\0, version/count/registryBytes/reserved (u32 LE), registry, IDs.
inline std::vector<std::uint32_t> effect_storage_index(
    std::span<const std::byte> bytes, std::span<const std::byte> registry,
    std::span<const std::uint64_t> sizes) {
  constexpr std::array<unsigned char,8> magic{'I','E','E','F','X','S','1',0};
  if(bytes.size()<24) throw std::runtime_error("truncated effect storage index");
  for(std::size_t i=0;i<8;++i) if(std::to_integer<unsigned char>(bytes[i])!=magic[i])
    throw std::runtime_error("invalid effect storage magic");
  const auto word=[&](std::size_t off) {
    std::uint32_t value=0;
    for(unsigned i=0;i<4;++i) value|=std::uint32_t(std::to_integer<unsigned char>(bytes[off+i]))<<(8*i);
    return value;
  };
  if(word(8)!=1 || word(12)!=sizes.size() || word(16)!=registry.size() || word(20)!=0 ||
     bytes.size()!=24ull+registry.size()+4ull*sizes.size() ||
     !std::equal(registry.begin(),registry.end(),bytes.begin()+24))
    throw std::runtime_error("effect storage registry binding differs");
  std::vector<std::uint32_t> result(sizes.size());
  for(std::size_t i=0;i<result.size();++i) {
    result[i]=word(24+registry.size()+4*i);
    if(result[i]>=sizes.size() || sizes[result[i]]!=sizes[i])
      throw std::runtime_error("effect storage source out of range or size differs");
  }
  for(auto id:result) if(result[id]!=id)
    throw std::runtime_error("effect storage source is not canonical");
  return result;
}
}
