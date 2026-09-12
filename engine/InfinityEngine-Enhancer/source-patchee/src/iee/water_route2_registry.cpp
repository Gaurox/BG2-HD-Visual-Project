#include "water_route2_registry.h"

#include <windows.h>
#include <bcrypt.h>

#include <algorithm>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <system_error>
#include <vector>

#include "iee/core/logger.h"
#include "iee/water_route2_registry.generated.h"

namespace iee::water_route2 {
namespace {
struct ValidatedRegistry {
  std::vector<const RegistryEntry*> entries;
};

std::atomic<std::shared_ptr<const ValidatedRegistry>> g_registry;

bool file_sha256(const std::filesystem::path& path, Sha256& digest) noexcept {
  BCRYPT_ALG_HANDLE algorithm = nullptr;
  BCRYPT_HASH_HANDLE hash = nullptr;
  try {
    if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0)
      return false;
    DWORD objectBytes = 0;
    DWORD copied = 0;
    DWORD digestBytes = 0;
    if (BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH,
                          reinterpret_cast<PUCHAR>(&objectBytes), sizeof(objectBytes),
                          &copied, 0) < 0 ||
        BCryptGetProperty(algorithm, BCRYPT_HASH_LENGTH,
                          reinterpret_cast<PUCHAR>(&digestBytes), sizeof(digestBytes),
                          &copied, 0) < 0 || digestBytes != digest.size()) {
      BCryptCloseAlgorithmProvider(algorithm, 0);
      return false;
    }
    std::vector<UCHAR> object(objectBytes);
    if (BCryptCreateHash(algorithm, &hash, object.data(), objectBytes, nullptr, 0, 0) < 0) {
      BCryptCloseAlgorithmProvider(algorithm, 0);
      return false;
    }
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error("open");
    std::vector<char> buffer(1024 * 1024);
    while (stream) {
      stream.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
      const auto count = stream.gcount();
      if (count > 0 && BCryptHashData(
              hash, reinterpret_cast<PUCHAR>(buffer.data()),
              static_cast<ULONG>(count), 0) < 0) throw std::runtime_error("hash");
    }
    if (!stream.eof() || BCryptFinishHash(
            hash, reinterpret_cast<PUCHAR>(digest.data()),
            static_cast<ULONG>(digest.size()), 0) < 0) throw std::runtime_error("finish");
    BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(algorithm, 0);
    return true;
  } catch (...) {
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
    return false;
  }
}

std::filesystem::path evidence_path(const std::filesystem::path& root,
                                    const RegistryFileEvidence& evidence) {
  const auto extension = evidence.kind == RegistryFileKind::BaseTis ||
                                 evidence.kind == RegistryFileKind::OverlayTis
                             ? ".TIS" : ".PVRZ";
  return root / (std::string(resref_view(evidence.resref)) + extension);
}

bool validate_file(const std::filesystem::path& root,
                   const RegistryFileEvidence& evidence) noexcept {
  try {
    const auto path = evidence_path(root, evidence);
    std::error_code error;
    const auto bytes = std::filesystem::file_size(path, error);
    if (error || bytes != evidence.bytes) return false;
    Sha256 digest{};
    return file_sha256(path, digest) && digest == evidence.sha256;
  } catch (...) {
    return false;
  }
}

