#include "supersample.h"

#include <windows.h>

#include <atomic>
#include <string>

#include "iee/core/hooking.h"
#include "iee/core/logger.h"
#include "iee/game/opengl_types.h"

namespace iee::supersample {
namespace {
using game::gl::OpenGLFunctions;
using FnViewport = void(APIENTRY*)(int, int, int, int);
using FnScissor = void(APIENTRY*)(int, int, int, int);

constexpr int SCALE = 2;
constexpr unsigned VERTEX_SHADER = 0x8B31;
constexpr unsigned FRAGMENT_SHADER = 0x8B30;
constexpr unsigned COMPILE_STATUS = 0x8B81;
constexpr unsigned LINK_STATUS = 0x8B82;
constexpr unsigned INFO_LOG_LENGTH = 0x8B84;

std::atomic<bool> g_enabled{false};
std::atomic<bool> g_renderingSupersampled{false};
core::Hook<FnViewport> g_viewportHook;
core::Hook<FnScissor> g_scissorHook;
HGLRC g_context{};
unsigned g_framebuffer{};
unsigned g_texture{};
unsigned g_program{};
unsigned g_vao{};
int g_sourceUniform{-1};
int g_logicalViewport[4]{};
int g_targetWidth{};
int g_targetHeight{};
bool g_frameArmed{};
bool g_loggedActive{};
bool g_loggedFailure{};

constexpr const char* VERTEX_SOURCE = R"glsl(
#version 330 core
out vec2 vUv;

void main() {
    const vec2 positions[3] = vec2[3](
        vec2(-1.0, -1.0),
        vec2( 3.0, -1.0),
        vec2(-1.0,  3.0)
    );
    vec2 position = positions[gl_VertexID];
    vUv = position * 0.5 + 0.5;
    gl_Position = vec4(position, 0.0, 1.0);
}
)glsl";

// With a source exactly twice as large on each axis, linear sampling at the
// destination pixel centre averages the corresponding 2x2 source footprint.
constexpr const char* FRAGMENT_SOURCE = R"glsl(
#version 330 core
in vec2 vUv;
out vec4 outColor;
uniform sampler2D uSource;

void main() {
    outColor = texture(uSource, vUv);
}
)glsl";

struct DrawState {
  int program{};
  int activeTexture{};
  int texture0Binding{};
  int vertexArray{};
  bool blend{};
  bool cull{};
  bool depth{};
  bool scissor{};
  bool stencil{};
  bool framebufferSrgb{};
};

void raw_viewport(int x, int y, int width, int height) noexcept {
  if (const auto original = g_viewportHook.original())
    original(x, y, width, height);
  else if (const auto& gl = game::gl::get_gl_functions(); gl.glViewport)
    gl.glViewport(x, y, width, height);
}

void APIENTRY detour_viewport(int x, int y, int width, int height) {
  const auto original = g_viewportHook.original();
  if (!original) return;
  if (!g_renderingSupersampled.load(std::memory_order_acquire)) {
    original(x, y, width, height);
    return;
  }
  g_logicalViewport[0] = x;
  g_logicalViewport[1] = y;
  g_logicalViewport[2] = width;
  g_logicalViewport[3] = height;
  original(x * SCALE, y * SCALE, width * SCALE, height * SCALE);
}

void APIENTRY detour_scissor(int x, int y, int width, int height) {
  const auto original = g_scissorHook.original();
  if (!original) return;
  if (g_renderingSupersampled.load(std::memory_order_acquire))
    original(x * SCALE, y * SCALE, width * SCALE, height * SCALE);
  else
    original(x, y, width, height);
}

void set_capability(const OpenGLFunctions& gl, unsigned capability, bool enabled) noexcept {
  if (enabled)
    gl.glEnable(capability);
  else
    gl.glDisable(capability);
}

