"""Reproduce this designated BOX session report; exclusive output, no game writes."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median


RUN = Path(__file__).resolve().parent
REPO = RUN.parents[5]
FILTER_RUN = RUN.parent / "palette-q3m-p4-filters-20261001-v1"
BASELINE = RUN.parent / "palette-q3m-p4-measurement-20261001-v1"
SOURCE = FILTER_RUN / "captures/box/p4-20261001T203636-1790886996165582.csv"
EXPECTED_SHA = "6971BDAF36E8825D1B51E2D39C116CC20AE69BF20622D57B375AB20EB0F91334"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def eligible(row: dict) -> bool:
    return (all(math.isfinite(v) for v in row.values())
            and row["view_valid"] == row["memory_valid"] == 1
            and not row["view_mixed"] and row["target_successes"] > 0
            and row["frame_samples"] >= 15 and not row["frame_dropped"]
            and row["window_s"] >= 0.9)


def stage(label: str, rows: list[dict]) -> dict:
    assert rows
    frames = sum(r["frames"] for r in rows)
    samples = sum(r["frame_samples"] for r in rows)
    seconds = sum(r["window_s"] for r in rows)
    zooms = {(r["zoom_x"], r["zoom_y"]) for r in rows}
    assert len(zooms) == 1
    return {
        "label": label, "zoom": list(next(iter(zooms))),
        "windows": len(rows), "seconds": seconds,
        "first_window_end_s": rows[0]["elapsed_s"],
        "last_window_end_s": rows[-1]["elapsed_s"],
        "frames": int(frames),
        "cadence_fps": 1000 * samples / sum(r["frame_samples"] * r["frame_avg_ms"] for r in rows),
        "window_p95_median_ms": median(r["frame_p95_ms"] for r in rows),
        "window_p95_max_ms": max(r["frame_p95_ms"] for r in rows),
        "frame_max_ms": max(r["frame_max_ms"] for r in rows),
        "cpu_composite_ms_per_frame": sum(r["target_cpu_ms"] for r in rows) / frames,
        "cpu_pixels_ms_per_frame": sum(r["pixel_cpu_ms"] for r in rows) / frames,
        "cpu_upload_setup_ms_per_frame": sum(r["upload_cpu_ms"] for r in rows) / frames,
        "cpu_mask_ms_per_frame": sum(r["mask_cpu_ms"] for r in rows) / frames,
        "mask_calls": int(sum(r["mask_calls"] for r in rows)),
        "mask_cpu_max_ms": max(r["mask_cpu_max_ms"] for r in rows),
        "rgba_upload_MB_per_second": sum(r["upload_bytes"] for r in rows) / seconds / 1e6,
        "camera_positions": len({(r["scroll_x"], r["scroll_y"]) for r in rows}),
    }


def main() -> None:
    names = ["session.csv", "summary.json", "result.json", "provenance.json", "runtime-excerpt.log", "README.md"]
    assert not any((RUN / name).exists() for name in names), "Historical outputs must not be overwritten."
    data = SOURCE.read_bytes()
    assert sha(data) == EXPECTED_SHA
    rows = [{k: float(v) for k, v in r.items()}
            for r in csv.DictReader(data.decode("utf-8").splitlines())]
    valid = [r for r in rows if r["view_valid"]]
    stable = [r for r in rows if eligible(r)]
    assert len(rows) == 175 and len(valid) == 162 and len(stable) == 130
    assert {(r["viewport_w"], r["viewport_h"], r["framebuffer"], r["scale"],
             r["filter_mode"], r["min_filter"], r["mag_filter"], r["max_mip_level"],
             r["animation_id"]) for r in valid} == {(2528, 1339, 0, 4, 3, 9728, 9728, 0, 24848)}
    ranges = [
        ("initial_static", 15.452125, 26.554451, 12),
        ("maximum_first", 29.572197, 48.724213, 20),
        ("habitual_static", 53.757603, 72.908171, 20),
        ("minimum", 91.078425, 116.242376, 26),
        ("maximum_return", 121.277385, 138.379898, 18),
        ("habitual_return_movement_camera", 143.427877, 176.649036, 34),
    ]
    stages = []
    for label, first, last, count in ranges:
        selected = [r for r in stable if first <= r["elapsed_s"] <= last]
        assert len(selected) == count, label
        stages.append(stage(label, selected))
    assert sum(s["windows"] for s in stages) == len(stable)
    assert stages[2]["zoom"] == stages[5]["zoom"]

    installation = json.loads((FILTER_RUN / "installation-verification.json").read_text(encoding="utf-8"))
    receipt = json.loads((FILTER_RUN / "ingame-filter/active-test.json").read_text(encoding="utf-8"))
    game = Path(receipt["game_root"])
    checked = {"InfinityEngine-Enhancer.dll": installation["dll_sha256"],
               "InfinityEngine-Enhancer.ini": installation["ini_sha256"]}
    checked.update({s["target"]: s["sha256"] for s in installation["shaders"]})
    for rel, expected in checked.items():
        assert sha((game / rel).read_bytes()) == expected, rel
    assert receipt["filter"] == "Box"
    stamp = int(re.search(r"-(\d+)\.csv$", SOURCE.name).group(1))
    start = datetime.fromtimestamp(stamp / 1e6, timezone.utc)
    end = start + timedelta(seconds=rows[-1]["elapsed_s"])
    paris = timezone(timedelta(hours=2))
    local_start, local_end = start.astimezone(paris), end.astimezone(paris)
    log_path = game / "InfinityEngine-Enhancer.log"
    log_data = log_path.read_bytes()
    all_log = log_data.decode("utf-8-sig").splitlines()
    current_log = []
    for line in all_log:
        match = re.match(r"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\]", line)
        if match:
            when = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=paris)
            if local_start - timedelta(seconds=2) <= when <= local_end:
                current_log.append(line)
    warnings = [line for line in current_log if re.search(r"\[(warning|warn|error|critical)\]", line)]
    excerpt = [line for line in current_log if
               any(key in line for key in ("catalog ready", "P4_SPRITE_PROBE", "DrawColorTone hook installed",
                                           "Composing creature sprite", "[warning]", "[error]", "[critical]"))
               or re.match(r"\[2026-10-01 22:(38:59\.(579|645|711)|39:04\.(177|244|311))\]", line)]
    baseline = json.loads((BASELINE / "result.json").read_text(encoding="utf-8"))
    comparisons = []
    for new_index, old_index in ((0, 0), (3, 1), (1, 2)):
        new, old = stages[new_index], baseline["stable_paliers"][old_index]
        comparisons.append({
            "box_stage": new["label"], "nearest_baseline_stage": old["label"],
            "box_window_p95_median_ms": new["window_p95_median_ms"],
            "nearest_window_p95_median_ms": old["window_p95_median_ms"],
            "median_p95_delta_percent": (new["window_p95_median_ms"] / old["window_p95_median_ms"] - 1) * 100,
            "within_plus_5_percent_on_this_statistic": new["window_p95_median_ms"] <= old["window_p95_median_ms"] * 1.05,
        })
    totals = {k: int(sum(r[k] for r in rows)) for k in
              ("target_calls", "target_successes", "upload_calls", "upload_successes",
               "pixel_calls", "pixel_cache_hits", "upload_bytes", "mask_calls", "mask_successes", "view_samples")}
    assert totals["target_calls"] == totals["target_successes"] == totals["upload_calls"] == totals["upload_successes"] == 9649
    assert totals["mask_calls"] == totals["mask_successes"] == 448
    totals.update({"window_count": len(rows), "duration_seconds": rows[-1]["elapsed_s"],
                   "pixel_cache_hit_percent": totals["pixel_cache_hits"] / totals["pixel_calls"] * 100,
                   "peak_process_working_set_bytes": int(max(r["working_set_bytes"] for r in rows)),
                   "peak_process_private_bytes": int(max(r["private_bytes"] for r in rows)),
                   "target_failures": totals["target_calls"] - totals["target_successes"],
                   "upload_failures": totals["upload_calls"] - totals["upload_successes"],
                   "mask_failures": totals["mask_calls"] - totals["mask_successes"]})
    result = {
        "schema": "bg2-p4-box-session-result-v1", "date": "2026-10-01",
        "status": "box-session-measured-user-reports-prettier-zoomed-out",
        "viewport": [2528, 1339], "scale": 4, "filter": "Box", "animation_scope": "0x6110",
        "sampler": {"MIN": "NEAREST", "MAG": "NEAREST", "MAX_LEVEL": 0,
                    "effective_minification": "explicit shader BOX area integral; filter_mode=3"},
        "overall": totals, "stable_stages": stages, "nearest_baseline_comparisons": comparisons,
        "baseline_path": str(BASELINE / "result.json"),
        "user_visual_feedback": {"verbatim": "ca semble plus joli en dézoom. j'ai compté 7 crans depuis le zoom max",
                                 "zoom_steps_back_from_maximum": 7,
                                 "habitual_measured_zoom": stages[2]["zoom"],
                                 "verdict_scope": "positive perceived zoom-out appearance; no explicit halo/detail/shimmer judgment"},
        "runtime_warnings": warnings,
        "native_frame_fallback": {
            "warning_observed": True, "resref": "CHFB1G11", "sequence": 6, "slot": -1,
            "local_time": "2026-10-01T22:39:00.710+02:00",
            "cause": "negative native frame slot rejected before filter; guard also present in HEAD",
            "source": "src/iee/creature_sprite_x2.cpp:4233; src/iee/hooks.cpp:954",
            "warning_frequency": "once per process; total native fallback count unavailable",
            "visual_consequence": "not established; retain as comparison observation"},
        "other_warnings": "WATER_ROUTE2 AR0900 native fallback and recovered EEex RenderTexture detour also logged in preceding 21:58 session; outside P4, unchanged here.",
        "outlier_windows_above_40ms": [{"window_end_s": r["elapsed_s"], "frame_max_ms": r["frame_max_ms"],
                                          "window_p95_ms": r["frame_p95_ms"], "eligible": eligible(r),
                                          "view_valid": bool(r["view_valid"]), "view_mixed": bool(r["view_mixed"])}
                                         for r in rows if r["frame_max_ms"] > 40],
        "limits": [
            "FPS describe the whole scene around 60 FPS; no isolated GPU time/cost available.",
            "Per-window p95 median/max, not a reconstructed global p95; isolated 52.2784ms stable-window frame retained.",
            "Stage labels combine user protocol, zoom/camera CSV and moving world positions in log; precise walk/camera subphase boundary uninstrumented.",
            "CPU pixels/upload are nested in composite; mask setup separate; CPU submission is not GPU execution.",
            "Process memory is not sprite-only memory or VRAM; upload_bytes are base traffic, not residency.",
            "Longer session, poses/cache history differ from prior Nearest; matching zoom does not establish controlled GPU/CPU A/B.",
            "BOX habitual zoom 2.480864 differs from prior Nearest habitual 2.6865; compare future trials at maximum minus 7 steps.",
            "Successful composite/mask counters do not count pre-composition native frame fallbacks.",
        ],
        "p4_scale_filter_decision": "pending mipmaps and x2 comparisons; BOX visual preference only",
        "installation_modified_during_measurement": False,
    }
    provenance = {
        "schema": "bg2-p4-box-measurement-provenance-v1", "source": str(SOURCE),
        "source_sha256": EXPECTED_SHA, "source_bytes": len(data),
        "session_start_utc": start.isoformat(), "session_end_utc": end.isoformat(),
        "session_start_local": local_start.isoformat(), "session_end_local": local_end.isoformat(),
        "source_last_write_utc": datetime.fromtimestamp(SOURCE.stat().st_mtime, timezone.utc).isoformat(),
        "runtime_log_source": str(log_path), "runtime_log_source_sha256": sha(log_data),
        "runtime_log_excerpt_sha256": sha(("\n".join(excerpt) + "\n").encode("utf-8")),
        "installation_verify": "Set-Sprite-P4-Filter.ps1 -Mode Verify: verified Box / 0x6110 / x4; game and InfinityLoader closed",
        "checked_installed_hashes": checked, "catalog_sha256": installation["catalog_sha256"],
        "analysis_script_sha256": sha(Path(__file__).read_bytes()),
        "parser_path": "pipeline/scripts/palette_p4_probe.py",
        "parser_sha256": sha((REPO / "pipeline/scripts/palette_p4_probe.py").read_bytes()),
        "baseline_result_sha256": sha((BASELINE / "result.json").read_bytes()),
        "authorization": "User: tests faits. tu peux vérifier la session",
        "pc_control": False, "game_installation_modified": False, "historical_evidence_modified": False,
    }
    spec = importlib.util.spec_from_file_location("p4_summary", REPO / "pipeline/scripts/palette_p4_probe.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with (RUN / "session.csv").open("xb") as stream:
        stream.write(data)
    summary = module.summarize(RUN / "session.csv")
    assert summary["ignored_windows"] == 45
    for name, value in (("summary.json", summary), ("result.json", result), ("provenance.json", provenance)):
        with (RUN / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    with (RUN / "runtime-excerpt.log").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(excerpt) + "\n")
    table = "\n".join(f"| {s['label']} | {s['zoom'][0]:.4f} | {s['windows']} | {s['cadence_fps']:.3f} | {s['window_p95_median_ms']:.4f} / {s['window_p95_max_ms']:.4f} | {s['cpu_composite_ms_per_frame']:.4f} | {s['cpu_mask_ms_per_frame']:.4f} |" for s in stages)
    readme = f"""# P4 BOX x4 — mesure 2026-10-01 v1

