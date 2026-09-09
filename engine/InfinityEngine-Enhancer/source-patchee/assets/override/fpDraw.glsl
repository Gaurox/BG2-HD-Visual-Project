// fpDraw.glsl
// D3 neutral source derived from BG2EE 2.7.3.0.

uniform lowp sampler2D uTex;
uniform highp vec4 uColorTone;
uniform lowp float uIeeShaderSuiteEnabled;
varying mediump vec2 vTc;
varying lowp vec4 vColor;

void main()
{
	vec4 texColor = texture2D(uTex, vTc) * vColor;
	float grey = dot(texColor.rgb, vec3(0.299,0.587,0.114));
	vec3 tone = grey * uColorTone.rgb;
	gl_FragColor = vec4(mix(texColor.rgb, tone, uColorTone.a), texColor.a);
}