bool capture_draw_state(const OpenGLFunctions& gl, DrawState& state) noexcept {
  if (!gl.glGetIntegerv || !gl.glIsEnabled || !gl.glActiveTexture) return false;
  gl.glGetIntegerv(game::gl::CURRENT_PROGRAM, &state.program);
  gl.glGetIntegerv(game::gl::ACTIVE_TEXTURE, &state.activeTexture);
  gl.glGetIntegerv(game::gl::VERTEX_ARRAY_BINDING, &state.vertexArray);
  state.blend = gl.glIsEnabled(game::gl::BLEND) != 0;
  state.cull = gl.glIsEnabled(game::gl::CULL_FACE) != 0;
  state.depth = gl.glIsEnabled(game::gl::DEPTH_TEST) != 0;
  state.scissor = gl.glIsEnabled(game::gl::SCISSOR_TEST) != 0;
  state.stencil = gl.glIsEnabled(game::gl::STENCIL_TEST) != 0;
  state.framebufferSrgb = gl.glIsEnabled(game::gl::FRAMEBUFFER_SRGB) != 0;
  gl.glActiveTexture(game::gl::TEXTURE0);
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &state.texture0Binding);
  return true;
}

void restore_draw_state(const OpenGLFunctions& gl, const DrawState& state) noexcept {
  gl.glBindTexture(game::gl::TEXTURE_2D, static_cast<unsigned>(state.texture0Binding));
  gl.glBindVertexArray(static_cast<unsigned>(state.vertexArray));
  gl.glUseProgram(static_cast<unsigned>(state.program));
  gl.glActiveTexture(static_cast<unsigned>(state.activeTexture));
  set_capability(gl, game::gl::BLEND, state.blend);
  set_capability(gl, game::gl::CULL_FACE, state.cull);
  set_capability(gl, game::gl::DEPTH_TEST, state.depth);
  set_capability(gl, game::gl::SCISSOR_TEST, state.scissor);
  set_capability(gl, game::gl::STENCIL_TEST, state.stencil);
  set_capability(gl, game::gl::FRAMEBUFFER_SRGB, state.framebufferSrgb);
}

std::string shader_log(const OpenGLFunctions& gl, unsigned shader) {
  int length = 0;
  gl.glGetShaderiv(shader, INFO_LOG_LENGTH, &length);
  if (length <= 1) return {};
  std::string log(static_cast<std::size_t>(length), '\0');
  int written = 0;
  gl.glGetShaderInfoLog(shader, length, &written, log.data());
  if (written >= 0 && written < length) log.resize(static_cast<std::size_t>(written));
  return log;
}

std::string program_log(const OpenGLFunctions& gl, unsigned program) {
  int length = 0;
  gl.glGetProgramiv(program, INFO_LOG_LENGTH, &length);
  if (length <= 1) return {};
  std::string log(static_cast<std::size_t>(length), '\0');
  int written = 0;
  gl.glGetProgramInfoLog(program, length, &written, log.data());
  if (written >= 0 && written < length) log.resize(static_cast<std::size_t>(written));
  return log;
}

unsigned compile_shader(const OpenGLFunctions& gl, unsigned type, const char* source) {
  const unsigned shader = gl.glCreateShader(type);
  if (!shader) return 0;
  gl.glShaderSource(shader, 1, &source, nullptr);
  gl.glCompileShader(shader);
  int compiled = 0;
  gl.glGetShaderiv(shader, COMPILE_STATUS, &compiled);
  if (compiled) return shader;
  LOG_ERROR("SSAA 2x shader compilation failed: {}", shader_log(gl, shader));
  gl.glDeleteShader(shader);
  return 0;
}

void forget_resources() noexcept {
  g_context = nullptr;
  g_framebuffer = 0;
  g_texture = 0;
  g_program = 0;
  g_vao = 0;
  g_sourceUniform = -1;
  g_targetWidth = 0;
  g_targetHeight = 0;
  g_frameArmed = false;
  g_renderingSupersampled.store(false, std::memory_order_release);
}

