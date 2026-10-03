from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];E=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
exec((Path(__file__).with_name('implement.py')).read_text().split("p=ROOT/'pipeline/scripts")[0])
p=E/'src/iee/creature_sprite_x2.cpp';s=p.read_text()
start=s.index('bool reconstruct_frame_pixels(');end=s.index('bool frame_uses_q3m_profile(',start)
base=s[start:end];clone=base.replace('bool reconstruct_frame_pixels(', 'bool reconstruct_frame_sdf_pixels(',1)
clone=clone.replace('    fingerprint = palette_fingerprint(frame, realized, palette.encoding);', '''    if (frame.sdf.empty() || scale!=2) return false;
    std::vector<std::uint32_t> source(static_cast<std::size_t>(width+12)*(height+12),0);
    for (int y=0;y<height;++y) std::copy_n(pixels.begin()+static_cast<std::size_t>(y)*width,width,source.begin()+static_cast<std::size_t>(y+6)*(width+12)+6);
    pixels.assign(source.size(),0);
    if (!encode_sdf_canvas(frame,*indices,*fractions,realized,pixels,width+12,height+12,6,6) || !finish_sdf_canvas(source,pixels)) return false;
    fingerprint = palette_fingerprint(frame, realized, palette.encoding);''')
edit(p,[(base,base+clone)])
s=p.read_text();start=s.index('bool reconstruct_composite_pixels(');end=s.index('bool ensure_frame_payload_available(',start)
base=s[start:end];clone=base.replace('bool reconstruct_composite_pixels(', 'bool reconstruct_composite_sdf_pixels(',1)
clone=clone.replace('    pixels = *cached;', '''    bool present=false;
    if (!encode_sdf_composite(layers,layerCount,bounds,bounds.logical_width()*2,bounds.logical_height()*2,*cached,pixels,present) || !present) return false;''')
edit(p,[(base,base+clone)])
edit(E/'src/iee/creature_sprite_x2.h',[
 ('// Diagnostic routing: V6', '''// V9 host diagnostics expose the exact encoded GPU plane, six-texel border.
bool reconstruct_frame_sdf_pixels(FrameHandle handle, const PaletteSnapshot& palette,
                                  std::vector<std::uint32_t>& pixels, std::uint64_t& fingerprint) noexcept;
bool reconstruct_composite_sdf_pixels(const CompositeLayer* layers, std::size_t layerCount,
                                      std::vector<std::uint32_t>& pixels, CompositeBounds& bounds) noexcept;
// Diagnostic routing: V6''')])
edit(E/'tests/palette_partner_tests.cpp',[
 ('require(argc==3,"usage: palette_partner_tests assets witnesses.oracle");','require(argc==3 || argc==4,"usage: palette_partner_tests assets witnesses.oracle [sdf.oracle]");\n    std::ifstream sdfOracle; if (argc==4) sdfOracle.open(argv[3],std::ios::binary);\n    if (argc==4) { std::array<char,8> m{};read(sdfOracle,m);require(m==std::array<char,8>{\'I\',\'E\',\'E\',\'S\',\'D\',\'F\',\'1\',0},"SDF oracle header"); }'),
 ('std::array<unsigned char,32> expected{};read(oracle,expected);','std::array<unsigned char,32> expected{};read(oracle,expected);\n          std::array<unsigned char,32> expectedSdf{};if(argc==4)read(sdfOracle,expectedSdf);'),
 ('require(pixel_sha(pixels)==expected,"Python/C++ V7 pixel bytes differ"); pixelsTotal+=pixels.size();','''require(pixel_sha(pixels)==expected,"Python/C++ V7 pixel bytes differ"); pixelsTotal+=pixels.size();
            if (argc==4) {
              require(cs::reconstruct_frame_sdf_pixels(handle,palette,pixels,fingerprint)&&pixels.size()==std::uint64_t(w*2+12)*(h*2+12),"SDF upload extent");
              if(encoding)for(auto& color:pixels)color=swap_rb(color);
              require(pixel_sha(pixels)==expectedSdf,"Python/C++ SDF upload bytes differ");
            }'''),
 ('        ++frames;', '''        if (argc==4) {
          std::array<unsigned char,32> expectedComposite{};read(sdfOracle,expectedComposite);
          require(cs::reconstruct_composite_sdf_pixels(&layer,1,pixels,bounds),"SDF native composition failed");
          require(pixel_sha(pixels)==expectedComposite,"SDF native composition bytes differ");
        }
        ++frames;'''),
 ('require(oracle.peek()==std::char_traits<char>::eof(),"oracle trailing bytes");','require(oracle.peek()==std::char_traits<char>::eof(),"oracle trailing bytes");\n    if(argc==4)require(sdfOracle.peek()==std::char_traits<char>::eof(),"SDF oracle trailing bytes");')])
