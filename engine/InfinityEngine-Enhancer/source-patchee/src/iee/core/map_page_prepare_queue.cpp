#include "map_page_prepare_queue.h"

#include <algorithm>
#include <utility>

namespace iee::core {
MapPagePrepareQueue::Claim::Claim(MapPagePrepareQueue* owner, std::size_t slot,
                                std::uint64_t generation) noexcept
    : owner_(owner), slot_(slot), generation_(generation) {}
MapPagePrepareQueue::Claim::Claim(Claim&& other) noexcept
    : owner_(std::exchange(other.owner_, nullptr)), slot_(other.slot_),
      generation_(other.generation_) {}
MapPagePrepareQueue::Claim& MapPagePrepareQueue::Claim::operator=(Claim&& other) noexcept {
  if (this != &other) {
    release();
    owner_ = std::exchange(other.owner_, nullptr);
    slot_ = other.slot_;
    generation_ = other.generation_;
  }
  return *this;
}
MapPagePrepareQueue::Claim::~Claim() { release(); }
void MapPagePrepareQueue::Claim::release() noexcept {
  if (owner_) {
    owner_->slots_[slot_].state.store(State::Retired, std::memory_order_release);
    owner_ = nullptr;
  }
}
const PvrzPreparedPage* MapPagePrepareQueue::Claim::page() const noexcept {
  return owner_ ? &owner_->slots_[slot_].page : nullptr;
}
bool MapPagePrepareQueue::Claim::current() const noexcept {
  return owner_ && owner_->generation() == generation_;
}

bool MapPagePrepareQueue::configure(std::vector<PrivatePageEntry> entries,
                                  std::size_t budget) {
  if (entries.empty() || entries.size() > slots_.size() || budget > kPrepareBudgetBytes)
    return false;
  for (std::size_t i = 0; i < entries.size(); ++i) {
    const auto& e = entries[i];
    if (e.resref.empty() || e.resref.size() > 8 || e.path.empty() ||
        e.compressedBytes < 6 || e.compressedBytes > kShadowMaximumCompressedBytes ||
        e.decodedBytes < 52 || e.decodedBytes > kShadowMaximumDecodedBytes ||
        std::size_t{e.compressedBytes} + e.decodedBytes + kPrepareScratchBytes > budget)
      return false;
    for (std::size_t j = 0; j < i; ++j)
      if (entries[j].resref == e.resref) return false;
  }
  for (auto& s : slots_) {
    s.page = {};
    s.entry = {};
    s.state.store(State::Empty);
    s.retiredThrough.store(0);
    s.generation = 0;
    s.reservation = 0;
  }
  count_ = entries.size();
  budget_ = budget;
  for (std::size_t i = 0; i < count_; ++i) slots_[i].entry = std::move(entries[i]);
  epoch_.store(0);
  reserved_.store(0); peak_.store(0);
  hits_.store(0); misses_.store(0); prepared_.store(0); failures_.store(0);
  return true;
}

void MapPagePrepareQueue::activate(bool active) noexcept {
  auto old = epoch_.load(std::memory_order_relaxed);
  while (static_cast<bool>(old & 1u) != active) {
    const auto next = ((old & ~std::uint64_t{1}) + 2u) | (active ? 1u : 0u);
    if (epoch_.compare_exchange_weak(old, next, std::memory_order_acq_rel)) return;
  }
}

MapPagePrepareQueue::Claim MapPagePrepareQueue::try_claim(std::string_view page) noexcept {
  const auto epoch = generation();
  if (!(epoch & 1u)) return {};
  for (std::size_t i = 0; i < count_; ++i) {
    auto& s = slots_[i];
    if (s.entry.resref != page) continue;
    // Retire this demand even on a miss. The worker can finish its private read
    // independently; no native reader handshake and no redundant retry loop.
    auto retired = s.retiredThrough.load(std::memory_order_relaxed);
    while (retired < epoch && !s.retiredThrough.compare_exchange_weak(retired, epoch)) {}
    auto expected = State::Ready;
    if (s.state.compare_exchange_strong(expected, State::Claimed, std::memory_order_acq_rel)) {
      Claim claim(this, i, s.generation);
      if (s.generation == epoch && generation() == epoch) {
        hits_.fetch_add(1, std::memory_order_relaxed);
        return claim;
      }
    }
    misses_.fetch_add(1, std::memory_order_relaxed);
    return {};
  }
  return {};
}

void MapPagePrepareQueue::retire_resident(std::string_view page) noexcept {
  const auto epoch = generation();
  if (!(epoch & 1u)) return;
  for (std::size_t i = 0; i < count_; ++i) {
    auto& s = slots_[i];
    if (s.entry.resref != page) continue;
    auto retired = s.retiredThrough.load(std::memory_order_relaxed);
    while (retired < epoch && !s.retiredThrough.compare_exchange_weak(retired, epoch)) {}
    return;
  }
}

void MapPagePrepareQueue::recycle(Slot& s) {
  s.page = {}; // Worker owns destruction; reservation released afterwards.
  reserved_.fetch_sub(s.reservation);
  s.reservation = 0;
  s.state.store(State::Empty, std::memory_order_release);
}

bool MapPagePrepareQueue::work_one(Loader loader) {
  const auto epoch = generation();
  // Reclaim first, including slots after the next pending job in table order.
  for (std::size_t i = 0; i < count_; ++i) {
    auto& s = slots_[i];
    auto state = s.state.load(std::memory_order_acquire);
    if (state == State::Retired) recycle(s);
    else if (state == State::Ready &&
             (s.generation != epoch || s.retiredThrough.load() >= s.generation)) {
      if (s.state.compare_exchange_strong(state, State::Loading, std::memory_order_acq_rel))
        recycle(s);
    }
  }
  if (!(epoch & 1u) || !loader) return false;
  for (std::size_t i = 0; i < count_; ++i) {
    auto& s = slots_[i];
    if (s.state.load(std::memory_order_acquire) != State::Empty ||
        s.generation == epoch || s.retiredThrough.load() >= epoch) continue;
    const auto reservation = std::size_t{s.entry.compressedBytes} +
                             s.entry.decodedBytes + kPrepareScratchBytes;
    if (reserved_.load() > budget_ - reservation) continue;
    s.state.store(State::Loading, std::memory_order_release);
    s.generation = epoch;
    s.reservation = reservation;
    const auto total = reserved_.fetch_add(reservation) + reservation;
    peak_.store((std::max)(peak_.load(), total));
    try { s.page = loader(s.entry); } catch (...) { s.page = {}; }
    if (s.page.status != PvrzPrepareStatus::Ready ||
        s.page.compressedBytes != s.entry.compressedBytes ||
        s.page.decodedBytes != s.entry.decodedBytes ||
        s.page.decoded.size() != s.entry.decodedBytes ||
        s.page.decoded.capacity() > s.entry.decodedBytes ||
        s.page.compressedCrc32 != s.entry.crc32) {
      failures_.fetch_add(1);
      recycle(s);
    } else if (generation() != epoch || s.retiredThrough.load() >= epoch) {
      recycle(s);
    } else {
      reserved_.fetch_sub(s.reservation - s.page.decoded.capacity());
      s.reservation = s.page.decoded.capacity();
      prepared_.fetch_add(1);
      s.state.store(State::Ready, std::memory_order_release);
    }
    return true;
  }
  return false;
}
} // namespace iee::core