bool resources_available(const OpenGLFunctions& gl) noexcept {
  return gl.shaderObjectsAvailable && gl.shaderIntrospectionAvailable && gl.uniformApiAvailable &&
         gl.textureUploadAvailable && gl.glBindFramebuffer && gl.glGenFramebuffers &&
         gl.glDeleteFramebuffers && gl.glFramebufferTexture2D && gl.glCheckFramebufferStatus &&
         gl.glGenVertexArrays && gl.glBindVertexArray && gl.glDeleteVertexArrays &&
         gl.glDrawArrays && gl.glViewport && gl.glIsEnabled && gl.glEnable && gl.glDisable;
}

bool initialize_resources(const OpenGLFunctions& gl, HGLRC context) {
  if (!resources_available(gl)) {
    LOG_ERROR("SSAA 2x unavailable: required OpenGL entry points are missing");
    return false;
  }

  const unsigned vertex = compile_shader(gl, VERTEX_SHADER, VERTEX_SOURCE);
  if (!vertex) return false;
  const unsigned fragment = compile_shader(gl, FRAGMENT_SHADER, FRAGMENT_SOURCE);
  if (!fragment) {
    gl.glDeleteShader(vertex);
    return false;
  }

  const unsigned program = gl.glCreateProgram();
  gl.glAttachShader(program, vertex);
  gl.glAttachShader(program, fragment);
  gl.glLinkProgram(program);
  gl.glDeleteShader(vertex);
  gl.glDeleteShader(fragment);
  int linked = 0;
  gl.glGetProgramiv(program, LINK_STATUS, &linked);
  if (!linked) {
    LOG_ERROR("SSAA 2x program link failed: {}", program_log(gl, program));
    gl.glDeleteProgram(program);
    return false;
  }

  unsigned framebuffer = 0;
  unsigned texture = 0;
  unsigned vao = 0;
  gl.glGenFramebuffers(1, &framebuffer);
  gl.glGenTextures(1, &texture);
  gl.glGenVertexArrays(1, &vao);
  if (!framebuffer || !texture || !vao) {
    if (framebuffer) gl.glDeleteFramebuffers(1, &framebuffer);
    if (texture) gl.glDeleteTextures(1, &texture);
    if (vao) gl.glDeleteVertexArrays(1, &vao);
    gl.glDeleteProgram(program);
    LOG_ERROR("SSAA 2x could not allocate its OpenGL objects");
    return false;
  }

  g_context = context;
  g_framebuffer = framebuffer;
  g_texture = texture;
  g_program = program;
  g_vao = vao;
  g_sourceUniform = gl.glGetUniformLocation(program, "uSource");
  return true;
}

bool resize_target(const OpenGLFunctions& gl, int logicalWidth, int logicalHeight) {
  if (logicalWidth <= 0 || logicalHeight <= 0) return false;
  const int width = logicalWidth * SCALE;
  const int height = logicalHeight * SCALE;
  if (width == g_targetWidth && height == g_targetHeight) return true;

  int previousFramebuffer = 0;
  int previousActiveTexture = 0;
  int previousTexture = 0;
  gl.glGetIntegerv(game::gl::FRAMEBUFFER_BINDING, &previousFramebuffer);
  gl.glGetIntegerv(game::gl::ACTIVE_TEXTURE, &previousActiveTexture);
  gl.glActiveTexture(game::gl::TEXTURE0);
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &previousTexture);

  game::gl::discard_errors();
  gl.glBindTexture(game::gl::TEXTURE_2D, g_texture);
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER,
                     static_cast<int>(game::gl::LINEAR));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                     static_cast<int>(game::gl::LINEAR));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_S,
                     static_cast<int>(game::gl::CLAMP_TO_EDGE));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_T,
                     static_cast<int>(game::gl::CLAMP_TO_EDGE));
  gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL, 0);
  gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8), width, height, 0,
                  game::gl::RGBA, game::gl::UNSIGNED_BYTE, nullptr);
  gl.glBindFramebuffer(game::gl::FRAMEBUFFER, g_framebuffer);
  gl.glFramebufferTexture2D(game::gl::FRAMEBUFFER, game::gl::COLOR_ATTACHMENT0,
                            game::gl::TEXTURE_2D, g_texture, 0);
  const unsigned status = gl.glCheckFramebufferStatus(game::gl::FRAMEBUFFER);

  gl.glBindFramebuffer(game::gl::FRAMEBUFFER, static_cast<unsigned>(previousFramebuffer));
  gl.glBindTexture(game::gl::TEXTURE_2D, static_cast<unsigned>(previousTexture));
  gl.glActiveTexture(static_cast<unsigned>(previousActiveTexture));
  if (status != game::gl::FRAMEBUFFER_COMPLETE ||
      !game::gl::check_error("SSAA 2x target allocation")) {
    LOG_ERROR("SSAA 2x framebuffer incomplete: status=0x{:X}", status);
    return false;
  }

  g_targetWidth = width;
  g_targetHeight = height;
  LOG_INFO("SSAA 2x target allocated: {}x{} -> {}x{}", width, height, logicalWidth,
           logicalHeight);
  return true;
}

