// fpSELECT.glsl
// D6 source derived from BG2EE 2.7.3.0; native operations preserved below.

uniform lowp sampler2D uTex;
uniform lowp float uSpriteBlurAmount;
uniform mediump vec2 uTcScale;
varying mediump vec2 vTc;
varying lowp vec4 vColor;

@@IEE_CREATURE_HD_COMMON@@

mediump float normpdf(in mediump float x, in mediump float sigma)
{
	return 0.39894*exp(-0.5*x*x/(sigma*sigma))/sigma;
}

const float fSolidThreshold = 0.1;

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

	lowp vec4 outColor;
	if (styleActive && uIeeCreatureOutlineMode > 0.5)
	{
		outColor = ieeApplyCreatureOutline(
			texColor, ieeCreatureWorkingRgb(vColor.rgb), vTc,
			uIeeCreatureTexelSize, 1.0);
	}
	else if (texColor.a > fSolidThreshold)
	{
		lowp vec4 selectionColor = vColor;
		if (styleActive)
		{
			selectionColor.rgb = ieeCreatureWorkingRgb(selectionColor.rgb);
		}
		outColor = mix(selectionColor, texColor, texColor.a);
	}
	else
	{
		int x,y;
		int kSize = 3;
		float minDist = float(kSize)+1.0;
		for (x = -kSize ; x <= kSize ; x++)
		{
			for (y = -kSize ; y <= kSize ; y++)
			{
				vec2 sampleCoord = vTc + vec2(float(x), float(y))*uTcScale;
				sampleCoord = sampleCoord/uTcScale;
				sampleCoord = sampleCoord + vec2(0.5, 0.5);
				sampleCoord.x = float(int(sampleCoord.x));
				sampleCoord.y = float(int(sampleCoord.y));
				sampleCoord = sampleCoord + vec2(0.5, 0.5);
				sampleCoord = sampleCoord * uTcScale;
				vec2 coordDiff = abs(vTc - sampleCoord)/uTcScale;
				vec4 texSample = texture2D(uTex, sampleCoord);
				if (texSample.a > fSolidThreshold)
				{
					float distance = sqrt((coordDiff.x*coordDiff.x) + (coordDiff.y*coordDiff.y));
					minDist = min(minDist, distance);
				}
			}
		}
		minDist = max(0.0, minDist-1.1);
		minDist = minDist/float(kSize);
		lowp vec4 selectionColor = vColor;
		if (styleActive)
		{
			selectionColor.rgb = ieeCreatureWorkingRgb(selectionColor.rgb);
		}
		outColor = mix(selectionColor, vec4(0,0,0,0), minDist);
	}
	gl_FragColor = styleActive ? ieeFinishCreatureColor(outColor) : outColor;
}
