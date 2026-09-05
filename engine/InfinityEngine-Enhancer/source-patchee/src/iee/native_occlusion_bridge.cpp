#include "iee/native_occlusion_bridge.h"

#include <windows.h>

#include <algorithm>
#include <cstring>
#include <limits>
#include <string>

#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"

namespace iee::native_occlusion_bridge {
namespace {
using game::gl::OpenGLFunctions;

constexpr std::size_t kEngineTextureDescriptorCount = 512;
constexpr std::size_t kEngineTextureDescriptorStride = 0x28;
constexpr std::uint64_t kMaximumPhysicalScratchBytes = 64ull * 1024ull * 1024ull;
constexpr unsigned kVertexShader = 0x8B31;
constexpr unsigned kFragmentShader = 0x8B30;
constexpr unsigned kCompileStatus = 0x8B81;
constexpr unsigned kLinkStatus = 0x8B82;
constexpr unsigned kInfoLogLength = 0x8B84;

HGLRC g_context{};
unsigned g_framebuffer{};
unsigned g_maskTexture{};
unsigned g_program{};
unsigned g_vao{};
int g_replacementUniform{-1};
int g_maskUniform{-1};
int g_scaleUniform{-1};
bool g_failureLogged{};
bool g_activeLogged{};

constexpr const char* kVertexSource = R"glsl(
#version 330 core
void main() {
    const vec2 positions[3] = vec2[3](
        vec2(-1.0, -1.0),
        vec2( 3.0, -1.0),
        vec2(-1.0,  3.0)
    );
    gl_Position = vec4(positions[gl_VertexID], 0.0, 1.0);
}
)glsl";

constexpr const char* kFragmentSource = R"glsl(
#version 330 core
layout(location = 0) out vec4 outColor;
uniform sampler2D uReplacement;
uniform sampler2D uVisibility;
uniform int uScale;

void main() {
    ivec2 highCoord = ivec2(gl_FragCoord.xy);
    ivec2 highSize = textureSize(uReplacement, 0);
    highCoord = clamp(highCoord, ivec2(0), highSize - ivec2(1));
    ivec2 maskCoord = highCoord / uScale;
    vec4 transfer = texelFetch(uVisibility, maskCoord, 0);
    vec4 replacement = texelFetch(uReplacement, highCoord, 0);
    if (transfer.g > (0.5 / 255.0)) {
        outColor = vec4(0.0, 0.0, 0.0, transfer.g);
    } else if (transfer.r < (0.5 / 255.0) || transfer.b > (0.5 / 255.0)) {
        // A fully cleared texel must also lose its colour: an ARE animation flagged
        // Blended is composited additively, so its RGB reaches the scene whatever the
        // alpha says and alpha-only visibility leaves it fully visible. B carries the
        // same clear into an adjacent x1-transparent cell populated only by xN edge
        // smoothing. Zero is the neutral element of both composition paths.
        outColor = vec4(0.0, 0.0, 0.0, 0.0);
    } else {
        outColor = vec4(replacement.rgb, replacement.a * transfer.r);
    }
}
)glsl";

struct EngineTextureDescriptor {
  std::uint32_t glName{};
  std::int32_t logicalWidth{};
  std::int32_t logicalHeight{};
  std::uint8_t deletePending{};
  std::uint32_t secondaryGlName{};
};

struct DrawState {
  int framebuffer{};
  int viewport[4]{};
  int program{};
  int activeTexture{};
  int texture0Binding{};
  int texture1Binding{};
  int vertexArray{};
  int unpackAlignment{4};
  int unpackRowLength{};
  int unpackSkipRows{};
  int unpackSkipPixels{};
  int unpackBuffer{};
  bool blend{};
  bool cull{};
  bool depth{};
  bool scissor{};
  bool stencil{};
  bool framebufferSrgb{};
};

int logical_texture_id(const EngineTextureApi& api) noexcept {
  if (!api.glTextureState) return 0;
  std::uint32_t state = 0;
  if (!core::safe_read(api.glTextureState, state)) return 0;
  return static_cast<int>((state >> 21u) & 0x1FFu);
}

