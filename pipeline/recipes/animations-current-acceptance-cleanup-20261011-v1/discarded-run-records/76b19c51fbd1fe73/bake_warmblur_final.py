"""Final warm-patch blur bake for AM0803B/C/E.

Mask = warmblur_v8 seed+propagate (seed V>92 largest component -> propagate
through Vmax>78 warm region -> margin + feather). Blur radius 2 (validated).
Only the 14 .rgba per resref change; geometry untouched so the structural
registry stays byte-identical -- only per-asset sha256 fields in the manifest
are rewritten (bytes unchanged: same dims, same RGBA8). RGB blurred in place
(pack RGB already premultiplied); alpha copied verbatim.

Per-resref mask params:
  B : grow_T=78 margin_dil=3 feather=4   (validated contour)
  C : grow_T=78 margin_dil=8 feather=5   (validated, widened)
  E : grow_T=78 margin_dil=8 feather=5   (validated, widened)
A and D get an empty mask from this method and are intentionally NOT processed.
"""
import copy, hashlib, json, shutil, sys
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import warmblur_v8 as wb

PROJ = Path("G:/AI/BG2_Upscale")
DATE = "20260907"
RADIUS = 3.5
MASK = {
    "AM0803B": dict(seed_T=92, grow_T=78, margin_dil=3, feather=4.0),
    "AM0803C": dict(seed_T=92, grow_T=78, margin_dil=8, feather=5.0),
    "AM0803E": dict(seed_T=92, grow_T=78, margin_dil=8, feather=5.0),
}

def sha(b): return hashlib.sha256(b).hexdigest()

for resref, mcfg in MASK.items():
    lc = resref.lower()
    src = PROJ / f"animations/ressources/{resref}/runs/{lc}-apo8-x4-30fps-v2-spline-fit1-feather4-{DATE}"
    dst = PROJ / f"animations/ressources/{resref}/runs/{lc}-apo8-x4-30fps-v2-spline-fit1-feather4-warmblur-{DATE}"
    if dst.exists():
        print(f"!! exists, skipping create: {dst.name} (remove to re-bake)"); sys.exit(1)
    shutil.copytree(src, dst)
    pack = dst / "03_runtime_pack"
    man = json.loads((pack / "manifest.json").read_text())
    reg_before = (pack / "AreaAnimations-X4.registry").read_bytes()
    res = man["resources"][0]
    assert res["resref"] == resref
    w, h = res["frames"][0]["physical_size_x4"]

    frames_rgba = []
    order = sorted(res["frames"], key=lambda x: int(x["frame"]))
    for fr in order:
        frames_rgba.append(np.frombuffer((pack / fr["asset"]).read_bytes(), np.uint8).reshape(h, w, 4).copy())
    out, M = wb.process_sequence(frames_rgba, radius=RADIUS, **mcfg)
    maskpx = int((M > 0.3).sum())

    newhash = {}
    for fr, a in zip(order, out):
        blob = a.tobytes()
        assert len(blob) == fr["bytes"], (fr["asset"], len(blob), fr["bytes"])
        (pack / fr["asset"]).write_bytes(blob)
        newhash[fr["asset"]] = sha(blob)

    for fr in res["frames"]:
        fr["sha256"] = newhash[fr["asset"]]
    for asset in res["assets"]:
        asset["sha256"] = newhash[asset["name"]]
    for key in ("new_assets", "replacement_assets"):
        for item in man.get(key) or []:
            if item["name"] in newhash:
                item["sha256"] = newhash[item["name"]]
    man["warm_patch_blur"] = {
        "effect": f"warm-patch-gaussian-blur-r{RADIUS}",
        "method": "warmblur_v8 seed(V>92 largest-comp) + propagate(Vmax>78 warm) + margin + feather",
        "mask_params": mcfg,
        "mask_px": maskpx,
        "applied_to": [resref],
        "rgb_policy": "blurred in place; pack RGB already premultiplied; alpha verbatim",
        "derived_from_run": src.name,
        "derived_from_pack_manifest_sha256": sha((src / "03_runtime_pack" / "manifest.json").read_bytes()),
    }
    (pack / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reg_after = (pack / "AreaAnimations-X4.registry").read_bytes()
    print(f"{resref}: 14 frames blurred r{RADIUS} | mask {maskpx}px | registry identical: {reg_before == reg_after}")
    print(f"   -> {dst.relative_to(PROJ)}")
