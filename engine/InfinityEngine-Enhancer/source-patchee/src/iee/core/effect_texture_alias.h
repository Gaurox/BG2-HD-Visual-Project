#pragma once
#include <array>

namespace iee::core {
// Existing compatible cloud packs retain geometry/timelines/RGB and restore
// native palette alpha. Native cells, BAMs and PROs stay unchanged. Backing
// numbers may differ after alpha deduplication; slot/phase semantics must match.
// Resolve this same identity at prefetch, selection and final draw boundaries.
[[nodiscard]] constexpr std::array<char,8> effect_texture_resref(
    const std::array<char,8>& native, bool normalProfile=false) noexcept {
  // WRITHING also has accepted Blended consumers. Its existing native-alpha
  // straight companion is selected only for normal native FX draws.
  if(normalProfile && native==std::array<char,8>{'W','R','I','T','H','I','N','G'})
    return {'X','2','8','W','R','T','H','\0'};
  if(normalProfile && native==std::array<char,8>{'B','D','W','O','F','O','G','A'})
    return {'X','5','8','W','F','O','G','\0'};
  constexpr std::array<char,8> cloud{'S','P','C','L','O','U','D','K'};
  constexpr std::array<char,8> alphaCloud{'X','5','8','C','L','K','\0','\0'};
  if(native==std::array<char,8>{'S','P','C','L','O','U','D','S'})
    return {'X','5','8','C','L','S','\0','\0'};
  if(native==std::array<char,8>{'S','P','D','F','O','G','A','\0'})
    return {'X','5','8','D','F','O','G','\0'};
  return native == cloud ? alphaCloud : native;
}
}
