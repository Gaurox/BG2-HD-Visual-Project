#pragma once
#include <filesystem>
#include "iee/core/map_page_prepare_queue.h"

namespace iee { struct AppContext; }
namespace iee::map_page_prepare {
bool configure(const std::filesystem::path& directory) noexcept;
bool enabled() noexcept;
void reset() noexcept;
void observe_area(const AppContext& ctx) noexcept;
// Once per generation on render thread, using the signature-validated LRU.
void retire_resident_pages(const void* cacheEntries) noexcept;
core::MapPagePrepareQueue::Claim begin_native_demand(void* resource) noexcept;
bool current(std::uint64_t generation) noexcept;
void record(bool consumed, std::uint64_t crcNanoseconds, std::uint64_t copyNanoseconds) noexcept;
void shutdown() noexcept;
}
