#pragma once

#include "iee/game/opengl_types.h"

namespace iee::game {
// Preserve raw GL state around a native queue flush / texture allocation.
// The caller additionally uses DrawPushState/PopState for the native DWORD.
// No fence, readback, framebuffer switch or glFinish is used for synchronization.
class ScopedEffectGlState {
 public:
  ScopedEffectGlState() noexcept : gl_(gl::get_gl_functions()) {
    if ((!gl_.valid && !gl_.initialize()) || !gl_.glGetIntegerv || !gl_.glBindTexture ||
        !gl_.glEnable || !gl_.glDisable || !gl_.glIsEnabled || !gl_.glPixelStorei ||
        !gl_.glViewport || !gl_.glBlendFunc || !gl_.glScissor) return;
    blendSeparate_ = load<BlendSeparate>("glBlendFuncSeparate");
    blendEquation_ = load<BlendEquation>("glBlendEquationSeparate");
    bindBuffer_ = load<BindBuffer>("glBindBuffer");
    colorMask_ = load<ColorMask>("glColorMask");
    depthMask_ = load<DepthMask>("glDepthMask");
    if (!colorMask_ || !depthMask_) return;
    gl_.glGetIntegerv(gl::VIEWPORT, viewport_);
    gl_.glGetIntegerv(0x0C10, scissor_);
    gl_.glGetIntegerv(0x0C23, color_);
    gl_.glGetIntegerv(0x0B72, &depthWrite_);
    const unsigned unpack[] = {gl::UNPACK_ALIGNMENT, gl::UNPACK_ROW_LENGTH,
                               gl::UNPACK_SKIP_ROWS, gl::UNPACK_SKIP_PIXELS};
    for (int i = 0; i < 4; ++i) gl_.glGetIntegerv(unpack[i], &unpack_[i]);
    for (int i = 0; i < 6; ++i) enabled_[i] = gl_.glIsEnabled(caps_[i]) != 0;
    if (blendSeparate_) {
      gl_.glGetIntegerv(0x80C9, &blend_[0]); gl_.glGetIntegerv(0x80C8, &blend_[1]);
      gl_.glGetIntegerv(0x80CB, &blend_[2]); gl_.glGetIntegerv(0x80CA, &blend_[3]);
    } else {
      gl_.glGetIntegerv(0x0BE1, &blend_[0]); gl_.glGetIntegerv(0x0BE0, &blend_[1]);
    }
    if (blendEquation_) {
      gl_.glGetIntegerv(0x8009, &equation_[0]); gl_.glGetIntegerv(0x883D, &equation_[1]);
    }
    if (gl_.glBindFramebuffer) {
      gl_.glGetIntegerv(gl::FRAMEBUFFER_BINDING, &framebuffer_);
      gl_.glGetIntegerv(0x8CAA, &readFramebuffer_);
    }
    if (gl_.glBindVertexArray) gl_.glGetIntegerv(gl::VERTEX_ARRAY_BINDING, &vao_);
    if (gl_.glUseProgram) gl_.glGetIntegerv(gl::CURRENT_PROGRAM, &program_);
    if (bindBuffer_) {
      gl_.glGetIntegerv(0x8894, &arrayBuffer_);
      gl_.glGetIntegerv(0x8895, &elementBuffer_);
      gl_.glGetIntegerv(gl::PIXEL_UNPACK_BUFFER_BINDING, &unpackBuffer_);
    }
    if (gl_.glActiveTexture) gl_.glGetIntegerv(gl::ACTIVE_TEXTURE, &active_);
    if (gl_.glActiveTexture) gl_.glActiveTexture(gl::TEXTURE0);
    gl_.glGetIntegerv(gl::TEXTURE_BINDING_2D, &texture0_);
    if (gl_.glActiveTexture) {
      gl_.glActiveTexture(gl::TEXTURE0 + 1);
      gl_.glGetIntegerv(gl::TEXTURE_BINDING_2D, &texture1_);
      gl_.glActiveTexture(static_cast<unsigned>(active_));
    }
    valid_ = true;
  }
  ~ScopedEffectGlState() {
    if (!valid_) return;
    if (gl_.glBindFramebuffer) {
      gl_.glBindFramebuffer(0x8CA9, static_cast<unsigned>(framebuffer_));
      gl_.glBindFramebuffer(0x8CA8, static_cast<unsigned>(readFramebuffer_));
    }
    gl_.glViewport(viewport_[0], viewport_[1], viewport_[2], viewport_[3]);
    gl_.glScissor(scissor_[0], scissor_[1], scissor_[2], scissor_[3]);
    if (gl_.glUseProgram) gl_.glUseProgram(static_cast<unsigned>(program_));
    if (gl_.glBindVertexArray) gl_.glBindVertexArray(static_cast<unsigned>(vao_));
    if (bindBuffer_) {
      bindBuffer_(0x8892, static_cast<unsigned>(arrayBuffer_));
      bindBuffer_(0x8893, static_cast<unsigned>(elementBuffer_));
      bindBuffer_(0x88EC, static_cast<unsigned>(unpackBuffer_));
    }
    if (blendSeparate_) blendSeparate_(blend_[0], blend_[1], blend_[2], blend_[3]);
    else gl_.glBlendFunc(blend_[0], blend_[1]);
    if (blendEquation_) blendEquation_(equation_[0], equation_[1]);
    colorMask_(static_cast<unsigned char>(color_[0]), static_cast<unsigned char>(color_[1]),
               static_cast<unsigned char>(color_[2]), static_cast<unsigned char>(color_[3]));
    depthMask_(static_cast<unsigned char>(depthWrite_));
    const unsigned unpack[] = {gl::UNPACK_ALIGNMENT, gl::UNPACK_ROW_LENGTH,
                               gl::UNPACK_SKIP_ROWS, gl::UNPACK_SKIP_PIXELS};
    for (int i = 0; i < 4; ++i) gl_.glPixelStorei(unpack[i], unpack_[i]);
    for (int i = 0; i < 6; ++i) {
      if (enabled_[i]) gl_.glEnable(caps_[i]); else gl_.glDisable(caps_[i]);
    }
    if (gl_.glActiveTexture) gl_.glActiveTexture(gl::TEXTURE0);
    gl_.glBindTexture(gl::TEXTURE_2D, static_cast<unsigned>(texture0_));
    if (gl_.glActiveTexture) {
      gl_.glActiveTexture(gl::TEXTURE0 + 1);
      gl_.glBindTexture(gl::TEXTURE_2D, static_cast<unsigned>(texture1_));
      gl_.glActiveTexture(static_cast<unsigned>(active_));
    }
  }
  [[nodiscard]] bool valid() const noexcept { return valid_; }
 private:
  template<class T> static T load(const char* name) noexcept {
    auto p = wglGetProcAddress(name);
    if (!p || p == reinterpret_cast<PROC>(1) || p == reinterpret_cast<PROC>(2) ||
        p == reinterpret_cast<PROC>(3) || p == reinterpret_cast<PROC>(-1))
      p = GetProcAddress(GetModuleHandleW(L"opengl32.dll"), name);
    return reinterpret_cast<T>(p);
  }
  using BlendSeparate = void(APIENTRY*)(unsigned, unsigned, unsigned, unsigned);
  using BlendEquation = void(APIENTRY*)(unsigned, unsigned);
  using BindBuffer = void(APIENTRY*)(unsigned, unsigned);
  using ColorMask = void(APIENTRY*)(unsigned char, unsigned char, unsigned char, unsigned char);
  using DepthMask = void(APIENTRY*)(unsigned char);
  BlendSeparate blendSeparate_{}; BlendEquation blendEquation_{}; BindBuffer bindBuffer_{};
  ColorMask colorMask_{}; DepthMask depthMask_{};
  gl::OpenGLFunctions& gl_;
  int viewport_[4]{}, scissor_[4]{}, color_[4]{}, unpack_[4]{}, blend_[4]{}, equation_[2]{};
  int depthWrite_{}, framebuffer_{}, readFramebuffer_{}, vao_{}, program_{}, arrayBuffer_{}, elementBuffer_{}, unpackBuffer_{};
  int active_{static_cast<int>(gl::TEXTURE0)}, texture0_{}, texture1_{};
  static constexpr unsigned caps_[6] = {gl::BLEND, gl::CULL_FACE, gl::DEPTH_TEST,
      gl::SCISSOR_TEST, gl::STENCIL_TEST, gl::FRAMEBUFFER_SRGB};
  bool enabled_[6]{}, valid_{};
};
}  // namespace iee::game