bool read_descriptor(const EngineTextureApi& api, int textureId,
                     EngineTextureDescriptor& out) noexcept {
  out = {};
  if (!api.glTextureTable || textureId <= 0 ||
      textureId >= static_cast<int>(kEngineTextureDescriptorCount)) {
    return false;
  }
  const auto* descriptor =
      api.glTextureTable +
      static_cast<std::size_t>(textureId) * kEngineTextureDescriptorStride;
  return core::safe_read(descriptor + 0x00, out.glName) &&
         core::safe_read(descriptor + 0x04, out.logicalWidth) &&
         core::safe_read(descriptor + 0x08, out.logicalHeight) &&
         core::safe_read(descriptor + 0x0D, out.deletePending) &&
         core::safe_read(descriptor + 0x24, out.secondaryGlName);
}

bool clear_private_secondary(const EngineTextureApi& api, int textureId,
                             EngineTextureDescriptor& descriptor) noexcept {
  if (descriptor.secondaryGlName == 0) return true;
  if (!api.glTextureTable || descriptor.glName == 0 || descriptor.deletePending != 0 ||
      textureId <= 0 || textureId >= static_cast<int>(kEngineTextureDescriptorCount)) {
    return false;
  }
  auto* secondary =
      api.glTextureTable +
      static_cast<std::size_t>(textureId) * kEngineTextureDescriptorStride + 0x24;
  if (!core::is_writable_non_executable_memory(secondary, sizeof(std::uint32_t))) {
    return false;
  }
  const std::uint32_t zero = 0;
  std::memcpy(secondary, &zero, sizeof(zero));
  return read_descriptor(api, textureId, descriptor) && descriptor.secondaryGlName == 0 &&
         descriptor.glName != 0 && descriptor.deletePending == 0;
}

void set_capability(const OpenGLFunctions& gl, unsigned capability,
                    bool enabled) noexcept {
  if (enabled)
    gl.glEnable(capability);
  else
    gl.glDisable(capability);
}

bool capture_draw_state(const OpenGLFunctions& gl, DrawState& state) noexcept {
  if (!gl.glGetIntegerv || !gl.glIsEnabled || !gl.glActiveTexture) return false;
  gl.glGetIntegerv(game::gl::FRAMEBUFFER_BINDING, &state.framebuffer);
  gl.glGetIntegerv(game::gl::VIEWPORT, state.viewport);
  gl.glGetIntegerv(game::gl::CURRENT_PROGRAM, &state.program);
  gl.glGetIntegerv(game::gl::ACTIVE_TEXTURE, &state.activeTexture);
  gl.glGetIntegerv(game::gl::VERTEX_ARRAY_BINDING, &state.vertexArray);
  gl.glGetIntegerv(game::gl::UNPACK_ALIGNMENT, &state.unpackAlignment);
  gl.glGetIntegerv(game::gl::UNPACK_ROW_LENGTH, &state.unpackRowLength);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_ROWS, &state.unpackSkipRows);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_PIXELS, &state.unpackSkipPixels);
  gl.glGetIntegerv(game::gl::PIXEL_UNPACK_BUFFER_BINDING, &state.unpackBuffer);
  state.blend = gl.glIsEnabled(game::gl::BLEND) != 0;
  state.cull = gl.glIsEnabled(game::gl::CULL_FACE) != 0;
  state.depth = gl.glIsEnabled(game::gl::DEPTH_TEST) != 0;
  state.scissor = gl.glIsEnabled(game::gl::SCISSOR_TEST) != 0;
  state.stencil = gl.glIsEnabled(game::gl::STENCIL_TEST) != 0;
  state.framebufferSrgb = gl.glIsEnabled(game::gl::FRAMEBUFFER_SRGB) != 0;
  gl.glActiveTexture(game::gl::TEXTURE0);
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &state.texture0Binding);
  gl.glActiveTexture(game::gl::TEXTURE0 + 1u);
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D, &state.texture1Binding);
  gl.glActiveTexture(static_cast<unsigned>(state.activeTexture));
  return gl.glGetError() == game::gl::GL_NO_ERROR;
}

