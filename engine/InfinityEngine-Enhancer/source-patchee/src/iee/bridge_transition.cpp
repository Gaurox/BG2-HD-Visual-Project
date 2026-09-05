#include "bridge_transition.h"

#include <windows.h>
#include <mmsystem.h>
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>

#include <algorithm>
#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <filesystem>
#include <fstream>
#include <memory>
#include <mutex>
#include <string>
#include <utility>
#include <vector>

#include "iee/core/logger.h"
#include "iee/frame_hook.h"
#include "iee/game/opengl_types.h"

namespace iee::bridge {
namespace {

constexpr wchar_t kForwardVideoName[] = L"BRIDGE01-classic-2048-audio.mp4";
constexpr wchar_t kReverseVideoName[] = L"BRIDGE01-classic-2048-reverse.mp4";
constexpr wchar_t kForwardAudioName[] = L"BRIDGE01-classic-audio.wav";
constexpr wchar_t kReverseAudioName[] = L"BRIDGE01-classic-audio-reverse.wav";
constexpr wchar_t kClosedHoldFrameName[] = L"BRIDGE01-classic-2048-closed.bgra";
constexpr wchar_t kOpenHoldFrameName[] = L"BRIDGE01-classic-2048-open.bgra";
constexpr wchar_t kAudioAlias[] = L"IEEBridgeTransition";
constexpr std::size_t kFrameCacheLimit = 8;
constexpr int kFrameCount = 124;
constexpr int kLastFrame = kFrameCount - 1;
constexpr int kAssetWidth = 2048;
constexpr int kAssetHeight = 2048;
constexpr std::size_t kHoldFrameBytes =
    static_cast<std::size_t>(kAssetWidth) * kAssetHeight * 4u;
constexpr std::int64_t kHundredNanosecondsPerSecond = 10'000'000;
constexpr std::int64_t kFrameHoldHundredNanoseconds = kHundredNanosecondsPerSecond / 24;
constexpr DWORD kFirstVideoStream = static_cast<DWORD>(MF_SOURCE_READER_FIRST_VIDEO_STREAM);
constexpr float kWorldX = 2848.0f;
constexpr float kWorldY = 1984.0f;
constexpr float kWorldWidth = 512.0f;
constexpr float kWorldHeight = 512.0f;

constexpr unsigned kVertexShader = 0x8B31;
constexpr unsigned kFragmentShader = 0x8B30;
constexpr unsigned kCompileStatus = 0x8B81;
constexpr unsigned kLinkStatus = 0x8B82;
constexpr unsigned kInfoLogLength = 0x8B84;

enum class Direction : std::uint8_t { Opening, Closing };
enum class RenderedDoorState : std::uint8_t { Unknown, Open, Closed };

// AR1300.WED / BRIDGE01 owns these base-overlay resource indices. Primary
// indices are the lowered bridge; secondary indices are the raised bridge.
// Watching the final resource selected by CInfTileSet follows the exact state
// the player sees, including script-driven CloseDoor actions.
constexpr RenderedDoorState rendered_door_state_for_tile(int tileIndex) noexcept {
  if ((tileIndex >= 2527 && tileIndex <= 2528) ||
      (tileIndex >= 2606 && tileIndex <= 2608) ||
      (tileIndex >= 2685 && tileIndex <= 2689) ||
      (tileIndex >= 2765 && tileIndex <= 2769) ||
      (tileIndex >= 2845 && tileIndex <= 2850) ||
      (tileIndex >= 2925 && tileIndex <= 2931) ||
      (tileIndex >= 3007 && tileIndex <= 3010) || tileIndex == 3089) {
    return RenderedDoorState::Open;
  }
  if (tileIndex >= 4840 && tileIndex <= 4873 && tileIndex != 4872) {
    return RenderedDoorState::Closed;
  }
  return RenderedDoorState::Unknown;
}

constexpr int asset_frame_for(Direction direction, int logicalFrame) noexcept {
  return direction == Direction::Opening ? logicalFrame : kLastFrame - logicalFrame;
}

constexpr int logical_frame_for(Direction direction, int assetFrame) noexcept {
  return direction == Direction::Opening ? assetFrame : kLastFrame - assetFrame;
}

constexpr std::int64_t timestamp_for_frame(int frameIndex) noexcept {
  return static_cast<std::int64_t>(frameIndex) * kHundredNanosecondsPerSecond / 24;
}

constexpr const char* direction_name(Direction direction) noexcept {
  return direction == Direction::Opening ? "opening" : "closing";
}

static_assert(asset_frame_for(Direction::Opening, 25) == 25);
static_assert(asset_frame_for(Direction::Closing, 25) == 98);
static_assert(logical_frame_for(Direction::Closing, 98) == 25);
static_assert(rendered_door_state_for_tile(2528) == RenderedDoorState::Open);
static_assert(rendered_door_state_for_tile(4841) == RenderedDoorState::Closed);
// Cell 3006 has WED secondary=-1 and is rendered in both door states. It must
// never vote "open" while the other BRIDGE01 cells select their closed tiles.
static_assert(rendered_door_state_for_tile(3006) == RenderedDoorState::Unknown);
static_assert(rendered_door_state_for_tile(4872) == RenderedDoorState::Unknown);

struct VideoFrame {
  int width{};
  int height{};
  std::int64_t timestamp{};
  int assetFrame{-1};
  std::vector<std::uint8_t> bgra;
};

struct AudioUpdate {
  bool stop{};
  bool start{};
  Direction direction{Direction::Opening};
  int assetFrame{};
};

struct ViewState {
  area::ViewTransform transform{};
  bool valid{};
  bool ar1300{};
};

// CPU decoder state.  Only its queue is shared with the render thread.
std::mutex g_decodeMutex;
std::condition_variable g_decodeWake;
detail::ProcessLifetimeWorker g_decodeWorker;
std::filesystem::path g_forwardVideoPath;
std::filesystem::path g_reverseVideoPath;
std::filesystem::path g_forwardAudioPath;
std::filesystem::path g_reverseAudioPath;
std::shared_ptr<const VideoFrame> g_closedHoldFrame;
std::shared_ptr<const VideoFrame> g_openHoldFrame;
std::deque<std::shared_ptr<const VideoFrame>> g_decodedFrames;
std::uint64_t g_requestedSerial{};
Direction g_requestedDirection{Direction::Opening};
int g_requestedStartLogicalFrame{};
bool g_requestedActive{};
std::uint64_t g_handledSerial{};
std::uint64_t g_streamEndedSerial{};
std::uint64_t g_failedSerial{};
bool g_stopping{};
bool g_mediaFoundationStarted{};
std::atomic<bool> g_ready{false};

// Render-thread-owned playback state.  request() may be called from another
// thread, so the serial is sampled while holding g_decodeMutex.
std::uint64_t g_renderSerial{};
Direction g_renderDirection{Direction::Opening};
int g_renderStartLogicalFrame{};
int g_renderStartAssetFrame{};
bool g_playing{};
bool g_waitingForStart{};
std::int64_t g_playStartTicks{};
std::shared_ptr<const VideoFrame> g_displayFrame;
int g_displayLogicalFrame{-1};
bool g_renderedDoorStateKnown{};
bool g_renderedDoorOpen{};
bool g_audioAliasOpen{};
ViewState g_view;

// Render-thread-owned GL resources.
HGLRC g_context{};
unsigned g_program{};
unsigned g_texture{};
unsigned g_vao{};
int g_sourceUniform{-1};
int g_rectOriginUniform{-1};
int g_rectSizeUniform{-1};
int g_viewportUniform{-1};
int g_textureWidth{};
int g_textureHeight{};
bool g_loggedActive{};
bool g_loggedFailure{};
bool g_loggedGeometry{};

bool load_hold_frame(const std::filesystem::path& path, int logicalFrame,
                     std::shared_ptr<const VideoFrame>& out) {
  if (!std::filesystem::is_regular_file(path) ||
      std::filesystem::file_size(path) != kHoldFrameBytes) {
    return false;
  }
  auto frame = std::make_shared<VideoFrame>();
  frame->width = kAssetWidth;
  frame->height = kAssetHeight;
  frame->timestamp = timestamp_for_frame(logicalFrame);
  frame->assetFrame = logicalFrame;
  frame->bgra.resize(kHoldFrameBytes);
  std::ifstream stream(path, std::ios::binary);
  if (!stream.read(reinterpret_cast<char*>(frame->bgra.data()),
                   static_cast<std::streamsize>(frame->bgra.size()))) {
    return false;
  }
  out = std::move(frame);
  return true;
}

constexpr const char* kVertexSource = R"glsl(
#version 330 core
out vec2 vUv;
uniform vec2 uRectOrigin;
uniform vec2 uRectSize;
uniform vec2 uViewportSize;

void main() {
    const vec2 positions[6] = vec2[6](
        vec2(0.0, 0.0), vec2(1.0, 0.0), vec2(0.0, 1.0),
        vec2(0.0, 1.0), vec2(1.0, 0.0), vec2(1.0, 1.0)
    );
    vec2 local = positions[gl_VertexID];
    vec2 pixel = uRectOrigin + local * uRectSize;
    vec2 clip = vec2(pixel.x / uViewportSize.x * 2.0 - 1.0,
                     1.0 - pixel.y / uViewportSize.y * 2.0);
    gl_Position = vec4(clip, 0.0, 1.0);
    // Media Foundation's RGB32 buffer begins with its top scanline. OpenGL
    // treats that row as texture-v=0, so preserve the original top-to-bottom
    // image by mapping v=0 to the top screen edge.
    vUv = local;
}
)glsl";

constexpr const char* kFragmentSource = R"glsl(
#version 330 core
in vec2 vUv;
out vec4 outColor;
uniform sampler2D uSource;
uniform vec2 uRectSize;
uniform vec2 uViewportSize;

// Spatial presentation gain measured from two consecutive, pixel-aligned
// screenshots: native AR1300 followed by the first transition frame.  BG2EE's
// baked lighting is not uniform over this world rectangle; the sunlit upper
// gate needs substantially more energy than the shaded lower approach.
const float kAr1300Lighting[64] = float[](
    1.357, 1.770, 1.759, 1.745, 1.274, 0.956, 0.955, 0.957,
    1.689, 1.816, 1.783, 0.963, 0.967, 0.962, 0.968, 0.956,
    0.958, 1.402, 1.309, 1.188, 0.947, 0.955, 0.991, 0.945,
    0.940, 0.954, 0.856, 0.937, 0.961, 1.080, 1.053, 1.028,
    0.957, 0.905, 0.939, 1.018, 0.961, 1.028, 0.988, 1.057,
    0.951, 0.957, 0.970, 0.955, 0.951, 0.939, 0.915, 0.976,
    0.963, 0.949, 0.961, 0.962, 0.957, 0.899, 0.895, 0.892,
    0.984, 0.945, 0.979, 0.973, 0.946, 0.967, 0.892, 0.930
);

float ar1300LightingGain(vec2 uv) {
    vec2 grid = clamp(uv, vec2(0.0), vec2(1.0)) * 7.0;
    ivec2 cell = ivec2(min(floor(grid), vec2(6.0)));
    vec2 blend = grid - vec2(cell);
    int topLeft = cell.y * 8 + cell.x;
    float top = mix(kAr1300Lighting[topLeft],
                    kAr1300Lighting[topLeft + 1], blend.x);
    float bottom = mix(kAr1300Lighting[topLeft + 8],
                       kAr1300Lighting[topLeft + 9], blend.x);
    return mix(top, bottom, blend.y);
}

void main() {
    // The source bridge frames need the same AR1300 presentation transform as
    // the native map. These coefficients
    // were fitted from matching pixels in the native closed-bridge crop and an
    // in-game capture of AR1300.  Apply the same transform to every decoded
    // frame; no spatial mask or animation-phase adjustment is involved.
    vec3 source = texture(uSource, vUv).rgb;
    vec3 presentationSource = pow(max(source, vec3(0.0)), vec3(1.05));
    mat3 ar1300Presentation = mat3(
         0.612465,  0.177050,  0.090400,
        -0.114695,  0.305485, -0.001538,
        -0.007613,  0.007816,  0.418410
    );
    vec3 graded = ar1300Presentation * presentationSource +
                  vec3(0.018913, 0.014819, 0.002986);
    graded *= ar1300LightingGain(vUv);
    vec2 edgePixels = min(vUv, vec2(1.0) - vUv) * uRectSize;
    float edgeDistance = min(edgePixels.x, edgePixels.y);
    float alpha = smoothstep(0.0, 64.0, edgeDistance);
    outColor = vec4(clamp(graded, 0.0, 1.0), alpha);
}
)glsl";

