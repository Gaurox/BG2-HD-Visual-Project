#!/usr/bin/env python3
"""Confirme le budget runtime de chaque zone d'un split-root et l'inscrit dans son manifeste.

Pourquoi ce script existe : `animation_release.py` exige `runtime_budget_enforced` a vrai dans le
manifeste de zone. Or seul `run_animation_upscale_30fps_v2.py` pose ce drapeau, sur le pack complet
avant decoupage ; `split_animation_pack_by_area.py`, `combine_area_pack_splits.py` et
`merge_area_pack_resources.py` ne le propagent pas. Aucun pack par zone ne peut donc franchir la
gate, alors que le decoupage est precisement l'etape qui ramene chaque zone sous le plafond.

Ce script ne suppose rien : il recalcule la charge brute de chaque zone a partir des assets
reellement presents, la compare au plafond `MAX_RAW_BYTES`, et ecrit le resultat mesure. Une zone
au-dela du plafond recoit `false` et la gate continue de la refuser.

Il ne touche ni les assets, ni le registre binaire, ni le jeu : il ne modifie que les deux champs
de metadonnee des manifestes, puis rehashe l'index pour rester coherent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import run_animation_upscale_30fps_v2 as v2  # noqa: E402
import split_animation_pack_by_area as splitter  # noqa: E402


def measured_raw_bytes(area_dir: Path, manifest: dict) -> int:
    """Somme les tailles reelles des assets declares, sans faire confiance au champ raw_bytes."""
    total = 0
    for resource in manifest.get("resources") or []:
        for asset in resource.get("assets") or []:
            path = area_dir / str(asset["name"])
            if not path.is_file():
                raise SystemExit(f"asset absent : {path}")
            total += path.stat().st_size
    return total


def confirm(split_root: Path, apply: bool) -> dict:
    index_path = split_root / "manifest.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if index.get("schema") != splitter.INDEX_SCHEMA or index.get("status") != "completed":
        raise SystemExit(f"split-root incompatible : {split_root}")

    report = []
    for entry in index.get("areas") or []:
        area = str(entry["area_id"])
        area_dir = split_root / str(entry["directory"])
        manifest_path = area_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        v2.validate_v2_pack(area_dir)

        raw = measured_raw_bytes(area_dir, manifest)
        within = raw <= v2.MAX_RAW_BYTES
        before = manifest.get("runtime_budget_enforced")
        report.append({
            "area": area, "raw_bytes": raw, "within_budget": within,
            "was": before, "now": within,
        })
        if not apply or before is within:
            continue
        manifest["runtime_budget_enforced"] = within
        manifest.setdefault("authoring_pack_for_area_split", False)
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        entry["manifest_sha256"] = v2.sha256_file(manifest_path)

    if apply:
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    over = [item["area"] for item in report if not item["within_budget"]]
    return {
        "split_root": split_root.as_posix(),
        "runtime_budget_bytes": v2.MAX_RAW_BYTES,
        "areas": len(report),
        "areas_over_budget": over,
        "largest_area_raw_bytes": max((item["raw_bytes"] for item in report), default=0),
        "applied": apply,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-root", type=Path, required=True)
    parser.add_argument("--run", action="store_true", help="ecrit ; sinon mesure seulement")
    args = parser.parse_args()
    print(json.dumps(confirm(args.split_root.resolve(), args.run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