bool ensure_resources(const OpenGLFunctions& gl, HGLRC context) {
  if (g_context && g_context != context) forget_resources();
  if (!g_program && !initialize_resources(gl, context)) return false;
  return resize_target(gl, g_logicalViewport[2], g_logicalViewport[3]);
}

void disable_after_failure(const char* reason) noexcept {
  g_enabled.store(false, std::memory_order_release);
  g_renderingSupersampled.store(false, std::memory_order_release);
  if (!g_loggedFailure) {
    LOG_ERROR("SSAA 2x disabled: {}", reason);
    g_loggedFailure = true;
  }
}
}  // namespace

bool configure(bool enabled) noexcept {
  if (!enabled) {
    g_enabled.store(false, std::memory_order_release);
    return true;
  }

  try {
    const HMODULE opengl32 = GetModuleHandleA("opengl32.dll");
    if (!opengl32) return false;
    void* viewport = reinterpret_cast<void*>(GetProcAddress(opengl32, "glViewport"));
    void* scissor = reinterpret_cast<void*>(GetProcAddress(opengl32, "glScissor"));
    if (!viewport || !scissor) return false;
    g_viewportHook.create(viewport, reinterpret_cast<void*>(&detour_viewport));
    g_scissorHook.create(scissor, reinterpret_cast<void*>(&detour_scissor));
    g_viewportHook.enable();
    g_scissorHook.enable();
    g_enabled.store(true, std::memory_order_release);
    LOG_INFO("Diagnostic SSAA 2x enabled (world + UI, 4x pixel workload)");
    return true;
  } catch (...) {
    (void)g_viewportHook.remove();
    (void)g_scissorHook.remove();
    g_enabled.store(false, std::memory_order_release);
    LOG_ERROR("SSAA 2x raster-state hooks could not be installed");
    return false;
  }
}

