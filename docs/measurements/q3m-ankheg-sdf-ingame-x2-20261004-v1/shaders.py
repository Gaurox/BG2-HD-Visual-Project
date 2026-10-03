from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
E=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
HERE=Path(__file__).resolve().parent
exec((HERE/'implement.py').read_text().split("p=ROOT/'pipeline/scripts")[0])
edit(E/'assets/shader-suite/creature-hd-common.glsl',[
 ('uniform lowp float uIeeCreatureFilterMode;', 'uniform lowp float uIeeCreatureFilterMode;\nuniform lowp float uIeeCreatureSdfEncoded;\nlowp vec4 ieeFetchCreatureSdf(in mediump vec2 texCoord);'),
 ('\tlowp vec4 sampleColor = texture2D(uTex, texCoord);','\tif (uIeeCreatureSdfEncoded > 0.5) return ieeFetchCreatureSdf(texCoord);\n\tlowp vec4 sampleColor = texture2D(uTex, texCoord);'),
 ('mediump float ieeCreatureNormalCdf(', (HERE/'sdf.glsl').read_text()+'\nmediump float ieeCreatureNormalCdf('),
 ('\tbool styleActive = ieeCreatureStyleActive();\n\tbool validSize', '\tif (uIeeCreatureSdfEncoded > 0.5) { gaussianRgb = vec3(0.0); return ieeCreatureWorkingSample(texCoord); }\n\tbool styleActive = ieeCreatureStyleActive();\n\tbool validSize'),
 ('clamp(texture2D(uTex, coordinate).a, 0.0, 1.0)','clamp(ieeCreatureNativeAlpha(coordinate), 0.0, 1.0)')])
edit(E/'assets/shader-suite/templates/fpSprite.glsl',[
 ('\tif (!styleActive || uIeeCreatureOutlineMode <= 0.5)', '\tif (uIeeCreatureSdfEncoded > 0.5)\n\t{\n\t\toutColor = texColor;\n\t}\n\telse if (!styleActive || uIeeCreatureOutlineMode <= 0.5)')])
edit(E/'assets/shader-suite/templates/fpSELECT.glsl',[
 ('\t\t\t\tif (texSample.a > fSolidThreshold)', '\t\t\t\tif (ieeCreatureNativeAlpha(sampleCoord) > fSolidThreshold)')])
