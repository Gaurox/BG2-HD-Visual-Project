"""Archive the user-designated Mipmaps session; exclusive outputs, read-only game."""
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
FILTER_RUN = RUN.parent / "palette-q3m-p4-filters-20261001-v1"
BOX_RUN = RUN.parent / "palette-q3m-p4-box-measurement-20261001-v1"
SOURCE = FILTER_RUN / "captures/mipmaps/p4-20261001T213456-1790890496586837.csv"
EXPECTED_SHA = "EECBE09C314FBEE1746D667B3BB005482694FD05A411777C8441D95125027A9F"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect_native_frame(game: Path) -> dict:
    digest = "18A66DCB6984F6B4A418607E94ABDBA28D33D4EB95A425E0108936EC420154F4"
    path = game / "iee-assets/creature-sprites" / f"CreatureSprites-XN-{digest}.registry"
    data = path.read_bytes()
    assert sha(data) == digest
    magic, version, scale, count, animation, profile, rule = struct.unpack_from("<8s6I", data)
    assert (magic, version, scale, count, animation, profile, rule) == (b"IEECSXN\0", 6, 4, 1, 65535, 1, 1)
    ref, source, frames, cycles = struct.unpack_from("<8s32sII", data, 32)
    assert ref == b"CHFB1G11"
    offset = 80
    for _ in range(frames):
        stored_i = struct.unpack_from("<I", data, offset + 12)[0]
        stored_f = struct.unpack_from("<I", data, offset + 560)[0]
        offset += 568 + stored_i + stored_f
    tables = []
    for _ in range(cycles):
        count = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        tables.append(list(struct.unpack_from("<" + str(count) + "I", data, offset)))
        offset += count * 4
    assert offset == len(data) and len(tables[5]) == 10
    assert source.hex().upper() == "F9C476D8828BCFB7151FAC470A91891E40728C49628DEE0989DC39376A73CE70"
    return {"path": str(path), "sha256": digest, "source_sha256": source.hex().upper(),
            "resref": "CHFB1G11", "frames": frames, "cycles": cycles,
            "sequence": 5, "cycle_slots": len(tables[5]), "valid_slot_range": [0, 9],
            "cycle_frames": tables[5], "requested_slot": 10, "requested_slot_out_of_range": True,
            "guard": "creature_sprite_x2.cpp resolve_frame: currentFrame >= cycle.size() returns false, before filtering",
            "warning_frequency": "once per process; total native fallback count unavailable"}