struct DrawState {
  int framebuffer{};
  int program{};
  int activeTexture{};
  int texture0Binding{};
  int vertexArray{};
  int blendSource{};
  int blendDestination{};
  bool blend{};
  bool cull{};
  bool depth{};
  bool scissor{};
  bool stencil{};
  bool framebufferSrgb{};
};

template <typename T>
void release_com(T*& value) noexcept {
  if (value) value->Release();
  value = nullptr;
}

void stop_audio() noexcept {
  if (!g_audioAliasOpen) return;
  const std::wstring stopCommand = std::wstring(L"stop ") + kAudioAlias;
  const std::wstring closeCommand = std::wstring(L"close ") + kAudioAlias;
  (void)mciSendStringW(stopCommand.c_str(), nullptr, 0, nullptr);
  (void)mciSendStringW(closeCommand.c_str(), nullptr, 0, nullptr);
  g_audioAliasOpen = false;
}

void start_audio(Direction direction, int assetFrame) noexcept {
  try {
    stop_audio();
    const auto& path = direction == Direction::Opening ? g_forwardAudioPath : g_reverseAudioPath;
    if (!std::filesystem::is_regular_file(path)) return;

    const std::wstring openCommand = std::wstring(L"open \"") + path.wstring() +
                                     L"\" type waveaudio alias " + kAudioAlias;
    MCIERROR error = mciSendStringW(openCommand.c_str(), nullptr, 0, nullptr);
    if (error != 0) {
      LOG_WARN("AR1300 bridge transition audio could not open (MCI error {})",
               static_cast<unsigned>(error));
      return;
    }
    g_audioAliasOpen = true;

    const std::wstring formatCommand =
        std::wstring(L"set ") + kAudioAlias + L" time format milliseconds";
    error = mciSendStringW(formatCommand.c_str(), nullptr, 0, nullptr);
    const auto milliseconds = timestamp_for_frame(std::clamp(assetFrame, 0, kLastFrame)) / 10'000;
    const std::wstring playCommand = std::wstring(L"play ") + kAudioAlias + L" from " +
                                     std::to_wstring(milliseconds);
    if (error == 0) error = mciSendStringW(playCommand.c_str(), nullptr, 0, nullptr);
    if (error != 0) {
      LOG_WARN("AR1300 bridge transition audio could not seek/play (MCI error {})",
               static_cast<unsigned>(error));
      stop_audio();
    }
  } catch (...) {
    stop_audio();
  }
}

