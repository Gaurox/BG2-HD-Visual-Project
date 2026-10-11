// fpFONT.glsl
// D3 neutral source derived from BG2EE 2.7.3.0.

uniform lowp sampler2D uTex;
uniform lowp float uIeeShaderSuiteEnabled;
varying mediump vec2 vTc;
varying lowp vec4 vColor;
varying highp float depth;

void main()
{
	highp vec4 color = texture2D(uTex, vTc);
	highp vec4 fontColor;
	fontColor.xyz = vec3(1.0, 1.0, 1.0);
	fontColor.a = color.r;
	gl_FragColor = fontColor * vColor;
}
