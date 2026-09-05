#pragma once

#include <cstdint>

namespace iee::frame {
    // Hooks SDL_GL_SwapWindow when dynamically available, otherwise the
    // validated gdi32!SwapBuffers fallback. Returns false only if neither frame
    // boundary can be installed.
    bool install(bool enablePerformanceLogging, bool enableFullFrameFxaa,
                 bool enableFullFrameSsaa2x);

    void uninstall() noexcept;

    unsigned long long frame_count() noexcept;

    bool boundary_available() noexcept;

    // Raw QPC access for runtime schedulers and diagnostics. Keeping integer
    // ticks avoids the long-session precision loss of seconds_since_install().
    std::int64_t clock_ticks() noexcept;
    std::int64_t clock_frequency() noexcept;

    float seconds_since_install() noexcept;
}