bool submit_request_locked(Direction direction, int startLogicalFrame, const char* reason) {
  ++g_requestedSerial;
  g_requestedDirection = direction;
  g_requestedStartLogicalFrame = std::clamp(startLogicalFrame, 0, kLastFrame);
  g_requestedActive = true;
  g_decodedFrames.clear();
  g_streamEndedSerial = 0;
  g_failedSerial = 0;
  g_decodeWake.notify_all();
  LOG_INFO("AR1300 bridge transition requested: {}, logical frame {}, serial {}, source={}",
           direction_name(direction), g_requestedStartLogicalFrame, g_requestedSerial, reason);
  return true;
}

bool submit_request(Direction direction, int startLogicalFrame, const char* reason) noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return false;
  try {
    std::lock_guard lock(g_decodeMutex);
    return submit_request_locked(direction, startLogicalFrame, reason);
  } catch (...) {
    return false;
  }
}

void set_capability(const game::gl::OpenGLFunctions& gl, unsigned capability, bool enabled) noexcept {
  if (enabled)
    gl.glEnable(capability);
  else
    gl.glDisable(capability);
}

bool capture_draw_state(const game::gl::OpenGLFunctions& gl, DrawState& state) noexcept {
  if (!gl.glGetIntegerv || !gl.glIsEnabled || !gl.glActiveTexture || !gl.glBindTexture ||
      !gl.glBindVertexArray || !gl.glUseProgram || !gl.glBlendFunc) {
    return false;
  }
  gl.glGetIntegerv(game::gl::FRAMEBUFFER_BINDING, &state.framebuffer);
  gl.glGetIntegerv(game::gl::CURRENT_PROGRAM, &state.program);
  gl.glGetIntegerv(game::gl::ACTIVE_TEXTURE, &state.activeTexture);
  gl.glGetIntegerv(game::gl::VERTEX_ARRAY_BINDING, &state.vertexArray);
  gl.glGetIntegerv(game::gl::BLEND_SRC, &state.blendSource);
  gl.glGetIntegerv(game::gl::BLEND_DST, &state.blendDestination);
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

void restore_draw_state(const game::gl::OpenGLFunctions& gl, const DrawState& state) noexcept {
  gl.glBlendFunc(static_cast<unsigned>(state.blendSource),
                 static_cast<unsigned>(state.blendDestination));
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

std::string shader_log(const game::gl::OpenGLFunctions& gl, unsigned shader) {
  int length = 0;
  gl.glGetShaderiv(shader, kInfoLogLength, &length);
  if (length <= 1) return {};
  std::string result(static_cast<std::size_t>(length), '\0');
  int written = 0;
  gl.glGetShaderInfoLog(shader, length, &written, result.data());
  if (written >= 0 && written < length) result.resize(static_cast<std::size_t>(written));
  return result;
}

std::string program_log(const game::gl::OpenGLFunctions& gl, unsigned program) {
  int length = 0;
  gl.glGetProgramiv(program, kInfoLogLength, &length);
  if (length <= 1) return {};
  std::string result(static_cast<std::size_t>(length), '\0');
  int written = 0;
  gl.glGetProgramInfoLog(program, length, &written, result.data());
  if (written >= 0 && written < length) result.resize(static_cast<std::size_t>(written));
  return result;
}

unsigned compile_shader(const game::gl::OpenGLFunctions& gl, unsigned type, const char* source) {
  const unsigned shader = gl.glCreateShader(type);
  if (!shader) return 0;
  gl.glShaderSource(shader, 1, &source, nullptr);
  gl.glCompileShader(shader);
  int compiled = 0;
  gl.glGetShaderiv(shader, kCompileStatus, &compiled);
  if (compiled) return shader;
  LOG_ERROR("AR1300 bridge transition shader compilation failed: {}", shader_log(gl, shader));
  gl.glDeleteShader(shader);
  return 0;
}

void forget_gl_resources() noexcept {
  g_context = nullptr;
  g_program = 0;
  g_texture = 0;
  g_vao = 0;
  g_sourceUniform = -1;
  g_rectOriginUniform = -1;
  g_rectSizeUniform = -1;
  g_viewportUniform = -1;
  g_textureWidth = 0;
  g_textureHeight = 0;
}

bool initialize_gl_resources(const game::gl::OpenGLFunctions& gl, HGLRC context) {
  if (!gl.shaderObjectsAvailable || !gl.shaderIntrospectionAvailable || !gl.uniformApiAvailable ||
      !gl.textureUploadAvailable || !gl.glTexSubImage2D || !gl.glGenVertexArrays ||
      !gl.glBindVertexArray || !gl.glDeleteVertexArrays || !gl.glDrawArrays || !gl.glIsEnabled ||
      !gl.glEnable || !gl.glDisable || !gl.glBlendFunc) {
    LOG_ERROR("AR1300 bridge transition unavailable: required OpenGL entry points are missing");
    return false;
  }

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
    LOG_ERROR("AR1300 bridge transition shader link failed: {}", program_log(gl, program));
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
    LOG_ERROR("AR1300 bridge transition could not allocate OpenGL objects");
    return false;
  }

  g_context = context;
  g_program = program;
  g_texture = texture;
  g_vao = vao;
  g_sourceUniform = gl.glGetUniformLocation(program, "uSource");
  g_rectOriginUniform = gl.glGetUniformLocation(program, "uRectOrigin");
  g_rectSizeUniform = gl.glGetUniformLocation(program, "uRectSize");
  g_viewportUniform = gl.glGetUniformLocation(program, "uViewportSize");
  LOG_INFO("AR1300 bridge transition renderer initialized");
  return true;
}

bool upload_frame(const game::gl::OpenGLFunctions& gl, const VideoFrame& frame) noexcept {
  if (frame.width <= 0 || frame.height <= 0 || frame.bgra.size() !=
          static_cast<std::size_t>(frame.width) * static_cast<std::size_t>(frame.height) * 4u) {
    return false;
  }
  int unpackAlignment = 4;
  gl.glGetIntegerv(game::gl::UNPACK_ALIGNMENT, &unpackAlignment);
  game::gl::discard_errors();
  gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, 1);
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
  if (g_textureWidth != frame.width || g_textureHeight != frame.height) {
    gl.glTexImage2D(game::gl::TEXTURE_2D, 0, static_cast<int>(game::gl::RGBA8), frame.width,
                    frame.height, 0, game::gl::BGRA, game::gl::UNSIGNED_BYTE, nullptr);
    g_textureWidth = frame.width;
    g_textureHeight = frame.height;
  }
  gl.glTexSubImage2D(game::gl::TEXTURE_2D, 0, 0, 0, frame.width, frame.height, game::gl::BGRA,
                     game::gl::UNSIGNED_BYTE, frame.bgra.data());
  gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT, unpackAlignment);
  return game::gl::check_error("AR1300 bridge transition texture upload");
}

