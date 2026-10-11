"""Freeze explicit five-tree approval; read installed bytes, write QA only, no release."""
import csv
import json
import shutil
import sys
from pathlib import Path

import build_renderer as b

ROOT, HERE = b.ROOT, b.HERE
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import animation_workflow as workflow
import run_animation_upscale_30fps_v2 as v2

REFS = [f"1400T{i:03}" for i in range(1,6)]
SOURCE = ROOT / "animations/batches/trees-seedvr-static-x4-20261011-v1"
FINAL_PACK = ROOT / "animations/packs-par-zone/trees-seedvr-native-lighting-accepted-20261011-v1"
CORRECTION = "trees-seedvr-native-lighting-night235-20261011-v1"
USER = "c'est tout bon ! valide ces assets en l'etat ! MAJ le suivi et committe !"


def rel(path):
    return path.relative_to(ROOT).as_posix()


def write(path, value):
    assert not path.exists(), f"Immutable final artifact already exists: {path}"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def main():
    assert not (HERE/"acceptance.json").exists()
    report = v2.load_json(HERE/"runtime.json")
    installed = v2.load_json(HERE/"installation.json")
    prepared = v2.load_json(ROOT/"pipeline/recipes/trees-native-lighting-20261011-v1/preparation.json")
    game = b.get_path("bg2ee_game_root",required=True)
    assert installed["status"] == "installed-for-ingame-test"
    assert b.sha(game/"InfinityEngine-Enhancer.dll") == report["dll_sha256"] == installed["dll_sha256"]
    assert b.sha(game/"InfinityEngine-Enhancer.ini") == report["ini_sha256"]
    assert report["targeted_tests_passed"] and report["water_generated_header_identical"]
    for name, expected in report["source_sha256"].items():
        assert b.sha(b.CANON/name) == expected
    assert not FINAL_PACK.exists()
    entries = []
    verified = {}
    for area, source_path in prepared["leaves"].items():
        leaf = ROOT/source_path
        assert b.sha(leaf/"manifest.json") == prepared["leaf_manifest_sha256"][area]
        assert (game/"iee-assets/areas"/area/v2.REGISTRY_NAME).read_bytes() == (leaf/v2.REGISTRY_NAME).read_bytes()
        manifest = v2.load_json(leaf/"manifest.json")
        for resource in manifest["resources"]:
            for asset in resource["assets"]:
                assert b.sha(game/"iee-assets/areas"/area/asset["name"]).lower() == asset["sha256"].lower()
            if resource["resref"] in REFS:
                assert resource["frame_count"] == 1 and resource["playback_mode"] == "Native"
                for frame in resource["frames"]:
                    assert frame["logical_size_x1"] == [255,255] and frame["centre_x1"] == [1,1]
                verified.setdefault(resource["resref"],{})[area] = resource["assets"]
        shutil.copytree(leaf,FINAL_PACK/area)
        for path in leaf.rglob("*"):
            if path.is_file():
                assert path.read_bytes() == (FINAL_PACK/area/path.relative_to(leaf)).read_bytes()
        entries.append(dict(area_id=area,directory=area,source_pack=source_path,
                            manifest_sha256=b.sha(leaf/"manifest.json")))
    write(FINAL_PACK/"manifest.json",dict(schema="bg2-upscale-area-animation-pack-index-v1",
        status="completed",created_utc=v2.utc_now(),areas=entries,
        accepted_resrefs=REFS,area_count=2,source_bytes_preserved=True,
        renderer_dll_sha256=report["dll_sha256"],renderer_installation=rel(HERE/"installation.json"),
        release_status="not-selected"))
    resources = []
    for ref in REFS:
        night = ref in ("1400T002","1400T003","1400T005")
        smooth = ref in ("1400T001","1400T003","1400T005")
        alpha = "Potrace0.8/opttol0.1/SS8/bande2x4 protégée, AA intérieure min176, support natif exact" if smooth else "alpha nearest natif strict"
        recipe = f"SeedVR2 7B INT8/LAB x4 seed20261011 ; {alpha} ; lumière native propriétaire dynamique"
        if night:
            recipe += " ; nuit R*0.60/G*0.55/B*0.85 après lumière native"
        run = ROOT/f"animations/ressources/{ref}/runs/{ref.lower()}-seedvr-native-lighting-accepted-20261011-v1"
        contract = dict(scale=4,frame_count=1,playback_mode="Native",logical_size_x1=[255,255],centre_x1=[1,1],
            alpha_support_native=True,lighting="owner-scoped CVidPalette::Realize RGB transfer",
            night_rgb_gains=report["rgb_gains"] if night else None,
            night_gate=report["night_gate"] if night else None,
            renderer_dll_sha256=report["dll_sha256"],renderer_source_sha256=report["source_sha256"],
            renderer_installation=rel(HERE/"installation.json"),renderer_receipt=installed["renderer_receipt"])
        write(run/"manifest.json",dict(schema="bg2-upscale-animation-final-selection-v1",status="completed",
            created_utc=v2.utc_now(),resrefs=[ref],source_run=rel(SOURCE),
            source_run_manifest_sha256=v2.sha256_file(SOURCE/"manifest.json"),
            source_pack=prepared["leaves"]["AR1400"],
            source_pack_manifest_sha256=v2.sha256_file(ROOT/prepared["leaves"]["AR1400"]/"manifest.json"),
            output_split_root=rel(FINAL_PACK),output_manifest_sha256=v2.sha256_file(FINAL_PACK/"manifest.json"),
            recipe=recipe,runtime_contract=contract,installed_assets=verified[ref],selection_reason=USER,
            accepted_resource_scope=["AR1400","AR1404"],release_status="not-selected"))
        decision = (f"Utilisateur : {USER} {ref} x4 accepté en l'état installé, jour/nuit. "
            f"Recette : {recipe}. Une frame statique ; géométrie/centres/cycles natifs conservés. "
            f"Contrat renderer DLL {report['dll_sha256']} et textures exactes liés au manifeste final. "
            "Deux cartes/deux occurrences partagent le même asset ; aucune visite exhaustive déduite. Aucune intégration release.")
        decision_id = f"2026-10-11-accepted-{ref.lower()}-seedvr-native-lighting-night235-v1"
        result = workflow.finalize(ROOT,ref,run,FINAL_PACK,["AR1400","AR1404"],"accepted","2026-10-11",decision,
            decision_id=decision_id,recipe_id="trees-seedvr-static-native-lighting-night235-v1",
            correction_id=CORRECTION,notes=decision,apply=True)
        checked = workflow.check_workspace(ROOT,ref)
        assert checked["ok"],checked
        resources.append(dict(resref=ref,areas=["AR1400","AR1404"],occurrences=2,selected_run=rel(run),
            qa_decision=result["decision_id"],recipe=recipe,installed_resource_and_registry_match=True,
            workspace_check_passed=True))
        print(f"Accepted {ref}",flush=True)
    alpha_path = ROOT/"animations/index/animation_alpha_corrections.csv"
    with alpha_path.open(encoding="utf-8",newline="") as handle:
        reader = csv.DictReader(handle)
        fields, rows = reader.fieldnames,list(reader)
    assert not any(r["resref"] in REFS and r["correction_id"] == CORRECTION for r in rows)
    with alpha_path.open("a",encoding="utf-8",newline="") as handle:
        writer = csv.DictWriter(handle,fieldnames=fields)
        for ref in REFS:
            smooth = ref in ("1400T001","1400T003","1400T005")
            writer.writerow(dict(resref=ref,areas="AR1400;AR1404",element="arbre",correction_id=CORRECTION,
                alpha_operations="protected-potrace-inward-antialias" if smooth else "native-nearest",
                inner_radius_x4=2 if smooth else 0,canvas_radius_x4=0,canvas_edges="none",
                rgb_policy="straight-seedvr-unlit-native-owner-lighting",status="validated-installed",
                validated_date="2026-10-11",prototype=rel(FINAL_PACK),
                notes="QA ingame explicite ; support/branches/canevas natifs protégés ; correctif RGB nocturne T002/T003/T005 seulement ; aucune release."))
    write(HERE/"acceptance.json",dict(schema="bg2-upscale-animation-batch-acceptance-v1",status="accepted-ingame",
        decision_origin="explicit-user-ingame-qa",decision_date="2026-10-11",recorded_at_utc=v2.utc_now(),
        decision=USER,resources=resources,area_count=2,occurrence_count=10,final_pack=rel(FINAL_PACK),
        renderer_dll_sha256=report["dll_sha256"],renderer_receipt=installed["renderer_receipt"],
        renderer_installation=rel(HERE/"installation.json"),
        renderer_installation_sha256=v2.sha256_file(HERE/"installation.json"),
        game_files_changed=False,release_changed=False))
    print("Five trees accepted; QA/selections/registry/alpha updated; game and release unchanged.")


if __name__ == "__main__":
    main()