void restore_draw_state(const OpenGLFunctions& gl, const DrawState& state) noexcept {
  gl.glBindFramebuffer(game::gl::FRAMEBUFFER, static_cast<unsigned>(state.framebuffer));
  gl.glViewport(state.viewport[0], state.viewport[1], state.viewport[2], state.viewport[3]);
  gl.glActiveTexture(game::gl::TEXTURE0);
  gl.glBindTexture(game::gl::TEXTURE_2D, static_cast<unsigned>(state.texture0Binding));
  gl.glActiveTexture(game::gl::TEXTURE0 + 1u);
  gl.glBindTexture(game::gl::TEXTURE_2D, static_cast<unsigned>(state.texture1Binding));
  gl.glBindVertexArray(static_cast<unsigned>(state.vertexArray));
  gl.glUseProgram(static_cast<unsigned>(state.program));
  gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, state.unpackAlignment);
  gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, state.unpackRowLength);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, state.unpackSkipRows);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, state.unpackSkipPixels);
  set_capability(gl, game::gl::BLEND, state.blend);
  set_capability(gl, game::gl::CULL_FACE, state.cull);
  set_capability(gl, game::gl::DEPTH_TEST, state.depth);
  set_capability(gl, game::gl::SCISSOR_TEST, state.scissor);
  set_capability(gl, game::gl::STENCIL_TEST, state.stencil);
  set_capability(gl, game::gl::FRAMEBUFFER_SRGB, state.framebufferSrgb);
  gl.glActiveTexture(static_cast<unsigned>(state.activeTexture));
}

std::string shader_log(const OpenGLFunctions& gl, unsigned shader) {
  int length = 0;
  gl.glGetShaderiv(shader, kInfoLogLength, &length);
  if (length <= 1) return {};
  std::string log(static_cast<std::size_t>(length), '\0');
  int written = 0;
  gl.glGetShaderInfoLog(shader, length, &written, log.data());
  if (written >= 0 && written < length) log.resize(static_cast<std::size_t>(written));
  return log;
}

std::string program_log(const OpenGLFunctions& gl, unsigned program) {
  int length = 0;
  gl.glGetProgramiv(program, kInfoLogLength, &length);
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
  gl.glGetShaderiv(shader, kCompileStatus, &compiled);
  if (compiled) return shader;
  LOG_ERROR("Native occlusion phase1 shader compilation failed: {}", shader_log(gl, shader));
  gl.glDeleteShader(shader);
  return 0;
}

void forget_resources() noexcept {
  g_context = nullptr;
  g_framebuffer = 0;
  g_maskTexture = 0;
  g_program = 0;
  g_vao = 0;
  g_replacementUniform = -1;
  g_maskUniform = -1;
  g_scaleUniform = -1;
}

bool resources_available(const OpenGLFunctions& gl) noexcept {
  return gl.shaderObjectsAvailable && gl.shaderIntrospectionAvailable &&
         gl.uniformApiAvailable && gl.textureUploadAvailable && gl.glBindFramebuffer &&
         gl.glGenFramebuffers && gl.glDeleteFramebuffers && gl.glFramebufferTexture2D &&
         gl.glCheckFramebufferStatus && gl.glGenVertexArrays && gl.glBindVertexArray &&
         gl.glDeleteVertexArrays && gl.glDrawArrays && gl.glViewport && gl.glIsEnabled &&
         gl.glEnable && gl.glDisable;
}

