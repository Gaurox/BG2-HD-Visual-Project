#pragma once
#include <filesystem>
#include "iee/core/map_page_prepare_queue.h"
#include "iee/core/pvr_demand_telemetry.h"
namespace iee { struct AppContext; }
namespace iee::map_page_preload {
using DemandPrepared = core::PvrPreloadTrace (*)(void*, const core::MapPagePrepareQueue::Claim&);
bool configure(const std::filesystem::path& bindings, DemandPrepared demand) noexcept;
void on_frame_interval(double milliseconds) noexcept;
void on_post_swap(AppContext& ctx, const void* cacheEntries) noexcept;
void shutdown() noexcept;
}