bool queue_frame(std::uint64_t serial, std::shared_ptr<const VideoFrame> frame) {
  std::unique_lock lock(g_decodeMutex);
  g_decodeWake.wait(lock, [&] {
    return g_stopping || serial != g_requestedSerial || g_decodedFrames.size() < kFrameCacheLimit;
  });
  if (g_stopping || serial != g_requestedSerial) return false;
  g_decodedFrames.push_back(std::move(frame));
  g_decodeWake.notify_all();
  return true;
}

bool decode_video(std::uint64_t serial, Direction direction, int startLogicalFrame) {
  CoInitializeEx(nullptr, COINIT_MULTITHREADED);
  IMFSourceReader* reader = nullptr;
  IMFAttributes* readerAttributes = nullptr;
  IMFMediaType* requestedType = nullptr;
  IMFMediaType* actualType = nullptr;
  bool success = false;

  const auto cleanup = [&] {
    release_com(actualType);
    release_com(requestedType);
    release_com(readerAttributes);
    release_com(reader);
    CoUninitialize();
  };

  // An H.264 source reader ordinarily exposes an NV12 decoder output.  Ask
  // Media Foundation to insert its software video processor so the reader can
  // produce the RGB32 pixels consumed by our OpenGL upload. Without this
  // attribute, SetCurrentMediaType() rejects this conversion with
  // MF_E_INVALIDMEDIATYPE on the retail Windows decoder.
  HRESULT result = MFCreateAttributes(&readerAttributes, 1);
  if (SUCCEEDED(result)) {
    result = readerAttributes->SetUINT32(MF_SOURCE_READER_ENABLE_VIDEO_PROCESSING, TRUE);
  }
  if (SUCCEEDED(result)) {
    const auto& videoPath =
        direction == Direction::Opening ? g_forwardVideoPath : g_reverseVideoPath;
    result = MFCreateSourceReaderFromURL(videoPath.c_str(), readerAttributes, &reader);
  }
  if (FAILED(result) || !reader) {
    LOG_ERROR("AR1300 bridge transition: cannot open video (HRESULT 0x{:08X})",
              static_cast<unsigned>(result));
    cleanup();
    return false;
  }
  result = MFCreateMediaType(&requestedType);
  if (SUCCEEDED(result)) result = requestedType->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
  if (SUCCEEDED(result)) result = requestedType->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_RGB32);
  if (SUCCEEDED(result)) {
    result = reader->SetCurrentMediaType(kFirstVideoStream, nullptr, requestedType);
  }
  if (SUCCEEDED(result)) {
    result = reader->GetCurrentMediaType(kFirstVideoStream, &actualType);
  }
  UINT32 width = 0;
  UINT32 height = 0;
  UINT32 rawStride = 0;
  if (SUCCEEDED(result)) result = MFGetAttributeSize(actualType, MF_MT_FRAME_SIZE, &width, &height);
  if (SUCCEEDED(result)) (void)actualType->GetUINT32(MF_MT_DEFAULT_STRIDE, &rawStride);
  if (FAILED(result) || width == 0 || height == 0 || width > 4096 || height > 4096) {
    LOG_ERROR("AR1300 bridge transition: unsupported decoded frame format (HRESULT 0x{:08X})",
              static_cast<unsigned>(result));
    cleanup();
    return false;
  }
  const auto stride = rawStride == 0 ? static_cast<LONG>(width * 4)
                                     : static_cast<LONG>(rawStride);
  const int startAssetFrame = asset_frame_for(direction, startLogicalFrame);
  if (startAssetFrame > 0) {
    PROPVARIANT position{};
    position.vt = VT_I8;
    position.hVal.QuadPart = timestamp_for_frame(startAssetFrame);
    result = reader->SetCurrentPosition(GUID_NULL, position);
    if (FAILED(result)) {
      LOG_ERROR("AR1300 bridge transition: seek to asset frame {} failed (HRESULT 0x{:08X})",
                startAssetFrame, static_cast<unsigned>(result));
      cleanup();
      return false;
    }
  }

  for (;;) {
    {
      std::lock_guard lock(g_decodeMutex);
      if (g_stopping || serial != g_requestedSerial) break;
    }
    DWORD streamFlags = 0;
    LONGLONG timestamp = 0;
    IMFSample* sample = nullptr;
    result = reader->ReadSample(kFirstVideoStream, 0, nullptr, &streamFlags,
                                &timestamp, &sample);
    if (FAILED(result)) {
      release_com(sample);
      LOG_ERROR("AR1300 bridge transition: video decode failed (HRESULT 0x{:08X})",
                static_cast<unsigned>(result));
      cleanup();
      return false;
    }
    if ((streamFlags & MF_SOURCE_READERF_ENDOFSTREAM) != 0) {
      release_com(sample);
      success = true;
      break;
    }
    if (!sample) continue;

    const int assetFrame = std::clamp(
        static_cast<int>((timestamp * 24 + kHundredNanosecondsPerSecond / 2) /
                         kHundredNanosecondsPerSecond),
        0, kLastFrame);
    if (assetFrame < startAssetFrame) {
      release_com(sample);
      continue;
    }

    IMFMediaBuffer* buffer = nullptr;
    result = sample->ConvertToContiguousBuffer(&buffer);
    release_com(sample);
    if (FAILED(result) || !buffer) {
      release_com(buffer);
      LOG_ERROR("AR1300 bridge transition: video sample cannot be made contiguous");
      cleanup();
      return false;
    }
    BYTE* data = nullptr;
    DWORD maxLength = 0;
    DWORD currentLength = 0;
    result = buffer->Lock(&data, &maxLength, &currentLength);
    const auto expectedMin = static_cast<std::uint64_t>(width) * static_cast<std::uint64_t>(height) * 4u;
    if (FAILED(result) || !data || currentLength < expectedMin) {
      if (SUCCEEDED(result)) buffer->Unlock();
      release_com(buffer);
      LOG_ERROR("AR1300 bridge transition: decoded frame has an invalid buffer");
      cleanup();
      return false;
    }

    auto frame = std::make_shared<VideoFrame>();
    frame->width = static_cast<int>(width);
    frame->height = static_cast<int>(height);
    frame->timestamp = timestamp;
    frame->assetFrame = assetFrame;
    frame->bgra.resize(static_cast<std::size_t>(width) * static_cast<std::size_t>(height) * 4u);
    const auto rowBytes = static_cast<std::size_t>(width) * 4u;
    for (UINT32 row = 0; row < height; ++row) {
      const auto sourceRow = stride >= 0 ? static_cast<std::ptrdiff_t>(row) * stride
                                         : static_cast<std::ptrdiff_t>(height - 1 - row) * -stride;
      std::copy_n(data + sourceRow, rowBytes, frame->bgra.data() + static_cast<std::size_t>(row) * rowBytes);
    }
    buffer->Unlock();
    release_com(buffer);
    if (!queue_frame(serial, std::move(frame))) break;
  }

  cleanup();
  return success;
}

