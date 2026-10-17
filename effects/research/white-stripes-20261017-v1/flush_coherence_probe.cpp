// Uses the unmodified production GL-state guard on a hidden real WGL context.
// The native delta-cache policy is modelled from the exact BG2EE PE disassembly.
// This is a host reproduction, not a capture or execution of the game.
#include <windows.h>
#include <array>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "iee/game/scoped_effect_gl_state.h"
#include <GL/gl.h>

template<class T> T proc(const char* name) {
  auto p=wglGetProcAddress(name);
  if (!p || p==reinterpret_cast<PROC>(1) || p==reinterpret_cast<PROC>(2) ||
      p==reinterpret_cast<PROC>(3) || p==reinterpret_cast<PROC>(-1))
    p=GetProcAddress(GetModuleHandleW(L"opengl32.dll"),name);
  if (!p) throw std::runtime_error(name);
  return reinterpret_cast<T>(p);
}
namespace iee::game::gl {
OpenGLFunctions& get_gl_functions() noexcept { static OpenGLFunctions f;return f; }
bool OpenGLFunctions::initialize() noexcept {return valid;}
}
void initialize_table() {
  auto& g=iee::game::gl::get_gl_functions();
#define LOAD(name) g.name=proc<decltype(g.name)>(#name)
  LOAD(glGetIntegerv);LOAD(glBindTexture);LOAD(glEnable);LOAD(glDisable);
  LOAD(glIsEnabled);LOAD(glPixelStorei);LOAD(glViewport);LOAD(glBlendFunc);
  LOAD(glScissor);LOAD(glBindFramebuffer);LOAD(glBindVertexArray);
  LOAD(glUseProgram);LOAD(glActiveTexture);LOAD(glCreateShader);
  LOAD(glShaderSource);LOAD(glCompileShader);LOAD(glGetShaderiv);
  LOAD(glCreateProgram);LOAD(glAttachShader);LOAD(glLinkProgram);LOAD(glGetProgramiv);
#undef LOAD
  g.valid=true;
}
GLuint shader(GLenum type,const char* source) {
  auto& g=iee::game::gl::get_gl_functions();GLuint s=g.glCreateShader(type);
  g.glShaderSource(s,1,&source,nullptr);g.glCompileShader(s);int ok=0;
  g.glGetShaderiv(s,0x8B81,&ok);if (!ok)throw std::runtime_error("compile");return s;
}
GLuint program(const char* fragment) {
  auto& g=iee::game::gl::get_gl_functions();GLuint p=g.glCreateProgram();
  g.glAttachShader(p,shader(0x8B31,"#version 120\nvoid main(){gl_Position=gl_Vertex;}"));
  g.glAttachShader(p,shader(0x8B30,fragment));g.glLinkProgram(p);int ok=0;
  g.glGetProgramiv(p,0x8B82,&ok);if (!ok)throw std::runtime_error("link");return p;
}
GLuint cachedProgram{};
void native_apply(GLuint wanted) {
  // DrawFlushGL 42B4F2/42B5A0: apply shader only if cached packed flags differ.
  if (wanted!=cachedProgram) {
    iee::game::gl::get_gl_functions().glUseProgram(wanted);cachedProgram=wanted;
  }
}
GLuint current_program() {
  int p=0;glGetIntegerv(iee::game::gl::CURRENT_PROGRAM,&p);return p;
}
void draw_strip() {
  glViewport(0,0,128,128);glDisable(GL_SCISSOR_TEST);glDisable(GL_BLEND);
  glClearColor(0,0,0,1);glClear(GL_COLOR_BUFFER_BIT);
  glBegin(GL_QUADS);glVertex2f(-0.25f,-1);glVertex2f(0.25f,-1);
  glVertex2f(0.25f,1);glVertex2f(-0.25f,1);glEnd();
}
std::array<unsigned char,4> pixels(const char* filename) {
  std::vector<unsigned char> all(128*128*3);glPixelStorei(GL_PACK_ALIGNMENT,1);
  glReadPixels(0,0,128,128,GL_RGB,GL_UNSIGNED_BYTE,all.data());
  std::ofstream out(filename,std::ios::binary);out<<"P6\n128 128\n255\n";
  out.write(reinterpret_cast<const char*>(all.data()),all.size());
  std::array<unsigned char,4> center{};
  glReadPixels(64,64,1,1,GL_RGBA,GL_UNSIGNED_BYTE,center.data());return center;
}
bool exercise() {
  initialize_table();auto& g=iee::game::gl::get_gl_functions();
  const GLuint white=program("#version 120\nvoid main(){gl_FragColor=vec4(1.0);}");
  const GLuint red=program("#version 120\nvoid main(){gl_FragColor=vec4(1,0,0,1);}");
  g.glUseProgram(white);cachedProgram=white;
  {
    iee::game::ScopedEffectGlState guard;
    if (!guard.valid())throw std::runtime_error("guard");
    native_apply(red); // Real native flush changes GL and the native cache.
  } // Production guard restores white; native cache still says red.
  const bool badMismatch=current_program()!=cachedProgram;
  native_apply(red);draw_strip();const auto bad=pixels("bad-before-flush.ppm");
  const auto badError=glGetError();
  g.glUseProgram(white);cachedProgram=white;
  native_apply(red); // Proposed ordering: flush before capturing upload state.
  {iee::game::ScopedEffectGlState guard;if (!guard.valid())return false;}
  const bool goodMatch=current_program()==cachedProgram;
  native_apply(red);draw_strip();const auto good=pixels("good-after-flush.ppm");
  const auto goodError=glGetError();
  std::cout<<"{\n  \"game_executed\":false,\n  \"production_guard_unmodified\":true,\n"
    <<"  \"guard_before_flush\":{\"cache_gl_mismatch\":"<<(badMismatch?"true":"false")
    <<",\"center_rgb\":["<<int(bad[0])<<","<<int(bad[1])<<","<<int(bad[2])<<"],\"gl_error\":"<<badError<<"},\n"
    <<"  \"guard_after_flush\":{\"cache_gl_coherent\":"<<(goodMatch?"true":"false")
    <<",\"center_rgb\":["<<int(good[0])<<","<<int(good[1])<<","<<int(good[2])<<"],\"gl_error\":"<<goodError<<"}\n}\n";
  return badMismatch && goodMatch && bad[0]==255 && bad[1]==255 && bad[2]==255 &&
    good[0]==255 && good[1]==0 && good[2]==0 && !badError && !goodError;
}
int main() {
  HWND window=CreateWindowExW(WS_EX_NOACTIVATE,L"STATIC",L"Hidden effect probe",WS_POPUP,
                            0,0,128,128,nullptr,nullptr,nullptr,nullptr);
  if (!window)return 2;HDC dc=GetDC(window);PIXELFORMATDESCRIPTOR f{};
  f.nSize=sizeof(f);f.nVersion=1;f.dwFlags=PFD_DRAW_TO_WINDOW|PFD_SUPPORT_OPENGL;
  f.iPixelType=PFD_TYPE_RGBA;f.cColorBits=32;f.cAlphaBits=8;
  const int pf=ChoosePixelFormat(dc,&f);bool ok=false;
  HGLRC ctx=pf && SetPixelFormat(dc,pf,&f)?wglCreateContext(dc):nullptr;
  if (ctx && wglMakeCurrent(dc,ctx)) {
    try {ok=exercise();}catch(const std::exception& e){std::cerr<<e.what()<<'\n';}
    wglMakeCurrent(nullptr,nullptr);
  }
  if(ctx)wglDeleteContext(ctx);ReleaseDC(window,dc);DestroyWindow(window);return ok?0:1;
}
