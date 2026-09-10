// D6-D7 creature-HD and sprite-scope functions adapted from Dshaders 0.3.5.
// Upstream commit: 4722673a8017c56ace4018b3db459392ecbb75a4
// See licenses/DSHADERS-MIT.txt.
// IEE_CREATURE_ROUTING_CONTRACT_V1
// IEE_CREATURE_FILTER_CONTRACT_V1
// IEE_CREATURE_STYLE_CONTRACT_V1
// IEE_SPRITE_SCOPE_CONTRACT_V1

uniform lowp float uIeeShaderSuiteEnabled;
uniform lowp float uIeeCreatureFilterMode;
uniform mediump vec2 uIeeCreatureTexelSize;
uniform lowp float uIeeCreatureStyleEnabled;
uniform lowp float uIeeCreatureColorSpace;
uniform lowp float uIeeCreatureSharpen;
uniform lowp float uIeeCreatureGamma;
uniform lowp float uIeeCreatureContrast;
uniform lowp float uIeeCreatureBrightness;
uniform lowp float uIeeCreatureSaturation;
uniform lowp float uIeeCreatureHueDegrees;
uniform lowp float uIeeCreatureOutlineMode;
uniform mediump float uIeeCreatureOutlineSize;
uniform mediump float uIeeCreatureTextureScale;

bool ieeCreatureStyleActive()
{
	return uIeeShaderSuiteEnabled > 0.5 && uIeeCreatureStyleEnabled > 0.5;
}

lowp vec3 ieeCreatureToLinear(in lowp vec3 srgb)
{
	lowp vec3 cutoff = vec3(lessThanEqual(srgb, vec3(0.039285714)));
	lowp vec3 higher = pow(srgb * 0.947867299 + 0.052132701, vec3(2.4));
	lowp vec3 lower = srgb * 0.077380154;
	return mix(higher, lower, cutoff);
}

lowp vec3 ieeCreatureFromLinear(in lowp vec3 rgb)
{
	rgb = max(rgb, vec3(0.0));
	lowp vec3 cutoff = vec3(lessThanEqual(rgb, vec3(0.0030399346)));
	lowp vec3 higher = pow(rgb, vec3(0.4166666667)) * 1.055 - 0.055;
	lowp vec3 lower = rgb * 12.9232101808;
	return mix(higher, lower, cutoff);
}

lowp vec3 ieeCreatureWorkingRgb(in lowp vec3 color)
{
	if (ieeCreatureStyleActive() && uIeeCreatureColorSpace > 0.5)
	{
		return ieeCreatureToLinear(clamp(color, vec3(0.0), vec3(1.0)));
	}
	return color;
}

lowp vec4 ieeCreatureWorkingSample(in mediump vec2 texCoord)
{
	lowp vec4 sampleColor = texture2D(uTex, texCoord);
	mediump float alpha = clamp(sampleColor.a, 0.0, 1.0);
	if (alpha <= 0.000001)
	{
		return vec4(0.0);
	}
	return vec4(ieeCreatureWorkingRgb(sampleColor.rgb), alpha);
}

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

mediump float ieeCreatureNormalCdf(in mediump float x, in mediump float invScale)
{
	mediump float sx = x * invScale;
	mediump float emx2 = exp(sx * sx * -0.5);
	return sign(x) * 0.56418958 * sqrt(max(0.0, 1.0 - emx2)) *
		(0.88622692 + emx2 * (emx2 * -0.042625 + 0.155)) + 0.5;
}

mediump vec4 ieeCreatureGaussianWeights(in mediump float phase)
{
	const mediump float invSigma = 0.4;
	// D5 phase grows toward base+1; adapt the upstream CDF to boundary-phase.
	mediump float stop0 = ieeCreatureNormalCdf(-phase - 1.5, invSigma);
	mediump float stop1 = ieeCreatureNormalCdf(-phase - 0.5, invSigma);
	mediump float stop2 = ieeCreatureNormalCdf(-phase + 0.5, invSigma);
	mediump float stop3 = ieeCreatureNormalCdf(-phase + 1.5, invSigma);
	mediump float stop4 = ieeCreatureNormalCdf(-phase + 2.5, invSigma);
	mediump float normalization = 1.0 / max(stop4 - stop0, 0.000001);
	return vec4(stop1 - stop0, stop2 - stop1, stop3 - stop2, stop4 - stop3) * normalization;
}

mediump vec4 ieePremultipliedCreatureTap(in mediump vec2 texCoord)
{
	lowp vec4 sampleColor = ieeCreatureWorkingSample(texCoord);
	return vec4(sampleColor.rgb * sampleColor.a, sampleColor.a);
}

