// fpSELECT.glsl
// D5 filtering source derived from BG2EE 2.7.3.0.
// IEE_CREATURE_ROUTING_CONTRACT_V1
// IEE_CREATURE_FILTER_CONTRACT_V1

uniform lowp sampler2D uTex;
uniform lowp float uSpriteBlurAmount;
uniform mediump vec2 uTcScale;
uniform lowp float uIeeShaderSuiteEnabled;
uniform lowp float uIeeCreatureFilterMode;
uniform mediump vec2 uIeeCreatureTexelSize;
varying mediump vec2 vTc;
varying lowp vec4 vColor;

mediump vec4 ieeCreatureCatmullRomWeights(in mediump float phase)
{
	mediump float phase2 = phase * phase;
	mediump float phase3 = phase2 * phase;
	return vec4(
		-0.5 * phase3 + phase2 - 0.5 * phase,
		 1.5 * phase3 - 2.5 * phase2 + 1.0,
		-1.5 * phase3 + 2.0 * phase2 + 0.5 * phase,
		 0.5 * phase3 - 0.5 * phase2);
}

mediump vec4 ieePremultipliedCreatureTap(in mediump vec2 texCoord)
{
	lowp vec4 sampleColor = texture2D(uTex, texCoord);
	mediump float alpha = clamp(sampleColor.a, 0.0, 1.0);
	return vec4(sampleColor.rgb * alpha, alpha);
}

mediump vec4 ieeFetchCreatureCatmullRom(in mediump vec2 texCoord,
										in mediump vec2 texelSize)
{
	mediump vec2 q = texCoord / texelSize - vec2(0.5);
	mediump vec2 baseTexel = floor(q);
	mediump vec2 phase = q - baseTexel;
	mediump vec4 weightsX = ieeCreatureCatmullRomWeights(phase.x);
	mediump vec4 weightsY = ieeCreatureCatmullRomWeights(phase.y);

	mediump vec2 tc0 = (baseTexel + vec2(-1.0) + vec2(0.5)) * texelSize;
	mediump vec2 tc1 = (baseTexel + vec2( 0.0) + vec2(0.5)) * texelSize;
	mediump vec2 tc2 = (baseTexel + vec2( 1.0) + vec2(0.5)) * texelSize;
	mediump vec2 tc3 = (baseTexel + vec2( 2.0) + vec2(0.5)) * texelSize;

	mediump vec4 filtered = vec4(0.0);
	filtered += ieePremultipliedCreatureTap(vec2(tc0.x, tc0.y)) * weightsX.x * weightsY.x;
	filtered += ieePremultipliedCreatureTap(vec2(tc1.x, tc0.y)) * weightsX.y * weightsY.x;
	filtered += ieePremultipliedCreatureTap(vec2(tc2.x, tc0.y)) * weightsX.z * weightsY.x;
	filtered += ieePremultipliedCreatureTap(vec2(tc3.x, tc0.y)) * weightsX.w * weightsY.x;
	filtered += ieePremultipliedCreatureTap(vec2(tc0.x, tc1.y)) * weightsX.x * weightsY.y;
	filtered += ieePremultipliedCreatureTap(vec2(tc1.x, tc1.y)) * weightsX.y * weightsY.y;
	filtered += ieePremultipliedCreatureTap(vec2(tc2.x, tc1.y)) * weightsX.z * weightsY.y;
	filtered += ieePremultipliedCreatureTap(vec2(tc3.x, tc1.y)) * weightsX.w * weightsY.y;
	filtered += ieePremultipliedCreatureTap(vec2(tc0.x, tc2.y)) * weightsX.x * weightsY.z;
	filtered += ieePremultipliedCreatureTap(vec2(tc1.x, tc2.y)) * weightsX.y * weightsY.z;
	filtered += ieePremultipliedCreatureTap(vec2(tc2.x, tc2.y)) * weightsX.z * weightsY.z;
	filtered += ieePremultipliedCreatureTap(vec2(tc3.x, tc2.y)) * weightsX.w * weightsY.z;
	filtered += ieePremultipliedCreatureTap(vec2(tc0.x, tc3.y)) * weightsX.x * weightsY.w;
	filtered += ieePremultipliedCreatureTap(vec2(tc1.x, tc3.y)) * weightsX.y * weightsY.w;
	filtered += ieePremultipliedCreatureTap(vec2(tc2.x, tc3.y)) * weightsX.z * weightsY.w;
	filtered += ieePremultipliedCreatureTap(vec2(tc3.x, tc3.y)) * weightsX.w * weightsY.w;

	mediump float alpha = clamp(filtered.a, 0.0, 1.0);
	if (alpha <= 0.000001)
	{
		return vec4(0.0);
	}
	mediump vec3 premultiplied = clamp(filtered.rgb, vec3(0.0), vec3(alpha));
	return vec4(premultiplied / alpha, alpha);
}

mediump float normpdf(in mediump float x, in mediump float sigma)
{
	return 0.39894*exp(-0.5*x*x/(sigma*sigma))/sigma;
}

const float fSolidThreshold = 0.1;

void main()
{
	vec4 texColor = texture2D(uTex, vTc);
	if (uIeeCreatureFilterMode > 1.5 &&
		uIeeCreatureTexelSize.x > 0.0 && uIeeCreatureTexelSize.y > 0.0)
	{
		texColor = ieeFetchCreatureCatmullRom(vTc, uIeeCreatureTexelSize);
	}
	if (texColor.a > fSolidThreshold)
	{
		gl_FragColor = mix(vColor, texColor, texColor.a);
		return;
	}

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
	gl_FragColor = mix(vColor, vec4(0,0,0,0), minDist);
}
