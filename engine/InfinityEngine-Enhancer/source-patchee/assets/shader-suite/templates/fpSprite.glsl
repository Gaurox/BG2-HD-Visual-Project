// fpSprite.glsl
// D6 source derived from BG2EE 2.7.3.0; native operations preserved below.

uniform lowp sampler2D uTex;
uniform lowp float uSpriteBlurAmount;
varying mediump vec2 vTc;
varying lowp vec4 vColor;

@@IEE_CREATURE_HD_COMMON@@

mediump float normpdf(in mediump float x, in mediump float sigma)
{
	return 0.39894*exp(-0.5*x*x/(sigma*sigma))/sigma;
}

void main()
{
	bool styleActive = ieeCreatureStyleActive();
	bool reconstruct = uIeeCreatureFilterMode > 1.5 &&
		uIeeCreatureTexelSize.x > 0.0 && uIeeCreatureTexelSize.y > 0.0;
	bool sharpenActive = styleActive && abs(uIeeCreatureSharpen) > 0.000001;
	mediump vec3 gaussianRgb = vec3(0.0);
	lowp vec4 texColor;
	if (reconstruct || sharpenActive)
	{
		texColor = ieeFetchCreatureCatmullRom(
			vTc, uIeeCreatureTexelSize, reconstruct, gaussianRgb);
	}
	else if (styleActive)
	{
		texColor = ieeCreatureWorkingSample(vTc);
	}
	else
	{
		texColor = texture2D(uTex, vTc);
	}
	if (sharpenActive && texColor.a > 0.000001)
	{
		texColor.rgb = texColor.rgb * (1.0 + uIeeCreatureSharpen) -
			gaussianRgb * uIeeCreatureSharpen;
	}

	lowp vec4 outColor = texColor;
	if (!styleActive || uIeeCreatureOutlineMode <= 0.5)
	{
		const int mSize = 5;
		const int kSize = (mSize-1)/2;
		int solidPixelCount = 0;
		mediump float kernel[mSize];
		lowp vec4 blurColour = vec4(0.0);
		mediump float sigma = 7.0;
		mediump float normalization = 0.0;
		for (int j = 0; j <= kSize; ++j)
		{
			kernel[kSize+j] = kernel[kSize-j] = normpdf(float(j), sigma);
		}
		for (int j = 0; j < mSize; ++j)
		{
			normalization += kernel[j];
		}
		for (int i=-kSize; i <= kSize; ++i)
		{
			for (int j=-kSize; j <= kSize; ++j)
			{
				mediump vec2 coordinate = vTc + vec2(float(i) * .0005,float(j) * .0005);
				lowp vec4 sampleColor = styleActive
					? ieeCreatureWorkingSample(coordinate)
					: texture2D(uTex, coordinate);
				blurColour += kernel[kSize+j]*kernel[kSize+i]*sampleColor;
				if (sampleColor.a > 0.5)
				{
					solidPixelCount = solidPixelCount+1;
				}
			}
		}
		if (solidPixelCount > 0)
		{
			blurColour.a = blurColour.a * uSpriteBlurAmount;
		}
		blurColour = blurColour/(normalization*normalization);
		outColor = mix(blurColour, texColor, texColor.a);
	}
	else
	{
		outColor = ieeApplyCreatureOutline(
			texColor, vec3(0.0), vTc, uIeeCreatureTexelSize, 1.0);
	}
	gl_FragColor = styleActive ? ieeFinishCreatureColor(outColor) : outColor;
}
