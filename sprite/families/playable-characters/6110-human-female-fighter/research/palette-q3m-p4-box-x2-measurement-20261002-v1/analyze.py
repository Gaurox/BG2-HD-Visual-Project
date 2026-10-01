"""Archive the designated x2 BOX session and dated P4 choice; game read-only."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path


RUN = Path(__file__).resolve().parent
REPO = RUN.parents[5]
INSTALL_RUN = RUN.parent / "palette-q3m-p4-box-x2-20261001-v1"
BOX_RUN = RUN.parent / "palette-q3m-p4-box-measurement-20261001-v1"
MIPS_RUN = RUN.parent / "palette-q3m-p4-mipmaps-measurement-20261001-v1"
SOURCE = INSTALL_RUN / "captures/box-x2/p4-20261001T220659-1790892419735420.csv"
EXPECTED_SHA = "188B421DDB07B4B0CF4F2870A16791BC6523E6AD0E5D4A3C2EE4952E2171518B"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_native_frame(game: Path) -> dict:
    coverage_path = RUN.parent / "palette-q3m-p3-20261001-v3-full-6110/coverage.json"
    resource = next(r for r in json.loads(coverage_path.read_text())["resources"] if r["resref"] == "CHFB1G11")
    digest = resource["registry_sha256"]
    path = game / "iee-assets/creature-sprites" / f"CreatureSprites-XN-{digest}.registry"
    data = path.read_bytes()
    assert sha(data) == digest
    assert struct.unpack_from("<8s6I", data) == (b"IEECSXN\0", 6, 2, 1, 65535, 1, 1)
    ref, source, frames, cycles = struct.unpack_from("<8s32sII", data, 32)
    assert ref == b"CHFB1G11" and source.hex().upper() == resource["source_sha256"]
    offset = 80
    for _ in range(frames):
        stored_i = struct.unpack_from("<I", data, offset + 12)[0]
        stored_f = struct.unpack_from("<I", data, offset + 560)[0]
        offset += 568 + stored_i + stored_f
    tables = []
    for _ in range(cycles):
        count = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        tables.append(list(struct.unpack_from(f"<{count}I", data, offset)))
        offset += count * 4
    assert offset == len(data) and len(tables[6]) == 10
    oracle = load_module("native_bam", REPO / "pipeline/scripts/palette_oracle.py")
    bam_path = RUN.parents[1] / "chfb1/source/resources/CHFB1G11/source.bamc"
    native = oracle.read_bam_p8(bam_path.read_bytes())
    assert sha(native["canonical"]) == source.hex().upper()
    assert native["cycles"][6]["frame_indices"] == tables[6]
    return {"path": str(path), "sha256": digest, "source_sha256": source.hex().upper(),
            "resref": "CHFB1G11", "frames": frames, "cycles": cycles, "sequence": 6,
            "cycle_slots": 10, "valid_slot_range": [0, 9], "cycle_frames": tables[6],
            "requested_slot": 10, "requested_slot_out_of_range": True,
            "source_cycle_identical": True, "local_time": "2026-10-02T00:08:16.720+02:00",
            "guard": "creature_sprite_x2.cpp:4300 rejects currentFrame >= cycle.size(), before filtering",
            "warning_frequency": "once/process; total native fallback count unavailable",
            "visual_consequence": "not established"}


def main() -> None:
    names = ["session.csv", "summary.json", "result.json", "decision.json", "provenance.json", "runtime-excerpt.log", "README.md"]
    assert not any((RUN / name).exists() for name in names), "Historical outputs must not be overwritten."
    data = SOURCE.read_bytes()
    assert sha(data) == EXPECTED_SHA
    rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(data.decode().splitlines())]
    helper = load_module("box_helpers", BOX_RUN / "analyze.py")
    stable = [r for r in rows if helper.eligible(r)]
    valid = [r for r in rows if r["view_valid"]]
    assert (len(rows), len(valid), len(stable)) == (92, 82, 68)
    assert {(r["viewport_w"], r["viewport_h"], r["framebuffer"], r["scale"], r["filter_mode"],
             r["min_filter"], r["mag_filter"], r["max_mip_level"], r["animation_id"])
            for r in valid} == {(2528, 1339, 0, 2, 3, 9728, 9728, 0, 24848)}
    ranges = [("initial_after_world_entry", 11.609167, 16.643960, 6),
              ("maximum_first", 18.661314, 31.810858, 14),
              ("habitual_static", 36.860953, 49.961375, 14),
              ("minimum", 53.982518, 69.091689, 16),
              ("habitual_return_movement_camera", 76.131664, 92.202163, 17)]
    stages = []
    for label, first, last, count in ranges:
        selected = [r for r in stable if first <= r["elapsed_s"] <= last]
        assert len(selected) == count, (label, len(selected))
        stages.append(helper.stage(label, selected))
    assert sum(s["windows"] for s in stages) == 67
    assert stages[2]["zoom"] == stages[4]["zoom"] == [2.480864, 2.479630]
    box = json.loads((BOX_RUN / "result.json").read_text(encoding="utf-8"))
    comparisons = []
    for new in stages:
        old_label = "initial_static" if new["label"] == "initial_after_world_entry" else new["label"]
        old = next(s for s in box["stable_stages"] if s["label"] == old_label)
        assert new["zoom"] == old["zoom"]
        metrics = ("cadence_fps", "window_p95_median_ms", "window_p95_max_ms", "cpu_composite_ms_per_frame",
                   "cpu_upload_setup_ms_per_frame", "cpu_mask_ms_per_frame", "rgba_upload_MB_per_second")
        comparison = {"stage": new["label"], "zoom": new["zoom"], "x2_seconds": new["seconds"], "x4_seconds": old["seconds"]}
        for key in metrics:
            comparison[f"x2_{key}"] = new[key]
            comparison[f"x4_{key}"] = old[key]
        for key in ("cpu_composite_ms_per_frame", "rgba_upload_MB_per_second", "window_p95_median_ms"):
            comparison[f"x2_to_x4_{key}_ratio"] = new[key] / old[key]
        comparisons.append(comparison)
    state_path = INSTALL_RUN / "ingame-installation/box-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert (state["scale"], state["filter"], state["animation"]) == (2, "Box", "0x6110")
    game = Path(state["game_root"])
    manifest = json.loads((REPO / "pipeline/runtime/manifests/iee-sprite-p4-box-x2-20261001-v1.json").read_text())
    checked = {"InfinityEngine-Enhancer.dll": state["after"]["dll"], "InfinityEngine-Enhancer.ini": state["after"]["ini"],
               "iee-assets/creature-sprites/CreatureSprites-XN.catalog": state["after"]["catalog"]}
    checked.update({s["target"]: s["sha256"] for s in manifest["shaders"]})
    for rel, expected in checked.items():
        assert sha((game / rel).read_bytes()) == expected, rel
    receipt_path = INSTALL_RUN / "ingame-installation/active-test.json"
    assert sha(receipt_path.read_bytes()) == state["catalog_receipt_sha256"]
    native = inspect_native_frame(game)
    stamp = int(re.search(r"-(\d+)\.csv$", SOURCE.name).group(1))
    start = datetime.fromtimestamp(stamp / 1e6, timezone.utc)
    end = start + timedelta(seconds=rows[-1]["elapsed_s"])
    paris = timezone(timedelta(hours=2))
    local_start, local_end = start.astimezone(paris), end.astimezone(paris)
    log_path = game / "InfinityEngine-Enhancer.log"
    log_data = log_path.read_bytes()
    current_log = []
    for line in log_data.decode("utf-8-sig").splitlines():
        match = re.match(r"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\]", line)
        if match:
            when = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=paris)
            if local_start - timedelta(seconds=2) <= when <= local_end + timedelta(seconds=1):
                current_log.append(line)
    warnings = [line for line in current_log if re.search(r"\[(warning|warn|error|critical)\]", line)]
    excerpt = [line for line in current_log if any(key in line for key in
               ("catalog ready", "P4_SPRITE_PROBE", "DrawColorTone hook installed", "Composing creature sprite", "[warning]", "[error]", "[critical]"))
               or re.match(r"\[2026-10-02 00:08:(15\.0|16\.7|2[01]\.1|31\.3)", line)]
    totals = {k: int(sum(r[k] for r in rows)) for k in ("target_calls", "target_successes", "upload_calls", "upload_successes",
              "pixel_calls", "pixel_cache_hits", "upload_bytes", "mask_calls", "mask_successes", "view_samples")}
    assert totals["target_calls"] == totals["target_successes"] == totals["upload_calls"] == totals["upload_successes"] == 4892
    assert totals["mask_calls"] == totals["mask_successes"] == 327
    totals.update({"window_count": len(rows), "duration_seconds": rows[-1]["elapsed_s"],
                   "pixel_cache_hit_percent": totals["pixel_cache_hits"] / totals["pixel_calls"] * 100,
                   "peak_process_working_set_bytes": int(max(r["working_set_bytes"] for r in rows)),
                   "peak_process_private_bytes": int(max(r["private_bytes"] for r in rows)),
                   "target_failures": 0, "upload_failures": 0, "mask_failures": 0})
    feedback = {"date_local": "2026-10-02",
                "filter_verbatim": "tests fait. au passage je confirme que box est bien meilleur visuellement que mimpas a mesure qu'on dézoome",
                "scale_verbatim": "J'ai un léger sentiment de préférer x2 bien que ce soit difficile à dire.",
                "interpretation": "clear BOX preference in zoom-out; slight, uncertain x2 preference; no quantified visual superiority or exhaustive artifact QA"}
    decision = {"schema": "bg2-p4-scale-filter-decision-v1", "date_local": "2026-10-02", "status": "decided",
                "default_scale": 2, "default_filter": "Box", "mipmaps_enabled": False, "animation_scope": "0x6110",
                "master_scale": 4, "x4_status": "optional quality candidate, not preferred in this trial",
                "basis": "User clearly prefers BOX to tested x4 Mipmaps; slightly prefers x2 to x4 with BOX. x2 has lower measured CPU composition and base upload traffic at matched zoom.",
                "feedback": feedback, "viewport": [2528, 1339], "habitual_zoom": stages[2]["zoom"],
                "habitual_steps_from_max": 7, "evidence": ["result.json", str(BOX_RUN / "result.json"), str(MIPS_RUN / "result.json")],
                "runtime_id": "iee-sprite-p4-box-x2-20261001-v1", "catalog_sha256": state["after"]["catalog"],
                "catalog_routes": ["0x6100", "0x6110"], "other_route_filter": "0x6100 remains Nearest; no BOX QA transferred",
                "installation": "existing x2 BOX remains active; no replacement during measurement",
                "qa_scope": "P4 scale/filter choice for tested Character scene; P3 acceptance preserved; no broader family/artifact-free QA inferred",
                "release_changed": False, "pc_control": False}
    result = {"schema": "bg2-p4-box-x2-session-result-v1", "date": "2026-10-02", "status": "measured-p4-choice-x2-box",
              "viewport": [2528, 1339], "scale": 2, "filter": "Box", "animation_scope": "0x6110",
              "sampler": {"MIN": "NEAREST", "MAG": "NEAREST", "filter_mode": 3, "max_mip_level": 0,
                          "effective_minification": "explicit shader BOX area integral; no mip chain"},
              "overall": totals, "stages": stages, "matched_zoom_box_x4_comparisons": comparisons,
              "provenance_windows": {"character_composite": 75, "masked": 7},
              "first_world_entry_window": rows[8],
              "stage_selection": "68 parser-eligible windows; 67 comparative. First owned window has 32/32 HD views and a 488.6283ms entry frame. Retained separately and in raw/summary. Stable outliers retained, including 66.7617ms at minimum and movement window p95 24.356ms.",
              "user_visual_feedback": feedback, "p4_decision": "decision.json", "native_frame_fallback": native,
              "runtime_warnings": warnings,
              "outlier_windows_above_40ms": [{"window_end_s": r["elapsed_s"], "frame_max_ms": r["frame_max_ms"],
                   "window_p95_ms": r["frame_p95_ms"], "eligible": helper.eligible(r),
                   "view_valid": bool(r["view_valid"]), "view_mixed": bool(r["view_mixed"])} for r in rows if r["frame_max_ms"] > 40],
              "limits": ["Whole-scene FPS and median/max per-window p95; no isolated GPU timing or reconstructed global p95.",
                         "CPU pixels/upload nested in composition; mask separate. Traffic is base RGBA upload, not VRAM residency.",
                         "x2 stages 14-17s vs longer x4 stages; poses/cache/session duration differ. Matching zoom is not a controlled cost A/B.",
                         "Process memory peaks include the entire process and session history, not sprite-only memory or VRAM.",
                         "Motion and camera observed; exact walk/pan subphase boundary uninstrumented. Last movement window has 51/60 owned views, retained.",
                         "Native rejection before counted compositions; warning once/process, no total native fallback count.",
                         "BOX x2 at habitual zoom ~2.48 is magnification (~0.806 texel/pixel), so nearest path; minimum ~0.823 is BOX minification (~2.43 texels/pixel).",
                         "Mipmaps compared at x4 only; no x2 Mipmaps trial or support inferred."],
              "installation_modified_during_measurement": False}
    excerpt_data = ("\n".join(excerpt) + "\n").encode("utf-8")
    provenance = {"schema": "bg2-p4-box-x2-measurement-provenance-v1", "source": str(SOURCE),
                  "source_sha256": EXPECTED_SHA, "source_bytes": len(data),
                  "session_start_utc": start.isoformat(), "session_end_utc": end.isoformat(),
                  "session_start_local": local_start.isoformat(), "session_end_local": local_end.isoformat(),
                  "runtime_log_source": str(log_path), "runtime_log_source_sha256": sha(log_data),
                  "runtime_log_excerpt_sha256": sha(excerpt_data), "checked_installed_hashes": checked,
                  "catalog_receipt_sha256": state["catalog_receipt_sha256"],
                  "installation_verify": "install.ps1 -Mode Verify: 1312 shards, scale=2, Box, 0x6110, Mipmaps=false; game/InfinityLoader closed",
                  "analysis_script_sha256": sha(Path(__file__).read_bytes()),
                  "parser_sha256": sha((REPO / "pipeline/scripts/palette_p4_probe.py").read_bytes()),
                  "helper_sha256": sha((BOX_RUN / "analyze.py").read_bytes()),
                  "x4_box_result_sha256": sha((BOX_RUN / "result.json").read_bytes()),
                  "x4_mipmaps_result_sha256": sha((MIPS_RUN / "result.json").read_bytes()),
                  "authorization": feedback["filter_verbatim"], "pc_control": False,
                  "game_installation_modified": False, "historical_evidence_modified": False}
    with (RUN / "session.csv").open("xb") as stream:
        stream.write(data)
    parser = load_module("p4_summary", REPO / "pipeline/scripts/palette_p4_probe.py")
    summary = parser.summarize(RUN / "session.csv")
    assert summary["ignored_windows"] == 24
    for name, value in (("summary.json", summary), ("result.json", result), ("decision.json", decision), ("provenance.json", provenance)):
        with (RUN / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    with (RUN / "runtime-excerpt.log").open("xb") as stream:
        stream.write(excerpt_data)
    table = "\n".join(f"| {s['label']} | {s['zoom'][0]:.4f} | {s['windows']} | {s['cadence_fps']:.3f} | {s['window_p95_median_ms']:.4f} / {s['window_p95_max_ms']:.4f} | {s['cpu_composite_ms_per_frame']:.4f} | {s['cpu_mask_ms_per_frame']:.4f} |" for s in stages)
    text = f"""# P4 — décision x2 + BOX, 2026-10-02 v1

