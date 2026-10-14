#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace iee::core {

// Render-thread-only diagnostic. No allocation, I/O, GL readback or scheduler
// changes. One row per real swap, rather than one row per draw call. Published
// only after the targeted effect has disappeared, outside its timed capture.
struct EffectPresentationSample {
  std::uint64_t epoch{};
  std::int64_t swapTicks{}, drawTicks{};
  int nativeSlot{-1}, phase{-1}, backing{-1};
  int width{}, height{}, texture{-1}, worldActive{-1};
  std::uint16_t draws{};
  bool ownerSeen{}, hd{}, masked{}, conflictingDraws{}, swapOk{};
};

struct EffectPresentationCapture {
  static constexpr std::size_t kRows = 2048;
  std::uintptr_t instance{};
  std::uint64_t id{}, generation{};
  int sequence{-1}, lastNativeSlot{-1};
  std::int64_t frequency{}, lastSeenTicks{};
  bool complete{}, published{}, overflow{};
  std::size_t rowCount{};
  EffectPresentationSample pending{};
  std::array<EffectPresentationSample, kRows> rows{};
};

class EffectPresentationTrace {
 public:
  static constexpr std::size_t kCaptures = 8;

  void owner(std::uintptr_t instance, std::uint64_t generation, int sequence,
             int nativeSlot, std::uint64_t epoch) noexcept {
    ownerEpoch_ = epoch;
    auto* c = find(instance, generation, sequence);
    if (c && ((nativeSlot >= 0 && c->lastNativeSlot > nativeSlot) ||
              (c->complete && !c->overflow))) {
      c->complete = true;  // reused instance or a fresh native sequence
      c = nullptr;
    }
    if (!c) {
      if (count_ == captures_.size()) { ++droppedOwners_; return; }
      c = &captures_[count_++];
      c->instance = instance; c->generation = generation;
      c->sequence = sequence; c->id = count_;
    }
    if (c->complete) return;
    c->lastNativeSlot = nativeSlot;
    if (c->pending.epoch != epoch) c->pending = {};
    c->pending.epoch = epoch; c->pending.ownerSeen = true;
    c->pending.nativeSlot = nativeSlot;
  }

  void draw(std::uintptr_t instance, std::uint64_t generation, int sequence,
            std::uint64_t epoch, int nativeSlot, int phase, int backing, int width, int height,
            int texture, bool hd, bool masked, std::int64_t ticks) noexcept {
    auto* c = find(instance, generation, sequence);
    if (!c || c->complete || !c->pending.ownerSeen || c->pending.epoch != epoch) return;
    auto& p = c->pending;
    if (p.draws && (p.phase != phase || p.backing != backing || p.hd != hd)) {
      p.conflictingDraws = true;
    }
    if (p.draws != 65535) ++p.draws;
    if (nativeSlot >= 0) p.nativeSlot = nativeSlot;
    p.phase = phase; p.backing = backing; p.width = width; p.height = height;
    p.texture = texture; p.hd = hd; p.masked = masked; p.drawTicks = ticks;
  }

  void swap(std::uint64_t epoch, std::int64_t ticks, std::int64_t frequency,
            int worldActive, bool success) noexcept {
    if (!count_ || frequency <= 0) return;
    if (ownerEpoch_ == epoch) lastAnyOwnerTicks_ = ticks;
    for (std::size_t i = 0; i < count_; ++i) {
      auto& c = captures_[i];
      if (c.complete) continue;
      auto p = c.pending;
      if (p.epoch != epoch) p = {};
      p.epoch = epoch; p.swapTicks = ticks; p.swapOk = success; p.worldActive = worldActive;
      c.frequency = frequency;
      if (p.ownerSeen) c.lastSeenTicks = ticks;
      if (c.rowCount == c.rows.size()) { c.overflow = true; c.complete = true; continue; }
      c.rows[c.rowCount++] = p;
      c.pending = {};
      // Do not declare an occurrence finished merely because its render is
      // suspended while the console/game is paused.
      if (!p.ownerSeen && worldActive > 0 && c.lastSeenTicks &&
          ticks - c.lastSeenTicks >= frequency / 4) c.complete = true;
    }
  }

  [[nodiscard]] bool ready_to_publish(std::int64_t ticks, std::int64_t frequency) const noexcept {
    if (!count_ || frequency <= 0 || ticks - lastAnyOwnerTicks_ < frequency / 4) return false;
    for (std::size_t i = 0; i < count_; ++i) if (!captures_[i].complete) return false;
    return true;
  }
  [[nodiscard]] std::size_t count() const noexcept { return count_; }
  [[nodiscard]] std::uint64_t dropped_owners() const noexcept { return droppedOwners_; }
  EffectPresentationCapture& capture(std::size_t i) noexcept { return captures_[i]; }

 private:
  EffectPresentationCapture* find(std::uintptr_t instance, std::uint64_t generation,
                                   int sequence) noexcept {
    // Search newest first: an engine object address can be reused for a cast.
    for (std::size_t i = count_; i > 0; --i) {
      auto& c = captures_[i - 1];
      if (c.instance == instance && c.generation == generation && c.sequence == sequence) return &c;
    }
    return nullptr;
  }
  std::array<EffectPresentationCapture, kCaptures> captures_{};
  std::size_t count_{};
  std::uint64_t ownerEpoch_{~std::uint64_t{0}}, droppedOwners_{};
  std::int64_t lastAnyOwnerTicks_{};
};
}  // namespace iee::core