void ieeAccumulateCreatureTap(in mediump vec4 tap,
							  in mediump float catmullWeight,
							  in mediump float gaussianWeight,
							  inout mediump vec4 catmull,
							  inout mediump vec4 gaussian)
{
	catmull += tap * catmullWeight;
	gaussian += tap * gaussianWeight;
}

mediump vec4 ieeFetchCreatureCatmullRom(in mediump vec2 texCoord,
										in mediump vec2 texelSize,
										in bool reconstruct,
										out mediump vec3 gaussianRgb)
{
	mediump vec2 q = texCoord / texelSize - vec2(0.5);
	mediump vec2 baseTexel = floor(q);
	mediump vec2 phase = q - baseTexel;
	mediump vec4 weightsX = ieeCreatureCatmullRomWeights(phase.x);
	mediump vec4 weightsY = ieeCreatureCatmullRomWeights(phase.y);
	mediump vec4 gaussianX = ieeCreatureGaussianWeights(phase.x);
	mediump vec4 gaussianY = ieeCreatureGaussianWeights(phase.y);

	mediump vec2 tc0 = (baseTexel + vec2(-1.0) + vec2(0.5)) * texelSize;
	mediump vec2 tc1 = (baseTexel + vec2( 0.0) + vec2(0.5)) * texelSize;
	mediump vec2 tc2 = (baseTexel + vec2( 1.0) + vec2(0.5)) * texelSize;
	mediump vec2 tc3 = (baseTexel + vec2( 2.0) + vec2(0.5)) * texelSize;

	mediump vec4 catmull = vec4(0.0);
	mediump vec4 gaussian = vec4(0.0);
	mediump vec4 tap;
	tap = ieePremultipliedCreatureTap(vec2(tc0.x, tc0.y)); ieeAccumulateCreatureTap(tap, weightsX.x * weightsY.x, gaussianX.x * gaussianY.x, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc1.x, tc0.y)); ieeAccumulateCreatureTap(tap, weightsX.y * weightsY.x, gaussianX.y * gaussianY.x, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc2.x, tc0.y)); ieeAccumulateCreatureTap(tap, weightsX.z * weightsY.x, gaussianX.z * gaussianY.x, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc3.x, tc0.y)); ieeAccumulateCreatureTap(tap, weightsX.w * weightsY.x, gaussianX.w * gaussianY.x, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc0.x, tc1.y)); ieeAccumulateCreatureTap(tap, weightsX.x * weightsY.y, gaussianX.x * gaussianY.y, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc1.x, tc1.y)); ieeAccumulateCreatureTap(tap, weightsX.y * weightsY.y, gaussianX.y * gaussianY.y, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc2.x, tc1.y)); ieeAccumulateCreatureTap(tap, weightsX.z * weightsY.y, gaussianX.z * gaussianY.y, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc3.x, tc1.y)); ieeAccumulateCreatureTap(tap, weightsX.w * weightsY.y, gaussianX.w * gaussianY.y, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc0.x, tc2.y)); ieeAccumulateCreatureTap(tap, weightsX.x * weightsY.z, gaussianX.x * gaussianY.z, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc1.x, tc2.y)); ieeAccumulateCreatureTap(tap, weightsX.y * weightsY.z, gaussianX.y * gaussianY.z, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc2.x, tc2.y)); ieeAccumulateCreatureTap(tap, weightsX.z * weightsY.z, gaussianX.z * gaussianY.z, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc3.x, tc2.y)); ieeAccumulateCreatureTap(tap, weightsX.w * weightsY.z, gaussianX.w * gaussianY.z, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc0.x, tc3.y)); ieeAccumulateCreatureTap(tap, weightsX.x * weightsY.w, gaussianX.x * gaussianY.w, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc1.x, tc3.y)); ieeAccumulateCreatureTap(tap, weightsX.y * weightsY.w, gaussianX.y * gaussianY.w, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc2.x, tc3.y)); ieeAccumulateCreatureTap(tap, weightsX.z * weightsY.w, gaussianX.z * gaussianY.w, catmull, gaussian);
	tap = ieePremultipliedCreatureTap(vec2(tc3.x, tc3.y)); ieeAccumulateCreatureTap(tap, weightsX.w * weightsY.w, gaussianX.w * gaussianY.w, catmull, gaussian);

	if (gaussian.a > 0.000001)
	{
		gaussianRgb = gaussian.rgb / gaussian.a;
	}
	else
	{
		gaussianRgb = vec3(0.0);
	}
	if (!reconstruct)
	{
		return ieeCreatureWorkingSample(texCoord);
	}
	mediump float alpha = clamp(catmull.a, 0.0, 1.0);
	if (alpha <= 0.000001)
	{
		return vec4(0.0);
	}
	mediump vec3 premultiplied = clamp(catmull.rgb, vec3(0.0), vec3(alpha));
	return vec4(premultiplied / alpha, alpha);
}

