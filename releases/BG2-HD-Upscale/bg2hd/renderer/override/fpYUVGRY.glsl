// fpYUVGRY.glsl
// D3 neutral source derived from BG2EE 2.7.3.0.

uniform lowp sampler2D uTex;
uniform lowp sampler2D uTex2;
uniform mediump vec4 uColorTone;
uniform lowp float uIeeShaderSuiteEnabled;
varying mediump vec2 vTc;
varying mediump vec2 vTcU;
varying mediump vec2 vTcV;
varying lowp vec4 vColor;

const lowp vec3 off = vec3(0.06250, 0.50000, 0.50000);
const lowp vec3 dotR = vec3(1.00000, 0.00000, 1.28033);
const lowp vec3 dotG = vec3(1.00000, -0.21482, -0.38059);
const lowp vec3 dotB = vec3(1.00000, 2.12798, 0.00000);
const mediump float Yextent = 0.6666666;
const mediump float epsilonPadding = 0.001;

float fracV(float y)
{
	y = y / Yextent;
	y = fract(y);
	y = y * Yextent;
	y = min(y, Yextent - epsilonPadding);
	y = max(y, epsilonPadding);
	return y;
}

float fracUV(float y)
{
	y = y - Yextent;
	y = y / (1.0-Yextent);
	y = fract(y);
	y = y * (1.0-Yextent);
	y = y + Yextent;
	y = min(y, 1.0 - epsilonPadding);
	y = max(y, Yextent + epsilonPadding);
	return y;
}

void main()
{
	lowp vec3 yuv;
	mediump vec2 tc = vTc;
	mediump vec2 tcU = vTcU;
	mediump vec2 tcV = vTcV;

	tc.y = fracV(tc.y);
	tcU.y = fracUV(tcU.y);
	tcV.y = fracUV(tcV.y);

	yuv.r = texture2D(uTex, tc).r;
	yuv.g = texture2D(uTex, tcU).r;
	yuv.b = texture2D(uTex, tcV).r;
	mediump vec2 vTcA = vTc;
	vTcA.y /= Yextent;
	float a = texture2D(uTex2, vTcA).r;

	yuv = yuv - off;
	lowp float r = dot(yuv, dotR);
	lowp float g = dot(yuv, dotG);
	lowp float b = dot(yuv, dotB);
	float grey = dot(vec3(r,g,b), vec3(0.299,0.587,0.114));
	vec3 tone = grey * uColorTone.rgb;
	gl_FragColor = vec4(mix(vec3(r,g,b), tone, uColorTone.a), a);
}