void decoder_thread_main() noexcept {
  try {
    for (;;) {
      std::uint64_t serial = 0;
      Direction direction = Direction::Opening;
      int startLogicalFrame = 0;
      bool active = false;
      {
        std::unique_lock lock(g_decodeMutex);
        g_decodeWake.wait(lock, [] { return g_stopping || g_requestedSerial != g_handledSerial; });
        if (g_stopping) return;
        serial = g_requestedSerial;
        direction = g_requestedDirection;
        startLogicalFrame = g_requestedStartLogicalFrame;
        active = g_requestedActive;
        g_handledSerial = serial;
        g_streamEndedSerial = 0;
        g_failedSerial = 0;
        g_decodedFrames.clear();
        g_decodeWake.notify_all();
      }
      if (!active) continue;
      const bool success = decode_video(serial, direction, startLogicalFrame);
      std::lock_guard lock(g_decodeMutex);
      if (!g_stopping && serial == g_requestedSerial) {
        if (success)
          g_streamEndedSerial = serial;
        else
          g_failedSerial = serial;
        g_decodeWake.notify_all();
      }
    }
  } catch (...) {
    std::lock_guard lock(g_decodeMutex);
    g_failedSerial = g_requestedSerial;
    g_decodeWake.notify_all();
    LOG_ERROR("AR1300 bridge transition decoder stopped after an unexpected exception");
  }
}

