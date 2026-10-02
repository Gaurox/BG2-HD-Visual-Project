#include "paperdoll_q3m.h"
#include <algorithm>
#include <atomic>
#include <cstring>
#include <fstream>
#include <mutex>
#include <stdexcept>
#include <zlib.h>
#include "iee/core/logger.h"
#include "iee/core/pattern_scanner.h"
#include "iee/game/opengl_types.h"

namespace iee::paperdoll_q3m {
namespace {
struct Reader {
  std::span<const std::uint8_t> bytes;
  std::size_t pos{};
  std::span<const std::uint8_t> take(std::size_t n) {
    if (n>bytes.size()-pos) throw std::runtime_error("truncated UI pack");
    auto result=bytes.subspan(pos,n);pos+=n;return result;
  }
  std::uint32_t u32() { auto b=take(4);return b[0]|(std::uint32_t(b[1])<<8)|(std::uint32_t(b[2])<<16)|(std::uint32_t(b[3])<<24); }
};
std::uint16_t u16(std::span<const std::uint8_t> b, std::size_t n) {return b[n]|(std::uint16_t(b[n+1])<<8);}
std::uint32_t u32(std::span<const std::uint8_t> b, std::size_t n) {
  return b[n]|(std::uint32_t(b[n+1])<<8)|(std::uint32_t(b[n+2])<<16)|(std::uint32_t(b[n+3])<<24);
}
void require(bool value) {if(!value)throw std::runtime_error("unsupported UI pack");}
std::mutex g_mutex;
std::atomic<bool> g_ready{};
std::array<Frames,kScope.size()> g_frames;
std::array<bool,kScope.size()> g_loaded{};
struct Texture {
  int id{};
  std::size_t owner{kScope.size()}, frame{};
  std::uint64_t stamp{};
  bool valid{};
  core::palette_fraction::Palette palette{};
  std::uint32_t crc{};
};
// Bounded engine texture pool: frames/palettes remain separate; flush before reuse.
std::array<Texture,32> g_textures;
std::uint64_t g_textureStamp{};
HGLRC g_context{};

bool palette_equal(const Frame& frame, const core::palette_fraction::Palette& a,
                    const core::palette_fraction::Palette& b) {
  for (std::size_t i=0;i<256;++i)
    if ((frame.dependencies[i/8]&(1u<<(i%8))) && a[i]!=b[i]) return false;
  return true;
}

bool upload(const Frame& frame, std::span<const std::uint32_t> pixels,
             int id, int previous, const TextureApi& api) {
  auto& gl=game::gl::get_gl_functions();
  if ((!gl.valid&&!gl.initialize())||!gl.glGetIntegerv||!gl.glPixelStorei||!gl.glTexImage2D||
      !gl.glTexParameteri||!gl.glGetTexLevelParameteriv||!gl.glGetError) return false;
  int alignment{},row{},skipRows{},skipPixels{},buffer{};
  gl.glGetIntegerv(game::gl::UNPACK_ALIGNMENT,&alignment);
  gl.glGetIntegerv(game::gl::UNPACK_ROW_LENGTH,&row);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_ROWS,&skipRows);
  gl.glGetIntegerv(game::gl::UNPACK_SKIP_PIXELS,&skipPixels);
  gl.glGetIntegerv(game::gl::PIXEL_UNPACK_BUFFER_BINDING,&buffer);
  if (buffer!=0) return false;
  const auto restore=[&] {
    gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT,alignment);
    gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH,row);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS,skipRows);
    gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS,skipPixels);
    api.engine.DrawBindTexture(previous);
  };
  game::gl::discard_errors();
  gl.glPixelStorei(game::gl::UNPACK_ALIGNMENT,1);
  gl.glPixelStorei(game::gl::UNPACK_ROW_LENGTH,0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_ROWS,0);
  gl.glPixelStorei(game::gl::UNPACK_SKIP_PIXELS,0);
  api.engine.DrawBindTexture(id);
  // Native descriptor stays x1/unbordered: common RenderTexture retains the
  // measured UV/clip/placement contract. Only the GL backing becomes x2.
  api.engine.TexImage(frame.width,frame.height,nullptr,0);
  game::gl::EngineTextureDescriptor descriptor{};
  int bound{};
  gl.glGetIntegerv(game::gl::TEXTURE_BINDING_2D,&bound);
  if (!game::gl::read_engine_texture_descriptor(api.glTextureTable,static_cast<unsigned>(id),descriptor)||
      bound<=0||descriptor.glName!=static_cast<unsigned>(bound)||
      descriptor.width!=frame.width||descriptor.height!=frame.height||descriptor.deletePending||
      gl.glGetError()!=game::gl::GL_NO_ERROR) {restore();return false;}
  gl.glTexImage2D(game::gl::TEXTURE_2D,0,static_cast<int>(game::gl::RGBA8),frame.width*2,frame.height*2,
      0,game::gl::BGRA,game::gl::UNSIGNED_INT_8_8_8_8_REV,pixels.data());
  for (const auto param : {game::gl::TEXTURE_WRAP_S,game::gl::TEXTURE_WRAP_T})
    gl.glTexParameteri(game::gl::TEXTURE_2D,param,static_cast<int>(game::gl::CLAMP_TO_EDGE));
  for (const auto param : {game::gl::TEXTURE_MIN_FILTER,game::gl::TEXTURE_MAG_FILTER})
    gl.glTexParameteri(game::gl::TEXTURE_2D,param,static_cast<int>(game::gl::NEAREST));
  gl.glTexParameteri(game::gl::TEXTURE_2D,game::gl::TEXTURE_MAX_LEVEL,0);
  int width{},height{};
  gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D,0,game::gl::TEXTURE_WIDTH,&width);
  gl.glGetTexLevelParameteriv(game::gl::TEXTURE_2D,0,game::gl::TEXTURE_HEIGHT,&height);
  const bool ok=width==frame.width*2 && height==frame.height*2 && gl.glGetError()==game::gl::GL_NO_ERROR;
  restore();return ok;
}
}

