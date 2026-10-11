// fpYUV.glsl
// D3 neutral source derived from BG2EE 2.7.3.0.

uniform lowp sampler2D uTex;
uniform lowp float uIeeShaderSuiteEnabled;
varying mediump vec2 vTc;
varying mediump vec2 vTcU;
varying mediump vec2 vTcV;
varying lowp vec4 vColor;

const lowp vec3 off = vec3(0.06250, 0.50000, 0.50000);
const lowp vec3 dotR = vec3(1.00000, 0.00000, 1.28033);
const lowp vec3 dotG = vec3(1.00000, -0.21482, -0.38059);
const lowp vec3 dotB = vec3(1.00000, 2.12798, 0.00000);

void main()
{
	lowp vec3 yuv;
	yuv.r = texture2D(uTex, vTc).r;
	yuv.g = texture2D(uTex, vTcU).r;
	yuv.b = texture2D(uTex, vTcV).r;
	yuv = yuv - off;

	lowp float r = dot(yuv, dotR);
	lowp float g = dot(yuv, dotG);
	lowp float b = dot(yuv, dotB);
	gl_FragColor = vec4(r,g,b,1.0) * vColor;
}