unsigned __stdcall decoder_thread_entry(void*) noexcept {
  decoder_thread_main();
  return 0;
}

bool acquire_playback_frame(std::int64_t nowTicks, std::shared_ptr<const VideoFrame>& out,
                            AudioUpdate& audio) {
  audio = {};
  std::lock_guard lock(g_decodeMutex);
  if (g_renderSerial != g_requestedSerial) {
    g_renderSerial = g_requestedSerial;
    g_renderDirection = g_requestedDirection;
    g_renderStartLogicalFrame = g_requestedStartLogicalFrame;
    g_renderStartAssetFrame =
        asset_frame_for(g_renderDirection, g_renderStartLogicalFrame);
    g_playing = false;
    g_waitingForStart = g_renderSerial != 0 && g_requestedActive;
    g_playStartTicks = 0;
    // Keep the current image visible while the decoder seeks to the matching
    // frame in the opposite stream. It is replaced only when that frame is
    // ready, so a direction change never flashes the native map.
    // For a new transition from rest there is no current video frame to keep:
    // cover the engine's already-switched WED tiles immediately with the old
    // endpoint until Media Foundation produces the first requested sample.
    if (!g_displayFrame && g_requestedActive) {
      if (g_renderStartLogicalFrame == 0 && g_closedHoldFrame) {
        g_displayFrame = g_closedHoldFrame;
        g_displayLogicalFrame = 0;
      } else if (g_renderStartLogicalFrame == kLastFrame && g_openHoldFrame) {
        g_displayFrame = g_openHoldFrame;
        g_displayLogicalFrame = kLastFrame;
      }
    }
    audio.stop = true;
  }
  if (g_renderSerial == 0 || !g_requestedActive) {
    g_displayFrame.reset();
    g_displayLogicalFrame = -1;
    return false;
  }
  if (g_failedSerial == g_renderSerial) {
    g_playing = false;
    g_waitingForStart = false;
    g_displayFrame.reset();
    g_displayLogicalFrame = -1;
    return false;
  }

  if (g_waitingForStart) {
    if (g_decodedFrames.empty()) {
      if (g_displayFrame) {
        out = g_displayFrame;
        return true;
      }
      return false;
    }
    g_displayFrame = g_decodedFrames.front();
    g_decodedFrames.pop_front();
    g_displayLogicalFrame =
        logical_frame_for(g_renderDirection, g_displayFrame->assetFrame);
    g_playStartTicks = nowTicks;
    g_playing = true;
    g_waitingForStart = false;
    audio.start = true;
    audio.direction = g_renderDirection;
    audio.assetFrame = g_displayFrame->assetFrame;
    LOG_INFO("AR1300 bridge transition began: {}, requested logical frame {}, decoded logical frame {}",
             direction_name(g_renderDirection), g_renderStartLogicalFrame,
             g_displayLogicalFrame);
    g_decodeWake.notify_all();
  }

  const auto frequency = frame::clock_frequency();
  if (frequency <= 0 || !g_displayFrame) return false;
  const auto elapsed = nowTicks >= g_playStartTicks ? nowTicks - g_playStartTicks : 0;
  const auto targetTimestamp = timestamp_for_frame(g_renderStartAssetFrame) +
                               elapsed * kHundredNanosecondsPerSecond / frequency;
  while (!g_decodedFrames.empty() &&
         g_decodedFrames.front()->timestamp <= targetTimestamp) {
    g_displayFrame = g_decodedFrames.front();
    g_decodedFrames.pop_front();
    g_displayLogicalFrame =
        logical_frame_for(g_renderDirection, g_displayFrame->assetFrame);
    g_decodeWake.notify_all();
  }
  const bool exhausted = g_streamEndedSerial == g_renderSerial && g_decodedFrames.empty() &&
                         targetTimestamp >=
                             timestamp_for_frame(kLastFrame) + kFrameHoldHundredNanoseconds;
  if (exhausted) {
    g_playing = false;
    g_displayFrame.reset();
    g_displayLogicalFrame = -1;
    audio.stop = true;
    return false;
  }
  out = g_displayFrame;
  return true;
}

bool calculate_rect(const int viewport[4], float& x, float& y, float& width, float& height) noexcept {
  if (!g_view.valid || !g_view.ar1300 || viewport[2] <= 0 || viewport[3] <= 0 ||
      g_view.transform.viewWorldW <= 0.0f || g_view.transform.viewWorldH <= 0.0f) {
    return false;
  }
  // Scale the logical CInfinity world transform into the live GL viewport.
  // Vertex coordinates are local to glViewport: its x/y origin is applied by
  // OpenGL after NDC conversion and must not be added here a second time.
  const float screenWidth = static_cast<float>(viewport[2]);
  const float screenHeight = static_cast<float>(viewport[3]);
  x = (kWorldX - g_view.transform.scrollX) * screenWidth / g_view.transform.viewWorldW;
  y = (kWorldY - g_view.transform.scrollY) * screenHeight / g_view.transform.viewWorldH;
  width = kWorldWidth * screenWidth / g_view.transform.viewWorldW;
  height = kWorldHeight * screenHeight / g_view.transform.viewWorldH;
  return width > 0.0f && height > 0.0f;
}

}  // namespace