mediump float ieeCreatureSegmentDistance2(in mediump vec2 point,
										  in mediump vec2 first,
										  in mediump vec2 second)
{
	mediump vec2 delta = second - first;
	mediump float length2 = dot(delta, delta);
	if (length2 <= 0.000001)
	{
		mediump vec2 offset = first - point;
		return dot(offset, offset);
	}
	mediump float position = clamp(dot(point - first, delta) / length2, 0.0, 1.0);
	mediump vec2 projection = first + position * delta - point;
	return dot(projection, projection);
}

void ieeFetchCreatureOutlineRegion(in mediump vec2 baseTexel,
								  in mediump vec2 texelSize,
								  out lowp float region[36])
{
	int index = 0;
	for (int y = -2; y <= 3; ++y)
	{
		for (int x = -2; x <= 3; ++x)
		{
			mediump vec2 coordinate =
				(baseTexel + vec2(float(x), float(y)) + vec2(0.5)) * texelSize;
			region[index] = clamp(texture2D(uTex, coordinate).a, 0.0, 1.0);
			++index;
		}
	}
}

lowp float ieeCreatureOutlineAlpha(in lowp float region[36],
									in int x, in int y)
{
	return region[(y + 2) * 6 + x + 2];
}

mediump vec2 ieeCreatureOutlineData(in mediump vec2 texCoord,
									in mediump vec2 texelSize,
									in mediump float outlineSize)
{
	mediump vec2 q = texCoord / texelSize - vec2(0.5);
	mediump vec2 baseTexel = floor(q);
	mediump vec2 phase = q - baseTexel;
	mediump float distance2 = (outlineSize + 1.0) * (outlineSize + 1.0);
	lowp float maximumAlpha = 0.0;
	lowp float region[36];
	ieeFetchCreatureOutlineRegion(baseTexel, texelSize, region);
	for (int y = -1; y < 3; ++y)
	{
		for (int x = -1; x < 3; ++x)
		{
			lowp float a00 = ieeCreatureOutlineAlpha(region, x, y);
			lowp float a01 = ieeCreatureOutlineAlpha(region, x + 1, y);
			lowp float a10 = ieeCreatureOutlineAlpha(region, x, y + 1);
			lowp float a11 = ieeCreatureOutlineAlpha(region, x + 1, y + 1);
			lowp float highAlpha = max(max(a00, a01), max(a10, a11));
			lowp float lowAlpha = min(min(a00, a01), min(a10, a11));
			maximumAlpha = max(maximumAlpha, highAlpha);
			if (0.0625 < lowAlpha || highAlpha <= 0.0625)
			{
				continue;
			}
			mediump float lineA0 = (a00 * 3.0 + a01 + a10 - a11) * 0.25 - 0.0625;
			mediump float lineAX = (a01 + a11 - a00 - a10) * 0.5;
			mediump float lineBX = (a10 + a11 - a00 - a01) * 0.5;
			mediump vec2 first = vec2(0.0);
			mediump vec2 second = vec2(0.0);
			int endpoints = 0;
			if (lineBX != 0.0)
			{
				mediump float y0 = -lineA0 / lineBX;
				mediump float y1 = -(lineA0 + lineAX) / lineBX;
				if (endpoints < 2 && 0.0 <= y0 && y0 <= 1.0) { if (endpoints == 0) first = vec2(0.0, y0); else second = vec2(0.0, y0); ++endpoints; }
				if (endpoints < 2 && 0.0 <= y1 && y1 <= 1.0) { if (endpoints == 0) first = vec2(1.0, y1); else second = vec2(1.0, y1); ++endpoints; }
			}
			if (lineAX != 0.0)
			{
				mediump float x0 = -lineA0 / lineAX;
				mediump float x1 = -(lineA0 + lineBX) / lineAX;
				if (endpoints < 2 && 0.0 <= x0 && x0 <= 1.0) { if (endpoints == 0) first = vec2(x0, 0.0); else second = vec2(x0, 0.0); ++endpoints; }
				if (endpoints < 2 && 0.0 <= x1 && x1 <= 1.0) { if (endpoints == 0) first = vec2(x1, 1.0); else second = vec2(x1, 1.0); ++endpoints; }
			}
			if (endpoints == 2)
			{
				distance2 = min(distance2, ieeCreatureSegmentDistance2(
					phase - vec2(float(x), float(y)), first, second));
			}
		}
	}
	return vec2(sqrt(distance2), maximumAlpha);
}

