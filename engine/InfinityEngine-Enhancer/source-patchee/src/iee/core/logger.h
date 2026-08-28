#pragma once
#include <spdlog/sinks/sink.h>
#include <spdlog/spdlog.h>

#include <cstddef>
#include <memory>
#include <string_view>

namespace iee::core {
inline constexpr std::size_t DEFAULT_LOG_MAX_FILE_SIZE_BYTES = 16u * 1024u * 1024u;
inline constexpr std::size_t DEFAULT_LOG_BACKUP_FILE_COUNT = 3u;

struct LoggerRotationPolicy {
  std::size_t maxFileSizeBytes = DEFAULT_LOG_MAX_FILE_SIZE_BYTES;
  std::size_t backupFileCount = DEFAULT_LOG_BACKUP_FILE_COUNT;
};

namespace detail {
std::shared_ptr<spdlog::sinks::sink> make_rotating_file_sink(
    std::string_view log_path_utf8, LoggerRotationPolicy policy = {});
}

void init_logger(std::string_view log_path_utf8, bool verbose = false);

spdlog::logger* logger() noexcept;

#define LOG_TRACE(...) ::iee::core::logger()->trace(__VA_ARGS__)
#define LOG_DEBUG(...) ::iee::core::logger()->debug(__VA_ARGS__)
#define LOG_INFO(...) ::iee::core::logger()->info(__VA_ARGS__)
#define LOG_WARN(...) ::iee::core::logger()->warn(__VA_ARGS__)
#define LOG_ERROR(...) ::iee::core::logger()->error(__VA_ARGS__)
#define LOG_CRITICAL(...) ::iee::core::logger()->critical(__VA_ARGS__)

#define LOG_DEBUG_FAST(...)                                        \
  do {                                                             \
    if (::iee::core::logger()->should_log(spdlog::level::debug)) { \
      ::iee::core::logger()->debug(__VA_ARGS__);                   \
    }                                                              \
  } while (0)
#define LOG_TRACE_FAST(...)                                        \
  do {                                                             \
    if (::iee::core::logger()->should_log(spdlog::level::trace)) { \
      ::iee::core::logger()->trace(__VA_ARGS__);                   \
    }                                                              \
  } while (0)
}  // namespace iee::core
