"""Reproducible source edit for the isolated V9 SDF runtime trial."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
E=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
def edit(path, replacements):
    p=Path(path);s=p.read_text(encoding='utf-8')
    for item in replacements:
        old,new=item[:2];expected=item[2] if len(item)>2 else 1
        if s.count(old)!=expected:raise ValueError(f'{p}: expected {expected} occurrences: {old[:100]} ({s.count(old)})')
        s=s.replace(old,new)
    p.write_text(s,encoding='utf-8',newline='\n')

p=ROOT/'pipeline/scripts/palette_partner_registry.py'
edit(p,[
 ('CONTOUR_VERSION = 8','CONTOUR_VERSION = 8\nSDF_VERSION = 9\nfrom sprite_sdf_registry import validate as validate_sdf'),
 ('version in (VERSION, CONTOUR_VERSION)', 'version in (VERSION, CONTOUR_VERSION, SDF_VERSION)'),
 ('alpha_present = coverage is not None', "sdf,material=frame.get('S'),frame.get('M')\n                    if version==SDF_VERSION:\n                        require(profile.kind==0, 'V9 fixed native palette required')\n                        validate_sdf(i,sdf,material)\n                    else:require(sdf is None and material is None,'SDF requires V9')\n                    alpha_present = coverage is not None"),
 ("coverage.tobytes() if alpha_present else b''):","coverage.tobytes() if alpha_present else b'', sdf.tobytes() if version==SDF_VERSION else b'', material.tobytes() if version==SDF_VERSION else b''):"),
 ('int(present),int(alpha_present),len(stored[0])','int(present),2 if version==SDF_VERSION else int(alpha_present),len(stored[0])'),
 ('output.write(stored[0]); output.write(stored[1])',"if version==SDF_VERSION:\n                        for k in (3,4):output.write(struct.pack('<IB3x',len(stored[k]),codecs[k]))\n                    output.write(stored[0]); output.write(stored[1])"),
 ('if version == CONTOUR_VERSION: output.write(stored[2])', 'if version == CONTOUR_VERSION: output.write(stored[2])\n                    if version==SDF_VERSION:output.write(stored[3]);output.write(stored[4])'),
 ('version in (VERSION,CONTOUR_VERSION)','version in (VERSION,CONTOUR_VERSION,SDF_VERSION)'),
 ('resources, frames_total, indices_total, coverage_total = [], 0, 0, 0','resources, frames_total, indices_total, coverage_total, sdf_total = [], 0, 0, 0, 0'),
 ('res in ((0,1) if version==CONTOUR_VERSION else (0,))','res in ((2,) if version==SDF_VERSION else ((0,1) if version==CONTOUR_VERSION else (0,)))'),
 ("reps = np.frombuffer(h,'<u2',256,16)","sdf_headers=[];sn=(w*2+12)*(he*2+12)\n                if version==SDF_VERSION:\n                    require(kind==0,'V9 native kind')\n                    for length in (sn,sn*4):\n                        sh=take(8);sz,sc=struct.unpack_from('<IB',sh)\n                        require(sh[5:]==bytes(3) and ((sc==0 and sz==length) or (sc==1 and 0<sz<length)),'SDF header')\n                        sdf_headers.append((sz,sc,length))\n                    sdf_total+=sn*5\n                    require(sdf_total<=registry.MAX_LAZY_FRAME_INDEX_BYTES,'resident SDF limit')\n                reps = np.frombuffer(h,'<u2',256,16)"),
 ('coverage_total += n if res else 0',"if version==SDF_VERSION:\n                    sp=[]\n                    for sz,sc,length in sdf_headers:sp.append(v6._decode_plane(sc,take(sz),length,decoder))\n                    s=np.frombuffer(sp[0],np.uint8).reshape(he*2+12,w*2+12)\n                    m=np.frombuffer(sp[1],'<u4').reshape(s.shape)\n                    validate_sdf(i,s,m)\n                coverage_total += n if version==CONTOUR_VERSION and res else 0"),
 ("if version==CONTOUR_VERSION:frame['A']=a.copy()","if version==CONTOUR_VERSION:frame['A']=a.copy()\n                    if version==SDF_VERSION:frame['S']=s.copy();frame['M']=m.copy()"),
 ("if version==CONTOUR_VERSION:info['coverage_bytes']=coverage_total","if version==CONTOUR_VERSION:info['coverage_bytes']=coverage_total\n    if version==SDF_VERSION:info['sdf_bytes']=sdf_total")])

p=E/'src/iee/creature_sprite_x2.cpp'
edit(p,[
 ('constexpr bool partner_version','constexpr std::uint32_t kXnSdfRegistryVersion = 9;\nconstexpr int kSdfPad = 6;\nconstexpr bool partner_version'),
 ('version == kXnPartnerRegistryVersion || version == kXnContourRegistryVersion','version == kXnPartnerRegistryVersion || version == kXnContourRegistryVersion || version == kXnSdfRegistryVersion'),
 ('std::vector<std::uint8_t> coverage;','std::vector<std::uint8_t> coverage;\n  std::vector<std::uint8_t> sdf;\n  std::vector<std::uint32_t> sdfMaterial;'),
 ('std::uint16_t animationId, int maximumMipLevel) noexcept {','std::uint16_t animationId, int maximumMipLevel, bool sdfEncoded = false) noexcept {'),
 ('maximumMipLevel > 0);','maximumMipLevel > 0, sdfEncoded);'),
 ('? std::to_integer<std::uint8_t>(frameReserved[2]) > 1\n              : frameReserved[2] != std::byte{0}', '? std::to_integer<std::uint8_t>(frameReserved[2]) > 1\n              : (parsed.version == kXnSdfRegistryVersion ? frameReserved[2] != std::byte{2} : frameReserved[2] != std::byte{0})'),
 ('const bool coveragePresent = parsed.version', 'const bool sdfPresent = parsed.version == kXnSdfRegistryVersion;\n      const auto sdfPixels = static_cast<std::uint64_t>(width * 2 + 12) * (height * 2 + 12);\n      std::array<std::uint32_t, 2> sdfStored{};\n      std::array<std::uint8_t, 2> sdfCodec{};\n      const bool coveragePresent = parsed.version'),
 ('if (!checked_add(decodedPayloadBytes, expectedIndices', '''if (sdfPresent) {
        if (parsed.scale != 2 || !frame.partnerProfile || frame.partnerProfile->nativeKind != 0 ||
            !checked_add(decodedCoverageBytes, sdfPixels * 5, kCatalogMetadataCacheBudgetBytes))
          throw std::runtime_error("invalid V9 SDF scope/limit");
        for (int k = 0; k < 2; ++k) {
          std::array<std::byte,3> reserved{};
          const auto length = sdfPixels * (k == 0 ? 1 : 4);
          if (!reader.read(sdfStored[k]) || !reader.read(sdfCodec[k]) || !reader.read(reserved) ||
              reserved != std::array<std::byte,3>{} ||
              !((sdfCodec[k] == kRegistryFrameCodecRaw && sdfStored[k] == length) ||
                (sdfCodec[k] == kRegistryFrameCodecXpressHuff && sdfStored[k] > 0 && sdfStored[k] < length)))
            throw std::runtime_error("invalid V9 SDF header");
        }
      }
      if (!checked_add(decodedPayloadBytes, expectedIndices'''),
 ('if (fractionalRegistry) {\n        // Validate', '''std::array<const std::byte*,2> sdfData{};
      if (sdfPresent) for (int k = 0; k < 2; ++k)
        if (!reader.read_view(sdfData[k], sdfStored[k])) throw std::runtime_error("truncated V9 SDF plane");
      if (fractionalRegistry) {
        // Validate'''),
 ('std::uint8_t codec) {\n          std::vector<std::uint8_t> result(static_cast<std::size_t>(expectedIndices));', 'std::uint8_t codec, std::size_t decodedLength) {\n          std::vector<std::uint8_t> result(decodedLength);'),
 ('inflate(indexData, storedBytes, frameCodec)','inflate(indexData, storedBytes, frameCodec, static_cast<std::size_t>(expectedIndices))'),
 ('inflate(fractionData, fractionStored, fractionCodec)','inflate(fractionData, fractionStored, fractionCodec, static_cast<std::size_t>(expectedIndices))'),
 ('inflate(coverageData, coverageStored, coverageCodec)','inflate(coverageData, coverageStored, coverageCodec, static_cast<std::size_t>(expectedIndices))'),
 ('if (coveragePresent) {\n          frame.coverage', '''if (sdfPresent) {
          frame.sdf = inflate(sdfData[0], sdfStored[0], sdfCodec[0], static_cast<std::size_t>(sdfPixels));
          const auto material = inflate(sdfData[1], sdfStored[1], sdfCodec[1], static_cast<std::size_t>(sdfPixels * 4));
          frame.sdfMaterial.resize(static_cast<std::size_t>(sdfPixels));
          std::memcpy(frame.sdfMaterial.data(), material.data(), material.size());
          const bool foreground = std::any_of(logicalI.begin(), logicalI.end(), [](auto i){ return i >= 2; });
          for (std::size_t n = 0; n < frame.sdf.size(); ++n) {
            const auto m = frame.sdfMaterial[n];
            if (frame.sdf[n] >= 128 || (foreground ? m >= logicalI.size() || logicalI[m] < 2
                                                 : m != 0xffffffffu || frame.sdf[n] >= 64))
              throw std::runtime_error("invalid V9 SDF material reference");
          }
        }
        if (coveragePresent) {
          frame.coverage'''),
 ('if (!add(frame.coverage.size()))', 'if (!add(frame.sdf.size()) || !add(frame.sdfMaterial.size() * 4)) return (std::numeric_limits<std::uint64_t>::max)();\n      if (!add(frame.coverage.size()))')])

# Encode only upload pixels. Original Q3m CPU reconstruction/composition remains unchanged.
helper='''
bool encode_sdf_canvas(const Frame& frame, const std::vector<std::uint8_t>& indices,
                       const std::vector<std::uint8_t>& fractions,
                       const std::array<std::uint32_t,256>& realized,
                       std::vector<std::uint32_t>& canvas, int width, int height,
                       int offsetX, int offsetY) {
  if (frame.sdf.empty()) return false;
  core::palette_fraction::Lut lut;
  if (!prepare_frame_lut(frame,indices,fractions,realized,lut)) return false;
  const int sw=frame.logicalWidth*2, sh=frame.logicalHeight*2, fw=sw+12;
  for (int y=0;y<sh+12;++y) for (int x=0;x<fw;++x) {
    const int dx=offsetX+x-kSdfPad, dy=offsetY+y-kSdfPad;
    if (dx<0 || dy<0 || dx>=width || dy>=height) continue;
    const auto n=static_cast<std::size_t>(y)*fw+x;
    const auto m=frame.sdfMaterial[n];
    const auto pixel=m==0xffffffffu ? 0u : frame_pixel(frame,indices,fractions,realized,lut,m);
    auto& dest=canvas[static_cast<std::size_t>(dy)*width+dx];
    // Maximum distance implements the union of body/earth silhouettes.
    if (frame.sdf[n] >= ((dest>>24)&127u)) dest=(pixel&0x00ffffffu)|(static_cast<std::uint32_t>(frame.sdf[n])<<24);
  }
  return true;
}

bool finish_sdf_canvas(const std::vector<std::uint32_t>& source, std::vector<std::uint32_t>& encoded) {
  if (source.size()!=encoded.size()) return false;
  for (std::size_t n=0;n<source.size();++n) {
    const auto alpha=source[n]>>24;
    if (alpha==255) encoded[n]=(encoded[n]&0xff000000u)|(source[n]&0x00ffffffu);
    else if (alpha) {
      // Native kind-0 shadows are black, alpha 127. Reject another contract.
      if (alpha!=127 || (source[n]&0x00ffffffu)) return false;
      encoded[n]|=0x80000000u;
    }
  }
  return true;
}

bool encode_sdf_composite(const CompositeLayer* layers, std::size_t count,
                           const CompositeBounds& bounds, int width, int height,
                           const std::vector<std::uint32_t>& source,
                           std::vector<std::uint32_t>& encoded, bool& present) {
  present=false;
  for (std::size_t k=0;k<count;++k) {
    const auto* r=resource_for_handle_locked(layers[k].frame);
    if (!r || layers[k].frame.frameIndex>=r->frames.size()) return false;
    present=present || !r->frames[layers[k].frame.frameIndex].sdf.empty();
  }
  if (!present) return true;
  encoded.assign(source.size(),0);
  for (std::size_t k=0;k<count;++k) {
    const auto& layer=layers[k];
    const auto* r=resource_for_handle_locked(layer.frame);
    const auto& f=r->frames[layer.frame.frameIndex];
    const auto* i=frame_indices_locked(layer.frame,true);
    const auto* fractions=frame_fractions_locked(layer.frame);
    auto palette=layer.palette.colors;enforce_transparent_entry(f,palette);
    if (!i || !fractions || f.sdf.empty() ||
        !encode_sdf_canvas(f,*i,*fractions,palette,encoded,width,height,
                          static_cast<int>(physical_layer_offset(f.centerX,bounds.left,2)),
                          static_cast<int>(physical_layer_offset(f.centerY,bounds.top,2)))) return false;
  }
  return finish_sdf_canvas(source,encoded);
}

'''
edit(p,[('bool upload_frame_locked(',helper+'bool upload_frame_locked('),
 ('                           static_cast<int>(contentOffset))) {\n    return false;\n  }',
 '''                           static_cast<int>(contentOffset))) {
    return false;
  }
  const bool sdfEncoded = !frame.sdf.empty();
  if (sdfEncoded) {
    if (physicalScale != 2 || creature_sprite_filter::registry().effective_mode(animationId,2) != core::CreatureSpriteFilterMode::CatmullRom) return false;
    auto encoded = std::vector<std::uint32_t>(replacement.size(),0);
    if (!encode_sdf_canvas(frame,indices,fractions,realized,encoded,physicalWidth,physicalHeight,
                          static_cast<int>(contentOffset),static_cast<int>(contentOffset)) ||
        !finish_sdf_canvas(replacement,encoded)) return false;
    replacement.swap(encoded);
  }
'''),
 ('animationId, maximumMipLevel);\n    if (mips && !published)', 'animationId, maximumMipLevel, sdfEncoded);\n    if ((mips || sdfEncoded) && !published)',2),
 ('std::uint16_t animationId) noexcept {\n  core::sprite_p4::ScopedMetric uploadMetric','std::uint16_t animationId, bool sdfEncoded) noexcept {\n  core::sprite_p4::ScopedMetric uploadMetric'),
 ('    transientTextureId =\n        api.DrawGenTexture', '''    std::vector<std::uint32_t> sdfPixels;
    bool sdfEncoded=false;
    if (!encode_sdf_composite(layers,layerCount,bounds,logicalWidth*physicalScale,logicalHeight*physicalScale,*pixels,sdfPixels,sdfEncoded)) return false;
    if (sdfEncoded) {
      if (physicalScale!=2 || creature_sprite_filter::registry().effective_mode(layers[0].frame.animationId,2)!=core::CreatureSpriteFilterMode::CatmullRom) return false;
      pixels=&sdfPixels;
    }
    transientTextureId =
        api.DrawGenTexture'''),
 ('api, probeTarget, layers[0].frame.animationId))','api, probeTarget, layers[0].frame.animationId, sdfEncoded))')])

edit(E/'src/iee/creature_sprite_filter.h',[
 ('  bool premultiplied{};','  bool premultiplied{};\n  bool sdfEncoded{};'),
 ('bool premultiplied = false) noexcept;', 'bool premultiplied = false, bool sdfEncoded = false) noexcept;')])
edit(E/'src/iee/creature_sprite_filter.cpp',[
 ('bool premultiplied) noexcept {','bool premultiplied, bool sdfEncoded) noexcept {'),
 ('  const bool mips = mode == core::CreatureSpriteFilterMode::Mipmaps;', '  if (sdfEncoded && (mode != core::CreatureSpriteFilterMode::CatmullRom || masked || scale != 2)) return false;\n  const bool mips = mode == core::CreatureSpriteFilterMode::Mipmaps;'),
 ('              .premultiplied = premultiplied,','              .premultiplied = premultiplied,\n              .sdfEncoded = sdfEncoded,')
])
edit(E/'src/iee/shader_uniform_bridge.h',[
 ('  int creatureTexelSize{kUnresolved};','  int creatureTexelSize{kUnresolved};\n  int creatureSdfEncoded{kUnresolved};'),
 ('const shader_suite::CreatureHdDrawStyle& style) noexcept;', 'const shader_suite::CreatureHdDrawStyle& style, bool sdfEncoded = false) noexcept;')])
edit(E/'src/iee/shader_uniform_bridge.cpp',[
 ('  return locations.creatureSampler >= 0', '  locations.creatureSdfEncoded = resolve_location(gl, program, locations.creatureSdfEncoded, "uIeeCreatureSdfEncoded");\n  return locations.creatureSampler >= 0'),
 ('const shader_suite::CreatureHdDrawStyle& style) noexcept {','const shader_suite::CreatureHdDrawStyle& style, bool sdfEncoded) noexcept {'),
 ('  gl.glUniform1f(locations.creatureFilterMode, mode);','  if (sdfEncoded && locations.creatureSdfEncoded < 0) return false;\n  if (locations.creatureSdfEncoded >= 0) gl.glUniform1f(locations.creatureSdfEncoded, sdfEncoded ? 1.0f : 0.0f);\n  gl.glUniform1f(locations.creatureFilterMode, mode);')])
edit(E/'src/iee/shader_probe.cpp',[
 ('decision.texelHeight, resolved.style);','decision.texelHeight, resolved.style, metadata->sdfEncoded);')])
