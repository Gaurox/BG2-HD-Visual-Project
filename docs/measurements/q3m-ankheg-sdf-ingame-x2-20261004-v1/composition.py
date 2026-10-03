"""Independent native body/earth union fixtures, including reversed order and K6 tints."""
import sys,json,struct,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;E=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
exec((HERE/'implement.py').read_text().split("p=ROOT/'pipeline/scripts")[0])
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_partner_registry as leaves
import run_creature_sprite_x2 as registry
from palette_work_plan import write_json
work=ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1';pack=json.loads((work/'isolated/pack.json').read_text())
resources=[leaves.inspect(work/'isolated'/registry.catalog_shard_filename(i['sha256']),include_frames=True)['resources'][0] for i in pack['leaves']]
oracle=(work/'isolated/witnesses.oracle').read_bytes();pos=12;palettes=[]
for r in resources:
    _,_,_,nf,nc=struct.unpack_from('<II8sII',oracle,pos);pos+=24
    palettes.append(np.frombuffer(oracle,np.uint8,6144,pos).reshape(6,256,4));pos+=6144+2052
    for _ in range(nc):n=struct.unpack_from('<I',oracle,pos)[0];pos+=4+n*4
    pos+=nf*208
names=[r['resref'] for r in resources]
cases=[];payload=bytearray((work/'isolated/sdf.oracle').read_bytes())
for ref,body in [('MAKHG1',11),('MAKHG1',25),('MAKHG3',20),('MAKHG1E',25)]:
    earth='MAKHDG'+ref[5:];bi,ei=names.index(ref),names.index(earth)
    for earth_frame in (0,6,13):
        for reverse in (False,True):
            for palette in (0,5):
                layers=[(ei,earth_frame),(bi,body)]
                if reverse:layers.reverse()
                frames=[resources[i]['frames'][f] for i,f in layers]
                left=min(-f['geometry'][2] for f in frames);top=min(-f['geometry'][3] for f in frames)
                right=max(f['geometry'][0]-f['geometry'][2] for f in frames);bottom=max(f['geometry'][1]-f['geometry'][3] for f in frames)
                w,h=(right-left+2)*2,(bottom-top+2)*2
                source=np.zeros((h,w,4),np.uint8);encoded=source.copy()
                for (ri,fi),f in zip(layers,frames):
                    rgba=resources[ri]['profile'].decode(f['I'],f['F'],palettes[ri][palette])
                    _,_,cx,cy,_=f['geometry'];x=(-cx-left+1)*2;y=(-cy-top+1)*2
                    canvas=source[y:y+rgba.shape[0],x:x+rgba.shape[1]];active=rgba[...,3]>0;canvas[active]=rgba[active]
                    s,m=f['S'],f['M'];extended=np.zeros((*s.shape,4),np.uint8);valid=m!=0xffffffff
                    extended[valid,:3]=rgba.reshape(-1,4)[m[valid],:3];extended[...,3]=s
                    x0=max(0,x-6);y0=max(0,y-6);x1=min(w,x-6+s.shape[1]);y1=min(h,y-6+s.shape[0])
                    view=extended[y0-y+6:y1-y+6,x0-x+6:x1-x+6];dest=encoded[y0:y1,x0:x1];take=view[...,3]>=dest[...,3];dest[take]=view[take]
                active=source[...,3]==255;encoded[active,:3]=source[active,:3];encoded[...,3]|=(source[...,3]==127).astype(np.uint8)*128
                cases.append((layers,palette,(left,top,right,bottom),hashlib.sha256(source.tobytes()).digest(),hashlib.sha256(encoded.tobytes()).digest()))
payload.extend(struct.pack('<I',len(cases)))
for layers,palette,bounds,plain,encoded in cases:
    payload.extend(struct.pack('<II',len(layers),palette))
    for ri,fi in layers:payload.extend(struct.pack('<II',ri,fi))
    payload.extend(struct.pack('<4i',*bounds));payload.extend(plain);payload.extend(encoded)
(work/'isolated/sdf-composite.oracle').write_bytes(payload)
edit(E/'tests/palette_partner_tests.cpp',[
 ('    std::uint64_t frames{},slots{},pixelsTotal{};', '    std::vector<cs::FrameHandle> handles;std::vector<std::array<pf::Palette,6>> witnessPalettes;\n    std::uint64_t frames{},slots{},pixelsTotal{};'),
 ('      require(resolved,"no native frames resolved");','      require(resolved,"no native frames resolved");\n      handles.push_back(handle);witnessPalettes.push_back(palettes);'),
 ('    require(oracle.peek()==std::char_traits<char>::eof(),"oracle trailing bytes");', '''    unsigned composites=0;
    if(argc==4 && sdfOracle.peek()!=std::char_traits<char>::eof()) {
      read(sdfOracle,composites);require(composites<=128,"SDF composite count");
      for(unsigned n=0;n<composites;++n) {
        unsigned count{},palette{};read(sdfOracle,count);read(sdfOracle,palette);
        require(count>0&&count<=8&&palette<6,"SDF layers/palette");
        std::vector<cs::CompositeLayer> layers(count);
        for(auto& layer:layers) {
          unsigned ri{},fi{};read(sdfOracle,ri);read(sdfOracle,fi);require(ri<handles.size(),"SDF resource");
          layer.frame=handles[ri];layer.frame.frameIndex=fi;layer.palette.colors=witnessPalettes[ri][palette];layer.palette.encoding={0x1908,0x1401};
        }
        std::array<int,4> expectedBounds{};read(sdfOracle,expectedBounds);
        std::array<unsigned char,32> plain{},encoded{};read(sdfOracle,plain);read(sdfOracle,encoded);
        std::vector<std::uint32_t> pixels;cs::CompositeBounds bounds{};
        require(cs::reconstruct_composite_pixels(layers.data(),count,pixels,bounds)&&pixel_sha(pixels)==plain,"native layering changed");
        require(bounds.left==expectedBounds[0]&&bounds.top==expectedBounds[1]&&bounds.right==expectedBounds[2]&&bounds.bottom==expectedBounds[3],"SDF layer centers changed");
        require(cs::reconstruct_composite_sdf_pixels(layers.data(),count,pixels,bounds)&&pixel_sha(pixels)==encoded,"body/earth SDF union bytes differ");
      }
      std::cout<<"SDF composite golden cases passed: "<<composites<<"\\n";
    }
    require(oracle.peek()==std::char_traits<char>::eof(),"oracle trailing bytes");''')])
print(json.dumps(dict(composite_cases=len(cases))))