bool prepare(const std::filesystem::path& assetDirectory) noexcept {
  shutdown();
  try {
    const auto forwardVideo = assetDirectory / kForwardVideoName;
    const auto reverseVideo = assetDirectory / kReverseVideoName;
    const auto forwardAudio = assetDirectory / kForwardAudioName;
    const auto reverseAudio = assetDirectory / kReverseAudioName;
    const auto closedHoldPath = assetDirectory / kClosedHoldFrameName;
    const auto openHoldPath = assetDirectory / kOpenHoldFrameName;
    if (!std::filesystem::is_regular_file(forwardVideo) ||
        !std::filesystem::is_regular_file(reverseVideo)) {
      LOG_WARN("AR1300 bridge transition disabled: forward or reverse video asset is missing");
      return false;
    }
    std::shared_ptr<const VideoFrame> closedHoldFrame;
    std::shared_ptr<const VideoFrame> openHoldFrame;
    if (!load_hold_frame(closedHoldPath, 0, closedHoldFrame) ||
        !load_hold_frame(openHoldPath, kLastFrame, openHoldFrame)) {
      LOG_WARN("AR1300 bridge transition disabled: a 2048x2048 BGRA hold frame is missing or invalid");
      return false;
    }
    const HRESULT result = MFStartup(MF_VERSION, MFSTARTUP_LITE);
    if (FAILED(result)) {
      LOG_WARN("AR1300 bridge transition disabled: Media Foundation startup failed (HRESULT 0x{:08X})",
               static_cast<unsigned>(result));
      return false;
    }
    g_mediaFoundationStarted = true;
    g_forwardVideoPath = forwardVideo;
    g_reverseVideoPath = reverseVideo;
    g_forwardAudioPath = forwardAudio;
    g_reverseAudioPath = reverseAudio;
    {
      std::lock_guard lock(g_decodeMutex);
      g_stopping = false;
      g_requestedSerial = 0;
      g_requestedDirection = Direction::Opening;
      g_requestedStartLogicalFrame = 0;
      g_requestedActive = false;
      g_handledSerial = 0;
      g_streamEndedSerial = 0;
      g_failedSerial = 0;
      g_decodedFrames.clear();
      g_closedHoldFrame = std::move(closedHoldFrame);
      g_openHoldFrame = std::move(openHoldFrame);
    }
    if (!g_decodeWorker.start(&decoder_thread_entry, nullptr, &g_decodeWorker)) {
      LOG_WARN(
          "AR1300 bridge transition disabled: decoder worker or DLL lifetime guard could not start");
      shutdown();
      return false;
    }
    g_ready.store(true, std::memory_order_release);
    LOG_INFO("AR1300 bridge transition prepared for rendered WED door tracking: {}",
             forwardVideo.string());
    return true;
  } catch (const std::exception& error) {
    LOG_WARN("AR1300 bridge transition disabled: {}", error.what());
  } catch (...) {
    LOG_WARN("AR1300 bridge transition disabled by an unknown initialization failure");
  }
  shutdown();
  return false;
}

void publish_view(const area::ViewTransform& view, bool isAr1300) noexcept {
  g_view.transform = view;
  g_view.valid = view.viewWorldW > 0.0f && view.viewWorldH > 0.0f;
  g_view.ar1300 = isAr1300;
}

void reset_area() noexcept {
  g_view = {};
  try {
    std::lock_guard lock(g_decodeMutex);
    if (g_ready.load(std::memory_order_acquire)) ++g_requestedSerial;
    g_requestedActive = false;
    g_decodedFrames.clear();
    g_streamEndedSerial = 0;
    g_failedSerial = 0;
    g_playing = false;
    g_waitingForStart = false;
    g_displayFrame.reset();
    g_displayLogicalFrame = -1;
    g_renderedDoorStateKnown = false;
    g_renderedDoorOpen = false;
    g_decodeWake.notify_all();
  } catch (...) {
  }
  stop_audio();
}

void observe_rendered_tile(int tileIndex) noexcept {
  if (!g_ready.load(std::memory_order_acquire) || !g_view.ar1300) return;
  const auto state = rendered_door_state_for_tile(tileIndex);
  if (state == RenderedDoorState::Unknown) return;
  const bool open = state == RenderedDoorState::Open;
  try {
    std::lock_guard lock(g_decodeMutex);
    if (!g_renderedDoorStateKnown) {
      g_renderedDoorStateKnown = true;
      g_renderedDoorOpen = open;
      LOG_INFO("AR1300 BRIDGE01 rendered state acquired: {}, tile={}",
               open ? "open" : "closed", tileIndex);
      return;
    }
    if (open == g_renderedDoorOpen) return;

    g_renderedDoorOpen = open;
    const Direction direction = open ? Direction::Opening : Direction::Closing;
    const bool reversing = g_displayLogicalFrame >= 0 && (g_playing || g_waitingForStart);
    const int startLogicalFrame =
        reversing ? g_displayLogicalFrame : (open ? 0 : kLastFrame);
    LOG_INFO("AR1300 BRIDGE01 rendered tile changed to {} (tile={}): {} from logical frame {}",
             open ? "open" : "closed", tileIndex,
             reversing ? "reversing" : "starting", startLogicalFrame);
    (void)submit_request_locked(direction, startLogicalFrame, "rendered-wed-state");
  } catch (...) {
  }
}

bool request() noexcept { return submit_request(Direction::Opening, 0, "F9/export-diagnostic"); }

