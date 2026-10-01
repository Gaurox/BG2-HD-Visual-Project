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
	mediump vec3 gaussianRgb = vec3(0.0);
	lowp vec4 texColor = ieeFetchCreatureColor(vTc, gaussianRgb);

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
