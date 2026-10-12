"""Generate effects work hints once; read the daily queue without scanning pixels.

Generated hints never grant production, QA, installation or release status.
Only sparse recipe/priority/usage overrides are manual.
"""
from __future__ import annotations

import argparse
import collections
import csv
import io
import json
from pathlib import Path
import struct
from typing import Any
import zlib

import effect_authority as authority
import effect_workflow as workflow

ROOT = Path(__file__).resolve().parents[2]
CLASSIFICATION = "effects/index/classification.json"
WORK_ITEMS = "effects/index/work-items.csv"
CONSUMERS = "effects/index/consumers.csv"
WORK_PLAN = "effects/index/source-work-plan.json"
TAGS = {"static", "one-shot", "loop", "staged", "directional", "alpha", "palette", "unresolved"}
USAGES = {"known", "unresolved", "excluded"}
ITEM_FIELDS = (
    "asset_key", "resref", "source_state", "canonical_sha256", "frames", "used_frames",
    "cycles", "empty_cycles", "static", "variable_geometry", "raw_x4_bytes",
    "consumer_count", "owner_routes", "native_fps", "playback", "tags",
    "reuse_bams", "reuse_animation", "usage", "priority", "recipe", "technical_notes", "notes",
)
CONSUMER_FIELDS = (
    "asset_key", "consumer_key", "relation", "via", "source_sha256", "owner_route",
    "native_fps", "loop", "cycles", "orientations", "mirror", "blend",
    "palette", "color_enabled", "colors", "flags_json",
)


def read_optional_csv(root: Path, relative: str) -> list[dict[str, str]]:
    path = root / relative
    return workflow.read_csv(path) if path.is_file() else []


