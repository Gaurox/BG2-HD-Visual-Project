#include "post_process.h"

#include <windows.h>

#include <atomic>
#include <string>

#include "iee/core/logger.h"
#include "iee/game/opengl_types.h"

namespace iee::post {
namespace {
using game::gl::OpenGLFunctions;

constexpr unsigned VERTEX_SHADER = 0x8B31;
constexpr unsigned FRAGMENT_SHADER = 0x8B30;
constexpr unsigned COMPILE_STATUS = 0x8B81;
constexpr unsigned LINK_STATUS = 0x8B82;
constexpr unsigned INFO_LOG_LENGTH = 0x8B84;

std::atomic<bool> g_enabled{false};
HGLRC g_context{};
unsigned g_program{};
unsigned g_texture{};
unsigned g_vao{};
int g_sourceUniform{-1};
int g_inverseResolutionUniform{-1};
int g_width{};
int g_height{};
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

// Classic direction-aware FXAA. This pass works in display space on the
// already assembled frame, which is exactly what the per-tile fpSEAM tests
// could not do.
constexpr const char* FRAGMENT_SOURCE = R"glsl(
#version 330 core
in vec2 vUv;
out vec4 outColor;

uniform sampler2D uSource;
uniform vec2 uInverseResolution;

float luma(vec3 rgb) {
    return dot(rgb, vec3(0.299, 0.587, 0.114));
}

void main() {
    vec3 rgbNW = texture(uSource, vUv + vec2(-1.0, -1.0) * uInverseResolution).rgb;
    vec3 rgbNE = texture(uSource, vUv + vec2( 1.0, -1.0) * uInverseResolution).rgb;
    vec3 rgbSW = texture(uSource, vUv + vec2(-1.0,  1.0) * uInverseResolution).rgb;
    vec3 rgbSE = texture(uSource, vUv + vec2( 1.0,  1.0) * uInverseResolution).rgb;
    vec4 center = texture(uSource, vUv);

    float lumaNW = luma(rgbNW);
    float lumaNE = luma(rgbNE);
    float lumaSW = luma(rgbSW);
    float lumaSE = luma(rgbSE);
    float lumaM = luma(center.rgb);
    float lumaMin = min(lumaM, min(min(lumaNW, lumaNE), min(lumaSW, lumaSE)));
    float lumaMax = max(lumaM, max(max(lumaNW, lumaNE), max(lumaSW, lumaSE)));

    vec2 direction;
    direction.x = -((lumaNW + lumaNE) - (lumaSW + lumaSE));
    direction.y =  ((lumaNW + lumaSW) - (lumaNE + lumaSE));

    float directionReduce = max(
        (lumaNW + lumaNE + lumaSW + lumaSE) * (0.25 * 0.0312),
        1.0 / 128.0
    );
    float reciprocalDirectionMin = 1.0 /
        (min(abs(direction.x), abs(direction.y)) + directionReduce);
    direction = clamp(direction * reciprocalDirectionMin, vec2(-8.0), vec2(8.0))
        * uInverseResolution;

    vec3 rgbA = 0.5 * (
        texture(uSource, vUv + direction * (1.0 / 3.0 - 0.5)).rgb +
        texture(uSource, vUv + direction * (2.0 / 3.0 - 0.5)).rgb
    );
    vec3 rgbB = rgbA * 0.5 + 0.25 * (
        texture(uSource, vUv + direction * -0.5).rgb +
        texture(uSource, vUv + direction *  0.5).rgb
    );

    float lumaB = luma(rgbB);
    vec3 filtered = (lumaB < lumaMin || lumaB > lumaMax) ? rgbA : rgbB;
    outColor = vec4(filtered, center.a);
}
)glsl";

struct StateSnapshot {
  int framebuffer{};
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

void set_capability(const OpenGLFunctions& gl, unsigned capability, bool enabled) noexcept {
  if (enabled)
    gl.glEnable(capability);
  else
    gl.glDisable(capability);
}

bool capture_state(const OpenGLFunctions& gl, StateSnapshot& state) noexcept {
  if (!gl.glGetIntegerv || !gl.glIsEnabled || !gl.glActiveTexture) return false;
  gl.glGetIntegerv(game::gl::FRAMEBUFFER_BINDING, &state.framebuffer);
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

void restore_state(const OpenGLFunctions& gl, const StateSnapshot& state) noexcept {
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
  LOG_ERROR("Full-frame FXAA shader compilation failed: {}", shader_log(gl, shader));
  gl.glDeleteShader(shader);
  return 0;
}

void forget_resources() noexcept {
  g_context = nullptr;
  g_program = 0;
  g_texture = 0;
  g_vao = 0;
  g_sourceUniform = -1;
  g_inverseResolutionUniform = -1;
  g_width = 0;
  g_height = 0;
}

bool initialize_resources(const OpenGLFunctions& gl, HGLRC context) {
  if (!gl.shaderObjectsAvailable || !gl.shaderIntrospectionAvailable || !gl.uniformApiAvailable ||
      !gl.textureUploadAvailable || !gl.glCopyTexSubImage2D || !gl.glGenVertexArrays ||
      !gl.glBindVertexArray || !gl.glDeleteVertexArrays || !gl.glDrawArrays || !gl.glIsEnabled ||
      !gl.glEnable || !gl.glDisable) {
    LOG_ERROR("Full-frame FXAA unavailable: required OpenGL entry points are missing");
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
    LOG_ERROR("Full-frame FXAA program link failed: {}", program_log(gl, program));
    gl.glDeleteProgram(program);
    return false;
  }

  unsigned texture = 0;
  unsigned vao = 0;
  gl.glGenTextures(1, &texture);
  gl.glGenVertexArrays(1, &vao);
  if (!texture || !vao) {
    if (texture) gl.glDeleteTextures(1, &texture);
    if (vao) gl.glDeleteVertexArrays(1, &vao);
    gl.glDeleteProgram(program);
    LOG_ERROR("Full-frame FXAA could not allocate its texture or vertex array");
    return false;
  }

  g_context = context;
  g_program = program;
  g_texture = texture;
  g_vao = vao;
  g_sourceUniform = gl.glGetUniformLocation(program, "uSource");
  g_inverseResolutionUniform = gl.glGetUniformLocation(program, "uInverseResolution");
  return true;
}

bool ensure_texture_size(const OpenGLFunctions& gl, int width, int height) {
  if (width == g_width && height == g_height) return true;
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
  if (!game::gl::check_error("full-frame FXAA texture allocation")) return false;
  g_width = width;
  g_height = height;
  LOG_INFO("Full-frame FXAA target allocated: {}x{}", width, height);
  return true;
}
}  // namespace

void configure(bool enabled) noexcept {
  g_enabled.store(enabled, std::memory_order_release);
  if (enabled) LOG_INFO("Diagnostic full-frame FXAA enabled (world + UI)");
}

void apply_frame_fxaa() noexcept {
  if (!g_enabled.load(std::memory_order_acquire)) return;

  try {
    const HGLRC context = game::gl::current_context();
    if (!context) return;
    const auto& gl = game::gl::get_gl_functions();

    StateSnapshot state{};
    if (!capture_state(gl, state)) return;
    if (state.framebuffer != 0) {
      restore_state(gl, state);
      return;
    }

    int viewport[4]{};
    gl.glGetIntegerv(game::gl::VIEWPORT, viewport);
    const int width = viewport[2];
    const int height = viewport[3];
    if (width <= 0 || height <= 0) {
      restore_state(gl, state);
      return;
    }

    if (g_context && g_context != context) {
      // The old context owns the old names and is no longer current. Forget
      // them rather than issuing deletes against the replacement context.
      forget_resources();
    }
    if (!g_program && !initialize_resources(gl, context)) {
      restore_state(gl, state);
      if (!g_loggedFailure) {
        LOG_ERROR("Diagnostic full-frame FXAA initialization failed; pass disabled for this run");
        g_loggedFailure = true;
      }
      return;
    }
    if (!ensure_texture_size(gl, width, height)) {
      restore_state(gl, state);
      return;
    }

    game::gl::discard_errors();
    gl.glBindTexture(game::gl::TEXTURE_2D, g_texture);
    gl.glCopyTexSubImage2D(game::gl::TEXTURE_2D, 0, 0, 0, viewport[0], viewport[1], width, height);

    gl.glDisable(game::gl::BLEND);
    gl.glDisable(game::gl::CULL_FACE);
    gl.glDisable(game::gl::DEPTH_TEST);
    gl.glDisable(game::gl::SCISSOR_TEST);
    gl.glDisable(game::gl::STENCIL_TEST);
    gl.glDisable(game::gl::FRAMEBUFFER_SRGB);
    gl.glUseProgram(g_program);
    gl.glUniform1i(g_sourceUniform, 0);
    gl.glUniform2f(g_inverseResolutionUniform, 1.0f / static_cast<float>(width),
                   1.0f / static_cast<float>(height));
    gl.glBindVertexArray(g_vao);
    gl.glDrawArrays(game::gl::TRIANGLES, 0, 3);
    const bool succeeded = game::gl::check_error("full-frame FXAA draw");
    restore_state(gl, state);

    if (succeeded && !g_loggedActive) {
      LOG_INFO("Diagnostic full-frame FXAA is active at the swap boundary");
      g_loggedActive = true;
    }
  } catch (...) {
    if (!g_loggedFailure) {
      LOG_ERROR("Diagnostic full-frame FXAA raised an unexpected exception");
      g_loggedFailure = true;
    }
  }
}

void release_resources() noexcept {
  try {
    if (g_context && game::gl::current_context() == g_context) {
      const auto& gl = game::gl::get_gl_functions();
      if (g_vao && gl.glDeleteVertexArrays) gl.glDeleteVertexArrays(1, &g_vao);
      if (g_texture && gl.glDeleteTextures) gl.glDeleteTextures(1, &g_texture);
      if (g_program && gl.glDeleteProgram) gl.glDeleteProgram(g_program);
    }
  } catch (...) {
  }
  forget_resources();
  g_loggedActive = false;
  g_loggedFailure = false;
}

}  // namespace iee::post
