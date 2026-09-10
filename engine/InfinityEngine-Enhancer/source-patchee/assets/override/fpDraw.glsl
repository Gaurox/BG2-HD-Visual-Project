// fpDraw.glsl
// D4 routing source derived from BG2EE 2.7.3.0.
// Valid routing modes remain pixel-identical until the D5 filter lands.
// IEE_CREATURE_ROUTING_CONTRACT_V1

uniform lowp sampler2D uTex;
uniform highp vec4 uColorTone;
uniform lowp float uIeeShaderSuiteEnabled;
uniform lowp float uIeeCreatureFilterMode;
uniform mediump vec2 uIeeCreatureTexelSize;
varying mediump vec2 vTc;
varying lowp vec4 vColor;

void main()
{
	vec4 texColor = texture2D(uTex, vTc) * vColor;
	// Keep the D4 uniforms active without changing any valid mode (0/1/2).
	if (uIeeCreatureFilterMode < 0.0)
	{
		texColor = texture2D(uTex, vTc + uIeeCreatureTexelSize) * vColor;
	}
	float grey = dot(texColor.rgb, vec3(0.299,0.587,0.114));
	vec3 tone = grey * uColorTone.rgb;
	gl_FragColor = vec4(mix(texColor.rgb, tone, uColorTone.a), texColor.a);
}