def csv_data(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def load_classification(root: Path) -> dict[str, Any]:
    path = root / CLASSIFICATION
    data = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {
        "schema": "bg2-effects-classification-v1", "assets": {},
    }
    if data.get("schema") != "bg2-effects-classification-v1" or not isinstance(data.get("assets"), dict):
        raise workflow.WorkflowError("classification effects invalide")
    for key, value in data["assets"].items():
        workflow.validate_resref(key)
        if not isinstance(value, dict) or set(value) - {"tags", "usage", "priority", "recipe", "notes"}:
            raise workflow.WorkflowError(f"classification invalide : {key}")
        if "tags" in value and (not isinstance(value["tags"], list) or any(t not in TAGS for t in value["tags"])):
            raise workflow.WorkflowError(f"tags invalides : {key}")
        if "usage" in value and value["usage"] not in USAGES:
            raise workflow.WorkflowError(f"usage invalide : {key}")
        if "priority" in value and (type(value["priority"]) is not int or not 0 <= value["priority"] <= 999):
            raise workflow.WorkflowError(f"priorité invalide : {key}")
        for name in ("recipe", "notes"):
            if name in value and not isinstance(value[name], str):
                raise workflow.WorkflowError(f"{name} invalide : {key}")
    return data


def resref(data: bytes, offset: int) -> str:
    return data[offset:offset + 8].split(b"\0")[0].decode("ascii").upper()


def source_bytes(root: Path, record: dict[str, str]) -> bytes:
    path = root / record["extracted_path"]
    data = path.read_bytes()
    if authority.digest(data) != record["source_sha256"].upper():
        raise workflow.WorkflowError(f"contrôleur source modifié : {record['asset_key']}")
    return data


def controller_fields(data: bytes) -> dict[str, Any]:
    if len(data) < 0x94 or data[:8] != b"VVC V1.0":
        raise workflow.WorkflowError("VVC invalide")
    display, color = struct.unpack_from("<HH", data, 0x18)
    sequence = struct.unpack_from("<I", data, 0x20)[0]
    cycles = [struct.unpack_from("<I", data, p)[0] for p in (0x68, 0x6C, 0x90)]
    return {"native_fps": struct.unpack_from("<I", data, 0x34)[0],
            "loop": int(bool(sequence & 1)), "cycles": ";".join(str(v) for v in cycles),
            "orientations": struct.unpack_from("<I", data, 0x38)[0],
            "blend": int(bool(display & 8)), "palette": resref(data, 0x44),
            "flags_json": json.dumps({"display": display, "color": color, "sequence": sequence,
                                      "duration": struct.unpack_from("<I", data, 0x5C)[0],
                                      "continuous": struct.unpack_from("<I", data, 0x74)[0]}, sort_keys=True)}


def build_consumers(root: Path) -> list[dict[str, Any]]:
    deps = read_optional_csv(root, "effects/index/dependencies.csv")
    by_controller: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for dep in deps:
        by_controller[dep["asset_key"]].append(dep)
    controllers = {r["asset_key"]: r for r in read_optional_csv(root, "effects/index/resources.csv")}
    vvc, vef = {}, {}
    for key, record in controllers.items():
        data = source_bytes(root, record)
        if record["format"] == "VVC":
            vvc[key] = controller_fields(data)
        elif record["format"] == "VEF":
            if data[:4] != b"VEF " or len(data) < 24:
                raise workflow.WorkflowError("VEF invalide")
            timing = {}
            for table, (offset_at, count_at) in enumerate(((8, 12), (16, 20)), 1):
                offset, count = struct.unpack_from("<I", data, offset_at)[0], struct.unpack_from("<I", data, count_at)[0]
                if offset + count * 0xE0 > len(data):
                    raise workflow.WorkflowError("table VEF hors limites")
                for i in range(count):
                    pos = offset + i * 0xE0
                    timing[f"component-{table}-{i}"] = {"controller": key,
                        "start_ticks": struct.unpack_from("<I", data, pos)[0],
                        "loop_ticks": struct.unpack_from("<I", data, pos + 8)[0],
                        "continuous": struct.unpack_from("<I", data, pos + 24)[0]}
            vef[key] = timing

    def leaves(key: str, seen: tuple[str, ...] = ()):
        if key in seen:
            raise workflow.WorkflowError(f"dépendance VEF cyclique : {key}")
        for dep in by_controller.get(key, []):
            fmt = dep["resolved_format"]
            if fmt == "BAM" or (dep["present"] == "no" and dep["relation"] in {"animation", "alpha-animation"}):
                fields = dict(vvc.get(key, {}))
                if key in vef:
                    fields["flags_json"] = json.dumps({"vef": [vef[key][dep["relation"]]]}, sort_keys=True)
                yield dep["dependency_resref"], key, dep["relation"], fields
            elif fmt in {"VVC", "VEF"}:
                child = f"effect:{fmt.lower()}:{dep['dependency_resref']}"
                for bam, via, relation, fields in leaves(child, (*seen, key)):
                    if key in vef:
                        fields = dict(fields)
                        flags = json.loads(fields.get("flags_json", "{}"))
                        flags.setdefault("vef", []).append(vef[key][dep["relation"]])
                        fields["flags_json"] = json.dumps(flags, sort_keys=True)
                    yield bam, via, relation, fields

    rows = []
    for key, record in controllers.items():
        for bam, via, relation, fields in leaves(key):
            rows.append({**dict.fromkeys(CONSUMER_FIELDS, ""), **fields,
                         "asset_key": f"effects:bam:{bam}", "consumer_key": key,
                         "relation": relation, "via": via if via != key else "",
                         "source_sha256": record["source_sha256"], "owner_route": "vvc"})
    projectiles = {r["asset_key"]: r for r in read_optional_csv(root, "projectiles/index/resources.csv")}
    for dep in read_optional_csv(root, "projectiles/index/dependencies.csv"):
        key = dep["asset_key"]
        record = projectiles[key]
        data = source_bytes(root, record)
        fmt = dep["resolved_format"]
        if fmt == "BAM":
            expanded = [(dep["dependency_resref"], "", dep["relation"], {})]
        elif fmt in {"VVC", "VEF"}:
            expanded = list(leaves(f"effect:{fmt.lower()}:{dep['dependency_resref']}"))
        else:
            continue
        for bam, via, relation, inherited in expanded:
            fields = dict(inherited)
            if dep["relation"] == "travel-animation" and len(data) >= 0x134:
                flags = struct.unpack_from("<I", data, 0x100)[0]
                fields.update({"cycles": str(data[0x114]), "mirror": data[0x133],
                               "palette": resref(data, 0x11C), "color_enabled": int(bool(flags & 1)),
                               "colors": ";".join(map(str, data[0x124:0x12B])),
                               "flags_json": json.dumps({"bam": flags, "extended": struct.unpack_from("<I", data, 0x2C)[0]}, sort_keys=True)})
            rows.append({**dict.fromkeys(CONSUMER_FIELDS, ""), **fields,
                         "asset_key": f"effects:bam:{bam}", "consumer_key": key,
                         "relation": dep["relation"], "via": via,
                         "source_sha256": record["source_sha256"],
                         "owner_route": "vvc" if via else "native-shadow" if dep["relation"] == "shadow-animation" else "projectile"})
    unique = {tuple(str(r[f]) for f in CONSUMER_FIELDS): r for r in rows}
    return [unique[k] for k in sorted(unique)]


def inspect_bam(path: Path, expected: str) -> tuple[dict[str, Any], set[bytes], set[bytes]]:
    # Decode in memory only: no PNG export, inference or persistent pixel cache.
    import hashlib
    from bam_export import decode_bam

    raw = path.read_bytes()
    if workflow.sha256_file(path) != expected.upper():
        raise workflow.WorkflowError(f"source modifiée : {path}")
    data = zlib.decompress(raw[12:]) if raw[:4] == b"BAMC" else raw
    if data[:8] != b"BAM V1  ":
        raise workflow.WorkflowError(f"BAM V1 attendu : {path}")
    count, cycle_count = struct.unpack_from("<HB", data, 8)
    if count == 0 or cycle_count == 0:
        raise workflow.WorkflowError(f"BAM sans frame/cycle : {path}")
    frame_offset, _, lookup_offset = struct.unpack_from("<III", data, 0x0C)
    geometry = [struct.unpack_from("<HHhh", data, frame_offset + i * 12) for i in range(count)]
    cycles, used = [], set()
    for i in range(cycle_count):
        n, first = struct.unpack_from("<HH", data, frame_offset + count * 12 + i * 4)
        slots = struct.unpack_from(f"<{n}H", data, lookup_offset + first * 2)
        if any(s >= count for s in slots):
            raise workflow.WorkflowError(f"cycle BAM hors limites : {path}")
        used.update(slots)
        cycles.append({"cycle": i, "slots": n, "unique_frames": len(set(slots)), "static": len(set(slots)) <= 1})
    frames, palette, transparent = decode_bam(data)
    rgba_keys, anchor_keys = set(), set()
    opaque, blank = 0, 0
    for idx, cx, cy, _ in frames:
        mask = idx != transparent
        rgb = palette[idx].copy()
        rgb[~mask] = 0
        payload = struct.pack("<HH", idx.shape[1], idx.shape[0]) + rgb.tobytes() + mask.tobytes()
        rgba_keys.add(hashlib.sha256(payload).digest())
        anchor_keys.add(hashlib.sha256(payload + struct.pack("<hh", cx, cy)).digest())
        opaque += int(mask.all())
        blank += int(not mask.any())
    return {"canonical_sha256": hashlib.sha256(data).hexdigest().upper(), "frames": count,
            "used_frames": len(used), "cycles": cycles, "empty_cycles": sum(c["slots"] == 0 for c in cycles),
            "static": all(c["static"] for c in cycles),
            "variable_geometry": len({geometry[i] for i in used}) > 1,
            "raw_x4_bytes": sum(w * h * 64 for w, h, _, _ in geometry),
            "max_frame_size_x1": [max(g[0] for g in geometry), max(g[1] for g in geometry)],
            "zero_dimension_frames": sum(w == 0 or h == 0 for w, h, _, _ in geometry),
            "blank_frames": blank, "opaque_frames": opaque}, rgba_keys, anchor_keys


def apply_override(row: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    updated = dict(row)
    updated.update(value)
    if isinstance(updated.get("tags"), list):
        updated["tags"] = ";".join(updated["tags"])
    return updated


@authority.guarded
def refresh(root: Path, write: bool = False) -> dict[str, Any]:
    assets = workflow.read_csv(root / "effects/index/bam-assets.csv")
    overrides = load_classification(root)
    keys = [a["asset_key"] for a in assets]
    if len(keys) != len(set(keys)):
        raise workflow.WorkflowError("asset_key dupliqué")
    if set(overrides["assets"]) - {a["resref"] for a in assets}:
        raise workflow.WorkflowError("classification d'un BAM absent de l'inventaire")
    consumers = build_consumers(root)
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in consumers:
        grouped[row["asset_key"]].append(row)
    animations = {r["bam_resref"]: r for r in read_optional_csv(root, "animations/index/ressources.csv")}
    metadata, rgba, anchors = {}, set(), set()
    source_groups: dict[str, list[str]] = collections.defaultdict(list)
    for asset in assets:
        if asset["source_state"] == "available":
            info, rgb_keys, anchor_keys = inspect_bam(root / asset["extracted_path"], asset["source_sha256"])
            metadata[asset["resref"]] = info
            rgba.update(rgb_keys)
            anchors.update(anchor_keys)
            source_groups[info["canonical_sha256"]].append(asset["resref"])
    rows = []
    for asset in assets:
        name, key = asset["resref"], asset["asset_key"]
        info = metadata.get(name, {})
        members = grouped[key]
        rates = sorted({int(c["native_fps"]) for c in members if str(c["native_fps"]).isdigit()})
        loops = {int(c["loop"]) for c in members if c["loop"] != ""}
        tags, notes = set(), []
        usage = "known" if members else "unresolved"
        if not members:
            tags.add("unresolved")
            notes.append("owner-not-demonstrated")
        if info.get("static"):
            tags.add("static")
        elif loops:
            tags.update("loop" if v else "one-shot" for v in loops)
        if any(c["blend"] == 1 for c in members):
            tags.add("alpha")
        if any(c["palette"] or c["color_enabled"] == 1 for c in members):
            tags.add("palette")
            notes.append("runtime-palette-support-undemonstrated")
        if any(str(c["orientations"]) == "16" or str(c["mirror"]) in {"5", "9", "16"} for c in members):
            tags.add("directional")
        if len(info.get("cycles", [])) > 1 and any(c["owner_route"] == "vvc"
                and len({v for v in str(c["cycles"]).split(";") if v not in {"0", "4294967295", ""}}) > 1 for c in members):
            tags.add("staged")
        if not info.get("static") and not rates and members:
            notes.append("native-timing-to-observe")
        if any(c["owner_route"] == "native-shadow" for c in members):
            notes.append("native-shadow-not-substituted")
        if asset["source_state"] != "available":
            notes.append("source-missing")
        if len(info.get("cycles", [])) > 1:
            notes.append("interpolation-multicycle-unsupported")
        if info.get("empty_cycles"):
            notes.append("runtime-empty-cycles-unsupported")
        if info.get("zero_dimension_frames"):
            notes.append("runtime-zero-dimensions-unsupported")
        if any(30 % n != 0 for n in rates if n > 0):
            notes.append("interpolation-noninteger-rate-unsupported")
        if "one-shot" in tags:
            notes.append("interpolation-endpoints-required")
        if info.get("raw_x4_bytes", 0) > 128 * 1024 * 1024:
            notes.append("runtime-raw-budget-exceeded")
        reuse_animation = ""
        if name in animations:
            candidate = root / "animations/ressources" / name / "source.bam"
            if candidate.is_file():
                payload = candidate.read_bytes()
                canonical = zlib.decompress(payload[12:]) if payload[:4] == b"BAMC" else payload
                if authority.digest(canonical) == info.get("canonical_sha256"):
                    reuse_animation = f"animations/ressources/{name}"
        playback = "static" if info.get("static") else "mixed" if len(loops) > 1 else "loop" if loops == {1} else "one-shot" if loops == {0} else "unknown"
        row = {**dict.fromkeys(ITEM_FIELDS, ""), "asset_key": key, "resref": name,
               "source_state": asset["source_state"], "canonical_sha256": info.get("canonical_sha256", ""),
               "frames": info.get("frames", ""), "used_frames": info.get("used_frames", ""),
               "cycles": len(info["cycles"]) if info else "", "empty_cycles": info.get("empty_cycles", ""),
               "static": int(info["static"]) if info else "", "variable_geometry": int(info["variable_geometry"]) if info else "",
               "raw_x4_bytes": info.get("raw_x4_bytes", ""), "consumer_count": len({c["consumer_key"] for c in members}),
               "owner_routes": ";".join(sorted({c["owner_route"] for c in members})), "native_fps": ";".join(map(str, rates)),
               "playback": playback, "tags": ";".join(sorted(tags)), "usage": usage,
               "reuse_bams": ";".join(n for n in source_groups.get(info.get("canonical_sha256", ""), []) if n != name),
               "reuse_animation": reuse_animation, "priority": 100 if usage == "unresolved" else 60 if notes else 20,
               "technical_notes": ";".join(notes)}
        rows.append(row)
    summary = {"assets": len(assets), "available_sources": len(metadata), "unique_sources": len(source_groups),
               "native_frames": sum(m["frames"] for m in metadata.values()), "unique_rgba_frames": len(rgba),
               "unique_rgba_geometry_frames": len(anchors), "consumer_links": len(consumers),
               "raw_x4_bytes": sum(m["raw_x4_bytes"] for m in metadata.values()),
               "single_cycle": sum(len(m["cycles"]) == 1 for m in metadata.values()),
               "multicycle": sum(len(m["cycles"]) > 1 for m in metadata.values()),
               "static": sum(m["static"] for m in metadata.values()),
               "with_empty_cycles": sum(bool(m["empty_cycles"]) for m in metadata.values())}
    plan = {"schema": "bg2-effects-source-work-plan-v1", "summary": summary,
            "inputs": [workflow.file_evidence(root, root / p) for p in (
                "effects/index/bam-assets.csv", "effects/index/resources.csv", "effects/index/dependencies.csv",
                "projectiles/index/resources.csv", "projectiles/index/dependencies.csv",
                "animations/index/ressources.csv") if (root / p).is_file()],
            "source_groups": [{"canonical_sha256": h, "resrefs": names} for h, names in sorted(source_groups.items()) if len(names) > 1],
            "assets": metadata,
            "reuse_contract": "same bytes do not prove compatible model context, alpha, palette, runtime geometry or QA"}
    if write:
        authority.commit(root, {WORK_ITEMS: csv_data(rows, ITEM_FIELDS), CONSUMERS: csv_data(consumers, CONSUMER_FIELDS),
                                WORK_PLAN: workflow.json_bytes(plan), CLASSIFICATION: workflow.json_bytes(overrides)})
    return {"command": "refresh", "write": write, **summary}


def work_item(root: Path, name: str) -> dict[str, Any] | None:
    overrides = load_classification(root)["assets"]
    row = next((r for r in read_optional_csv(root, WORK_ITEMS) if r["resref"] == name), None)
    return apply_override(row, overrides.get(name, {})) if row else None


@authority.guarded
def classify(root: Path, name: str, changes: dict[str, Any], write: bool = False) -> dict[str, Any]:
    name, _, _, _ = workflow.load_asset(root, name)
    if set(changes) - {"tags", "usage", "priority", "recipe", "notes"}:
        raise workflow.WorkflowError("champ de classification inconnu")
    data = load_classification(root)
    data["assets"].setdefault(name, {}).update(changes)
    # Validate before a mutation, using the same rules as the reader.
    if "tags" in changes and any(t not in TAGS for t in changes["tags"]):
        raise workflow.WorkflowError("tag inconnu")
    if "usage" in changes and changes["usage"] not in USAGES:
        raise workflow.WorkflowError("usage inconnu")
    if "priority" in changes and (type(changes["priority"]) is not int or not 0 <= changes["priority"] <= 999):
        raise workflow.WorkflowError("priorité hors 0..999")
    if any(k in changes and not isinstance(changes[k], str) for k in ("recipe", "notes")):
        raise workflow.WorkflowError("recette/notes : texte requis")
    if write:
        authority.commit(root, {CLASSIFICATION: workflow.json_bytes(data)})
    return {"command": "classify", "resref": name, "write": write, "classification": data["assets"][name]}


@authority.guarded
def queue(root: Path, limit: int = 20, write: bool = False) -> dict[str, Any]:
    items = read_optional_csv(root, WORK_ITEMS)
    if not items:
        raise workflow.WorkflowError("vue absente : effect_tracking.py refresh --run")
    overrides = load_classification(root)["assets"]
    processing = {r["asset_key"]: r for r in workflow.read_csv(root / "effects/index/processing.csv", workflow.PROCESSING_FIELDS)}
    selections = root / "effects/index/selections"
    rows, counts = [], collections.Counter()
    for base in items:
        item = apply_override(base, overrides.get(base["resref"], {}))
        state = processing[item["asset_key"]]
        accepted = state["qa_state"] in {"passed", "native"}
        selection_file = selections / f"{item['resref']}.json"
        selected = json.loads(selection_file.read_text(encoding="utf-8-sig")) if selection_file.is_file() else {}
        accepted_runs = selected.get("contract", {}).get("source", {})
        working = accepted and any(state[f"{stage}_run"] and state[f"{stage}_run"] != accepted_runs.get(f"{stage}_run") for stage in workflow.STAGES)
        bucket = "working" if working else "accepted" if accepted else "blocked" if item["source_state"] != "available" else "excluded" if item["usage"] == "excluded" else "unresolved" if item["usage"] == "unresolved" else "pending"
        counts[bucket] += 1
        if bucket in {"accepted", "excluded"}:
            continue
        rows.append({k: item[k] for k in ("resref", "tags", "recipe", "usage", "priority", "reuse_bams", "reuse_animation", "technical_notes")} | {
            "spatial_state": state["spatial_state"], "interpolation_state": state["interpolation_state"],
            "queue_state": bucket, "acquired_qa": state["qa_state"],
            "selection": f"effects/index/selections/{item['resref']}.json" if (selections / f"{item['resref']}.json").is_file() else ""})
    rows.sort(key=lambda r: (0 if r["usage"] == "known" else 1, int(r["priority"]), r["resref"]))
    return {"command": "queue", "counts": dict(counts), "items": rows[:limit],
            "hint": "hints only; no automatic QA, installation, release or production gate"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    refresh_parser = commands.add_parser("refresh", help="recalcule les vues techniques ; exceptionnel")
    refresh_parser.add_argument("--run", action="store_true")
    queue_parser = commands.add_parser("queue", help="file rapide, aucun hash global")
    queue_parser.add_argument("--limit", type=int, default=20)
    classify_parser = commands.add_parser("classify", help="facultatif : recette/priorité/usage d'un BAM")
    classify_parser.add_argument("--resref", required=True)
    classify_parser.add_argument("--tags", nargs="*", choices=sorted(TAGS))
    classify_parser.add_argument("--usage", choices=sorted(USAGES))
    classify_parser.add_argument("--priority", type=int)
    classify_parser.add_argument("--recipe")
    classify_parser.add_argument("--notes")
    classify_parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    root = args.workspace_root.resolve()
    try:
        if args.command == "refresh":
            result = refresh(root, args.run)
        elif args.command == "queue":
            if args.limit < 1:
                raise workflow.WorkflowError("limit doit être positif")
            result = queue(root, args.limit)
        else:
            changes = {k: getattr(args, k) for k in ("tags", "usage", "priority", "recipe", "notes") if getattr(args, k) is not None}
            if not changes:
                raise workflow.WorkflowError("indiquer au moins une classification")
            result = classify(root, args.resref, changes, args.run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, struct.error) as error:
        print(f"ERROR: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
