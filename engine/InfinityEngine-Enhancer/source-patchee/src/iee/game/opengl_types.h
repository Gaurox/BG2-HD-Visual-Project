#pragma once
#include <cstdint>

#ifdef _WIN32
#include <windows.h>
#endif

namespace iee::game::gl {

constexpr unsigned VENDOR = 0x1F00;
constexpr unsigned RENDERER = 0x1F01;
constexpr unsigned VERSION = 0x1F02;
constexpr unsigned SHADING_LANGUAGE_VERSION = 0x8B8C;
constexpr unsigned TEXTURE_2D = 0x0DE1;
constexpr unsigned TEXTURE_WRAP_S = 0x2802;
constexpr unsigned TEXTURE_WRAP_T = 0x2803;
constexpr unsigned CLAMP_TO_EDGE = 0x812F;
constexpr unsigned TEXTURE_MIN_FILTER = 0x2801;
constexpr unsigned TEXTURE_MAG_FILTER = 0x2800;
constexpr unsigned TEXTURE_MAX_LEVEL = 0x813D;
constexpr unsigned LINEAR = 0x2601;
constexpr unsigned LINEAR_MIPMAP_LINEAR = 0x2703;
constexpr unsigned NEAREST = 0x2600;
constexpr unsigned REPEAT = 0x2901;
constexpr unsigned RGBA8 = 0x8058;
constexpr unsigned RGBA = 0x1908;
constexpr unsigned RGB = 0x1907;
constexpr unsigned BGRA = 0x80E1;
constexpr unsigned BGR = 0x80E0;
constexpr unsigned ALPHA = 0x1906;
constexpr unsigned LUMINANCE = 0x1909;
constexpr unsigned LUMINANCE_ALPHA = 0x190A;
constexpr unsigned TEXTURE_BINDING_2D = 0x8069;
constexpr unsigned TEXTURE_WIDTH = 0x1000;
constexpr unsigned TEXTURE_HEIGHT = 0x1001;
constexpr unsigned MAX_TEXTURE_MAX_ANISOTROPY_EXT = 0x84FF;
constexpr unsigned TEXTURE_MAX_ANISOTROPY_EXT = 0x84FE;
constexpr unsigned TEXTURE_LOD_BIAS = 0x8501;
constexpr unsigned TEXTURE0 = 0x84C0;
constexpr unsigned R8 = 0x8229;
constexpr unsigned RED = 0x1903;
constexpr unsigned UNSIGNED_BYTE = 0x1401;
constexpr unsigned UNSIGNED_INT_8_8_8_8 = 0x8035;
constexpr unsigned UNSIGNED_INT_8_8_8_8_REV = 0x8367;
constexpr unsigned UNPACK_ALIGNMENT = 0x0CF5;
constexpr unsigned UNPACK_ROW_LENGTH = 0x0CF2;
constexpr unsigned UNPACK_SKIP_ROWS = 0x0CF3;
constexpr unsigned UNPACK_SKIP_PIXELS = 0x0CF4;
constexpr unsigned PACK_ALIGNMENT = 0x0D05;
constexpr unsigned PIXEL_PACK_BUFFER_BINDING = 0x88ED;
constexpr unsigned PIXEL_UNPACK_BUFFER_BINDING = 0x88EF;
constexpr unsigned MAX_TEXTURE_SIZE = 0x0D33;
constexpr unsigned FRAMEBUFFER = 0x8D40;
constexpr unsigned FRAMEBUFFER_BINDING = 0x8CA6;
constexpr unsigned COLOR_ATTACHMENT0 = 0x8CE0;
constexpr unsigned FRAMEBUFFER_COMPLETE = 0x8CD5;
constexpr unsigned VIEWPORT = 0x0BA2;
constexpr unsigned CURRENT_PROGRAM = 0x8B8D;
constexpr unsigned ACTIVE_TEXTURE = 0x84E0;
constexpr unsigned VERTEX_ARRAY_BINDING = 0x85B5;
constexpr unsigned BLEND = 0x0BE2;
constexpr unsigned BLEND_DST = 0x0BE0;
constexpr unsigned BLEND_SRC = 0x0BE1;
constexpr unsigned SRC_ALPHA = 0x0302;
constexpr unsigned ONE_MINUS_SRC_ALPHA = 0x0303;
constexpr unsigned CULL_FACE = 0x0B44;
constexpr unsigned DEPTH_TEST = 0x0B71;
constexpr unsigned SCISSOR_TEST = 0x0C11;
constexpr unsigned STENCIL_TEST = 0x0B90;
constexpr unsigned FRAMEBUFFER_SRGB = 0x8DB9;
constexpr unsigned TRIANGLES = 0x0004;
constexpr unsigned COMPRESSED_RGB_S3TC_DXT1_EXT = 0x83F0;
constexpr unsigned COMPRESSED_RGBA_S3TC_DXT1_EXT = 0x83F1;
constexpr unsigned COMPRESSED_RGBA_S3TC_DXT5_EXT = 0x83F3;
constexpr unsigned COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT = 0x8C4D;
constexpr unsigned COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT = 0x8C4F;
constexpr unsigned COMPRESSED_RG_RGTC2 = 0x8DBD;
constexpr unsigned COMPRESSED_RGBA_BPTC_UNORM = 0x8E8C;
constexpr unsigned COMPRESSED_SRGB_ALPHA_BPTC_UNORM = 0x8E8D;

// OpenGL error codes
constexpr unsigned GL_NO_ERROR = 0x0000;
constexpr unsigned GL_INVALID_ENUM = 0x0500;
constexpr unsigned GL_INVALID_VALUE = 0x0501;
constexpr unsigned GL_INVALID_OPERATION = 0x0502;
constexpr unsigned GL_OUT_OF_MEMORY = 0x0505;
constexpr unsigned GL_INVALID_FRAMEBUFFER_OPERATION = 0x0506;
constexpr unsigned GL_CONTEXT_LOST = 0x0507;

// GL1.1 core — loaded via opengl32.dll GetProcAddress
using PFN_glGetString = const unsigned char*(APIENTRY*)(unsigned name);
using PFN_glTexParameteri = void(APIENTRY*)(unsigned target, unsigned pname, int param);
using PFN_glTexParameterf = void(APIENTRY*)(unsigned target, unsigned pname, float param);
using PFN_glGetIntegerv = void(APIENTRY*)(unsigned pname, int* data);
using PFN_glGetTexParameteriv = void(APIENTRY*)(unsigned target, unsigned pname, int* params);
using PFN_glGetTexLevelParameteriv = void(APIENTRY*)(unsigned target, int level, unsigned pname,
                                                     int* params);
using PFN_glGetTexImage = void(APIENTRY*)(unsigned target, int level, unsigned format,
                                          unsigned type, void* pixels);
using PFN_glGetError = unsigned int(APIENTRY*)();
using PFN_glGenTextures = void(APIENTRY*)(int n, unsigned* textures);
using PFN_glBindTexture = void(APIENTRY*)(unsigned target, unsigned texture);
using PFN_glTexImage2D = void(APIENTRY*)(unsigned target, int level, int internalformat, int width,
                                         int height, int border, unsigned format, unsigned type,
                                         const void* data);
using PFN_glTexSubImage2D = void(APIENTRY*)(unsigned target, int level, int xoffset, int yoffset,
                                            int width, int height, unsigned format, unsigned type,
                                            const void* data);
using PFN_glDeleteTextures = void(APIENTRY*)(int n, const unsigned* textures);
using PFN_glPixelStorei = void(APIENTRY*)(unsigned pname, int param);
using PFN_glCopyTexSubImage2D = void(APIENTRY*)(unsigned target, int level, int xoffset,
                                               int yoffset, int x, int y, int width, int height);
using PFN_glIsEnabled = unsigned char(APIENTRY*)(unsigned cap);
using PFN_glEnable = void(APIENTRY*)(unsigned cap);
using PFN_glDisable = void(APIENTRY*)(unsigned cap);
using PFN_glBlendFunc = void(APIENTRY*)(unsigned sourceFactor, unsigned destinationFactor);
using PFN_glViewport = void(APIENTRY*)(int x, int y, int width, int height);
using PFN_glScissor = void(APIENTRY*)(int x, int y, int width, int height);
// Extensions — loaded via wglGetProcAddress
using PFN_glCreateShader = unsigned int(APIENTRY*)(unsigned shaderType);
using PFN_glShaderSource = void(APIENTRY*)(unsigned shader, int count, const char* const* string,
                                           const int* length);
using PFN_glCompileShader = void(APIENTRY*)(unsigned shader);
using PFN_glDeleteShader = void(APIENTRY*)(unsigned shader);
using PFN_glGetShaderiv = void(APIENTRY*)(unsigned shader, unsigned pname, int* params);
using PFN_glGetShaderInfoLog = void(APIENTRY*)(unsigned shader, int maxLength, int* length,
                                               char* infoLog);
using PFN_glCreateProgram = unsigned int(APIENTRY*)();
using PFN_glAttachShader = void(APIENTRY*)(unsigned program, unsigned shader);
using PFN_glLinkProgram = void(APIENTRY*)(unsigned program);
using PFN_glUseProgram = void(APIENTRY*)(unsigned program);
using PFN_glDeleteProgram = void(APIENTRY*)(unsigned program);
using PFN_glGetProgramiv = void(APIENTRY*)(unsigned program, unsigned pname, int* params);
using PFN_glGetProgramInfoLog = void(APIENTRY*)(unsigned program, int maxLength, int* length,
                                                char* infoLog);
using PFN_glGetAttachedShaders = void(APIENTRY*)(unsigned program, int maxCount, int* count,
                                                 unsigned* shaders);
using PFN_glGetShaderSource = void(APIENTRY*)(unsigned shader, int bufSize, int* length,
                                              char* source);
using PFN_glGetUniformLocation = int(APIENTRY*)(unsigned program, const char* name);
using PFN_glUniform1f = void(APIENTRY*)(int location, float v0);
using PFN_glUniform1i = void(APIENTRY*)(int location, int v0);
using PFN_glUniform2f = void(APIENTRY*)(int location, float v0, float v1);
using PFN_glUniform3f = void(APIENTRY*)(int location, float v0, float v1, float v2);
using PFN_glActiveTexture = void(APIENTRY*)(unsigned texture);
using PFN_glCompressedTexImage2D = void(APIENTRY*)(unsigned target, int level,
                                                   unsigned internalformat, int width, int height,
                                                   int border, int imageSize, const void* data);
using PFN_glGenerateMipmap = void(APIENTRY*)(unsigned target);
using PFN_glBindFramebuffer = void(APIENTRY*)(unsigned target, unsigned framebuffer);
using PFN_glGenVertexArrays = void(APIENTRY*)(int n, unsigned* arrays);
using PFN_glBindVertexArray = void(APIENTRY*)(unsigned array);
using PFN_glDeleteVertexArrays = void(APIENTRY*)(int n, const unsigned* arrays);
using PFN_glDrawArrays = void(APIENTRY*)(unsigned mode, int first, int count);
using PFN_glGenFramebuffers = void(APIENTRY*)(int n, unsigned* framebuffers);
using PFN_glDeleteFramebuffers = void(APIENTRY*)(int n, const unsigned* framebuffers);
using PFN_glFramebufferTexture2D = void(APIENTRY*)(unsigned target, unsigned attachment,
                                                   unsigned textarget, unsigned texture,
                                                   int level);
using PFN_glCheckFramebufferStatus = unsigned(APIENTRY*)(unsigned target);
using PFN_glIsProgram = unsigned char(APIENTRY*)(unsigned program);
using PFN_glShaderSourceARB = void(APIENTRY*)(unsigned shader, int count, const char* const* string,
                                              const int* length);
using PFN_glCompileShaderARB = void(APIENTRY*)(unsigned shader);
using PFN_glLinkProgramARB = void(APIENTRY*)(unsigned program);
using PFN_glUseProgramObjectARB = void(APIENTRY*)(unsigned program);
using PFN_glDeleteObjectARB = void(APIENTRY*)(unsigned object);

const char* error_string(unsigned error_code) noexcept;
void discard_errors(unsigned maximumErrors = 16) noexcept;
bool check_error(const char* operation) noexcept;

struct OpenGLFunctions {
  // GL1.1 core
  PFN_glGetString glGetString{};
  PFN_glTexParameteri glTexParameteri{};
  PFN_glTexParameterf glTexParameterf{};
  PFN_glGetIntegerv glGetIntegerv{};
  PFN_glGetTexParameteriv glGetTexParameteriv{};
  PFN_glGetTexLevelParameteriv glGetTexLevelParameteriv{};
  PFN_glGetTexImage glGetTexImage{};
  PFN_glGetError glGetError{};
  PFN_glGenTextures glGenTextures{};
  PFN_glBindTexture glBindTexture{};
  PFN_glTexImage2D glTexImage2D{};
  PFN_glTexSubImage2D glTexSubImage2D{};
  PFN_glDeleteTextures glDeleteTextures{};
  PFN_glPixelStorei glPixelStorei{};
  PFN_glCopyTexSubImage2D glCopyTexSubImage2D{};
  PFN_glIsEnabled glIsEnabled{};
  PFN_glEnable glEnable{};
  PFN_glDisable glDisable{};
  PFN_glBlendFunc glBlendFunc{};
  PFN_glViewport glViewport{};
  PFN_glScissor glScissor{};
  // Extensions
  PFN_glCreateShader glCreateShader{};
  PFN_glShaderSource glShaderSource{};
  PFN_glCompileShader glCompileShader{};
  PFN_glDeleteShader glDeleteShader{};
  PFN_glGetShaderiv glGetShaderiv{};
  PFN_glGetShaderInfoLog glGetShaderInfoLog{};
  PFN_glCreateProgram glCreateProgram{};
  PFN_glAttachShader glAttachShader{};
  PFN_glLinkProgram glLinkProgram{};
  PFN_glUseProgram glUseProgram{};
  PFN_glDeleteProgram glDeleteProgram{};
  PFN_glGetProgramiv glGetProgramiv{};
  PFN_glGetProgramInfoLog glGetProgramInfoLog{};
  PFN_glGetAttachedShaders glGetAttachedShaders{};
  PFN_glGetShaderSource glGetShaderSource{};
  PFN_glGetUniformLocation glGetUniformLocation{};
  PFN_glUniform1f glUniform1f{};
  PFN_glUniform1i glUniform1i{};
  PFN_glUniform2f glUniform2f{};
  PFN_glUniform3f glUniform3f{};
  PFN_glActiveTexture glActiveTexture{};
  PFN_glCompressedTexImage2D glCompressedTexImage2D{};
  PFN_glGenerateMipmap glGenerateMipmap{};
  PFN_glBindFramebuffer glBindFramebuffer{};
  PFN_glGenVertexArrays glGenVertexArrays{};
  PFN_glBindVertexArray glBindVertexArray{};
  PFN_glDeleteVertexArrays glDeleteVertexArrays{};
  PFN_glDrawArrays glDrawArrays{};
  PFN_glGenFramebuffers glGenFramebuffers{};
  PFN_glDeleteFramebuffers glDeleteFramebuffers{};
  PFN_glFramebufferTexture2D glFramebufferTexture2D{};
  PFN_glCheckFramebufferStatus glCheckFramebufferStatus{};
  PFN_glIsProgram glIsProgram{};
  PFN_glShaderSourceARB glShaderSourceARB{};
  PFN_glCompileShaderARB glCompileShaderARB{};
  PFN_glLinkProgramARB glLinkProgramARB{};
  PFN_glUseProgramObjectARB glUseProgramObjectARB{};
  PFN_glDeleteObjectARB glDeleteObjectARB{};

  bool valid{false};
  bool shaderObjectsAvailable{false};
  bool shaderIntrospectionAvailable{false};
  bool uniformApiAvailable{false};
  bool readyForSourcePatching{false};
  bool arbShaderObjectsAvailable{false};
  bool textureUploadAvailable{false};
  bool compressedTextureUploadAvailable{false};

  bool initialize() noexcept;
};

// Get the global OpenGL function table
OpenGLFunctions& get_gl_functions() noexcept;
#ifdef _WIN32
// Returns the context current on the calling thread, or nullptr. GL resources
// must never be reused across a context change.
HGLRC current_context() noexcept;
#endif

}  // namespace iee::game::gl
