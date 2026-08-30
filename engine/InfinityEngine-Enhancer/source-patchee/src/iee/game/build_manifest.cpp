#include "build_manifest.h"

#ifdef _WIN64
#include <windows.h>

#include <array>
#include <cwchar>
#include <limits>
#include <vector>
#endif

namespace iee::game {
namespace {
constexpr bool is_hex_char(char c) noexcept {
  return (c >= '0' && c <= '9') || (c >= 'A' && c <= 'F') || (c >= 'a' && c <= 'f');
}

constexpr bool is_wildcard_token(std::string_view token) noexcept {
  return token == "?" || token == "??";
}

constexpr bool is_hex_token(std::string_view token) noexcept {
  return token.size() == 2 && is_hex_char(token[0]) && is_hex_char(token[1]);
}

constexpr bool validate_pattern_format(std::string_view pattern) noexcept {
  if (pattern.empty()) {
    return false;
  }

  std::size_t tokenStart = 0;
  bool sawToken = false;
  while (tokenStart < pattern.size()) {
    while (tokenStart < pattern.size() && pattern[tokenStart] == ' ') {
      ++tokenStart;
    }
    if (tokenStart >= pattern.size()) {
      break;
    }

    std::size_t tokenEnd = tokenStart;
    while (tokenEnd < pattern.size() && pattern[tokenEnd] != ' ') {
      ++tokenEnd;
    }

    const auto token = pattern.substr(tokenStart, tokenEnd - tokenStart);
    if (!is_hex_token(token) && !is_wildcard_token(token)) {
      return false;
    }

    sawToken = true;
    tokenStart = tokenEnd;
  }

  return sawToken;
}

std::string normalize_product_name(std::string_view productName) {
  std::string normalized;
  normalized.reserve(productName.size());
  for (const unsigned char ch : productName) {
    if (ch >= 'A' && ch <= 'Z') {
      normalized.push_back(static_cast<char>(ch - 'A' + 'a'));
    } else if ((ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9')) {
      normalized.push_back(static_cast<char>(ch));
    }
  }
  return normalized;
}

#ifdef _WIN64
std::string wide_to_utf8(std::wstring_view value) {
  if (value.empty() || value.size() > static_cast<std::size_t>((std::numeric_limits<int>::max)())) {
    return {};
  }
  const auto inputLength = static_cast<int>(value.size());
  const int outputLength =
      WideCharToMultiByte(CP_UTF8, 0, value.data(), inputLength, nullptr, 0, nullptr, nullptr);
  if (outputLength <= 0) return {};
  std::string output(static_cast<std::size_t>(outputLength), '\0');
  if (WideCharToMultiByte(CP_UTF8, 0, value.data(), inputLength, output.data(), outputLength,
                          nullptr, nullptr) != outputLength) {
    return {};
  }
  return output;
}

std::string read_product_name(const std::vector<std::byte>& versionData) {
  struct LanguageAndCodePage {
    WORD language;
    WORD codePage;
  };

  LanguageAndCodePage* translations = nullptr;
  UINT translationBytes = 0;
  std::array<LanguageAndCodePage, 3> fallbacks{{
      {0x0409, 0x04B0},
      {0x0409, 0x04E4},
      {0x0000, 0x04B0},
  }};
  const LanguageAndCodePage* candidates = fallbacks.data();
  std::size_t candidateCount = fallbacks.size();
  if (VerQueryValueW(versionData.data(), L"\\VarFileInfo\\Translation",
                     reinterpret_cast<void**>(&translations), &translationBytes) &&
      translations && translationBytes >= sizeof(LanguageAndCodePage)) {
    candidates = translations;
    candidateCount = translationBytes / sizeof(LanguageAndCodePage);
  }

  const auto readField = [&](const wchar_t* fieldName) -> std::string {
    for (std::size_t index = 0; index < candidateCount; ++index) {
      wchar_t query[96]{};
      if (swprintf_s(query, sizeof(query) / sizeof(query[0]),
                     L"\\StringFileInfo\\%04x%04x\\%ls",
                     static_cast<unsigned>(candidates[index].language),
                     static_cast<unsigned>(candidates[index].codePage), fieldName) <= 0) {
        continue;
      }
      wchar_t* value = nullptr;
      UINT valueChars = 0;
      if (!VerQueryValueW(versionData.data(), query, reinterpret_cast<void**>(&value),
                          &valueChars) ||
          !value || valueChars <= 1) {
        continue;
      }
      std::size_t length = valueChars;
      if (value[length - 1] == L'\0') --length;
      if (auto utf8 = wide_to_utf8(std::wstring_view(value, length)); !utf8.empty()) return utf8;
    }
    return {};
  };

  if (auto productName = readField(L"ProductName"); !productName.empty()) return productName;
  return readField(L"FileDescription");
}
#endif

constexpr BuildManifest kKnownBuilds[] = {
    {
        "BGEE 2.6.6.x",
        {"Baldur's Gate Enhanced Edition", "Baldur's Gate"},
        {2, 6, 6, ExecutableVersion::kAnyRevision},
        {
            "40 55 53 56 57 41 54 41 55 41 56 41 57 48 8D AC 24 48 FD FF FF",
            "48 8B C4 44 89 48 20 48 83 EC 48 48 89 58 08 8B DA 48 89 68 10",
        },
        {0x27E710, 0x4247E0},
        {0x100, 0x1DC, 0x14, 0x6590, 0x6598, 0x65F8},
        {},
        {},
        {{
            {"CRes_Demand", 0x36, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawBindTexture", 0x6E, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawDisable", 0x7F, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawColor", 0x89, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawPushState", 0x91, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawColorTone", 0xB6, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawBegin", 0xC0, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawTexCoord", 0xCD, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawVertex", 0xDB, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawEnd", 0x17A, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawPopState", 0x1AD, BranchInstructionKind::JmpRel32, 0xE9, 1, 5, true},
        }},
    },
    // Offline-validated 2026-07-16 (docs/validation/bgee-2.7.3-evidence.md):
    // both signatures match exactly once, all 10 callsites decode at the same
    // intra-function offsets, and CVidTile::pRes is read at RenderTexture+0x1D
    // as on 2.6.6. Only the function RVAs moved.
    {
        "BGEE 2.7.3.x",
        {"Baldur's Gate Enhanced Edition", "Baldur's Gate"},
        {2, 7, 3, ExecutableVersion::kAnyRevision},
        {
            "40 55 53 56 57 41 54 41 55 41 56 41 57 48 8D AC 24 48 FD FF FF",
            "48 8B C4 44 89 48 20 48 83 EC 48 48 89 58 08 8B DA 48 89 68 10",
        },
        {0x27EBD0, 0x4257C0},
        {0x100, 0x1DC, 0x14, 0x6590, 0x6598, 0x65F8},
        {},
        {},
        {{
            {"CRes_Demand", 0x36, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawBindTexture", 0x6E, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawDisable", 0x7F, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawColor", 0x89, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawPushState", 0x91, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawColorTone", 0xB6, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawBegin", 0xC0, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawTexCoord", 0xCD, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawVertex", 0xDB, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawEnd", 0x17A, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawPopState", 0x1AD, BranchInstructionKind::JmpRel32, 0xE9, 1, 5, true},
        }},
        {0x3F6DC0,
         "48 89 5C 24 10 48 89 74 24 18 48 89 7C 24 20 41 56 48 83 EC 30 83 79 58 00",
         {0xDC,
          0x402A00,
          0x15F,
          0x4000F0,
          "40 53 48 83 EC 20 8B 02 48 8B DA 48 8D 54 24 38 89 44 24 38 E8 ? ? ? ? "
          "8B 4C 24 38 89 0B 48 83 C4 20 5B C3",
          0x164,
           "8B 4F 30 48 8D 57 34 44 8B 47 08 48 03 D1 44 8B 4C 24 40 44 89 43 5C "
           "44 2B CA 8B 4F 1C 44 03 CF 89 4B 64 8B 47 18 89 43 68 8B 4F 1C 48 89 "
           "54 24 20 8B 57 18 E8 ? ? ? ? 48 8B CF E8 ? ? ? ?"},
          {0x19,
           0x721B70,
           128,
           0x3F70B0,
           "48 89 5C 24 08 57 48 83 EC 20 33 FF 48 8D 15 ? ? ? ? 48 8B D9 39 79 58 "
           "0F 84 ? ? ? ?",
           0x0C,
           0xE2,
           0x408430,
           "40 53 55 56 57 41 54 41 56 41 57 48 81 EC 80 02 00 00 48 8B 05 ? ? ? ? "
           "48 33 C4 48 89 84 24 70 02 00 00"}},
    },
    // Offline-validated 2026-08-13 (docs/validation/bg2ee-2.7.3-evidence.md):
    // BG2EE 2.7.3.0 ships the same unified engine image as BGEE 2.7.3 (the game
    // is selected at runtime by engine.lua's engine_mode). Both signatures match
    // exactly once at the *same* RVAs as BGEE 2.7.3, all 10 callsites decode at
    // the same intra-function offsets to the same targets, CVidTile::pRes is
    // read at RenderTexture+0x1D, and the .text disp32 census is identical.
    // Only the version-resource product name differs, hence a separate entry.
    {
        "BG2EE 2.7.3.x",
        {"Baldur's Gate II: Enhanced Edition", "Baldur's Gate II"},
        {2, 7, 3, ExecutableVersion::kAnyRevision},
        {
            "40 55 53 56 57 41 54 41 55 41 56 41 57 48 8D AC 24 48 FD FF FF",
            "48 8B C4 44 89 48 20 48 83 EC 48 48 89 58 08 8B DA 48 89 68 10",
        },
        {0x27EBD0, 0x4257C0},
        {0x100, 0x1DC, 0x14, 0x6590, 0x6598, 0x65F8},
        {
            true,
            0x1F2B50,
            0x425790,
            0x413270,
            0x413350,
            0x413390,
            0x4135E0,
            0x2F73F6C,
            0x757040,
            {{0x42BBEC, 0x42D074, 0x42B037}},
            0x42B90F,
            0x72A1B0,
            0x421430,
            0x4242C1,
            0x2F7401C,
            0x2F74020,
            0x1C0,
            0x1C8,
            0x1CA,
            0x32D770,
            0x32E360,
            0x08,
            0xCD8,
            0x32C240,
            0xD00,
            {{0x1360, 0x1888, 0x1DB0}},
            0x08,
            0x110,
            0x118,
            0x11A,
            {{
                "40 55 53 41 55 41 56 48 8D 6C 24",
                "48 83 EC 48 8B 44 24 78",
                "83 3D 39 77 31 00 01",
                "83 3D 59 76 31 00 01",
                "8B 05 1A 76 31 00 C3",
                "83 3D C9 73 31 00 01",
                "40 55 56 41 54 41 55 41 56 41 57 48 8D 6C 24 F9 48 81 EC D8 00 00 00",
                "44 0F B7 51 20 45 85 D2 74 0B 41 83 FA 01 75 0A E9 ? ? ? ? E9 ? ? ? ? C3",
                "4C 8D 35 E8 5E 30 00 44 8B C5 49 8B D6 E8 5D D1 FF FF",
                "40 55 56 57 41 54 41 55 41 56 41 57 48 8D 6C 24 F9 48 81 EC B0 00 00 00",
                "48 8D 1D 75 B4 32 00",
                "48 8D 0D C5 9F 32 00",
                "48 8D 05 0F C0 32 00",
                "4C 8B FF 83 7F 24 00 0F 84 01 01 00 00 B9 C0 84 00 00",
                "40 55 56 41 54 41 55 41 56 48 8D 6C 24 F9 48 81 EC E0 00 00 00 48 8B 05 4C 72 33 00",
            }},
            0x0C,
            0x10,
            0x14,
            0x29E4C0,
            "40 57 41 55 48 81 EC 18 01 00 00 48 8B 05 ? ? ? ? 48 33 C4",
            0x2F74050,
            0x42CB1B,
            "48 8D 05 ? ? ? ? 48 03 D8 44 8B 43 28 41 C1 E0 15",
        },
        {
            true,
            0x189360,
            "40 55 41 56 41 57 48 8D 6C 24 B9 48 81 EC 90 00 00 00 48 8B 05 5F B6 4D 00",
            0x42B350,
            "4C 8B DC 55 41 56 41 57 49 8D 6B D8 48 81 EC 10 01 00 00 48 8B 05 6E 96",
        },
        {{
            {"CRes_Demand", 0x36, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawBindTexture", 0x6E, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawDisable", 0x7F, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawColor", 0x89, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawPushState", 0x91, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawColorTone", 0xB6, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawBegin", 0xC0, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawTexCoord", 0xCD, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawVertex", 0xDB, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawEnd", 0x17A, BranchInstructionKind::CallRel32, 0xE8, 1, 5, true},
            {"DrawPopState", 0x1AD, BranchInstructionKind::JmpRel32, 0xE9, 1, 5, true},
        }},
        {0x3F6DC0,
         "48 89 5C 24 10 48 89 74 24 18 48 89 7C 24 20 41 56 48 83 EC 30 83 79 58 00",
         {0xDC,
          0x402A00,
          0x15F,
          0x4000F0,
          "40 53 48 83 EC 20 8B 02 48 8B DA 48 8D 54 24 38 89 44 24 38 E8 ? ? ? ? "
          "8B 4C 24 38 89 0B 48 83 C4 20 5B C3",
          0x164,
           "8B 4F 30 48 8D 57 34 44 8B 47 08 48 03 D1 44 8B 4C 24 40 44 89 43 5C "
           "44 2B CA 8B 4F 1C 44 03 CF 89 4B 64 8B 47 18 89 43 68 8B 4F 1C 48 89 "
           "54 24 20 8B 57 18 E8 ? ? ? ? 48 8B CF E8 ? ? ? ?"},
          {0x19,
           0x721B70,
           128,
           0x3F70B0,
           "48 89 5C 24 08 57 48 83 EC 20 33 FF 48 8D 15 ? ? ? ? 48 8B D9 39 79 58 "
           "0F 84 ? ? ? ?",
           0x0C,
           0xE2,
           0x408430,
           "40 53 55 56 57 41 54 41 56 41 57 48 81 EC 80 02 00 00 48 8B 05 ? ? ? ? "
           "48 33 C4 48 89 84 24 70 02 00 00"}},
    },
};

static_assert(validate_pattern_format(kKnownBuilds[0].patterns.loadArea),
              "LoadArea pattern format is invalid");
static_assert(validate_pattern_format(kKnownBuilds[0].patterns.renderTexture),
              "RenderTexture pattern format is invalid");
static_assert(kKnownBuilds[0].validate(), "Known build manifest is invalid");
static_assert(validate_pattern_format(kKnownBuilds[1].patterns.loadArea),
              "2.7.3 LoadArea pattern format is invalid");
static_assert(validate_pattern_format(kKnownBuilds[1].patterns.renderTexture),
              "2.7.3 RenderTexture pattern format is invalid");
static_assert(validate_pattern_format(kKnownBuilds[1].pvrDemand.signature),
              "2.7.3 CResPVR::Demand pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[1].pvrDemand.decodeBoundary.uncompressSignature),
              "2.7.3 PVR uncompress pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[1].pvrDemand.decodeBoundary.consumeWindowSignature),
              "2.7.3 PVR consume-window pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[1].pvrDemand.lifecycleBoundary.cacheReleaseSignature),
              "2.7.3 PVR cache-release pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[1].pvrDemand.lifecycleBoundary.resourceFileOpenSignature),
              "2.7.3 CRes file-open pattern format is invalid");
static_assert(kKnownBuilds[1].validate(), "2.7.3 build manifest is invalid");
static_assert(validate_pattern_format(kKnownBuilds[2].patterns.loadArea),
              "BG2EE 2.7.3 LoadArea pattern format is invalid");
static_assert(validate_pattern_format(kKnownBuilds[2].patterns.renderTexture),
              "BG2EE 2.7.3 RenderTexture pattern format is invalid");
static_assert(validate_pattern_format(kKnownBuilds[2].pvrDemand.signature),
              "BG2EE 2.7.3 CResPVR::Demand pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[2].pvrDemand.decodeBoundary.uncompressSignature),
              "BG2EE 2.7.3 PVR uncompress pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[2].pvrDemand.decodeBoundary.consumeWindowSignature),
              "BG2EE 2.7.3 PVR consume-window pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[2].pvrDemand.lifecycleBoundary.cacheReleaseSignature),
              "BG2EE 2.7.3 PVR cache-release pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[2].pvrDemand.lifecycleBoundary.resourceFileOpenSignature),
              "BG2EE 2.7.3 CRes file-open pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[2].areaAnimations.infinityFxRenderClippingPolysSignature),
              "BG2EE 2.7.3 FXRenderClippingPolys pattern format is invalid");
static_assert(validate_pattern_format(
                  kKnownBuilds[2].areaAnimations.fxSurfacePoolReferenceSignature),
              "BG2EE 2.7.3 FX surface-pool reference pattern format is invalid");
static_assert([] {
  for (const auto signature : kKnownBuilds[2].areaAnimations.signatures) {
    if (!validate_pattern_format(signature)) return false;
  }
  return true;
}(), "BG2EE 2.7.3 area-animation signature format is invalid");
static_assert(
    validate_pattern_format(kKnownBuilds[2].worldOverlay.gameAreaRenderSignature),
    "BG2EE 2.7.3 CGameArea::Render signature format is invalid");
static_assert(validate_pattern_format(kKnownBuilds[2].worldOverlay.drawFlushGlSignature),
              "BG2EE 2.7.3 DrawFlush_GL signature format is invalid");
static_assert(kKnownBuilds[2].validate(), "BG2EE 2.7.3 build manifest is invalid");
}  // namespace

const BuildManifest& current_manifest() noexcept { return kKnownBuilds[0]; }

std::optional<std::reference_wrapper<const BuildManifest>> find_manifest(
    std::string_view buildId) noexcept {
  for (const auto& manifest : kKnownBuilds) {
    if (manifest.buildId == buildId) {
      return manifest;
    }
  }
  return std::nullopt;
}

std::optional<std::reference_wrapper<const BuildManifest>> find_manifest_for_version(
    std::uint16_t major, std::uint16_t minor, std::uint16_t patch,
    std::uint16_t revision) noexcept {
  for (const auto& manifest : kKnownBuilds) {
    if (manifest.executableVersion.matches(major, minor, patch, revision)) {
      return manifest;
    }
  }
  return std::nullopt;
}

std::optional<std::reference_wrapper<const BuildManifest>> find_manifest_for_identity(
    std::uint16_t major, std::uint16_t minor, std::uint16_t patch, std::uint16_t revision,
    std::string_view productName) {
  for (const auto& manifest : kKnownBuilds) {
    if (manifest.executableVersion.matches(major, minor, patch, revision) &&
        supports_product_name(manifest, productName)) {
      return manifest;
    }
  }
  return std::nullopt;
}

bool supports_product_name(const BuildManifest& manifest, std::string_view productName) {
  const auto normalizedCandidate = normalize_product_name(productName);
  if (normalizedCandidate.empty()) return false;
  for (const auto expected : manifest.supportedProductNames) {
    if (!expected.empty() && normalize_product_name(expected) == normalizedCandidate) return true;
  }
  return false;
}

const BuildManifest* detect_manifest(ExecutableVersion* detectedVersion,
                                     std::string* detectedProductName) noexcept {
  if (detectedVersion) *detectedVersion = {};
  if (detectedProductName) detectedProductName->clear();
#ifdef _WIN64
  try {
    wchar_t executablePath[MAX_PATH]{};
    const auto pathLength = GetModuleFileNameW(nullptr, executablePath, MAX_PATH);
    if (pathLength == 0 || pathLength >= MAX_PATH) {
      return nullptr;
    }

    DWORD ignored = 0;
    const auto versionBytes = GetFileVersionInfoSizeW(executablePath, &ignored);
    if (versionBytes == 0) {
      return nullptr;
    }

    std::vector<std::byte> versionData(versionBytes);
    if (!GetFileVersionInfoW(executablePath, 0, versionBytes, versionData.data())) {
      return nullptr;
    }

    VS_FIXEDFILEINFO* fixedInfo = nullptr;
    UINT fixedInfoBytes = 0;
    if (!VerQueryValueW(versionData.data(), L"\\", reinterpret_cast<void**>(&fixedInfo),
                        &fixedInfoBytes) ||
        !fixedInfo || fixedInfoBytes < sizeof(VS_FIXEDFILEINFO) ||
        fixedInfo->dwSignature != 0xFEEF04BD) {
      return nullptr;
    }

    const auto major = static_cast<std::uint16_t>(HIWORD(fixedInfo->dwFileVersionMS));
    const auto minor = static_cast<std::uint16_t>(LOWORD(fixedInfo->dwFileVersionMS));
    const auto patch = static_cast<std::uint16_t>(HIWORD(fixedInfo->dwFileVersionLS));
    const auto revision = static_cast<std::uint16_t>(LOWORD(fixedInfo->dwFileVersionLS));
    if (detectedVersion) *detectedVersion = {major, minor, patch, revision};
    const auto productName = read_product_name(versionData);
    if (detectedProductName) *detectedProductName = productName;
    // Several games share a fixed file version because they ship the same
    // unified engine image, so the product name is part of the identity: select
    // the manifest that matches both, not merely the first version match.
    if (const auto manifest =
            find_manifest_for_identity(major, minor, patch, revision, productName)) {
      return &manifest->get();
    }
    return nullptr;
  } catch (...) {
    return nullptr;
  }
#else
  (void)detectedVersion;
  return nullptr;
#endif
}
}  // namespace iee::game
