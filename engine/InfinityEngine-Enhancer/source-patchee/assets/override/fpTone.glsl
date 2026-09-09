// fpTone.glsl
// D3 neutral source derived from BG2EE 2.7.3.0.

uniform lowp sampler2D uTex;
uniform lowp vec4 uColorTone;
uniform lowp float uIeeShaderSuiteEnabled;
varying mediump vec2 vTc;
varying lowp vec4 vColor;

void main()
{
	lowp vec4 c = texture2D(uTex, vTc) * vColor;
	lowp float grey = dot(c.rgb, vec3(0.299,0.587,0.114));
	lowp vec3 tone = grey * uColorTone.rgb;
	gl_FragColor = vec4(mix(c.rgb, tone, uColorTone.a), c.a);
}
