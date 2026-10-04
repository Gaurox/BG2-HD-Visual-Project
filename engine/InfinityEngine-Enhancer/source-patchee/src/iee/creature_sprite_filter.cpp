#include "iee/creature_sprite_filter.h"
#include "iee/core/sprite_minification.h"

#include <algorithm>
#include <limits>

namespace iee::creature_sprite_filter {
namespace {
constexpr int kGlNearest = 0x2600;
constexpr int kGlLinear = 0x2601;
constexpr int kGlLinearMipmapLinear = 0x2703;

std::uint64_t next_generation(std::uint64_t current) noexcept {
  return current == (std::numeric_limits<std::uint64_t>::max)() ? 1 : current + 1;
}
}  // namespace

TextureRegistry::TextureRegistry(std::size_t capacity) noexcept
    : capacity_((std::min)(capacity, slots_.size())) {}

void TextureRegistry::configure(core::CreatureSpriteFilterMode mode,
                                std::uint16_t animationId) noexcept {
  if (mode_ != mode || animationId_ != animationId) {
    for (auto& slot : slots_) slot = {};
    size_ = 0;
    capacityExceeded_ = false;
  }
  mode_ = mode;
  animationId_ = animationId;
}

core::CreatureSpriteFilterMode TextureRegistry::effective_mode(
    std::uint16_t animationId, int scale) const noexcept {
  if ((animationId_ != 0 && animationId_ != animationId) ||
      (mode_ == core::CreatureSpriteFilterMode::Box && scale != 2 && scale != 4) ||
      (mode_ == core::CreatureSpriteFilterMode::Mipmaps && scale != 4))
    return core::CreatureSpriteFilterMode::Nearest;
  return mode_;
}

core::CreatureSpriteFilterMode TextureRegistry::configured_mode() const noexcept {
  return mode_;
}

std::uint64_t TextureRegistry::observe_context(
    std::uintptr_t contextIdentity) noexcept {
  if (contextIdentity == contextIdentity_) return contextGeneration_;
  for (auto& slot : slots_) slot = {};
  contextIdentity_ = contextIdentity;
  contextGeneration_ = next_generation(contextGeneration_);
  size_ = 0;
  capacityExceeded_ = false;
  return contextGeneration_;
}

void TextureRegistry::clear() noexcept {
  for (auto& slot : slots_) slot = {};
  contextIdentity_ = 0;
  contextGeneration_ = next_generation(contextGeneration_);
  size_ = 0;
  capacityExceeded_ = false;
}

std::size_t TextureRegistry::find_index(unsigned glName) const noexcept {
  if (glName == 0) return slots_.size();
  for (std::size_t index = 0; index < capacity_; ++index) {
    if (slots_[index].occupied && slots_[index].metadata.glName == glName) {
      return index;
    }
  }
  return slots_.size();
}

Sampler TextureRegistry::expected_sampler(core::CreatureSpriteFilterMode mode,
                                          bool masked) const noexcept {
  if (mode == core::CreatureSpriteFilterMode::Mipmaps) return Sampler::TrilinearNearestMag;
  if (masked) {
    return (mode == core::CreatureSpriteFilterMode::CatmullRom ||
            mode == core::CreatureSpriteFilterMode::Box)
               ? Sampler::Nearest
               : Sampler::Linear;
  }
  return mode == core::CreatureSpriteFilterMode::Linear ? Sampler::Linear
                                                          : Sampler::Nearest;
}

bool TextureRegistry::publish(std::uintptr_t contextIdentity, unsigned glName,
                              int physicalWidth, int physicalHeight, int scale,
                              TextureProvenance provenance, bool masked,
                              std::uint16_t animationId, int maximumMipLevel,
                              bool premultiplied, std::uint8_t sdfEncoded) noexcept {
  const auto mode = effective_mode(animationId, scale);
  if (sdfEncoded > 2 || (sdfEncoded && (mode != core::CreatureSpriteFilterMode::CatmullRom || masked || scale != 2))) return false;
  const bool mips = mode == core::CreatureSpriteFilterMode::Mipmaps;
  if (contextIdentity == 0 || glName == 0 || physicalWidth <= 0 ||
      physicalHeight <= 0 || (scale != 2 && scale != 4) ||
      physicalWidth % scale != 0 || physicalHeight % scale != 0 ||
      maximumMipLevel < 0 || (mips != premultiplied) ||
      (mips ? maximumMipLevel == 0 || maximumMipLevel !=
                  core::sprite_minification::mip_layout(physicalWidth, physicalHeight).maximumLevel
            : maximumMipLevel != 0)) {
    return false;
  }
  (void)observe_context(contextIdentity);
  auto index = find_index(glName);
  if (index == slots_.size()) {
    if (size_ >= capacity_) {
      capacityExceeded_ = true;
      return false;
    }
    for (std::size_t candidate = 0; candidate < capacity_; ++candidate) {
      if (!slots_[candidate].occupied) {
        index = candidate;
        break;
      }
    }
  }
  if (index == slots_.size()) {
    capacityExceeded_ = true;
    return false;
  }
  const bool wasOccupied = slots_[index].occupied;
  nextContentGeneration_ = next_generation(nextContentGeneration_);
  slots_[index] = {
      .metadata =
          {
              .contextGeneration = contextGeneration_,
              .glName = glName,
              .physicalWidth = physicalWidth,
              .physicalHeight = physicalHeight,
              .scale = static_cast<std::uint8_t>(scale),
              .contentGeneration = nextContentGeneration_,
              .provenance = provenance,
              .expectedSampler = expected_sampler(mode, masked),
              .masked = masked,
              .filterMode = mode,
              .animationId = animationId,
              .maximumMipLevel = maximumMipLevel,
              .premultiplied = premultiplied,
              .sdfEncoded = sdfEncoded,
          },
      .occupied = true,
  };
  if (!wasOccupied) ++size_;
  return true;
}

bool TextureRegistry::transfer_masked(std::uintptr_t contextIdentity,
                                      unsigned parentGlName,
                                      unsigned outputGlName, int maximumMipLevel) noexcept {
  const auto parent = find(contextIdentity, parentGlName);
  if (!parent || outputGlName == 0 || outputGlName == parentGlName) return false;
  return publish(contextIdentity, outputGlName, parent->physicalWidth,
                 parent->physicalHeight, parent->scale,
                 TextureProvenance::Masked, true, parent->animationId,
                 maximumMipLevel, parent->premultiplied);
}

void TextureRegistry::forget(std::uintptr_t contextIdentity,
                             unsigned glName) noexcept {
  if (contextIdentity == 0 || contextIdentity != contextIdentity_ || glName == 0) return;
  const auto index = find_index(glName);
  if (index == slots_.size()) return;
  slots_[index] = {};
  if (size_ > 0) --size_;
}

void TextureRegistry::forget_many(std::uintptr_t contextIdentity, int count,
                                  const unsigned* glNames) noexcept {
  if (count <= 0 || !glNames) return;
  for (int index = 0; index < count; ++index) {
    forget(contextIdentity, glNames[index]);
  }
}

std::optional<TextureMetadata> TextureRegistry::find(
    std::uintptr_t contextIdentity, unsigned glName) const noexcept {
  if (contextIdentity == 0 || contextIdentity != contextIdentity_) return std::nullopt;
  const auto index = find_index(glName);
  if (index == slots_.size()) return std::nullopt;
  return slots_[index].metadata;
}

DrawDecision TextureRegistry::decide(
    const DrawObservation& observation) const noexcept {
  DrawDecision decision{};
  if (!observation.routingProgram || !observation.uniformsAvailable ||
      observation.physicalWidth <= 0 || observation.physicalHeight <= 0) {
    return decision;
  }
  const auto metadata = find(observation.contextIdentity, observation.glName);
  if (!metadata || metadata->physicalWidth != observation.physicalWidth ||
      metadata->physicalHeight != observation.physicalHeight ||
      metadata->expectedSampler != observation.sampler ||
      metadata->maximumMipLevel != observation.maximumMipLevel ||
      ((metadata->filterMode == core::CreatureSpriteFilterMode::Box ||
        metadata->filterMode == core::CreatureSpriteFilterMode::Mipmaps) &&
       !observation.minificationContract)) {
    return decision;
  }
  decision.owner = true;
  decision.filterActive = metadata->filterMode == core::CreatureSpriteFilterMode::CatmullRom ||
                          metadata->filterMode == core::CreatureSpriteFilterMode::Box ||
                          metadata->filterMode == core::CreatureSpriteFilterMode::Mipmaps;
  decision.mode = static_cast<float>(static_cast<std::uint8_t>(metadata->filterMode));
  decision.texelWidth = 1.0f / static_cast<float>(metadata->physicalWidth);
  decision.texelHeight = 1.0f / static_cast<float>(metadata->physicalHeight);
  decision.scale = metadata->scale;
  decision.provenance = metadata->provenance;
  decision.contentGeneration = metadata->contentGeneration;
  return decision;
}

RegistryState TextureRegistry::state() const noexcept {
  return {
      .contextIdentity = contextIdentity_,
      .contextGeneration = contextGeneration_,
      .size = size_,
      .capacity = capacity_,
      .capacityExceeded = capacityExceeded_,
  };
}

TextureRegistry& registry() noexcept {
  static TextureRegistry instance;
  return instance;
}

bool is_routing_fragment(std::string_view name) noexcept {
  return name == "fpDraw" || name == "fpSprite" || name == "fpSELECT";
}

Sampler sampler_from_gl(int minFilter, int magFilter) noexcept {
  if (minFilter == kGlNearest && magFilter == kGlNearest) return Sampler::Nearest;
  if (minFilter == kGlLinear && magFilter == kGlLinear) return Sampler::Linear;
  if (minFilter == kGlLinearMipmapLinear && magFilter == kGlNearest)
    return Sampler::TrilinearNearestMag;
  return Sampler::Unknown;
}

}  // namespace iee::creature_sprite_filter