bool initialize_resources(const OpenGLFunctions& gl, HGLRC context) {
  if (!resources_available(gl)) return false;
  const unsigned vertex = compile_shader(gl, kVertexShader, kVertexSource);
  if (!vertex) return false;
  const unsigned fragment = compile_shader(gl, kFragmentShader, kFragmentSource);
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
  gl.glGetProgramiv(program, kLinkStatus, &linked);
  if (!linked) {
    LOG_ERROR("Native occlusion phase1 program link failed: {}", program_log(gl, program));
    gl.glDeleteProgram(program);
    return false;
  }
  unsigned framebuffer = 0;
  unsigned maskTexture = 0;
  unsigned vao = 0;
  gl.glGenFramebuffers(1, &framebuffer);
  gl.glGenTextures(1, &maskTexture);
  gl.glGenVertexArrays(1, &vao);
  if (!framebuffer || !maskTexture || !vao) {
    if (framebuffer) gl.glDeleteFramebuffers(1, &framebuffer);
    if (maskTexture) gl.glDeleteTextures(1, &maskTexture);
    if (vao) gl.glDeleteVertexArrays(1, &vao);
    gl.glDeleteProgram(program);
    return false;
  }
  g_context = context;
  g_framebuffer = framebuffer;
  g_maskTexture = maskTexture;
  g_program = program;
  g_vao = vao;
  g_replacementUniform = gl.glGetUniformLocation(program, "uReplacement");
  g_maskUniform = gl.glGetUniformLocation(program, "uVisibility");
  g_scaleUniform = gl.glGetUniformLocation(program, "uScale");
  if (g_replacementUniform >= 0 && g_maskUniform >= 0 && g_scaleUniform >= 0) {
    return true;
  }
  gl.glDeleteFramebuffers(1, &g_framebuffer);
  gl.glDeleteTextures(1, &g_maskTexture);
  gl.glDeleteVertexArrays(1, &g_vao);
  gl.glDeleteProgram(g_program);
  forget_resources();
  return false;
}

bool ensure_resources(const OpenGLFunctions& gl, HGLRC context) {
  if (g_context && g_context != context) {
    forget_resources();
    g_failureLogged = false;
    g_activeLogged = false;
  }
  return g_program != 0 || initialize_resources(gl, context);
}

void log_failure_once(const char* reason) noexcept {
  if (g_failureLogged) return;
  g_failureLogged = true;
  LOG_WARN("Native occlusion phase1 bridge failed closed: {}", reason);
}
}  // namespace