void before_swap() noexcept {
  if (!g_enabled.load(std::memory_order_acquire) || !g_frameArmed) return;

  try {
    const HGLRC context = game::gl::current_context();
    if (!context || context != g_context) {
      disable_after_failure("OpenGL context changed while a supersampled frame was active");
      return;
    }
    const auto& gl = game::gl::get_gl_functions();
    int framebuffer = 0;
    gl.glGetIntegerv(game::gl::FRAMEBUFFER_BINDING, &framebuffer);
    if (framebuffer != static_cast<int>(g_framebuffer)) {
      disable_after_failure("the engine replaced the diagnostic framebuffer");
      return;
    }

    g_renderingSupersampled.store(false, std::memory_order_release);
    if (g_targetWidth != g_logicalViewport[2] * SCALE ||
        g_targetHeight != g_logicalViewport[3] * SCALE) {
      // A resize arrived during the frame. Present no stale-scale image; the
      // target will be rebuilt immediately after this swap.
      gl.glBindFramebuffer(game::gl::FRAMEBUFFER, 0);
      raw_viewport(g_logicalViewport[0], g_logicalViewport[1], g_logicalViewport[2],
                   g_logicalViewport[3]);
      g_frameArmed = false;
      return;
    }

    DrawState state{};
    if (!capture_draw_state(gl, state)) {
      disable_after_failure("could not capture OpenGL draw state");
      return;
    }

    game::gl::discard_errors();
    gl.glBindFramebuffer(game::gl::FRAMEBUFFER, 0);
    raw_viewport(g_logicalViewport[0], g_logicalViewport[1], g_logicalViewport[2],
                 g_logicalViewport[3]);
    gl.glDisable(game::gl::BLEND);
    gl.glDisable(game::gl::CULL_FACE);
    gl.glDisable(game::gl::DEPTH_TEST);
    gl.glDisable(game::gl::SCISSOR_TEST);
    gl.glDisable(game::gl::STENCIL_TEST);
    gl.glDisable(game::gl::FRAMEBUFFER_SRGB);
    gl.glActiveTexture(game::gl::TEXTURE0);
    gl.glBindTexture(game::gl::TEXTURE_2D, g_texture);
    gl.glUseProgram(g_program);
    gl.glUniform1i(g_sourceUniform, 0);
    gl.glBindVertexArray(g_vao);
    gl.glDrawArrays(game::gl::TRIANGLES, 0, 3);
    const bool succeeded = game::gl::check_error("SSAA 2x downsample draw");
    restore_draw_state(gl, state);
    g_frameArmed = false;

    if (succeeded && !g_loggedActive) {
      LOG_INFO("Diagnostic SSAA 2x is actively presenting supersampled frames");
      g_loggedActive = true;
    }
  } catch (...) {
    disable_after_failure("unexpected exception before presentation");
  }
}

void after_swap() noexcept {
  if (!g_enabled.load(std::memory_order_acquire)) return;

  try {
    const HGLRC context = game::gl::current_context();
    if (!context) return;
    const auto& gl = game::gl::get_gl_functions();
    if (!g_context) {
      gl.glGetIntegerv(game::gl::VIEWPORT, g_logicalViewport);
    }
    if (!ensure_resources(gl, context)) {
      disable_after_failure("OpenGL resource initialization failed");
      return;
    }

    gl.glBindFramebuffer(game::gl::FRAMEBUFFER, g_framebuffer);
    raw_viewport(g_logicalViewport[0] * SCALE, g_logicalViewport[1] * SCALE,
                 g_logicalViewport[2] * SCALE, g_logicalViewport[3] * SCALE);
    g_renderingSupersampled.store(true, std::memory_order_release);
    g_frameArmed = true;
  } catch (...) {
    disable_after_failure("unexpected exception after presentation");
  }
}

void shutdown() noexcept {
  g_enabled.store(false, std::memory_order_release);
  g_renderingSupersampled.store(false, std::memory_order_release);
  (void)g_scissorHook.remove();
  (void)g_viewportHook.remove();
  try {
    if (g_context && game::gl::current_context() == g_context) {
      const auto& gl = game::gl::get_gl_functions();
      gl.glBindFramebuffer(game::gl::FRAMEBUFFER, 0);
      if (g_framebuffer && gl.glDeleteFramebuffers)
        gl.glDeleteFramebuffers(1, &g_framebuffer);
      if (g_texture && gl.glDeleteTextures) gl.glDeleteTextures(1, &g_texture);
      if (g_vao && gl.glDeleteVertexArrays) gl.glDeleteVertexArrays(1, &g_vao);
      if (g_program && gl.glDeleteProgram) gl.glDeleteProgram(g_program);
    }
  } catch (...) {
  }
  forget_resources();
  g_loggedActive = false;
  g_loggedFailure = false;
}

}  // namespace iee::supersample