void render_world_overlay() noexcept {
  if (!g_ready.load(std::memory_order_acquire)) return;
  try {
    static bool f9WasDown = false;
    const bool f9Down = (GetAsyncKeyState(VK_F9) & 0x8000) != 0;
    if (f9Down && !f9WasDown && g_view.ar1300) {
      (void)request();
    }
    f9WasDown = f9Down;
    if (!g_view.ar1300) return;

    std::shared_ptr<const VideoFrame> frame;
    AudioUpdate audio{};
    const bool hasFrame = acquire_playback_frame(frame::clock_ticks(), frame, audio);
    if (audio.stop) stop_audio();
    if (audio.start) start_audio(audio.direction, audio.assetFrame);
    if (!hasFrame || !frame) return;

    const HGLRC context = game::gl::current_context();
    if (!context) return;
    const auto& gl = game::gl::get_gl_functions();
    if (g_context && g_context != context) forget_gl_resources();
    if (!g_program && !initialize_gl_resources(gl, context)) {
      if (!g_loggedFailure) {
        LOG_ERROR("AR1300 bridge transition renderer disabled after an OpenGL initialization failure");
        g_loggedFailure = true;
      }
      return;
    }

    DrawState state{};
    if (!capture_draw_state(gl, state)) return;
    int viewport[4]{};
    gl.glGetIntegerv(game::gl::VIEWPORT, viewport);
    float rectX = 0.0f;
    float rectY = 0.0f;
    float rectWidth = 0.0f;
    float rectHeight = 0.0f;
    if (!calculate_rect(viewport, rectX, rectY, rectWidth, rectHeight) || !upload_frame(gl, *frame)) {
      restore_draw_state(gl, state);
      return;
    }
    if (!g_loggedGeometry) {
      LOG_INFO(
          "AR1300 bridge map target: framebuffer={}, viewport=({}, {}, {}x{}), "
          "rect=({}, {}, {}x{}), scroll=({}, {}), world-view={}x{}",
          state.framebuffer, viewport[0], viewport[1], viewport[2], viewport[3], rectX, rectY,
          rectWidth, rectHeight, g_view.transform.scrollX, g_view.transform.scrollY,
          g_view.transform.viewWorldW, g_view.transform.viewWorldH);
      g_loggedGeometry = true;
    }

    gl.glEnable(game::gl::BLEND);
    gl.glBlendFunc(game::gl::SRC_ALPHA, game::gl::ONE_MINUS_SRC_ALPHA);
    gl.glDisable(game::gl::CULL_FACE);
    gl.glDisable(game::gl::DEPTH_TEST);
    gl.glDisable(game::gl::SCISSOR_TEST);
    gl.glDisable(game::gl::STENCIL_TEST);
    gl.glDisable(game::gl::FRAMEBUFFER_SRGB);
    gl.glActiveTexture(game::gl::TEXTURE0);
    gl.glBindTexture(game::gl::TEXTURE_2D, g_texture);
    gl.glUseProgram(g_program);
    gl.glUniform1i(g_sourceUniform, 0);
    gl.glUniform2f(g_rectOriginUniform, rectX, rectY);
    gl.glUniform2f(g_rectSizeUniform, rectWidth, rectHeight);
    gl.glUniform2f(g_viewportUniform, static_cast<float>(viewport[2]), static_cast<float>(viewport[3]));
    gl.glBindVertexArray(g_vao);
    gl.glDrawArrays(game::gl::TRIANGLES, 0, 6);
    const bool succeeded = game::gl::check_error("AR1300 bridge transition draw");
    restore_draw_state(gl, state);
    if (succeeded && !g_loggedActive) {
      LOG_INFO("AR1300 bridge transition is actively rendering; rendered BRIDGE01 tiles drive it");
      g_loggedActive = true;
    }
  } catch (...) {
    if (!g_loggedFailure) {
      LOG_ERROR("AR1300 bridge transition renderer raised an unexpected exception");
      g_loggedFailure = true;
    }
  }
}

void shutdown() noexcept {
  g_ready.store(false, std::memory_order_release);
  try {
    {
      std::lock_guard lock(g_decodeMutex);
      g_stopping = true;
      g_decodeWake.notify_all();
    }
    const auto joinResult = g_decodeWorker.join();
    if (joinResult == detail::ProcessLifetimeWorker::JoinResult::SelfJoinRejected) {
      LOG_ERROR(
          "AR1300 bridge transition shutdown rejected a decoder self-join; worker state retained");
      return;
    }
    if (joinResult == detail::ProcessLifetimeWorker::JoinResult::WaitFailed) {
      LOG_ERROR(
          "AR1300 bridge transition shutdown could not join the decoder; worker state retained");
      return;
    }
    {
      std::lock_guard lock(g_decodeMutex);
      g_decodedFrames.clear();
      g_requestedSerial = 0;
      g_requestedDirection = Direction::Opening;
      g_requestedStartLogicalFrame = 0;
      g_requestedActive = false;
      g_handledSerial = 0;
      g_streamEndedSerial = 0;
      g_failedSerial = 0;
      g_stopping = false;
    }
    if (g_context && game::gl::current_context() == g_context) {
      const auto& gl = game::gl::get_gl_functions();
      if (g_vao && gl.glDeleteVertexArrays) gl.glDeleteVertexArrays(1, &g_vao);
      if (g_texture && gl.glDeleteTextures) gl.glDeleteTextures(1, &g_texture);
      if (g_program && gl.glDeleteProgram) gl.glDeleteProgram(g_program);
    }
    forget_gl_resources();
    if (g_mediaFoundationStarted) {
      MFShutdown();
      g_mediaFoundationStarted = false;
    }
    stop_audio();
    g_forwardVideoPath.clear();
    g_reverseVideoPath.clear();
    g_forwardAudioPath.clear();
    g_reverseAudioPath.clear();
    g_view = {};
    g_renderSerial = 0;
    g_renderDirection = Direction::Opening;
    g_renderStartLogicalFrame = 0;
    g_renderStartAssetFrame = 0;
    g_playing = false;
    g_waitingForStart = false;
    g_displayFrame.reset();
    g_displayLogicalFrame = -1;
    g_closedHoldFrame.reset();
    g_openHoldFrame.reset();
    g_renderedDoorStateKnown = false;
    g_renderedDoorOpen = false;
    g_loggedActive = false;
    g_loggedFailure = false;
  } catch (...) {
    // The worker has either been joined or remains protected by its DLL
    // self-reference. Never force cleanup from this noexcept boundary.
    return;
  }
  // Must be the final operation: explicit callers still own the normal loader
  // reference, while the worker-only reference is no longer needed.
  (void)g_decodeWorker.release_module_reference();
}

}  // namespace iee::bridge