bool bind_masked_texture(const std::vector<std::uint8_t>& visibilityTransfer,
                         int logicalWidth, int logicalHeight,
                         int replacementTextureId, const EngineTextureApi& api,
                         int& transientTextureId) noexcept {
  transientTextureId = 0;
  if (logicalWidth <= 0 || logicalHeight <= 0 || replacementTextureId <= 0 ||
      !api.DrawGenTexture || !api.DrawBindTexture || !api.DrawDeleteTexture ||
      !api.TexImage || !api.glTextureState || !api.glTextureTable) {
    return false;
  }
  const auto logicalPixels = static_cast<std::uint64_t>(logicalWidth) *
                             static_cast<std::uint64_t>(logicalHeight);
  if (logicalPixels == 0 || logicalPixels >
                                (std::numeric_limits<std::uint64_t>::max)() / 4ull ||
      logicalPixels * 4ull != visibilityTransfer.size()) {
    return false;
  }

  try {
    auto& gl = game::gl::get_gl_functions();
    if ((!gl.valid && !gl.initialize()) || !gl.glGetTexLevelParameteriv ||
        !gl.glGetError) {
      log_failure_once("required OpenGL functions are unavailable");
      return false;
    }
    const HGLRC context = game::gl::current_context();
    if (!context || !ensure_resources(gl, context)) {
      log_failure_once("shader/FBO resources are unavailable");
      return false;
    }
    if (logical_texture_id(api) != replacementTextureId) {
      return false;
    }
    EngineTextureDescriptor replacement{};
    if (!read_descriptor(api, replacementTextureId, replacement) ||
        replacement.glName == 0 || replacement.deletePending != 0 ||
        replacement.logicalWidth != logicalWidth ||
        replacement.logicalHeight != logicalHeight) {
      return false;
    }

    DrawState state{};
    game::gl::discard_errors();
    if (!capture_draw_state(gl, state)) {
      log_failure_once("OpenGL state capture failed");
      return false;
    }
    const auto restoreReplacement = [&](int transient) {
      restore_draw_state(gl, state);
      api.DrawBindTexture(replacementTextureId);
      if (transient > 0 && transient != replacementTextureId) {
        api.DrawDeleteTexture(transient);
      }
    };
    if (state.unpackBuffer != 0) {
      restoreReplacement(0);
      log_failure_once("a pixel-unpack buffer is active");
      return false;
    }

    gl.glActiveTexture(game::gl::TEXTURE0);
    gl.glBindTexture(game::gl::TEXTURE_2D, replacement.glName);
    int physicalWidth = 0;
    int physicalHeight = 0;
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_WIDTH,
                                &physicalWidth);
    gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D, 0, game::gl::TEXTURE_HEIGHT,
                                &physicalHeight);
    if (physicalWidth <= 0 || physicalHeight <= 0 ||
        physicalWidth % logicalWidth != 0 || physicalHeight % logicalHeight != 0) {
      restoreReplacement(0);
      return false;
    }
    const int scale = physicalWidth / logicalWidth;
    if ((scale != 2 && scale != 4) || physicalHeight / logicalHeight != scale) {
      restoreReplacement(0);
      return false;
    }
    const auto physicalBytes = static_cast<std::uint64_t>(physicalWidth) *
                               static_cast<std::uint64_t>(physicalHeight) * 4ull;
    if (physicalBytes > kMaximumPhysicalScratchBytes) {
      restoreReplacement(0);
      log_failure_once("the xN frame exceeds the 64 MiB transient GPU bound");
      return false;
    }

    const int generated = api.DrawGenTexture(static_cast<int>(game::gl::LINEAR), 0, 0, 0);
    if (generated <= 0 || generated == replacementTextureId) {
      restoreReplacement(generated);
      return false;
    }
    transientTextureId = generated;
    EngineTextureDescriptor output{};
    if (!read_descriptor(api, generated, output) || output.glName == 0 ||
        output.deletePending != 0 || !clear_private_secondary(api, generated, output)) {
      restoreReplacement(generated);
      transientTextureId = 0;
      return false;
    }

    api.DrawBindTexture(generated);
    api.TexImage(logicalWidth, logicalHeight, nullptr, 0);
    if (!read_descriptor(api, generated, output) || output.glName == 0 ||
        output.deletePending != 0 || output.secondaryGlName != 0 ||
        output.logicalWidth != logicalWidth || output.logicalHeight != logicalHeight) {
      restoreReplacement(generated);
      transientTextureId = 0;
      return false;
    }

    gl.glActiveTexture(game::gl::TEXTURE0);
    gl.glBindTexture(game::gl::TEXTURE_2D, output.glName);
    gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8),
                    physicalWidth, physicalHeight, 0, game::gl::RGBA,
                    game::gl::UNSIGNED_BYTE, nullptr);
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER,
                       static_cast<int>(game::gl::LINEAR));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                       static_cast<int>(game::gl::LINEAR));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_S,
                       static_cast<int>(game::gl::CLAMP_TO_EDGE));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_T,
                       static_cast<int>(game::gl::CLAMP_TO_EDGE));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL, 0);

    gl.glActiveTexture(game::gl::TEXTURE0 + 1u);
    gl.glBindTexture(game::gl::TEXTURE_2D, g_maskTexture);
    gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, 1);
    gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH, 0);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS, 0);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS, 0);
    gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8),
                    logicalWidth, logicalHeight, 0, game::gl::RGBA,
                    game::gl::UNSIGNED_BYTE, visibilityTransfer.data());
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MIN_FILTER,
                       static_cast<int>(game::gl::NEAREST));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAG_FILTER,
                       static_cast<int>(game::gl::NEAREST));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_S,
                       static_cast<int>(game::gl::CLAMP_TO_EDGE));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_WRAP_T,
                       static_cast<int>(game::gl::CLAMP_TO_EDGE));
    gl.glTexParameteri(game::gl::TEXTURE_2D, game::gl::TEXTURE_MAX_LEVEL, 0);

    gl.glBindFramebuffer(game::gl::FRAMEBUFFER, g_framebuffer);
    gl.glFramebufferTexture2D(game::gl::FRAMEBUFFER, game::gl::COLOR_ATTACHMENT0,
                              game::gl::TEXTURE_2D, output.glName, 0);
    if (gl.glCheckFramebufferStatus(game::gl::FRAMEBUFFER) !=
        game::gl::FRAMEBUFFER_COMPLETE) {
      restoreReplacement(generated);
      transientTextureId = 0;
      return false;
    }
    gl.glViewport(0, 0, physicalWidth, physicalHeight);
    gl.glDisable(game::gl::BLEND);
    gl.glDisable(game::gl::CULL_FACE);
    gl.glDisable(game::gl::DEPTH_TEST);
    gl.glDisable(game::gl::SCISSOR_TEST);
    gl.glDisable(game::gl::STENCIL_TEST);
    gl.glDisable(game::gl::FRAMEBUFFER_SRGB);
    gl.glActiveTexture(game::gl::TEXTURE0);
    gl.glBindTexture(game::gl::TEXTURE_2D, replacement.glName);
    gl.glActiveTexture(game::gl::TEXTURE0 + 1u);
    gl.glBindTexture(game::gl::TEXTURE_2D, g_maskTexture);
    gl.glUseProgram(g_program);
    gl.glUniform1i(g_replacementUniform, 0);
    gl.glUniform1i(g_maskUniform, 1);
    gl.glUniform1i(g_scaleUniform, scale);
    gl.glBindVertexArray(g_vao);
    gl.glDrawArrays(game::gl::TRIANGLES, 0, 3);
    const bool rendered = game::gl::check_error("native occlusion phase1 mask draw");
    restore_draw_state(gl, state);

    // TexImage left the engine cache on the transient id. Move away and back
    // so the deferred renderer resolves the transient GL name, not merely the
    // raw binding restored above.
    api.DrawBindTexture(replacementTextureId);
    if (!rendered) {
      api.DrawDeleteTexture(generated);
      transientTextureId = 0;
      return false;
    }
    api.DrawBindTexture(generated);
    if (logical_texture_id(api) != generated) {
      api.DrawBindTexture(replacementTextureId);
      api.DrawDeleteTexture(generated);
      transientTextureId = 0;
      return false;
    }
    if (!g_activeLogged) {
      g_activeLogged = true;
      LOG_INFO(
          "Native occlusion phase1 bridge active: logical mask {}x{}, x{} backing, "
          "transient GPU budget capped at 64 MiB",
          logicalWidth, logicalHeight, scale);
    }
    return true;
  } catch (const std::exception& error) {
    if (api.DrawBindTexture) api.DrawBindTexture(replacementTextureId);
    if (api.DrawDeleteTexture && transientTextureId > 0 &&
        transientTextureId != replacementTextureId) {
      api.DrawDeleteTexture(transientTextureId);
    }
    transientTextureId = 0;
    LOG_WARN("Native occlusion phase1 bridge exception; failed closed: {}", error.what());
  } catch (...) {
    if (api.DrawBindTexture) api.DrawBindTexture(replacementTextureId);
    if (api.DrawDeleteTexture && transientTextureId > 0 &&
        transientTextureId != replacementTextureId) {
      api.DrawDeleteTexture(transientTextureId);
    }
    transientTextureId = 0;
    LOG_WARN("Native occlusion phase1 bridge exception; failed closed");
  }
  return false;
}

void finish_masked_texture(const EngineTextureApi& api, int nativeTextureId,
                           int transientTextureId) noexcept {
  if (api.DrawBindTexture && nativeTextureId > 0) api.DrawBindTexture(nativeTextureId);
  if (api.DrawDeleteTexture && transientTextureId > 0 &&
      transientTextureId != nativeTextureId) {
    api.DrawDeleteTexture(transientTextureId);
  }
}

void shutdown() noexcept {
  try {
    if (g_context && game::gl::current_context() == g_context) {
      auto& gl = game::gl::get_gl_functions();
      if (g_framebuffer && gl.glDeleteFramebuffers) {
        gl.glDeleteFramebuffers(1, &g_framebuffer);
      }
      if (g_maskTexture && gl.glDeleteTextures) {
        gl.glDeleteTextures(1, &g_maskTexture);
      }
      if (g_vao && gl.glDeleteVertexArrays) gl.glDeleteVertexArrays(1, &g_vao);
      if (g_program && gl.glDeleteProgram) gl.glDeleteProgram(g_program);
    }
  } catch (...) {
  }
  forget_resources();
  g_failureLogged = false;
  g_activeLogged = false;
}
}  // namespace iee::native_occlusion_bridge