bool resource_for_resref(const std::array<char,8>& resref, ResourceId& body) noexcept {
  for (std::size_t n=0;n<kScope.size();++n) if(resref==kScope[n].resref) {
    body=static_cast<ResourceId>(n);return true;
  }
  return false;
}

const NativeGeometry* native_geometry(ResourceId resource, int slot) noexcept {
  const auto n=static_cast<std::size_t>(resource);
  if(n>=kScope.size() || slot<0 || slot>3) return nullptr;
  return &kScope[n].geometry[static_cast<std::size_t>(slot/2)];
}

bool parse(std::span<const std::uint8_t> bytes, Frames& out, ResourceId body) noexcept {
  out={};
  try {
    const auto bi=static_cast<std::size_t>(body);
    require(bi<kScope.size() && bytes.size()>=32 && bytes.size()<=512000);
    Reader reader{bytes};
    auto magic=reader.take(8);require(std::memcmp(magic.data(),"IEECSXN\0",8)==0);
    require(reader.u32()==6 && reader.u32()==2 && reader.u32()==1 && reader.u32()==0xffff && reader.u32()==1 && reader.u32()==1);
    auto resref=reader.take(8);require(std::memcmp(resref.data(),kScope[bi].resref.data(),8)==0);
    auto source=reader.take(32);require(std::equal(source.begin(),source.end(),kScope[bi].source.begin()));
    require(reader.u32()==kScope[bi].frameCount && reader.u32()==1);
    Frames parsed(kScope[bi].frameCount);
    for (std::size_t index=0;index<parsed.size();++index) {
      auto h=reader.take(568);auto& frame=parsed[index];
      frame.width=u16(h,0);frame.height=u16(h,2);
      frame.centerX=static_cast<std::int16_t>(u16(h,4));frame.centerY=static_cast<std::int16_t>(u16(h,6));
      require(frame.width==kScope[bi].geometry[index].width && frame.height==kScope[bi].geometry[index].height &&
              frame.centerX==kScope[bi].geometry[index].centerX && frame.centerY==kScope[bi].geometry[index].centerY);
      const auto n=static_cast<std::size_t>(frame.width*frame.height*4);
      require(h[8]==0 && h[9]==0 && h[10]==1 && h[11]==0 && u32(h,12)==n &&
              u32(h,560)==n && h[564]==0 && h[565]==0 && h[566]==0 && h[567]==0);
      for (std::size_t p=0;p<256;++p) {const auto rep=u16(h,16+p*2);require(rep==65535 || rep<frame.width*frame.height);}
      std::copy_n(h.begin()+528,32,frame.dependencies.begin());
      auto i=reader.take(n),f=reader.take(n);
      frame.indices.assign(i.begin(),i.end());frame.fractions.assign(f.begin(),f.end());
      require(core::palette_fraction::validate(frame.indices,frame.fractions,frame.dependencies));
    }
    require(reader.u32()==4 && reader.u32()==0 && reader.u32()==0 && reader.u32()==1 && reader.u32()==1 && reader.pos==bytes.size());
    out=std::move(parsed);return true;
  } catch (...) {out={};return false;}
}

bool decode(const Frame& frame, core::palette_fraction::Palette palette,
             std::vector<std::uint32_t>& pixels) noexcept {
  pixels.clear();
  try {
    if (frame.width<=0 || frame.width>128 || frame.height<=0 || frame.height>160 ||
        frame.indices.size()!=static_cast<std::size_t>(frame.width*frame.height*4) ||
        frame.fractions.size()!=frame.indices.size() ||
        !core::palette_fraction::validate(frame.indices,frame.fractions,frame.dependencies)) return false;
    palette[0]=0;
    core::palette_fraction::Lut lut;
    if (!lut.prepare(frame.indices,frame.fractions,palette)) return false;
    pixels.resize(frame.indices.size());
    for (std::size_t n=0;n<pixels.size();++n) pixels[n]=lut.pixel(frame.indices[n],frame.fractions[n]);
    return true;
  } catch (...) {pixels.clear();return false;}
}