- Session autorisée : `tests faits. tu peux vérifier la session` ; Paris {local_start:%H:%M:%S}–{local_end:%H:%M:%S}, {totals['duration_seconds']:.6f} s ; SHA256 CSV `{EXPECTED_SHA}`.
- Installation vérifiée : `iee-sprite-p4-filters-20261001-v1`, BOX x4, `0x6110` ; viewport 2528×1339, FBO=0 ; mode=3, MIN=MAG=NEAREST, MAX_LEVEL=0. BOX effectif au shader ; aucun mipmap attendu.
- 175 fenêtres : 162 avec draw cible, 130 éligibles, 45 ignorées par critères existants du parseur. Scinder les phases contiguës ; ne pas confondre les deux passages au zoom habituel.

| Phase | Zoom x | Fenêtres | FPS | p95 fenêtre médian / max ms | CPU composition ms/frame | CPU masque ms/frame |
|---|---:|---:|---:|---:|---:|---:|
{table}

- Totaux : 9 649/9 649 compositions et uploads, 448/448 masques ; cache pixels 7 208 hits ({totals['pixel_cache_hit_percent']:.2f} %) ; 6.686 GiB trafic RGBA base. Pics processus : WS 981.875 MiB, privé 1.808 GiB ; ni mémoire sprites seule, ni VRAM.
- Composition 3/3 : `CHFB1G12` + `WQNJ8G1` + `WQNFSG1` ; phases marche avec coordonnées monde variables et caméra mobile observées. Provenance composite=1 (153 fenêtres), masque=2 (9).
- Comparaison baseline Nearest `../palette-q3m-p4-measurement-20261001-v1/result.json` : p95 médian au zoom initial/min/max ≈ +0.267 % / −0.098 % / +0.046 %. Chaque statistique < +5 % ; observation scène/cadence, pas coût GPU isolé ni preuve globale de non-régression.
- Zoom habituel confirmé utilisateur : **maximum −7 crans**, x=2.480864, y=2.479630 ; répété exactement au retour. Différent du zoom habituel Nearest précédent (2.6865) : reprendre −7 aux essais suivants.
- Retour utilisateur exact : « ca semble plus joli en dézoom. j'ai compté 7 crans depuis le zoom max ». Préférence BOX en réduction ; aucun verdict explicite contours/halo/scintillement.
- Avertissement cible à 22:39:00.710 : `CHFB1G11 sequence=6 slot=-1`, rendu natif conservé. Slot négatif rejeté avant filtrage par garde existante dans HEAD ; warning limité à une occurrence/processus ⇒ nombre réel de replis inconnu. Effet visible non établi ; à surveiller en Nearest/Mipmaps.
- Autres warnings : eau `AR0900/WTLAKE` en repli natif et prologue RenderTexture EEex récupéré ; déjà présents au lancement 21:58 ; hors périmètre P4, aucune correction ici.
- Outliers conservés dans `result.json` : démarrage/chargement 1 461/836 ms ; transitions zoom ≈49–51 ms ; frame isolée 52.2784 ms dans palier initial stable. Aucun retrait rétrospectif de cette fenêtre stable.
- Limites : FPS globaux ≈60 ; p95 calculé par fenêtre, pas global ; CPU imbriqué composition/pixels/upload, masque séparé ; session plus longue/poses/cache différents ; frontière marche/panoramique non instrumentée.
- **P4 ouverte** : BOX mesuré + retour visuel positif ; Mipmaps et x2 restant à comparer avant décision datée échelle/filtre. P3 acceptée conservée ; aucune modification installation/release pendant la mesure.

Artefacts : `session.csv` copie exacte ; `summary.json` parseur commun ; `result.json` phases/totaux/limites ; `provenance.json` hashes/identités ; `runtime-excerpt.log` lancement/layers/marche/warnings ; `analyze.py` calcul exclusif (refuse d'écraser les sorties).
"""
    with (RUN / "README.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(readme)
    assert sha(SOURCE.read_bytes()) == sha((RUN / "session.csv").read_bytes()) == EXPECTED_SHA
    print(json.dumps({"status": "measured", "report": str(RUN / "README.md"),
                      "rows": len(rows), "eligible": len(stable), "totals": totals,
                      "stages": stages, "comparison": comparisons, "warnings": len(warnings)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
