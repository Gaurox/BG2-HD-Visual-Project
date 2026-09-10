#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>

#include "iee/core/config.h"

namespace iee::creature_sprite_filter {

inline constexpr std::size_t kTextureRegistryCapacity = 512;

enum class TextureProvenance : std::uint8_t {
  Frame,
  CharacterComposite,
  Masked,
};

enum class Sampler : std::uint8_t {
  Unknown,
  Nearest,
  Linear,
};

struct TextureMetadata {
  std::uint64_t contextGeneration{};
  unsigned glName{};
  int physicalWidth{};
  int physicalHeight{};
  std::uint8_t scale{};
  std::uint64_t contentGeneration{};
  TextureProvenance provenance{TextureProvenance::Frame};
  Sampler expectedSampler{Sampler::Unknown};
  bool masked{};
};

struct DrawObservation {
  std::uintptr_t contextIdentity{};
  unsigned glName{};
  int physicalWidth{};
  int physicalHeight{};
  Sampler sampler{Sampler::Unknown};
  bool routingProgram{};
  bool uniformsAvailable{};
};

struct DrawDecision {
  bool owner{};
  bool filterActive{};
  float mode{};
  float texelWidth{};
  float texelHeight{};
  TextureProvenance provenance{TextureProvenance::Frame};
  std::uint64_t contentGeneration{};
};

struct RegistryState {
  std::uintptr_t contextIdentity{};
  std::uint64_t contextGeneration{};
  std::size_t size{};
  std::size_t capacity{};
  bool capacityExceeded{};
};

// Fixed-capacity render-thread registry. It performs no allocation, I/O or
// locking and is independent from the creature catalog mutex.
class TextureRegistry {
 public:
  explicit TextureRegistry(
      std::size_t capacity = kTextureRegistryCapacity) noexcept;

  void configure(core::CreatureSpriteFilterMode mode) noexcept;
  [[nodiscard]] core::CreatureSpriteFilterMode configured_mode() const noexcept;

  // A different native context starts a fresh monotonic context generation
  // and invalidates every prior GL name.
  [[nodiscard]] std::uint64_t observe_context(
      std::uintptr_t contextIdentity) noexcept;
  void clear() noexcept;

  [[nodiscard]] bool publish(std::uintptr_t contextIdentity, unsigned glName,
                             int physicalWidth, int physicalHeight, int scale,
                             TextureProvenance provenance, bool masked) noexcept;
  [[nodiscard]] bool transfer_masked(std::uintptr_t contextIdentity,
                                     unsigned parentGlName,
                                     unsigned outputGlName) noexcept;
  void forget(std::uintptr_t contextIdentity, unsigned glName) noexcept;
  void forget_many(std::uintptr_t contextIdentity, int count,
                   const unsigned* glNames) noexcept;

  [[nodiscard]] std::optional<TextureMetadata> find(
      std::uintptr_t contextIdentity, unsigned glName) const noexcept;
  [[nodiscard]] DrawDecision decide(const DrawObservation& observation) const noexcept;
  [[nodiscard]] RegistryState state() const noexcept;

 private:
  struct Slot {
    TextureMetadata metadata{};
    bool occupied{};
  };

  [[nodiscard]] std::size_t find_index(unsigned glName) const noexcept;
  [[nodiscard]] Sampler expected_sampler(bool masked) const noexcept;

  std::array<Slot, kTextureRegistryCapacity> slots_{};
  std::uintptr_t contextIdentity_{};
  std::uint64_t contextGeneration_{};
  std::uint64_t nextContentGeneration_{};
  std::size_t size_{};
  std::size_t capacity_{kTextureRegistryCapacity};
  core::CreatureSpriteFilterMode mode_{core::CreatureSpriteFilterMode::Nearest};
  bool capacityExceeded_{};
};

TextureRegistry& registry() noexcept;

[[nodiscard]] bool is_routing_fragment(std::string_view name) noexcept;
[[nodiscard]] Sampler sampler_from_gl(int minFilter, int magFilter) noexcept;

}  // namespace iee::creature_sprite_filter
