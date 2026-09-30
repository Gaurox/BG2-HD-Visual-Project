"""P0 independent BAM V1/P8 reader and neutral Character palette oracle.

No installation. Declared BAM geometry is retained, including zero-size frames.
NativeMix executes only the pinned, self-contained RealizeRange mixing loop in
this Python process; it does not call the game, patch a DLL or emulate effects.
"""
from __future__ import annotations

import ctypes
import hashlib
import platform
import struct
import zlib
from pathlib import Path

import numpy as np

EXE_SHA256 = "b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57"
MIX_START, MIX_END = 0x421F7B, 0x42201E


def read_bam_p8(raw: bytes) -> dict:
    """Strict BAM/BAMC V1, BGRA palette, signed centres, raw/RLE and cycles."""
    packed = raw[:4] == b"BAMC"
    if packed:
        if len(raw) < 12 or raw[:8] != b"BAMCV1  ":
            raise ValueError("unsupported/truncated BAMC")
        expected = struct.unpack_from("<I", raw, 8)[0]
        if expected > 256 * 1024 * 1024:
            raise ValueError("BAMC exceeds audit size bound")
        decoder = zlib.decompressobj()
        raw = decoder.decompress(raw[12:], expected + 1)
        if len(raw) != expected or not decoder.eof or decoder.unused_data:
            raise ValueError("BAMC length or stream differs")
    if len(raw) < 24 or raw[:8] != b"BAM V1  ":
        raise ValueError("unsupported/truncated BAM V1")

    def bounded(offset, size, label):
        if offset < 24 or offset + size > len(raw):
            raise ValueError(f"truncated/out-of-bounds {label}")

    nf, nc, transparent = struct.unpack_from("<HBB", raw, 8)
    frame_offset, palette_offset, lookup_offset = struct.unpack_from("<III", raw, 12)
    bounded(frame_offset, nf * 12 + nc * 4, "frame/cycle table")
    bounded(palette_offset, 1024, "palette")
    bounded(lookup_offset, 0, "lookup")
    palette = np.frombuffer(raw[palette_offset:palette_offset + 1024], np.uint8).reshape(256, 4).copy()
    cycles = []
    for ci in range(nc):
        count, first = struct.unpack_from("<HH", raw, frame_offset + nf * 12 + ci * 4)
        bounded(lookup_offset + first * 2, count * 2, "cycle lookup")
        indices = list(struct.unpack_from(f"<{count}H", raw, lookup_offset + first * 2))
        if any(index >= nf for index in indices):
            raise ValueError("cycle references missing frame")
        cycles.append({"index": ci, "lookup_start": first, "frame_indices": indices})
    frames = []
    for fi in range(nf):
        width, height, cx, cy, tagged = struct.unpack_from("<HHhhI", raw, frame_offset + fi * 12)
        offset, compressed = tagged & 0x7FFFFFFF, not bool(tagged & 0x80000000)
        need = width * height
        if need > 16 * 1024 * 1024:
            raise ValueError("frame exceeds audit size bound")
        pixels = bytearray()
        rle_tail_overflow = 0
        if need and compressed:
            while len(pixels) < need:
                bounded(offset, 1, "RLE pixel")
                value = raw[offset]
                offset += 1
                count = 1
                if value == transparent:
                    bounded(offset, 1, "RLE run")
                    count = raw[offset] + 1
                    offset += 1
                if len(pixels) + count > need:
                    # Stock WQNAXA5 contains this case. Like decode_bam, consume
                    # the marker but truncate the final transparent run.
                    rle_tail_overflow = len(pixels) + count - need
                    count = need - len(pixels)
                pixels.extend(bytes([value]) * count)
        elif need:
            bounded(offset, need, "raw pixels")
            pixels.extend(raw[offset:offset + need])
        frames.append({"index": fi, "width": width, "height": height,
                       "center_x": cx, "center_y": cy, "compressed": compressed,
                       "rle_tail_overflow": rle_tail_overflow,
                       "indices": np.frombuffer(bytes(pixels), np.uint8).reshape(height, width)})
    return {"frames": frames, "cycles": cycles, "transparent": transparent,
            "palette_bgra": palette, "palette_rgb": palette[:, [2, 1, 0]],
            "packed": packed, "canonical": raw}