def main() -> None:
    names = ["session.csv", "summary.json", "result.json", "provenance.json", "runtime-excerpt.log", "README.md"]
    assert not any((RUN / name).exists() for name in names), "Historical outputs must not be overwritten."
    data = SOURCE.read_bytes()
    assert sha(data) == EXPECTED_SHA
    rows = [{k: float(v) for k, v in r.items()} for r in csv.DictReader(data.decode("utf-8").splitlines())]
    helper = load_module("box_session_helpers", BOX_RUN / "analyze.py")
    stable = [r for r in rows if helper.eligible(r)]
    valid = [r for r in rows if r["view_valid"]]
    assert len(rows) == 72 and len(valid) == 65 and len(stable) == 53
    assert {(r["viewport_w"], r["viewport_h"], r["framebuffer"], r["scale"], r["filter_mode"],
             r["min_filter"], r["mag_filter"], r["max_mip_level"], r["animation_id"])
            for r in valid} == {(2528, 1339, 0, 4, 4, 9987, 9728, 8, 24848)}
    ranges = [
        ("maximum_after_initial_world_entry", 9.313873, 20.366844, 12),
        ("habitual_static", 24.397990, 31.441286, 8),
        ("intermediate_static", 34.470439, 35.471005, 2),
        ("minimum", 38.496556, 48.555973, 11),
        ("movement_return_different_zoom", 54.614595, 71.759865, 18),
    ]
    stages = []
    for label, first, last, count in ranges:
        selected = [r for r in stable if first <= r["elapsed_s"] <= last]
        assert len(selected) == count, label
        stages.append(helper.stage(label, selected))
    assert sum(s["windows"] for s in stages) == 51
    box = json.loads((BOX_RUN / "result.json").read_text(encoding="utf-8"))
    comparisons = []
    for new_index, old_label in ((0, "maximum_first"), (1, "habitual_static"), (3, "minimum")):
        new = stages[new_index]
        old = next(s for s in box["stable_stages"] if s["label"] == old_label)
        assert new["zoom"] == old["zoom"]
        comparisons.append({
            "stage": new["label"], "zoom": new["zoom"], "mipmaps_seconds": new["seconds"], "box_seconds": old["seconds"],
            "mipmaps_fps": new["cadence_fps"], "box_fps": old["cadence_fps"],
            "mipmaps_window_p95_median_ms": new["window_p95_median_ms"], "box_window_p95_median_ms": old["window_p95_median_ms"],
            "median_p95_delta_percent": (new["window_p95_median_ms"] / old["window_p95_median_ms"] - 1) * 100,
            "mipmaps_cpu_composite_ms_per_frame": new["cpu_composite_ms_per_frame"], "box_cpu_composite_ms_per_frame": old["cpu_composite_ms_per_frame"],
            "cpu_composite_ratio": new["cpu_composite_ms_per_frame"] / old["cpu_composite_ms_per_frame"],
            "mipmaps_cpu_upload_ms_per_frame": new["cpu_upload_setup_ms_per_frame"], "box_cpu_upload_ms_per_frame": old["cpu_upload_setup_ms_per_frame"],
            "cpu_upload_ratio": new["cpu_upload_setup_ms_per_frame"] / old["cpu_upload_setup_ms_per_frame"],
        })
    totals = {k: int(sum(r[k] for r in rows)) for k in ("target_calls", "target_successes", "upload_calls", "upload_successes",
                                                         "pixel_calls", "pixel_cache_hits", "upload_bytes", "mask_calls", "mask_successes", "view_samples")}
    assert totals["target_calls"] == totals["target_successes"] == totals["upload_calls"] == totals["upload_successes"] == 3802
    assert totals["mask_calls"] == totals["mask_successes"] == 248
    totals.update({"window_count": len(rows), "duration_seconds": rows[-1]["elapsed_s"],
                   "pixel_cache_hit_percent": totals["pixel_cache_hits"] / totals["pixel_calls"] * 100,
                   "peak_process_working_set_bytes": int(max(r["working_set_bytes"] for r in rows)),
                   "peak_process_private_bytes": int(max(r["private_bytes"] for r in rows)),
                   "target_failures": 0, "upload_failures": 0, "mask_failures": 0})
    receipt = json.loads((FILTER_RUN / "ingame-filter/active-test.json").read_text(encoding="utf-8"))
    installation = json.loads((FILTER_RUN / "installation-verification.json").read_text(encoding="utf-8"))
    game = Path(receipt["game_root"])
    assert receipt["filter"] == "Mipmaps"
    checked = {"InfinityEngine-Enhancer.dll": installation["dll_sha256"], "InfinityEngine-Enhancer.ini": receipt["ini_after_sha256"],
               "iee-assets/creature-sprites/CreatureSprites-XN.catalog": receipt["catalog_sha256"]}
    checked.update({s["target"]: s["sha256"] for s in installation["shaders"]})
    for rel, expected in checked.items():
        assert sha((game / rel).read_bytes()) == expected, rel
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
               or re.match(r"\[2026-10-01 23:35:5[23]\.(847|181|332|514|581)\]", line)]
    result = {
        "schema": "bg2-p4-mipmaps-session-result-v1", "date": "2026-10-01", "status": "measured-comparison-limited-no-perceived-gain",
        "viewport": [2528, 1339], "scale": 4, "filter": "Mipmaps", "animation_scope": "0x6110",
        "sampler": {"MIN": "LINEAR_MIPMAP_LINEAR", "MAG": "NEAREST", "filter_mode": 4, "max_mip_level": 8, "levels": 9},
        "overall": totals, "stages": stages, "matched_zoom_box_comparisons": comparisons,
        "provenance_windows": {"character_composite": 61, "masked": 4},
        "partial_entry_exit_windows": [{"phase": phase, **r} for phase, r in (("first_world_entry", rows[6]), ("exit_partial_owned_draw", rows[70]))],
        "stage_selection": "53 parser-eligible windows retained in summary; comparison stages contain 51. First owned window includes 697.7903ms loading; final owned window has only 16/59 HD views during exit. Both retained explicitly, not removed from raw evidence. Stable spikes retained.",
        "habitual_static_zoom_matches_box": True, "return_movement_zoom": stages[4]["zoom"],
        "return_movement_zoom_matches_box": False,
        "user_visual_feedback": {"verbatim": "je vois pas de difference ingame", "scope": "no perceived difference Mipmaps vs BOX; not explicit artifact-free QA"},
        "native_frame_fallback": native, "runtime_warnings": warnings,
        "outlier_windows_above_40ms": [{"window_end_s": r["elapsed_s"], "frame_max_ms": r["frame_max_ms"], "window_p95_ms": r["frame_p95_ms"],
                                          "eligible": helper.eligible(r), "view_valid": bool(r["view_valid"]), "view_mixed": bool(r["view_mixed"])}
                                         for r in rows if r["frame_max_ms"] > 40],
        "working_recommendation": "BOX x4 provisional: lower measured CPU cost, user sees no Mipmaps gain. Do not treat as final P4 scale/filter decision.",
        "p4_scale_filter_decision": "pending x2 comparison / final user choice",
        "limits": [
            "Static plateaus are shorter than instructed: 12.07s maximum after first-entry window, 8.04s habitual, 11.08s minimum; longer BOX plateaus.",
            "Motion return zoom 2.672304/2.672655 differs from BOX habitual 2.480864/2.479630; motion costs are descriptive, not controlled A/B.",
            "FPS/p95 describe the entire scene; median/max of window p95, not global p95 or GPU execution time.",
            "CPU upload includes premultiplication, glGenerateMipmap and driver submission; CPU increase does not isolate any one operation or GPU time.",
            "Pixels/upload are nested in composition; CPU mask is separate. Masks and poses differ across sessions.",
            "Process memory peaks are not sprite-only memory or VRAM; base upload bytes are traffic and exclude GPU-generated mip bytes.",
            "All counted compositions/uploads/masks succeeded; native frame rejection occurs before these counters. Warning is once/process.",
        ],
        "installation_modified_during_measurement": False,
    }
    excerpt_data = ("\n".join(excerpt) + "\n").encode("utf-8")
    provenance = {
        "schema": "bg2-p4-mipmaps-measurement-provenance-v1", "source": str(SOURCE), "source_sha256": EXPECTED_SHA, "source_bytes": len(data),
        "source_last_write_utc": datetime.fromtimestamp(SOURCE.stat().st_mtime, timezone.utc).isoformat(),
        "session_start_utc": start.isoformat(), "session_end_utc": end.isoformat(),
        "session_start_local": local_start.isoformat(), "session_end_local": local_end.isoformat(),
        "runtime_log_source": str(log_path), "runtime_log_source_sha256": sha(log_data), "runtime_log_excerpt_sha256": sha(excerpt_data),
        "installed_hashes_checked": checked, "active_filter_receipt_sha256": sha((FILTER_RUN / "ingame-filter/active-test.json").read_bytes()),
        "installation_verify": "Set-Sprite-P4-Filter.ps1 -Mode Verify: Mipmaps / 0x6110 / x4; Baldur, BaldurReal and InfinityLoader closed",
        "analysis_script_sha256": sha(Path(__file__).read_bytes()), "shared_stage_helper": str(BOX_RUN / "analyze.py"),
        "shared_stage_helper_sha256": sha((BOX_RUN / "analyze.py").read_bytes()), "box_result_sha256": sha((BOX_RUN / "result.json").read_bytes()),
        "parser_path": "pipeline/scripts/palette_p4_probe.py", "parser_sha256": sha((REPO / "pipeline/scripts/palette_p4_probe.py").read_bytes()),
        "authorization": "User: test fait. controle la derniere session", "pc_control": False, "game_installation_modified": False,
        "historical_evidence_modified": False,
    }
    with (RUN / "session.csv").open("xb") as stream:
        stream.write(data)
    parser = load_module("p4_summary", REPO / "pipeline/scripts/palette_p4_probe.py")
    summary = parser.summarize(RUN / "session.csv")
    assert summary["ignored_windows"] == 19
    for name, value in (("summary.json", summary), ("result.json", result), ("provenance.json", provenance)):
        with (RUN / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    with (RUN / "runtime-excerpt.log").open("xb") as stream:
        stream.write(excerpt_data)
    table = "\n".join(f"| {c['stage']} | {c['zoom'][0]:.4f} | {c['mipmaps_seconds']:.2f} | {c['mipmaps_fps']:.2f} | {c['mipmaps_window_p95_median_ms']:.4f} | {c['mipmaps_cpu_composite_ms_per_frame']:.3f} / {c['box_cpu_composite_ms_per_frame']:.3f} | {c['mipmaps_cpu_upload_ms_per_frame']:.3f} / {c['box_cpu_upload_ms_per_frame']:.3f} |" for c in comparisons)
    ws = totals['peak_process_working_set_bytes'] / 2**20
    private = totals['peak_process_private_bytes'] / 2**30
    readme = f"""# P4 Mipmaps x4 — mesure 2026-10-01 v1

- Session désignée par utilisateur : `test fait. controle la derniere session` ; Paris {local_start:%H:%M:%S}–{local_end:%H:%M:%S}, {totals['duration_seconds']:.6f} s ; SHA256 CSV `{EXPECTED_SHA}`.
- Runtime installé vérifié : `iee-sprite-p4-filters-20261001-v1` ; x4, `0x6110`, viewport 2528×1339, FBO=0 ; mode=4, MIN=9987 (LINEAR_MIPMAP_LINEAR), MAG=9728 (NEAREST), MAX_LEVEL=8 ⇒ **9 niveaux effectifs**. 65 fenêtres avec draw cible, provenance composite=61 / masque=4.
- 72 fenêtres : 53 éligibles au parseur, 19 ignorées ; `summary.json` conserve les groupes bruts. Comparaisons ci-dessous : phases contiguës, 51 fenêtres au total avec le zoom intermédiaire et la marche ; première fenêtre monde/dernière fenêtre avant sortie conservées séparément.

| Palier | Zoom x | Durée Mips s | FPS Mips | p95 médian fenêtres ms | CPU composition Mips / BOX ms/frame | CPU upload Mips / BOX ms/frame |
|---|---:|---:|---:|---:|---:|---:|
{table}

- Même zoom exact BOX/Mips aux trois paliers statiques ; p95 médian voisin, cadence ≈60. Au zoom habituel : composition **4.258 vs 0.280 ms/frame**, upload **4.124 vs 0.174 ms/frame** ; augmentation CPU nette mesurée, sans attribution à une opération/GPU isolée.
- Coût upload Mips inclut prémultiplication, génération de chaîne et soumission pilote ; pixels/upload imbriqués dans composition. Ne pas les additionner. Masque mesuré séparément.
- Marche/caméra : retour à **2.672304 / 2.672655**, différent du zoom statique habituel **2.480864 / 2.479630** (maximum −7 crans) et du retour BOX. 18.145 s hors sortie partielle ; FPS 59.74, p95 médian 17.1322 ms / max 34.8330 ms ; CPU composition 2.174, masque 0.510 ms/frame. Pas de comparaison contrôlée de mouvement avec BOX.
- Totaux : **3 802/3 802 compositions et uploads, 248/248 masques** ; 2 817 hits pixels ({totals['pixel_cache_hit_percent']:.2f} %) ; trafic RGBA base {totals['upload_bytes']/2**30:.3f} GiB (hors octets mips générés GPU). Pics processus WS {ws:.3f} MiB / privé {private:.3f} GiB ; ni mémoire sprites seule, ni VRAM.
- Layers 3/3 : `CHFB1G12`, `WQNJ8G1`, `WQNFSG1` ; marche `CHFB1G1/CHFB1G11`, coordonnées monde variables observées.
- Repli natif à 23:35:53.312 : `CHFB1G11 sequence=5 slot=10`. Shard installé SHA256 `{native['sha256']}` vérifié ; cycle 5 = 10 slots valides **0–9**. La demande 10 est hors cycle, rejetée avant filtrage par garde existante ; protection fail-closed. Warning une fois/processus ⇒ total replis non mesuré. Même cycle longueur 10 dans BAM source canonique SHA256 `{native['source_sha256']}` ; pas une frame manquante introduite par génération mipmaps.
- Autres warnings : eau `AR0900/WTLAKE` en repli natif, prologue RenderTexture EEex récupéré ; déjà observés avec BOX, hors périmètre.
- Outliers conservés : chargement 1 480/698 ms ; transitions zoom 59–85 ms ; palier habituel statique frame max **41.2176 ms** ; marche frame max **49.3138 ms**, p95 fenêtre **34.8330 ms**. La première fenêtre monde (19 vues) et la sortie partielle (16/59 vues) ne sont pas utilisées dans les comparaisons statiques/marche, mais restent dans CSV, groupes bruts et `result.json`.
- Limites : paliers 8–12 s, plus courts que BOX et que les 20 s demandées ; contexte cache/poses différent ; zoom marche différent ; FPS global autour de 60 ne mesure pas un coût GPU isolé. Aucun retrait des pics dans les phases stables.
- Retour utilisateur exact : **« je vois pas de difference ingame »** (Mipmaps vs BOX). Aucun verdict explicite d'absence de halos/scintillement déduit.
- Recommandation provisoire : **BOX x4**, coût CPU inférieur sans gain Mips perçu. **P4 reste ouverte** : comparaison x2 et décision finale utilisateur ; P3 acceptée conservée. Mipmaps reste installé, aucune bascule ni modification release pendant cette mesure.

Artefacts : `session.csv` copie exacte ; `summary.json` parseur commun ; `result.json` phases/comparaisons/limites + contrôle cycle natif ; `provenance.json` hashes ; `runtime-excerpt.log` lancement/layers/marche/warnings ; `analyze.py` calcul exclusif, refuse tout écrasement historique.
"""
    with (RUN / "README.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(readme)
    assert sha(SOURCE.read_bytes()) == sha((RUN / "session.csv").read_bytes()) == EXPECTED_SHA
    print(json.dumps({"status": result["status"], "report": str(RUN / "README.md"), "totals": totals,
                      "comparisons": comparisons, "native_frame_check": native, "warnings": len(warnings)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