- Décision `decision.json` : **x2 + BOX sur 0x6110**, sans mipmaps ; master x4 conservé, x4 option qualité. Préférence utilisateur BOX nette en dézoom ; préférence x2 légère/incertaine. Aucun verdict visuel quantifié ni QA transférée à 0x6100/release.
- Session Paris {local_start:%Y-%m-%d %H:%M:%S}–{local_end:%H:%M:%S}, {totals['duration_seconds']:.6f} s ; CSV SHA256 `{EXPECTED_SHA}`, {len(data)} octets. Viewport 2528×1339, FBO=0 ; scale=2, mode=3, MIN=MAG=NEAREST, MAX_LEVEL=0 ; BOX explicite shader, aucune chaîne mip.
- 92 fenêtres ; 82 draw cible, 68 éligibles parseur, 24 ignorées ; 67 fenêtres comparatives + première entrée monde (488.6283 ms) retenue séparément/raw. Provenance composite=75, masque=7.

| Phase | Zoom x | Fenêtres | FPS | p95 fenêtre médian / max ms | CPU composition ms/frame | CPU masque ms/frame |
|---|---:|---:|---:|---:|---:|---:|
{table}

- Totaux : 4 892/4 892 compositions et uploads ; 327/327 masques ; cache 3 670 hits ({totals['pixel_cache_hit_percent']:.2f} %) ; {totals['upload_bytes']} octets RGBA base. Pics processus WS={totals['peak_process_working_set_bytes'] / 2**20:.3f} MiB, privé={totals['peak_process_private_bytes'] / 2**30:.3f} GiB ; ni mémoire sprites seule ni VRAM.
- Habituel **maximum −7 crans** : zoom 2.480864/2.479630, exact aux phases statique/mouvement x2 et BOX x4 ; CPU composition 0.148325 vs 0.279973 ms/frame ; trafic base 11.082 vs 44.269 MB/s ; FPS 60.003 vs 59.998. Sessions indépendantes, durées/poses/cache différents ⇒ observation comparative, pas GPU isolé.
- À ce zoom, x2 est en magnification Nearest (empreinte ~0.806 texel/pixel) ; BOX agit au minimum (zoom ~0.823, empreinte ~2.43). Dimensions logiques/géométrie inchangées.
- Retours exacts utilisateur : « {feedback['filter_verbatim']} » ; « {feedback['scale_verbatim']} ». Le nouvel avis BOX complète l'ancien « je vois pas de difference ingame » sans réécrire le bilan Mipmaps x4.
- Repli natif à 00:08:16.720 : `CHFB1G11 sequence=6 slot=10`. Shard x2 et BAM source vérifiés : cycle 6 possède 10 slots (0–9), tables identiques ; rejet avant filtre par garde existante. Même type de repli observé x4 BOX/Mipmaps ; cause de la demande native hors borne/effet visible non établi, warning une fois/processus.
- Warnings eau AR0900 et detour EEex récupéré conservés ; hors P4. Outliers conservés : entrée 1 513/489 ms, transitions jusqu'à 120 ms, palier minimum 66.7617 ms ; p95 fenêtre mouvement max 24.356 ms. Aucune attribution causale au filtre.
- Limites : paliers 14–17 s ; FPS scène et p95 par fenêtre ; CPU imbriqué pixels/upload, masque séparé ; phase marche/panoramique non instrumentée ; historique mémoire/session différent ; Mipmaps essayé x4 seulement.
- Installation actuelle vérifiée `iee-sprite-p4-box-x2-20261001-v1`, catalogue x2 partagé 0x6100/0x6110 ; **BOX seulement 0x6110, 0x6100 Nearest**. Aucun fichier installé remplacé pendant la mesure. P3 acquise conservée ; P4 choix échelle/filtre consigné, release inchangée. P5 frontières Q8c vs Q3m à engager sur demande.

Artefacts : `session.csv` copie exacte ; `summary.json` parseur commun ; `result.json` mesures/limites/repli ; `decision.json` choix daté ; `provenance.json` identités/hashes ; `runtime-excerpt.log` lancement/layers/marche/warnings ; `analyze.py` sortie exclusive.
"""
    with (RUN / "README.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    assert sha(SOURCE.read_bytes()) == sha((RUN / "session.csv").read_bytes()) == EXPECTED_SHA
    print(json.dumps({"status": "measured", "report": str(RUN / "README.md"), "totals": totals,
                      "habitual": stages[2], "native_frame": native, "decision": "x2 + BOX / 0x6110"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