def scalar_palette(ramps) -> np.ndarray:
    """Independent address-loop translation; no production classes/pair table."""
    ramps = np.asarray(ramps)
    if ramps.shape != (7, 12, 3) or ramps.dtype != np.uint8:
        raise ValueError("seven RGB u8 ramps required")
    buffer = bytearray(1024)
    buffer[1] = 255  # reserved transparent green
    for channel in range(7):
        for shade in range(12):
            for component in range(3):
                buffer[(4 + channel * 12 + shade) * 4 + component] = int(ramps[channel, shade, component])
    a, destination = 0x18, 0x160
    for outer in range(1, 7):
        b = a + 0x30
        for _ in range(7 - outer):
            for _ in range(8):
                for component in range(3):
                    buffer[destination + component] = (buffer[a + component] + buffer[b + component]) >> 1
                a, b, destination = a + 4, b + 4, destination + 4
            a, b = a - 0x20, b + 0x10
        a += 0x30
    return np.frombuffer(buffer, np.uint8).reshape(256, 4)[:, :3].copy()


def pe_rva(raw: bytes, rva: int, size: int) -> bytes:
    """Extract a wholly mapped PE section span from the pinned local image."""
    pe = struct.unpack_from("<I", raw, 0x3C)[0]
    if raw[pe:pe + 4] != b"PE\0\0" or struct.unpack_from("<H", raw, pe + 4)[0] != 0x8664:
        raise ValueError("x64 PE required")
    sections, optional = struct.unpack_from("<H", raw, pe + 6)[0], struct.unpack_from("<H", raw, pe + 20)[0]
    for index in range(sections):
        pos = pe + 24 + optional + index * 40
        virtual, address, length, offset = struct.unpack_from("<IIII", raw, pos + 8)
        if address <= rva and rva + size <= address + min(virtual, length):
            return raw[offset + rva - address:offset + rva - address + size]
    raise ValueError("RVA outside a mapped section")


class NativeMix:
    """Windows x64 ABI wrapper; saves nonvolatile registers, owns RX allocation."""
    def __init__(self, exe: Path):
        raw = exe.read_bytes()
        if hashlib.sha256(raw).hexdigest() != EXE_SHA256:
            raise ValueError("unsupported game executable hash")
        if platform.system() != "Windows" or ctypes.sizeof(ctypes.c_void_p) != 8:
            raise ValueError("native oracle requires Windows x64")
        fragment = pe_rva(raw, MIX_START, MIX_END - MIX_START)
        self.fragment_sha256 = hashlib.sha256(fragment).hexdigest()
        # push rbx/rdi/r12; mov r8,rcx; loop; pop r12/rdi/rbx; ret.
        # The excluded instruction at MIX_END starts accessing the game stack.
        stub = bytes.fromhex("53 57 41 54 49 89 c8") + fragment + bytes.fromhex("41 5c 5f 5b c3")
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
        api.VirtualAlloc.restype = ctypes.c_void_p
        api.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
        api.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong]
        api.GetCurrentProcess.restype = ctypes.c_void_p
        api.FlushInstructionCache.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        self.api, self.address = api, api.VirtualAlloc(None, len(stub), 0x3000, 4)
        if not self.address:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            ctypes.memmove(self.address, stub, len(stub))
            previous = ctypes.c_ulong()
            if not api.VirtualProtect(self.address, len(stub), 0x20, ctypes.byref(previous)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not api.FlushInstructionCache(api.GetCurrentProcess(), self.address, len(stub)):
                raise ctypes.WinError(ctypes.get_last_error())
            self.function = ctypes.WINFUNCTYPE(None, ctypes.c_void_p)(self.address)
        except BaseException:
            self.close()
            raise

    def __call__(self, ramps) -> np.ndarray:
        buffer = np.zeros((256, 4), np.uint8)
        buffer[0, 1] = 255
        buffer[4:88, :3] = np.asarray(ramps, np.uint8).reshape(84, 3)
        self.function(buffer.ctypes.data)
        return buffer[:, :3].copy()

    def close(self):
        if self.address:
            self.api.VirtualFree(self.address, 0, 0x8000)
            self.address = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
