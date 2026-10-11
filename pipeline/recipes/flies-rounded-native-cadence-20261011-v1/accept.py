"""Record the user's ingame approval of FLIESL and FLIESS; no installation/release writes."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build
import animation_workflow as workflow


def main() -> None:
    receipt = build.v2.load_json(HERE / "installation-v1.json")
    assert receipt["status"] == "installed-for-ingame-test" and receipt["area_count"] == 21
    pack = ROOT / receipt["complete_split_root"]
    index = build.v2.load_json(pack / "manifest.json")
    game = build.get_path("bg2ee_game_root", required=True) / "iee-assets/areas"
    registry = {r["resref"]: r for r in csv.DictReader(
        (ROOT / "animations/index/animation_upscale_registry.csv").open(encoding="utf-8")
    )}
    checks = []
    recipes = {
        "FLIESL": "Ellipses par composante 8-connexe, centres/surfaces conservés, aspect ≤1,6 ; supersampling16 → BOX x4",
        "FLIESS": "Ouverture disque rayon1,25px x4, supersampling8 → LANCZOS x4 ; premier essai PNG",
    }
    for ref in sorted(build.TARGETS):
        areas = registry[ref]["areas"].split(";")
        for entry in index["areas"]:
            area = entry["area_id"]
            if area not in areas:
                continue
            leaf = pack / entry["directory"]
            manifest = build.v2.load_json(leaf / "manifest.json")
            resources = [r for r in manifest["resources"] if r["resref"] == ref]
            assert len(resources) == 1 and resources[0]["playback_mode"] == "Native"
            resource = resources[0]
            assert resource["frame_count"] == 18
            assert (game / area / build.v2.REGISTRY_NAME).read_bytes() == (leaf / build.v2.REGISTRY_NAME).read_bytes()
            assert all(build.v2.sha256_file(game / area / a["name"]).lower() == a["sha256"].lower()
                       for a in resource["assets"])
        wrapper = ROOT / "animations/ressources" / ref / "runs" / f"{ref.lower()}-rounded-native-cadence-accepted-20261011-v1"
        wrapper.mkdir(parents=True, exist_ok=False)
        first = next(e for e in index["areas"] if e["area_id"] in areas)
        leaf = pack / first["directory"]
        build.write(wrapper / "manifest.json", {
            "schema": "bg2-upscale-animation-final-selection-v1", "status": "completed",
            "created_utc": build.v2.utc_now(), "resrefs": [ref],
            "source_run": build.relative(build.RUN), "source_run_manifest_sha256": build.v2.sha256_file(build.RUN / "manifest.json"),
            "source_pack": build.relative(leaf), "source_pack_manifest_sha256": build.v2.sha256_file(leaf / "manifest.json"),
            "output_split_root": build.relative(pack), "output_manifest_sha256": build.v2.sha256_file(pack / "manifest.json"),
            "recipe": recipes[ref], "native_cadence_preserved": True,
            "installation_receipt": build.relative(HERE / "installation-v1.json"),
            "selection_reason": "Utilisateur : ok je valide les 2. maj le suivi et committe.",
            "accepted_resource_scope": areas, "release_status": "not-selected",
        })
        decision_id = f"2026-10-11-accepted-{ref.lower()}-rounded-native-cadence-v1"
        decision = ("Utilisateur : ok je valide les 2. maj le suivi et committe. "
                    f"{ref} x4 arrondi accepté ingame ; ressource partagée validée dans le déploiement de 21 cartes. "
                    f"Recette : {recipes[ref]}. 18 frames et cadence/cycles/dimensions/centres BAM natifs conservés. "
                    "Les octets et le contrat runtime du resref sont identiques dans toutes ses zones ; "
                    "cette décision ne prétend pas à une visite individuelle des 216 occurrences. Aucun changement release.")
        result = workflow.finalize(
            ROOT, ref, wrapper, pack, areas, "accepted", "2026-10-11", decision,
            decision_id=decision_id, recipe_id=f"{ref.lower()}-rounded-native-cadence-20261011-v1",
            correction_id=build.RUN_ID,
            notes=f"QA ingame utilisateur acceptée 2026-10-11 : {recipes[ref]}. 18 frames natives, cadence/centres/dimensions/cycles conservés. "
                  f"Remplace la conservation native antérieure ; {registry[ref]['occurrences']} occurrences / {len(areas)} cartes. "
                  "Ressource partagée acceptée, octets installés identiques dans toutes ses zones. "
                  "Reçu pipeline/recipes/flies-rounded-native-cadence-20261011-v1/installation-v1.json ; aucune intégration release.",
            apply=True,
        )
        checked = workflow.check_workspace(ROOT, ref)
        assert checked["ok"], checked
        checks.append({"resref": ref, "areas": areas, "occurrences": int(registry[ref]["occurrences"]),
                       "selected_run": build.relative(wrapper), "qa_decision": result["decision_id"],
                       "workspace_check_passed": True, "installed_resource_and_registry_match": True})
        print(f"Accepted {ref}: {len(areas)} maps", flush=True)
    alpha_path = ROOT / "animations/index/animation_alpha_corrections.csv"
    with alpha_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields, alpha_rows = reader.fieldnames, list(reader)
    assert not any(r["resref"] in build.TARGETS for r in alpha_rows)
    with alpha_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        for ref in sorted(build.TARGETS):
            writer.writerow({
                "resref": ref, "areas": registry[ref]["areas"], "element": "mouches",
                "correction_id": build.RUN_ID,
                "alpha_operations": "area-matched-component-ellipses" if ref == "FLIESL" else "disk-opening-supersampled-antialias",
                "inner_radius_x4": 0, "canvas_radius_x4": 0, "canvas_edges": "none",
                "rgb_policy": "straight-source-palette-nearest-opaque-edge", "status": "validated-installed",
                "validated_date": "2026-10-11", "prototype": build.relative(pack),
                "notes": recipes[ref] + "; QA ingame explicite utilisateur, cadence et géométrie natives ; aucune intégration release.",
            })
    build.write(HERE / "acceptance.json", {
        "status": "accepted", "recorded_utc": build.v2.utc_now(), "decision_origin": "explicit-user-ingame-qa",
        "decision": "ok je valide les 2. maj le suivi et committe", "resources": checks,
        "area_count": 21, "occurrence_count": 216, "game_files_changed": False, "release_changed": False,
    })
    print("QA/selections/registry/alpha catalogue updated; release and game unchanged")


if __name__ == "__main__":
    main()
