#include <filesystem>
#include <iostream>
#include <string_view>

#include "iee/core/map_page_shadow.h"

namespace {
std::string_view status_name(iee::core::PvrzPrepareStatus status) noexcept {
  using iee::core::PvrzPrepareStatus;
  switch (status) {
    case PvrzPrepareStatus::Ready:
      return "ready";
    case PvrzPrepareStatus::Missing:
      return "missing";
    case PvrzPrepareStatus::IoError:
      return "io-error";
    case PvrzPrepareStatus::CompressedLimit:
      return "compressed-limit";
    case PvrzPrepareStatus::InvalidEnvelope:
      return "invalid-envelope";
    case PvrzPrepareStatus::InflateError:
      return "inflate-error";
    case PvrzPrepareStatus::InvalidPvr:
      return "invalid-pvr";
  }
  return "unknown";
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: iee_map_page_shadow_preflight <page.PVRZ>\n";
    return 2;
  }
  const auto result = iee::core::prepare_pvrz_file(std::filesystem::path(argv[1]));
  std::cout << "status=" << status_name(result.status)
            << " compressedBytes=" << result.compressedBytes
            << " decodedBytes=" << result.decodedBytes << " width=" << result.width
            << " height=" << result.height << " pixelFormat=" << result.pixelFormat
            << " prepareMs=" << static_cast<double>(result.prepareNanoseconds) / 1'000'000.0
            << '\n';
  return result.status == iee::core::PvrzPrepareStatus::Ready ? 0 : 1;
}
