"""Phase 1 CPU contract builder. No model, cache, registry, game or install writes.

Reproduction requires numpy and unicorn==2.1.4 (temporary --unicorn-path allowed).
Existing outputs are immutable: choose another output directory to reproduce.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from palette_oracle import EXE_SHA256, pe_rva, read_bam_p8
from reboutcx_quantize import srgb_u8_to_oklab

FAMILIES = (
    ("Spectateur", "BEHSPE01", "0x7F02", "7f02-mbeh-beholder", "MBEH", 2),
    ("Bodhi", "BODHI", "0x7F30", "7f30-nboh-bodhi", "NBOH", 4),
    ("Golem geôlier", "IGOLEM02", "0x7F07", "7f07-mglc-golem-clay", "MGLC", 6),
)
FITS = (
    ("neutral", 5, [255, 255, 255]),
    ("warm", 0x20005, [255, 192, 128]),
    ("cold", 0x20005, [128, 192, 255]),
    ("green", 0x20005, [128, 255, 160]),
    ("red", 0x20005, [255, 128, 160]),
    ("dim", 0x20005, [128, 128, 128]),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class NativeFixed:
    """Emulate the pinned type-0 Realize branch, never launch the executable.

    Only OS/security-independent, static tint conditions are admitted. The unused
    area-tint query returns white; /GS check is bypassed in isolated emulation.
    Clock/base are deterministic; brightness, gamma, animated effects are zero.
    Neither substitution participates in the selected native colour arithmetic.
    """

    def __init__(self, raw):
        import unicorn
        from unicorn import x86_const as reg

        if unicorn.__version__ != "2.1.4" or sha(raw) != EXE_SHA256:
            raise ValueError("oracle dependency or executable identity differs")
        self.reg = reg
        self.uc = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_64)
        self.uc.mem_map(0, 0x4000000)
        self.uc.mem_map(0x10000000, 0x20000)
        pe = struct.unpack_from("<I", raw, 0x3C)[0]
        n = struct.unpack_from("<H", raw, pe + 6)[0]
        opt = struct.unpack_from("<H", raw, pe + 20)[0]
        for i in range(n):
            p = pe + 24 + opt + i * 40
            _, address, length, offset = struct.unpack_from("<IIII", raw, p + 8)
            self.uc.mem_write(address, raw[offset:offset + length])
        self.uc.mem_write(0x667560, struct.pack("<Q", 0x10000000))
        self.uc.mem_write(0x10000210, struct.pack("<Q", 0x10001000))
        for offset, value in ((0x190, 16), (0x194, 8), (0x198, 0)):
            self.uc.mem_write(0x10001000 + offset, struct.pack("<I", value))
        self.uc.mem_write(0x41D9E0, bytes.fromhex("b8ffffff00c3"))
        self.uc.mem_write(0x4F77A0, b"\xc3")

    def realize(self, palette, flags, tint, transparency=255):
        if flags not in (1, 5, 7, 0x20005):
            raise ValueError("unsupported oracle condition")
        self.uc.mem_write(0x10004000, palette.tobytes())
        self.uc.mem_write(0x10003000,
                          struct.pack("<QQQI", 0, 1, 0x10004000, 256) + bytes(20))
        self.uc.mem_write(0x10005000, bytes(tint) + bytes(0xCD))
        stack = 0x1001F000
        self.uc.mem_write(stack, struct.pack("<Q", 0x1000F000))
        self.uc.mem_write(stack + 0x28, struct.pack("<II", transparency, 0))
        for name, value in (("RCX", 0x10003000), ("RDX", 0x10006000),
                            ("R8", flags), ("R9", 0x10005000), ("RSP", stack)):
            self.uc.reg_write(getattr(self.reg, "UC_X86_REG_" + name), value)
        self.uc.emu_start(0x421430, 0x1000F000, count=100000)
        if self.uc.reg_read(self.reg.UC_X86_REG_RIP) != 0x1000F000:
            raise ValueError("native branch did not finish")
        bgra = np.frombuffer(bytes(self.uc.mem_read(0x10006000, 1024)), np.uint8).reshape(256, 4)
        return bgra[:, [2, 1, 0, 3]].copy()


def expected_palette(palette, flags, tint, transparency=255):
    """Independent scalar translation of the selected native branch only."""
    out = palette[:, [2, 1, 0, 3]].copy()
    if flags & 0x20000:
        out[2:, :3] = (out[2:, :3].astype(np.uint16) * tint) >> 8
    out[:, 3] = transparency if flags & 2 else 255
    out[0, 3] = 0
    if flags & 4:
        out[1, 3] = (128 * transparency // 255) if flags & 2 else 255 - 128
    return out


def successors(palettes):
    lab = srgb_u8_to_oklab(palettes[:, :, :3])
    distance = np.mean(np.sum((lab[:, :, None, :] - lab[:, None, :, :]) ** 2, axis=-1), axis=0)
    identical = np.all(palettes[:, :, None, :3] == palettes[:, None, :, :3], axis=(0, 3))
    distance[identical] = np.inf
    distance[:, :3] = np.inf
    result = np.arange(256, dtype=np.uint8)
    result[3:] = np.argmin(distance[3:], axis=1).astype(np.uint8)
    assert np.all(np.isfinite(distance[np.arange(3, 256), result[3:]]))
    assert np.all(result[3:] >= 3) and np.all(result[3:] != np.arange(3, 256))
    return result


def verify_decoder(palettes, succ):
    count = 0
    for palette in palettes:
        for fraction in range(8):
            indices = range(256) if fraction == 0 else range(3, 256)
            vector = (((8 - fraction) * palette[:, :3].astype(np.uint16)
                       + fraction * palette[succ, :3].astype(np.uint16) + 4) >> 3).astype(np.uint8)
            for index in indices:
                scalar = [((8 - fraction) * int(palette[index, c])
                           + fraction * int(palette[int(succ[index]), c]) + 4) >> 3 for c in range(3)]
                assert vector[index].tolist() == scalar
                if fraction:
                    assert palette[index, 3] == palette[int(succ[index]), 3]
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unicorn-path", type=Path)
    args = parser.parse_args()
    if args.unicorn_path:
        sys.path.insert(0, str(args.unicorn_path))
    paths = [args.output / name for name in ("contract.json", "profiles.json", "verification.json")]
    if any(p.exists() for p in paths):
        raise ValueError("immutable outputs exist; use a new output directory")
    config = json.loads((ROOT / "config/workspace-paths.local.json").read_text())
    raw = (Path(config["paths"]["bg2ee_game_root"]) / "BaldurReal.exe").read_bytes()
    oracle = NativeFixed(raw)
    with (ROOT / "sprite/index/sprite_families.csv").open(encoding="utf-8-sig", newline="") as stream:
        inventory = list(csv.DictReader(stream))
    profiles, families, resources, golem_audit = [], [], [], []
    native_calls = decoder_cases = 0
    for label, cre, animation, family, prefix, first_profile in FAMILIES:
        source_root = ROOT / "sprite/families/monsters/7fxx" / family / "source/stock"
        manifest = json.loads((source_root / "manifest.json").read_text())
        assert manifest["animation_id"] == animation and len(manifest["bams"]) == 13
        matches = [x for x in inventory if x["animation_id"] == animation
                   and x["bam_prefix"] == prefix and x["layer_kind"] == "body"]
        assert len(matches) == 1
        indexed_family = matches[0]
        assert indexed_family["engine_section"] == "monster"
        if "family_id" in manifest:
            assert manifest["family_id"] == indexed_family["family_id"]
        groups = {1: [], 2: []}
        for bam in manifest["bams"]:
            source = source_root / bam["canonical_bam"]
            head = source.read_bytes()
            assert head[:8] == b"BAM V1  " and head[11] == 0
            offset = struct.unpack_from("<I", head, 16)[0]
            palette = np.frombuffer(head[offset:offset + 1024], np.uint8).reshape(256, 4).copy()
            assert palette[:, 3].tolist() == [0] * 256
            assert palette[:3, [2, 1, 0]].tolist() == [[0, 255, 0], [0, 0, 0], [255, 128, 0]]
            group = int(bam["name"][len(prefix) + 1])
            groups[group].append((bam["name"], palette))
            resources.append({"resref": bam["name"], "animation_id": animation,
                              "source": source.relative_to(ROOT).as_posix(),
                              "canonical_sha256_registered": bam["canonical_bam_sha256"],
                              "palette_bgra_sha256": sha(palette.tobytes()),
                              "palette_profile_id": first_profile + group - 1,
                              "frame_count_registered": bam["frame_count"],
                              "cycle_count_registered": bam["cycle_count"]})
            if prefix == "MGLC":
                decoded = read_bam_p8(head)
                null = 0
                hist = np.zeros(256, np.int64)
                for frame in decoded["frames"]:
                    pixels = frame["indices"]
                    hist += np.bincount(pixels.ravel(), minlength=256)
                    if np.any(pixels == 2):
                        assert (frame["width"], frame["height"], frame["center_x"], frame["center_y"], pixels.size) == (1, 1, 0, 0, 1)
                        null += 1
                golem_audit.append({"resref": bam["name"], "frames": len(decoded["frames"]),
                                    "index2_null_frames": null, "special_pixels_0_1_2": hist[:3].tolist()})
        for group, members in groups.items():
            base = members[0][1]
            assert len(members) == (6 if group == 1 else 7)
            assert all(np.array_equal(base, p) for _, p in members)
            palettes = []
            for _, flags, tint in FITS:
                realized = oracle.realize(base, flags, tint)
                assert np.array_equal(realized, expected_palette(base, flags, tint))
                palettes.append(realized)
                native_calls += 1
            palettes = np.stack(palettes)
            probes = []
            for flags, transparency in ((7, 128), (7, 0), (1, 255)):
                realized = oracle.realize(base, flags, [255] * 3, transparency)
                assert np.array_equal(realized, expected_palette(base, flags, [255] * 3, transparency))
                probes.append({"flags": flags, "transparency": transparency,
                               "alpha_0_1_2_3": realized[:4, 3].tolist()})
                native_calls += 1
            succ = successors(palettes)
            decoder_cases += verify_decoder(palettes, succ)
            profiles.append({"palette_profile_id": first_profile + group - 1,
                             "rule_id": 2, "name": prefix + "-G" + str(group) + "-fixed-k6-v1",
                             "status": "reserved-contract-only-runtime-not-implemented",
                             "resrefs": [name for name, _ in members],
                             "base_bgra_hex": base.tobytes().hex(),
                             "base_bgra_sha256": sha(base.tobytes()),
                             "successor_u8_hex": succ.tobytes().hex(),
                             "successor_sha256": sha(succ.tobytes()),
                             "fits": [{"name": name, "rgba_hex": p.tobytes().hex(),
                                       "rgba_sha256": sha(p.tobytes())}
                                      for (name, _, _), p in zip(FITS, palettes)],
                             "alpha_native_probes": probes})
        families.append({"target": label, "cre": cre, "animation_id": animation,
                         "family_id": indexed_family["family_id"], "runtime_owner": 3,
                         "runtime_profile": manifest["runtime_profile"], "false_color": 0,
                         "source_manifest": (source_root / "manifest.json").relative_to(ROOT).as_posix()})
    profile_bytes = (json.dumps({"schema": "bg2-q3m-monster-fixed-profiles-v1", "profiles": profiles}, indent=2) + "\n").encode()
    contract = {
        "schema": "bg2-q3m-monster-fixed-contract-v1", "version": "20261002-v1",
        "state": "specified-cpu-verified-not-produced-not-installed",
        "phase": 1, "scale": 2, "families": families, "resources": resources,
        "profiles_file": "profiles.json", "profiles_file_sha256": sha(profile_bytes),
        "semantic_classes": {"transparent": [0], "shadow_black": [1], "null_frame_marker": [2], "material": "3..255"},
        "classes_policy": "Historical fixed material class retained; no inferred Character ramps or i+1 order.",
        "successor_rule": "Specials self. Material: nearest distinct material RGB vector across six fits, equal-weight mean squared OKLab f64; exact tie lowest index. Freeze table; never recompute at runtime.",
        "fitting": [{"name": name, "weight": 1, "flags": flags, "tint_rgb": tint,
                     "transparency": 255} for name, flags, tint in FITS],
        "fitting_provenance": "Designed static native states, not measured ingame conditions; Character REF/DEFAULT/LATIN fits cannot be reused.",
        "oracle": {"exe": "config://bg2ee_game_root/BaldurReal.exe", "exe_sha256": EXE_SHA256,
                   "entry_rva": "0x421430", "fixed_type": 0, "fixed_rva": "0x42d350",
                   "branch_sha256": sha(pe_rva(raw, 0x42D350, 0x42DB06 - 0x42D350)),
                   "method": "unicorn-2.1.4 PE image CPU emulation; static mocked video state; area query white unused; /GS bypass only",
                   "limitations": "No ingame capture, animated range effects, gamma, brightness, area/light/add fits or arbitrary native flags verified."},
        "encoding": {"planes": ["I:u8", "F:u8"], "fraction_range": [0, 7], "dependency_bytes": 32,
                     "candidates": "For guide material, I=3..255 F=0..7; for specials I=guide F=0.",
                     "objective": "Equal-weight K6 mean squared OKLab f64 of integer reconstructed candidates vs six ReboutCX float32 x2 targets; exact tie I then F.",
                     "rgb_decoder": "((8-F)*P[I].rgb + F*P[succ[I]].rgb + 4) >> 3",
                     "alpha_decoder": "P[I].alpha from realized LIVE palette; force transparent index 0 alpha=0; do not infer from source reserved byte.",
                     "dependency": "Union of I and succ[I] where F>0, 256 bits; include live alpha of every primary index in palette change detection.",
                     "dither": False, "B_plane": False, "Q8c": False},
        "guide": "Existing xBR2X provenance-based guide; classify source indices, preserve 0/1/2; no Character mapping. Audit and recipe identity must match before historical guide reuse.",
        "inference_parameters_retained": {"model": "config://reboutcx_model", "model_sha256": "C36A14DDB51AE094324A53B67C345DA2D6B6BBF6A2249726056D5B94BDEDAB05",
                                          "model_scale": 4, "fp16": True, "batch": 86, "canvas_quantum": 32,
                                          "output": "float32 BOX x4 to x2 before integer encoding", "fill": "nearest opaque RGB under index-0 transparency"},
        "cache_identity": "New recipe namespace containing profile/rule, classes, source palette, frozen successor, six fit arrays, alpha/guide policy, xBR/model/kernel and scale. Existing Character namespace incompatible; work key alone insufficient. Phase 2 defines keys and reuse plan; no cache created here.",
        "geometry_format": "V6 I/F/dep layout proposed unchanged; all source frames, native signed centres, exact cycle lookups and null geometry retained. Profile IDs 2..7/rule 2 require producer and reader dispatch extension.",
        "runtime_requirements": ["Dispatch owner 3 and exact animation/resref/palette profile, accept realized fixed kind 0; no Character fallback profile.",
                                 "Frozen six successor tables; alpha stays primary; reject unknown profile/rule or invalid dep/specials; native fallback.",
                                 "Guard equal live alpha on positive material pairs; include live colours/alpha and profile in LUT/cache identities.",
                                 "Retain owner 1/profile 1/rule 1 and UI readers; capability manifest must declare new profiles before installation."],
        "installation_future": "Extend active 78-Character catalogue by only these three families; preserve 81 paperdolls, UI shaders and BOX world settings. No active installation/release/QA/registry touched in phase 1.",
        "build_script_sha256": sha(Path(__file__).read_bytes()),
    }
    verification = {"schema": "bg2-q3m-monster-contract-verification-v1", "status": "passed",
                    "scope": "phase1-only-offline-cpu", "palette_headers": len(resources),
                    "profiles": len(profiles), "native_realization_cases": native_calls,
                    "native_palette_entries_checked": native_calls * 256,
                    "decoder_rgb_cases": decoder_cases, "mismatches": 0,
                    "golem_index2_audit": golem_audit,
                    "golem_index2_total": sum(x["index2_null_frames"] for x in golem_audit),
                    "historical_semantics_reused": [
                        "sprite/families/monsters/7fxx/7f02-mbeh-beholder/jobs/reboutcx-p2-mbeh-v2.json",
                        "sprite/families/monsters/7fxx/7f30-nboh-bodhi/jobs/reboutcx-p2-sample-v1.json"],
                    "no_source_frame_dedup_or_character_revalidation": True,
                    "pending": ["MBEH index2 exclusive-null guard in phase2 if not established by existing witnesses",
                                "Runtime implementation, captured actual Monster palette kind/flags/alpha and ingame QA",
                                "Visual pilot quality of K6/successors; replace contract with new version if needed"]}
    args.output.mkdir(parents=True, exist_ok=True)
    for path, payload in zip(paths, (contract, None, verification)):
        data = profile_bytes if payload is None else (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
        with path.open("xb") as stream:
            stream.write(data)
    print(json.dumps({k: verification[k] for k in ("status", "profiles", "native_realization_cases", "decoder_rgb_cases", "golem_index2_total")}))


if __name__ == "__main__":
    main()