lowp vec4 ieeApplyCreatureOutline(in lowp vec4 color,
								  in lowp vec3 outlineColor,
								  in mediump vec2 texCoord,
								  in mediump vec2 texelSize,
								  in lowp float opacity)
{
	if (!ieeCreatureStyleActive() || uIeeCreatureOutlineMode <= 0.5 ||
		uIeeCreatureOutlineSize <= 0.70710678)
	{
		return color;
	}
	mediump vec2 outlineData = ieeCreatureOutlineData(
		texCoord, texelSize * uIeeCreatureTextureScale,
		uIeeCreatureOutlineSize);
	mediump float distanceFactor = max(
		0.0, 1.0 - outlineData.x / (uIeeCreatureOutlineSize + 0.29289321));
	distanceFactor *= distanceFactor;
	mediump float outlineAlpha = distanceFactor *
		(outlineData.y + 3.0) * 0.25 * clamp(opacity, 0.0, 1.0);
	mediump float combinedAlpha =
		outlineAlpha * (1.0 - color.a) + color.a;
	if (combinedAlpha <= 0.000001)
	{
		return vec4(0.0);
	}
	lowp vec3 combinedRgb =
		(outlineColor * distanceFactor * outlineAlpha * (1.0 - color.a) +
		 color.rgb * color.a) / combinedAlpha;
	return vec4(combinedRgb, clamp(combinedAlpha, 0.0, 1.0));
}

lowp vec3 ieeCreatureHueSaturation(in lowp vec3 color)
{
	mediump float absoluteHue = abs(uIeeCreatureHueDegrees);
	if (absoluteHue > 0.000001 && abs(absoluteHue - 360.0) > 0.000001)
	{
		mediump float radians = uIeeCreatureHueDegrees * 3.14159265 / 180.0;
		mediump float hueU = cos(radians);
		mediump float hueW = sin(radians);
		lowp mat3 hueMatrix = mat3(
			0.299 + 0.701 * hueU + 0.168 * hueW,
			0.299 - 0.299 * hueU - 0.328 * hueW,
			0.299 - 0.300 * hueU + 1.250 * hueW,
			0.587 - 0.587 * hueU + 0.330 * hueW,
			0.587 + 0.413 * hueU + 0.035 * hueW,
			0.587 - 0.588 * hueU - 1.050 * hueW,
			0.114 - 0.114 * hueU - 0.497 * hueW,
			0.114 - 0.114 * hueU + 0.292 * hueW,
			0.114 + 0.886 * hueU - 0.203 * hueW);
		color = hueMatrix * color;
	}
	lowp float grey = dot(color, vec3(0.299, 0.587, 0.114));
	return color * uIeeCreatureSaturation + grey * (1.0 - uIeeCreatureSaturation);
}

lowp vec3 ieeCreatureFinishRgb(in lowp vec3 color)
{
	color = (color - 0.5) * uIeeCreatureContrast + 0.5 + uIeeCreatureBrightness;
	color = pow(max(color, vec3(0.0)), vec3(max(uIeeCreatureGamma, 0.000001)));
	if (uIeeCreatureColorSpace > 0.5)
	{
		color = ieeCreatureFromLinear(color);
	}
	return clamp(color, vec3(0.0), vec3(1.0));
}

lowp vec4 ieeFinishCreatureColor(in lowp vec4 color)
{
	if (color.a <= 0.000001)
	{
		return vec4(0.0);
	}
	color.rgb = ieeCreatureHueSaturation(color.rgb);
	color.rgb = ieeCreatureFinishRgb(color.rgb);
	return vec4(color.rgb, clamp(color.a, 0.0, 1.0));
}

lowp vec4 ieeFinishCreatureDrawColor(in lowp vec4 color,
									 in lowp vec4 colorTone)
{
	if (color.a <= 0.000001)
	{
		return vec4(0.0);
	}
	color.rgb = ieeCreatureHueSaturation(color.rgb);
	lowp float grey = dot(color.rgb, vec3(0.299, 0.587, 0.114));
	lowp vec3 tone = grey * ieeCreatureWorkingRgb(colorTone.rgb);
	color.rgb = mix(color.rgb, tone, colorTone.a);
	color.rgb = ieeCreatureFinishRgb(color.rgb);
	return vec4(color.rgb, clamp(color.a, 0.0, 1.0));
}
