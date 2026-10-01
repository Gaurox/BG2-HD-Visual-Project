"""Compile/render P4 shaders on a hidden WGL context; no game or desktop input.

Tests actual driver sampling against analytic checker/alpha/footprint oracles.
The hidden 16x16 window is never shown or activated. Only its own DC is used.
"""
from __future__ import annotations

import ctypes as c
from ctypes import wintypes as w
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
U, I, F, P = c.c_uint, c.c_int, c.c_float, c.c_void_p


class PixelFormat(c.Structure):
    _fields_ = [("size", w.WORD), ("version", w.WORD), ("flags", w.DWORD),
                *[(name, w.BYTE) for name in (
                    "pixel_type", "color_bits", "red_bits", "red_shift", "green_bits", "green_shift",
                    "blue_bits", "blue_shift", "alpha_bits", "alpha_shift", "accum_bits",
                    "accum_red", "accum_green", "accum_blue", "accum_alpha", "depth_bits",
                    "stencil_bits", "aux_buffers", "layer_type", "reserved")],
                ("layer_mask", w.DWORD), ("visible_mask", w.DWORD), ("damage_mask", w.DWORD)]


def main():
    user, gdi, ogl = c.WinDLL("user32"), c.WinDLL("gdi32"), c.WinDLL("opengl32")
    user.CreateWindowExW.restype = w.HWND
    user.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD,
                                  I, I, I, I, w.HWND, w.HMENU, w.HINSTANCE, P]
    user.GetDC.restype = w.HDC
    user.GetDC.argtypes = [w.HWND]
    user.ReleaseDC.argtypes = [w.HWND, w.HDC]
    user.DestroyWindow.argtypes = [w.HWND]
    gdi.ChoosePixelFormat.argtypes = [w.HDC, c.POINTER(PixelFormat)]
    gdi.SetPixelFormat.argtypes = [w.HDC, I, c.POINTER(PixelFormat)]
    ogl.wglCreateContext.argtypes = [w.HDC]
    ogl.wglCreateContext.restype = P
    ogl.wglMakeCurrent.argtypes = [w.HDC, P]
    ogl.wglDeleteContext.argtypes = [P]
    ogl.wglGetProcAddress.argtypes = [c.c_char_p]
    ogl.wglGetProcAddress.restype = P
    hwnd = user.CreateWindowExW(0x08000000, "STATIC", "IEE P4 hidden GL test",
                                0x80000000, 0, 0, 16, 16, None, None, None, None)
    if not hwnd:
        raise RuntimeError("hidden test window unavailable")
    dc, context = None, None
    try:
        dc = user.GetDC(hwnd)
        pfd = PixelFormat(size=c.sizeof(PixelFormat), version=1, flags=0x24,
                          pixel_type=0, color_bits=32, alpha_bits=8)
        pixel_format = gdi.ChoosePixelFormat(dc, c.byref(pfd))
        if not pixel_format or not gdi.SetPixelFormat(dc, pixel_format, c.byref(pfd)):
            raise RuntimeError("test pixel format unavailable")
        context = ogl.wglCreateContext(dc)
        if not context or not ogl.wglMakeCurrent(dc, context):
            raise RuntimeError("hidden test GL context unavailable")

        def function(name, result, *args):
            address = ogl.wglGetProcAddress(name.encode())
            if address and address not in (1, 2, 3, c.c_void_p(-1).value):
                return c.WINFUNCTYPE(result, *args)(address)
            native = getattr(ogl, name)
            native.restype, native.argtypes = result, list(args)
            return native

        get_string = function("glGetString", c.c_char_p, U)
        get_error = function("glGetError", U)
        create_shader = function("glCreateShader", U, U)
        shader_source = function("glShaderSource", None, U, I, c.POINTER(c.c_char_p), P)
        compile_shader = function("glCompileShader", None, U)
        shader_iv = function("glGetShaderiv", None, U, U, c.POINTER(I))
        shader_log = function("glGetShaderInfoLog", None, U, I, P, P)
        create_program = function("glCreateProgram", U)
        attach = function("glAttachShader", None, U, U)
        link = function("glLinkProgram", None, U)
        program_iv = function("glGetProgramiv", None, U, U, c.POINTER(I))
        program_log = function("glGetProgramInfoLog", None, U, I, P, P)
        use = function("glUseProgram", None, U)
        location = function("glGetUniformLocation", I, U, c.c_char_p)
        uniform1f = function("glUniform1f", None, I, F)
        uniform2f = function("glUniform2f", None, I, F, F)
        uniform1i = function("glUniform1i", None, I, I)
        gen_tex = function("glGenTextures", None, I, c.POINTER(U))
        bind_tex = function("glBindTexture", None, U, U)
        active_tex = function("glActiveTexture", None, U)
        image = function("glTexImage2D", None, U, I, I, I, I, I, U, U, P)
        parameter = function("glTexParameteri", None, U, U, I)
        generate = function("glGenerateMipmap", None, U)
        gen_fbo = function("glGenFramebuffers", None, I, c.POINTER(U))
        bind_fbo = function("glBindFramebuffer", None, U, U)
        attach_tex = function("glFramebufferTexture2D", None, U, U, U, U, I)
        fbo_status = function("glCheckFramebufferStatus", U, U)
        gen_vao = function("glGenVertexArrays", None, I, c.POINTER(U))
        bind_vao = function("glBindVertexArray", None, U)
        viewport = function("glViewport", None, I, I, I, I)
        draw = function("glDrawArrays", None, U, I, I)
        read = function("glReadPixels", None, I, I, I, I, U, U, P)

        prefix = "#version 130\n#define lowp\n#define mediump\n#define highp\n"
        vertex = prefix + """
uniform vec2 testFirstEdge;
uniform vec2 testFootprint;
out vec2 vTc;
out vec4 vColor;
void main() {
    vec2 position = vec2(gl_VertexID == 1 ? 3.0 : -1.0,
                         gl_VertexID == 2 ? 3.0 : -1.0);
    gl_Position = vec4(position, 0.0, 1.0);
    vTc = testFirstEdge + (position + 1.0) * 0.5 * testFootprint;
    vColor = vec4(1.0);
}
"""

        def program(fragment, vertex_source=vertex):
            result = create_program()
            for kind, source in ((0x8B31, vertex_source), (0x8B30, fragment)):
                shader = create_shader(kind)
                encoded = source.encode()
                sources = (c.c_char_p * 1)(encoded)
                shader_source(shader, 1, sources, None)
                compile_shader(shader)
                okay = I()
                shader_iv(shader, 0x8B81, c.byref(okay))
                if not okay.value:
                    log = c.create_string_buffer(65536)
                    shader_log(shader, len(log), None, log)
                    raise RuntimeError(log.value.decode())
                attach(result, shader)
            link(result)
            okay = I()
            program_iv(result, 0x8B82, c.byref(okay))
            if not okay.value:
                log = c.create_string_buffer(65536)
                program_log(result, len(log), None, log)
                raise RuntimeError(log.value.decode())
            return result

        programs = {name: program(prefix + (ROOT / "assets/override" / name).read_text())
                    for name in ("fpDraw.glsl", "fpSprite.glsl", "fpSELECT.glsl")}
        # Compile the exact embedded native-mask sources as well.
        bridge = (ROOT / "src/iee/native_occlusion_bridge.cpp").read_text()
        native_vertex, native_fragment = re.findall(r'R"glsl\((.*?)\)glsl"', bridge, re.S)
        native_program = program(native_fragment, native_vertex)
        vao, output, fbo, source_texture = U(), U(), U(), U()
        gen_vao(1, c.byref(vao)); bind_vao(vao)
        gen_tex(1, c.byref(output)); bind_tex(0x0DE1, output)
        image(0x0DE1, 0, 0x8058, 1, 1, 0, 0x1908, 0x1401, None)
        gen_fbo(1, c.byref(fbo)); bind_fbo(0x8D40, fbo)
        attach_tex(0x8D40, 0x8CE0, 0x0DE1, output, 0)
        assert fbo_status(0x8D40) == 0x8CD5
        gen_tex(1, c.byref(source_texture)); bind_tex(0x0DE1, source_texture)
        for axis in (0x2802, 0x2803): parameter(0x0DE1, axis, 0x812F)
        viewport(0, 0, 1, 1)
        checks = []

        def render(pixels, width, height, mode, first, footprint):
            data = (c.c_ubyte * len(pixels))(*pixels)
            bind_tex(0x0DE1, source_texture)
            image(0x0DE1, 0, 0x8058, width, height, 0, 0x1908, 0x1401, data)
            parameter(0x0DE1, 0x2801, 0x2600)
            parameter(0x0DE1, 0x2800, 0x2600)
            parameter(0x0DE1, 0x813D, 0)
            if mode == 4:
                parameter(0x0DE1, 0x813D, int(math.log2(max(width, height))))
                generate(0x0DE1)
                parameter(0x0DE1, 0x2801, 0x2703)
            target = programs["fpDraw.glsl"]
            use(target)
            uniform1i(location(target, b"uTex"), 0)
            uniform1f(location(target, b"uIeeCreatureFilterMode"), mode)
            uniform2f(location(target, b"uIeeCreatureTexelSize"), 1 / width, 1 / height)
            uniform2f(location(target, b"testFirstEdge"), first[0] / width, first[1] / height)
            uniform2f(location(target, b"testFootprint"), footprint[0] / width, footprint[1] / height)
            draw(0x0004, 0, 3)
            result = (c.c_ubyte * 4)()
            read(0, 0, 1, 1, 0x1908, 0x1401, result)
            assert get_error() == 0
            return list(result)

        def expect(name, actual, expected, tolerance=1):
            assert all(abs(a - b) <= tolerance for a, b in zip(actual, expected)), (name, actual, expected)
            checks.append({"test": name, "actual_rgba": actual, "expected_rgba": expected})

        checker = [channel for y in range(8) for x in range(8)
                   for channel in ([255, 255, 255, 255] if (x + y) % 2 else [0, 0, 0, 255])]
        expect("box_checker_4x4", render(checker, 8, 8, 3, (0, 0), (4, 4)), [128, 128, 128, 255])
        expect("mips_checker_lod2", render(checker, 8, 8, 4, (0, 0), (4, 4)), [128, 128, 128, 255])
        # Noninteger footprint: [0.25,1.75] => equal area red and transparent blue.
        alpha = [255, 0, 0, 255, 0, 0, 255, 0] * 2
        expect("box_alpha_no_blue_halo", render(alpha, 2, 2, 3, (.25, .25), (1.5, 1.5)), [255, 0, 0, 128])
        asymmetric = [0, 0, 0, 255, 255, 255, 255, 255] * 2
        expect("box_fractional_overlap", render(asymmetric, 2, 2, 3, (.2, .2), (1.5, 1.5)), [119, 119, 119, 255])
        expect("box_mirror_fractional_overlap", render(asymmetric, 2, 2, 3, (1.7, .2), (-1.5, 1.5)), [119, 119, 119, 255])
        expect("box_mag_nearest", render(asymmetric, 2, 2, 3, (.1, .1), (.5, .5)), [0, 0, 0, 255])
        premult = [255, 0, 0, 255, 0, 0, 0, 0] * 2
        expect("mips_alpha_no_dark_halo", render(premult, 2, 2, 4, (0, 0), (2, 2)), [255, 0, 0, 128])
        expect("mips_mag_straight_decode", render([128, 0, 0, 128] * 4, 2, 2, 4, (.1, .1), (.5, .5)), [255, 0, 0, 128])
        expect("nearest_baseline_unchanged", render(asymmetric, 2, 2, 0, (.1, .1), (.5, .5)), [0, 0, 0, 255])
        mask_texture = U()
        gen_tex(1, c.byref(mask_texture))
        for name, transfer, expected in (
                ("mask_premultiplied_visibility", [128, 0, 0, 0], [64, 0, 0, 64]),
                ("mask_shadow", [255, 64, 0, 0], [0, 0, 0, 64]),
                ("mask_clear_hidden_rgb", [0, 0, 0, 0], [0, 0, 0, 0])):
            active_tex(0x84C0)
            bind_tex(0x0DE1, source_texture)
            image(0x0DE1, 0, 0x8058, 2, 2, 0, 0x1908, 0x1401,
                  (c.c_ubyte * 16)(*([128, 0, 0, 128] * 4)))
            parameter(0x0DE1, 0x813D, 0)
            parameter(0x0DE1, 0x2801, 0x2600)
            active_tex(0x84C1)
            bind_tex(0x0DE1, mask_texture)
            image(0x0DE1, 0, 0x8058, 1, 1, 0, 0x1908, 0x1401,
                  (c.c_ubyte * 4)(*transfer))
            parameter(0x0DE1, 0x813D, 0)
            parameter(0x0DE1, 0x2801, 0x2600)
            parameter(0x0DE1, 0x2800, 0x2600)
            use(native_program)
            for uniform, value in ((b"uReplacement", 0), (b"uVisibility", 1),
                                   (b"uScale", 2), (b"uPremultiplied", 1)):
                uniform1i(location(native_program, uniform), value)
            draw(0x0004, 0, 3)
            result = (c.c_ubyte * 4)()
            read(0, 0, 1, 1, 0x1908, 0x1401, result)
            assert get_error() == 0
            expect(name, list(result), expected)
        print(json.dumps({"status": "passed", "renderer": get_string(0x1F01).decode(),
                          "gl_version": get_string(0x1F02).decode(),
                          "compiled": list(programs) + ["native_occlusion_bridge"],
                          "checks": checks, "desktop_input": False, "window_shown": False}, indent=2))
    finally:
        if context:
            ogl.wglMakeCurrent(None, None)
            ogl.wglDeleteContext(context)
        if dc: user.ReleaseDC(hwnd, dc)
        user.DestroyWindow(hwnd)


if __name__ == "__main__":
    main()
