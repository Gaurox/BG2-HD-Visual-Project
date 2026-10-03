// IEE_CREATURE_SDF_CONTRACT_V1
// V9: RGB = extruded live Q3m material. A = 7-bit signed distance + shadow bit.
// Distance units are x2 texels, encoded as round(distance*16)+64.
lowp vec4 ieeFetchCreatureSdf(in mediump vec2 texCoord)
{
    mediump vec2 q = texCoord / uIeeCreatureTexelSize - vec2(0.5);
    mediump vec2 base = floor(q);
    mediump vec2 phase = q - base;
    mediump vec4 wx = ieeCreatureCatmullRomWeights(phase.x);
    mediump vec4 wy = ieeCreatureCatmullRomWeights(phase.y);
    mediump float distances[16];
    mediump vec3 rgb = vec3(0.0);
    mediump float shadow = 0.0;
    for (int y = 0; y < 4; ++y)
    {
        for (int x = 0; x < 4; ++x)
        {
            lowp vec4 tap = texture2D(uTex, (base + vec2(float(x-1), float(y-1)) + vec2(0.5)) * uIeeCreatureTexelSize);
            mediump float code = floor(tap.a * 255.0 + 0.5);
            distances[y*4+x] = (mod(code, 128.0) - 64.0) / 16.0;
            mediump float weight = wx[x] * wy[y];
            rgb += tap.rgb * weight;
            shadow += floor(code / 128.0) * (127.0/255.0) * weight;
        }
    }
    // Integrate the bilinear field over one screen pixel: same 8x8 rule as PDF.
    mediump vec2 footprint = (abs(dFdx(texCoord)) + abs(dFdy(texCoord))) / uIeeCreatureTexelSize;
    mediump float alpha = 0.0;
    if (max(footprint.x, footprint.y) <= 2.0)
    {
        for (int y = 0; y < 8; ++y)
        {
            for (int x = 0; x < 8; ++x)
            {
                mediump vec2 p = phase + (vec2(float(x)+0.5, float(y)+0.5)/8.0 - vec2(0.5)) * footprint;
                mediump vec2 cell = floor(p);
                mediump vec2 f = p - cell;
                int index = (int(cell.y)+1)*4 + int(cell.x)+1;
                mediump float upper = mix(distances[index], distances[index+1], f.x);
                mediump float lower = mix(distances[index+4], distances[index+5], f.x);
                alpha += mix(upper, lower, f.y) > 0.0 ? 1.0/64.0 : 0.0;
            }
        }
    }
    else
    {
        // Extreme zoom-out exceeds this sixteen-texel stencil.
        mediump float distance = mix(mix(distances[5],distances[6],phase.x), mix(distances[9],distances[10],phase.x),phase.y);
        mediump float width = max(max(footprint.x,footprint.y),0.0001);
        alpha = smoothstep(-width*0.5,width*0.5,distance);
    }
    mediump float total = alpha + clamp(shadow,0.0,1.0)*(1.0-alpha);
    if (total <= 0.000001) return vec4(0.0);
    return vec4(clamp(rgb,0.0,1.0)*alpha/total,total);
}

mediump float ieeCreatureNativeAlpha(in mediump vec2 texCoord)
{
    mediump float a = texture2D(uTex,texCoord).a;
    if (uIeeCreatureSdfEncoded < 0.5) return a;
    mediump float code = floor(a*255.0+0.5);
    return mod(code,128.0) > 64.0 ? 1.0 : floor(code/128.0)*(127.0/255.0);
}