bool validate_entry(const std::filesystem::path& root,
                    const RegistryEntry& entry) noexcept {
  if (entry.slotCount < 2 || entry.slotCount > entry.slots.size() ||
      entry.overlaySlot == 0 || entry.overlaySlot >= entry.slotCount ||
      entry.fileStart > generated::kFiles.size() ||
      entry.fileCount > generated::kFiles.size() - entry.fileStart ||
      !(entry.approvedStrength >= 0.0f && entry.approvedStrength <= 1.0f)) return false;
  const bool hasTemporal = entry.temporalFrameCount != 0 || entry.temporalSourceFps != 0.0f ||
                           entry.temporalTargetFps != 0.0f ||
                           entry.temporalAtlasColumns != 0 ||
                           entry.temporalAtlasStridePixels != 0 ||
                           entry.temporalAtlasPaddingPixels != 0;
  if (hasTemporal &&
      (entry.temporalFrameCount != entry.overlayTileCount ||
       entry.temporalFrameCount < 2 || entry.temporalSourceFps <= 0.0f ||
       entry.temporalTargetFps < entry.temporalSourceFps ||
       entry.temporalAtlasColumns == 0 ||
       entry.temporalAtlasStridePixels <= entry.temporalAtlasPaddingPixels * 2 ||
       entry.temporalAtlasStridePixels - entry.temporalAtlasPaddingPixels * 2 !=
           entry.tileDimension)) return false;
  const auto wedOverride = root / (std::string(resref_view(entry.wed)) + ".WED");
  std::error_code error;
  const bool hasWedOverride = std::filesystem::is_regular_file(wedOverride, error);
  const bool wedOverrideAbsent = error == std::errc::no_such_file_or_directory;
  if ((error && !wedOverrideAbsent) ||
      (!hasWedOverride && !entry.allowStockWedWhenOverrideAbsent)) return false;
  if (hasWedOverride) {
    Sha256 digest{};
    if (!file_sha256(wedOverride, digest) || digest != entry.wedSha256) return false;
  }
  bool overlayPagePresent = false;
  for (std::uint32_t index = 0; index < entry.fileCount; ++index) {
    const auto& evidence = generated::kFiles[entry.fileStart + index];
    if (!validate_file(root, evidence)) return false;
    overlayPagePresent |= evidence.kind == RegistryFileKind::OverlayPvrz;
  }
  return overlayPagePresent;
}

bool page_matches(const Query& query, const RegistryEntry& entry) noexcept {
  unsigned matches = 0;
  for (std::uint32_t index = 0; index < entry.fileCount; ++index) {
    const auto& evidence = generated::kFiles[entry.fileStart + index];
    if (evidence.kind == RegistryFileKind::OverlayPvrz &&
        query.page == resref_view(evidence.resref) &&
        query.pageWidth == evidence.width && query.pageHeight == evidence.height) ++matches;
  }
  return matches == 1;
}
}  // namespace

bool prepare(const std::filesystem::path& overrideRoot) noexcept {
  try {
    auto validated = std::make_shared<ValidatedRegistry>();
    for (const auto& entry : generated::kEntries) {
      if (validate_entry(overrideRoot, entry)) {
        validated->entries.push_back(&entry);
      } else {
        LOG_WARN("WATER_ROUTE2 registry rejected wed={} overlay={} slot={}",
                 resref_view(entry.wed), resref_view(entry.overlayTis), entry.overlaySlot);
      }
    }
    g_registry.store(validated, std::memory_order_release);
    LOG_INFO("WATER_ROUTE2 registry version={} validated={}/{}",
             generated::kRegistryVersion, validated->entries.size(), generated::kEntries.size());
    return !validated->entries.empty();
  } catch (...) {
    release();
    return false;
  }
}

std::optional<Match> match(const Query& query) noexcept {
  const auto registry = g_registry.load(std::memory_order_acquire);
  if (!registry) return std::nullopt;
  const RegistryEntry* matched = nullptr;
  for (const auto* entry : registry->entries) {
    if (!identity_matches(query, *entry) || !page_matches(query, *entry)) continue;
    if (matched) return std::nullopt;
    matched = entry;
  }
  if (!matched) return std::nullopt;
  return Match{matched->approvedStrength,
               matched->materialId,
               generated::kRegistryVersion,
               matched->temporalFrameCount,
               matched->temporalSourceFps,
               matched->temporalTargetFps,
               matched->temporalAtlasColumns,
               matched->temporalAtlasStridePixels,
               matched->temporalAtlasPaddingPixels};
}

std::uint32_t version() noexcept { return generated::kRegistryVersion; }

void release() noexcept { g_registry.store({}, std::memory_order_release); }
}  // namespace iee::water_route2
