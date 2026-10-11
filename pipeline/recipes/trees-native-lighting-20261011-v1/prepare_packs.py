"""Replace only prelit trees with the finished unlit SeedVR frames in two complete packs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"pipeline/scripts"))
import run_animation_upscale_30fps_v2 as v2
import merge_area_pack_resources as merger
import area_pack_state as state
from workspace_paths import get_path


def main():
    assert not (HERE/"preparation.json").exists()
    old = v2.load_json(ROOT/"pipeline/recipes/trees-seedvr-static-x4-20261011-v1/preparation.json")
    unlit = ROOT/"animations/batches/trees-seedvr-static-x4-20261011-v1/06_split"
    refs = {f"1400T{i:03}" for i in range(1,6)}
    game = get_path("bg2ee_game_root",required=True)
    areas = game/"iee-assets/areas"
    lock = state.load_lock()
    baseline,leaves = {},{}
    for area in ("AR1400","AR1404"):
        previous = ROOT/old["leaves"][area]
        signatures = state.zone_signatures(areas/area)
        assert signatures == state.leaf_signatures(previous), "Installed area changed; recompose"
        baseline[area] = {"lock_entry":lock["areas"].get(area),"signatures":signatures,
            "registry_sha256":v2.sha256_file(areas/area/v2.REGISTRY_NAME)}
        specs = [str(unlit/area)]
        manifest = v2.load_json(previous/"manifest.json")
        for resource in manifest["resources"]:
            if resource["resref"] not in refs:
                specs.insert(0,str(previous)+"::"+resource["resref"])
        output = ROOT/f"animations/packs-par-zone/trees-native-lighting-20261011-v1-{area.lower()}"
        merger.merge(specs,area,output,False)
        leaf = output/area
        actual = state.leaf_signatures(leaf)
        assert {k:v for k,v in actual.items() if k not in refs} == {k:v for k,v in signatures.items() if k not in refs}
        leaves[area] = leaf.relative_to(ROOT).as_posix()
    data = dict(schema="bg2-trees-unlit-packs-v1",status="completed",created_utc=v2.utc_now(),
        baseline=baseline,leaves=leaves,leaf_manifest_sha256={a:v2.sha256_file(ROOT/p/"manifest.json") for a,p in leaves.items()},
        lighting="Native owner-scoped palette at draw time; no baked lightmap",
        fountains_byte_identical=True,source_seedvr_run="trees-seedvr-static-x4-20261011-v1",
        geometry_cycles_alpha_preserved=True,qa_status="pending-user-ingame-test",release=False)
    (HERE/"preparation.json").write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
    print("Two unlit complete tree packs prepared; fountains byte-identical.")


if __name__ == "__main__": main()
