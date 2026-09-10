// fpDraw.glsl
// D6 source derived from BG2EE 2.7.3.0; native operations preserved below.

uniform lowp sampler2D uTex;
uniform highp vec4 uColorTone;
varying mediump vec2 vTc;
varying lowp vec4 vColor;

@@IEE_CREATURE_HD_COMMON@@

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

	lowp vec4 modulation = vColor;
	if (styleActive)
	{
		modulation.rgb = ieeCreatureWorkingRgb(modulation.rgb);
	}
	texColor *= modulation;
	if (!styleActive)
	{
		float grey = dot(texColor.rgb, vec3(0.299,0.587,0.114));
		vec3 tone = grey * uColorTone.rgb;
		gl_FragColor = vec4(mix(texColor.rgb, tone, uColorTone.a), texColor.a);
		return;
	}

	texColor = ieeApplyCreatureOutline(
		texColor, vec3(0.0), vTc, uIeeCreatureTexelSize, vColor.a);
	gl_FragColor = ieeFinishCreatureDrawColor(texColor, uColorTone);
}