bool prepare(const std::filesystem::path& directory) noexcept {
  release();
  try {
    std::lock_guard lock(g_mutex);
    for (std::size_t bi=0;bi<kScope.size();++bi) {
      const std::string resref(kScope[bi].resref.begin(),kScope[bi].resref.end());
      const auto path=directory/(resref+"-Q3m-X2.registry");
      std::ifstream file(path,std::ios::binary|std::ios::ate);
      if (!file) continue;
      if (file.tellg()<=0 || file.tellg()>512000) {
        LOG_WARN("P7_Q3M_PACK invalid: {}; native UI retained",resref);continue;
      }
      std::vector<std::uint8_t> bytes(static_cast<std::size_t>(file.tellg()));
      file.seekg(0);
      if (!file.read(reinterpret_cast<char*>(bytes.data()),static_cast<std::streamsize>(bytes.size()))) continue;
      Frames frames;
      if(!parse(bytes,frames,static_cast<ResourceId>(bi))) {
        LOG_WARN("P7_Q3M_PACK invalid: {}; native UI retained",resref);continue;
      }
      g_frames[bi]=std::move(frames);g_loaded[bi]=true;
      LOG_INFO("P7_Q3M_PACK ready: {}, {} native frames, raw V6 x2, {} bytes; UI sampling=Nearest",resref,g_frames[bi].size(),bytes.size());
    }
    g_ready.store(std::any_of(g_loaded.begin(),g_loaded.end(),[](bool value){return value;}));
    return g_ready.load();
  } catch (...) {LOG_WARN("P7_Q3M_PACK unavailable: native UI retained");return false;}
}
bool ready() noexcept {return g_ready.load();}
void release() noexcept {std::lock_guard lock(g_mutex);g_ready.store(false);g_frames={};g_loaded={};g_textures={};g_context=nullptr;}
void forget_engine_textures() noexcept {std::lock_guard lock(g_mutex);g_textures={};g_context=nullptr;}

bool bind(int sequence, int slot, int width, int height,
           core::palette_fraction::Palette palette, const TextureApi& api,
           int& previousTexture, std::uint32_t& pixelCrc, bool& uploaded, ResourceId body) noexcept {
  previousTexture=0;pixelCrc=0;uploaded=false;
  if (!ready()||sequence!=0||slot<0||slot>3||!api.engine.DrawGenTexture||!api.engine.DrawBindTexture||
      !api.engine.DrawDeleteTexture||!api.engine.TexImage||!api.engine.DrawGetRenderer||!api.engine.glTextureState||
      !api.glTextureTable||!api.DrawFlushGl||api.engine.DrawGetRenderer()==1) return false;
  try {
    const auto bi=static_cast<std::size_t>(body);
    std::lock_guard lock(g_mutex);if(!ready()||bi>=g_loaded.size()||!g_loaded[bi])return false;
    const auto index=static_cast<std::size_t>(slot/2);const auto& frame=g_frames[bi][index];
    if(frame.width!=width||frame.height!=height)return false;
    const auto context=game::gl::current_context();if(!context)return false;
    if(context!=g_context){g_textures={};g_context=context;}
    std::uint32_t state{};if(!core::safe_read(api.engine.glTextureState,state))return false;
    previousTexture=static_cast<int>((state>>21)&0x1ff);if(previousTexture<=0)return false;
    palette[0]=0;
    auto selected=std::find_if(g_textures.begin(),g_textures.end(),[&](const Texture& t) {
      return t.owner==bi && t.frame==index;
    });
    if(selected==g_textures.end()) {
      selected=std::min_element(g_textures.begin(),g_textures.end(),[](const Texture& a,const Texture& b) {
        return a.stamp<b.stamp;
      });
      selected->valid=false;
    }
    auto& texture=*selected;texture.owner=bi;texture.frame=index;texture.stamp=++g_textureStamp;
    if(!texture.valid || !palette_equal(frame,texture.palette,palette)) {
      std::vector<std::uint32_t> pixels;if(!decode(frame,palette,pixels))return false;
      // Flush native/UI draws before changing a backing, including eviction.
      // Previously submitted equipment and actors retain their own palettes.
      api.DrawFlushGl();api.engine.DrawBindTexture(previousTexture);
      if(texture.id==0)texture.id=api.engine.DrawGenTexture(static_cast<int>(game::gl::NEAREST),0,0,0);
      if(texture.id<=0||texture.id>=512){texture={};api.engine.DrawBindTexture(previousTexture);return false;}
      texture.valid=false;
      if(!upload(frame,pixels,texture.id,previousTexture,api)) {
        api.engine.DrawDeleteTexture(texture.id);texture={};api.engine.DrawBindTexture(previousTexture);return false;
      }
      texture.palette=palette;texture.valid=true;
      texture.crc=static_cast<std::uint32_t>(crc32(0,reinterpret_cast<const Bytef*>(pixels.data()),static_cast<uInt>(pixels.size()*4)));
      uploaded=true;
    }
    api.engine.DrawBindTexture(texture.id);pixelCrc=texture.crc;return true;
  } catch (...) {if(previousTexture>0)api.engine.DrawBindTexture(previousTexture);return false;}
}
} // namespace iee::paperdoll_q3m
