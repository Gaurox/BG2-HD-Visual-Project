#!/usr/bin/env python3
"""État verrouillé des packs d'animations de zone installés dans le jeu.

`animations/index/area-pack-lock.json` mémorise, pour chaque zone servie, ses ressources
(signature de contenu), la recette pour la reconstruire (pack stocké ou liste `merged_from`) et
l'empreinte du dossier installé. Les installateurs le mettent à jour ; `status` le compare au
dossier du jeu et au registre en quelques secondes ; `restore` reconstruit une zone depuis le
verrou ou depuis une sauvegarde d'installation.

  status                       écarts installé / verrou / registre
  status --deep                idem + chaque recette du verrou est rejouée et comparée
  bootstrap [--zones AR..]     enregistre les zones installées non verrouillées
  restore --zones AR.. | --all-missing
                               reconstruit + réinstalle depuis le verrou (`--all-missing` :
                               toutes les zones verrouillées absentes du jeu)
  restore --from-backup DIR --zones AR.. | --all-missing
                               idem depuis un dossier `areas` sauvegardé (versions acceptées
                               du registre prioritaires, sinon contenu identique octet pour octet)
                               (`--exact` : contenu identique octet pour octet, sans substitution)
  forget AR..                  retire une zone du verrou
  prior-work                   ressources `non-traité` qui ont déjà des runs/packs
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOCK_PATH = ROOT / "animations" / "index" / "area-pack-lock.json"
EXCEPTIONS_PATH = ROOT / "animations" / "index" / "area-pack-exceptions.json"
PACKS = ROOT / "animations" / "packs-par-zone"
SCHEMA = "bg2-upscale-area-pack-lock-v1"
ASSET_RE = re.compile(r"^AAX4-(.+)-frame\d+\.rgba$")
POSITION_RE = re.compile(r"^\s*-?\d+\s*,\s*-?\d+\s*$")
DEFAULT_EXCEPTIONS = [
    {"resref": "FLAME2S", "areas": "*",
     "reason": "validé-x4 mais aucun pack de zone n'existe : servi par le BAM vanilla (abandonné)"},
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def group_signature(hashes: list[tuple[str, str]]) -> str:
    """Signature d'une ressource : sha256 des hashes de ses frames triées par nom."""
    return hashlib.sha256("".join(h for _n, h in sorted(hashes)).encode()).hexdigest()[:12]


def resource_key(asset_name: str) -> str | None:
    match = ASSET_RE.match(asset_name)
    return match.group(1) if match else None


def base_resref(key: str) -> str:
    return re.sub(r"-v\d+$", "", key)


# ---------------------------------------------------------------- dossier de zone installé
def game_areas_dir() -> Path:
    sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))
    from workspace_paths import get_path  # noqa: PLC0415
    return Path(get_path("bg2ee_game_root", required=True)) / "iee-assets" / "areas"


def zone_fingerprint(directory: Path) -> dict[str, int]:
    files = size = newest = 0
    with os.scandir(directory) as entries:
        for entry in entries:
            if entry.is_file():
                stat = entry.stat()
                files += 1
                size += stat.st_size
                newest = max(newest, stat.st_mtime_ns)
    return {"files": files, "bytes": size, "max_mtime_ns": newest}


def zone_signatures(directory: Path) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    with os.scandir(directory) as entries:
        for entry in sorted(entries, key=lambda item: item.name):
            key = resource_key(entry.name)
            if key and entry.is_file():
                groups[key].append((entry.name, sha256_file(Path(entry.path))))
    return {key: {"sig": group_signature(hashes), "frames": len(hashes)}
            for key, hashes in groups.items()}


def zone_resource_names(directory: Path) -> set[str]:
    if not directory.is_dir():
        return set()
    return {key for name in os.listdir(directory) if (key := resource_key(name))}


# ---------------------------------------------------------------- packs stockés
def leaf_signatures(leaf: Path) -> dict[str, dict[str, Any]] | None:
    manifest_path = leaf / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for resource in manifest.get("resources") or []:
        assets = resource.get("assets") or [
            {"name": frame.get("asset"), "sha256": frame.get("sha256")}
            for frame in resource.get("frames") or []]
        for asset in assets:
            key = resource_key(str(asset.get("name")))
            if key:
                groups[key].append((asset["name"], asset["sha256"]))
    return {key: {"sig": group_signature(hashes), "frames": len(hashes)}
            for key, hashes in groups.items()}


def leaf_resource_entry(leaf: Path, key: str) -> dict[str, Any] | None:
    """Entrée `resources[]` du manifeste d'une feuille qui porte la ressource `key`."""
    manifest = json.loads((leaf / "manifest.json").read_text(encoding="utf-8"))
    for resource in manifest.get("resources") or []:
        assets = resource.get("assets") or resource.get("frames") or []
        first = assets[0].get("name") or assets[0].get("asset") if assets else None
        if first and resource_key(str(first)) == key:
            return resource
    return None


class StoredIndex:
    """Index (zone, ressource, signature) -> packs stockés, construit à la demande."""

    def __init__(self, zones: set[str]) -> None:
        self.zones = zones
        self.by_resource: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        self.leaves: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        for pack in sorted(PACKS.iterdir(), reverse=True):
            for zone in zones:
                signatures = leaf_signatures(pack / zone) if (pack / zone).is_dir() else None
                if not signatures:
                    continue
                self.leaves[(pack.name, zone)] = signatures
                for key, info in signatures.items():
                    self.by_resource[(zone, key, info["sig"])].append(pack.name)

    def whole_leaf(self, zone: str, wanted: dict[str, dict[str, Any]]) -> str | None:
        target = {key: info["sig"] for key, info in wanted.items()}
        for (pack, area), signatures in self.leaves.items():
            if area == zone and {key: info["sig"] for key, info in signatures.items()} == target:
                return pack
        return None


def accepted_source(resref: str, zone: str) -> str | None:
    """Pack accepté par la QA (sélection courante) pour cette ressource dans cette zone."""
    path = ROOT / "animations" / "index" / "selections" / f"{resref}.json"
    if not path.is_file():
        return None
    try:
        selection = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for area in (selection.get("source_pack") or {}).get("areas") or []:
        if area.get("area") == zone and area.get("path"):
            leaf = Path(str(area["path"]).replace("\\", "/"))
            return leaf.parent.name if leaf.name == zone else leaf.name
    return None


def resolve_zone(zone: str, wanted: dict[str, dict[str, Any]], index: StoredIndex,
                 prefer_accepted: bool) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    """Recette de reconstruction : (build, ressources introuvables, notes)."""
    notes: list[str] = []
    substituted = False
    if prefer_accepted:
        for key, info in wanted.items():
            accepted = accepted_source(base_resref(key), zone)
            if accepted and key in index.leaves.get((accepted, zone), {}) \
                    and index.leaves[(accepted, zone)][key]["sig"] != info["sig"]:
                substituted = True
    if not substituted:
        # Une feuille stockée identique à la zone évite toute fusion (et porte les variantes liées).
        pack = index.whole_leaf(zone, wanted)
        if pack:
            return {"leaf": f"animations/packs-par-zone/{pack}/{zone}"}, [], notes
    args: list[str] = []
    missing: list[str] = []
    for key, info in sorted(wanted.items()):
        pack = None
        if prefer_accepted:
            accepted = accepted_source(base_resref(key), zone)
            if accepted and (accepted, zone) in index.leaves and key in index.leaves[(accepted, zone)]:
                pack = accepted
                if index.leaves[(accepted, zone)][key]["sig"] != info["sig"]:
                    notes.append(f"{key}: version acceptée actuelle ({accepted})")
        if pack is None:
            candidates = index.by_resource.get((zone, key, info["sig"]))
            if candidates:
                pack = candidates[0]
        if pack is None:
            missing.append(key)
            continue
        leaf = PACKS / pack / zone
        entry = leaf_resource_entry(leaf, key) or {}
        position = entry.get("position")
        selector = f"::{base_resref(key)}" if not position else \
            f"::{base_resref(key)}::{int(position[0])},{int(position[1])}"
        args.append(f"animations/packs-par-zone/{pack}/{zone}{selector}")
    if missing:
        return None, missing, notes
    return {"merged_from": args}, [], notes


def recipe_sources(entry: dict[str, Any]) -> list[str]:
    """Dossiers de pack dont dépend la recette d'une zone."""
    build = entry.get("build") or {}
    if "leaf" in build:
        return [str(build["leaf"])]
    return [str(item).split("::")[0] for item in build.get("merged_from") or []]


def recipe_signatures(entry: dict[str, Any]) -> dict[str, str] | None:
    """Signatures que la recette reproduirait, lues dans les manifestes : aucune écriture."""
    build = entry.get("build") or {}
    if "leaf" in build:
        signatures = leaf_signatures(ROOT / build["leaf"])
        return None if signatures is None else {key: info["sig"] for key, info in signatures.items()}
    if not build.get("merged_from"):
        return None
    result: dict[str, str] = {}
    for item in build["merged_from"]:
        # `CHEMIN`, `CHEMIN::RESREF`, `CHEMIN::X,Y` ou `CHEMIN::RESREF::X,Y` : seul un segment
        # qui n'est pas une position est un sélecteur de ressource.
        path, *selectors = str(item).split("::")
        signatures = leaf_signatures(ROOT / path)
        if signatures is None:
            return None
        resref = next((part for part in selectors if not POSITION_RE.match(part)), "")
        for key, info in signatures.items():
            if not resref or base_resref(key) == resref:
                result[key] = info["sig"]
    return result


def build_leaf(zone: str, build: dict[str, Any], scratch: Path) -> Path:
    if "leaf" in build:
        return ROOT / build["leaf"]
    output = scratch / zone.lower()
    if output.exists():
        shutil.rmtree(output)
    command = [sys.executable, str(ROOT / "pipeline" / "scripts" / "merge_area_pack_resources.py"),
               "--area", zone, "--output", str(output)]
    for item in build["merged_from"]:
        command += ["--pack", item]
    subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return output / zone


# ---------------------------------------------------------------- verrou
def load_lock() -> dict[str, Any]:
    if LOCK_PATH.is_file():
        return json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    return {"schema": SCHEMA, "areas": {}}


def save_lock(lock: dict[str, Any]) -> None:
    lock["updated_utc"] = utc_now()
    lock["areas"] = dict(sorted(lock["areas"].items()))
    temporary = LOCK_PATH.with_suffix(".json.part")
    temporary.write_text(json.dumps(lock, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    temporary.replace(LOCK_PATH)


def build_from_leaf(leaf: Path) -> dict[str, Any]:
    """Recette d'une feuille installée : ses `merged_from` si elle sort d'une fusion."""
    index_manifest = leaf.parent / "manifest.json"
    if index_manifest.is_file():
        try:
            merged = json.loads(index_manifest.read_text(encoding="utf-8")).get("merged_from")
        except (OSError, ValueError):
            merged = None
        if merged:
            return {"merged_from": [str(item).replace("\\", "/") for item in merged]}
    return {"leaf": rel(leaf)}


def record_zone(zone: str, areas_dir: Path, *, leaf: Path | None = None,
                index: StoredIndex | None = None) -> str:
    """Enregistre l'état installé d'une zone dans le verrou (best effort côté installateurs)."""
    directory = areas_dir / zone
    signatures = zone_signatures(directory)
    lock = load_lock()
    entry: dict[str, Any] = {"recorded_utc": utc_now(), "resources": signatures,
                             "fingerprint": zone_fingerprint(directory)}
    if leaf is not None:
        entry["build"] = build_from_leaf(leaf)
    else:
        index = index or StoredIndex({zone})
        build, missing, _notes = resolve_zone(zone, signatures, index, prefer_accepted=False)
        if build is None:
            entry["build"] = None
            entry["unresolved"] = missing
        else:
            entry["build"] = build
    lock["areas"][zone] = entry
    save_lock(lock)
    return "ok" if entry.get("build") else f"recette introuvable pour {entry.get('unresolved')}"


# ---------------------------------------------------------------- commandes
def registry_expectations() -> dict[str, set[str]]:
    """Ressources `validé-x4` attendues par zone d'après le registre et les occurrences."""
    registry = {row["resref"]: row["status"] for row in csv.DictReader(
        (ROOT / "animations/index/animation_upscale_registry.csv").open(encoding="utf-8"))}
    expected: dict[str, set[str]] = defaultdict(set)
    for row in csv.DictReader((ROOT / "animations/index/occurrences.csv").open(encoding="utf-8")):
        if row["resource_kind"] == "BAM" and registry.get(row["resource_resref"]) == "validé-x4":
            expected[row["area_id"]].add(row["resource_resref"])
    return expected


def load_exceptions() -> list[dict[str, Any]]:
    if EXCEPTIONS_PATH.is_file():
        return json.loads(EXCEPTIONS_PATH.read_text(encoding="utf-8"))
    return DEFAULT_EXCEPTIONS


def is_exception(exceptions: list[dict[str, Any]], resref: str, zone: str) -> bool:
    return any(item["resref"] == resref and (item["areas"] == "*" or zone in item["areas"])
               for item in exceptions)


def command_status(args: argparse.Namespace) -> int:
    areas_dir = game_areas_dir()
    lock = load_lock()
    installed = sorted(item.name for item in areas_dir.iterdir() if item.is_dir())
    problems = 0
    unlocked, changed, touched = [], [], []
    live: dict[str, set[str]] = {}
    for zone in installed:
        entry = lock["areas"].get(zone)
        if entry is None:
            unlocked.append(zone)
            live[zone] = zone_resource_names(areas_dir / zone)
            continue
        locked_res = entry.get("resources") or {}
        if not args.deep and entry.get("fingerprint") \
                and zone_fingerprint(areas_dir / zone) == entry["fingerprint"]:
            live[zone] = set(locked_res)
            continue
        signatures = zone_signatures(areas_dir / zone)
        live[zone] = set(signatures)
        if {k: v["sig"] for k, v in signatures.items()} == {k: v["sig"] for k, v in locked_res.items()}:
            if not args.deep:
                touched.append(zone)
        else:
            gone = sorted(set(locked_res) - set(signatures))
            new = sorted(set(signatures) - set(locked_res))
            diff = sorted(k for k in set(signatures) & set(locked_res)
                          if signatures[k]["sig"] != locked_res[k]["sig"])
            changed.append((zone, gone, new, diff))
    missing = sorted(zone for zone in lock["areas"] if zone not in installed)
    print(f"Zones installées : {len(installed)} | verrou : {len(lock['areas'])}")
    if unlocked:
        problems += 1
        print(f"! installées mais absentes du verrou ({len(unlocked)}) : {' '.join(unlocked)}"
              "  -> `bootstrap`")
    for zone, gone, new, diff in changed:
        problems += 1
        print(f"! {zone} diffère du verrou : retirées {gone or '-'} | ajoutées {new or '-'} | changées {diff or '-'}")
    if touched:
        print(f"  (fichiers réécrits à l'identique, contenu OK : {' '.join(touched)})")
    if missing:
        problems += 1
        print(f"! dans le verrou mais plus installées ({len(missing)}) : {' '.join(missing)}"
              "  -> `restore --zones ...`")
    no_recipe = sorted(zone for zone, entry in lock["areas"].items() if not entry.get("build"))
    if no_recipe:
        problems += 1
        print(f"! zones verrouillées sans recette de reconstruction ({len(no_recipe)}) : "
              f"{' '.join(no_recipe)}")
    absent_sources = sorted({source for entry in lock["areas"].values()
                             for source in recipe_sources(entry)
                             if not (ROOT / source).is_dir()})
    if absent_sources:
        problems += 1
        print(f"! packs sources du verrou supprimés du disque ({len(absent_sources)}) : "
              f"{' '.join(absent_sources[:4])}{' …' if len(absent_sources) > 4 else ''}")
    if args.deep:
        broken = []
        for zone, entry in sorted(lock["areas"].items()):
            expected = {key: info["sig"] for key, info in (entry.get("resources") or {}).items()}
            produced = recipe_signatures(entry)
            if produced is None:
                broken.append(f"{zone} (pack source illisible)")
            elif produced != expected:
                broken.append(f"{zone} ({sorted(set(produced) ^ set(expected)) or 'signatures'})")
        if broken:
            problems += 1
            print(f"! recettes qui ne reproduisent plus le verrou ({len(broken)}) : "
                  f"{' | '.join(broken[:6])}")
        else:
            print(f"  recettes rejouées : {len(lock['areas'])}/{len(lock['areas'])} reproduisent "
                  "le verrou ; frames réhachées sur disque")
    expected = registry_expectations()
    exceptions = load_exceptions()
    not_served: dict[str, list[str]] = {}
    for zone, resrefs in expected.items():
        have = {base_resref(key) for key in live.get(zone, set())}
        lacking = sorted(r for r in resrefs if r not in have and not is_exception(exceptions, r, zone))
        if lacking:
            not_served[zone] = lacking
    if not_served:
        total = sum(len(v) for v in not_served.values())
        print(f"! validé-x4 au registre mais non servi : {total} couples dans {len(not_served)} zones")
        if args.verbose:
            for zone, lacking in sorted(not_served.items()):
                print(f"    {zone}: {' '.join(lacking)}")
        else:
            print("    (détail : `status -v`)")
        problems += 1
    if not problems:
        print("OK : installé = verrou = registre.")
    return 1 if problems else 0


def command_bootstrap(args: argparse.Namespace) -> int:
    areas_dir = game_areas_dir()
    lock = load_lock()
    zones = args.zones or sorted(item.name for item in areas_dir.iterdir()
                                 if item.is_dir() and item.name not in lock["areas"])
    if not zones:
        print("Rien à enregistrer.")
        return 0
    index = StoredIndex(set(zones))
    for zone in zones:
        print(f"{zone}: {record_zone(zone, areas_dir, index=index)}")
    return 0


def load_area_test() -> Any:
    path = ROOT / "pipeline" / "area-animation-area-test" / "area_animation_area_test.py"
    spec = importlib.util.spec_from_file_location("area_animation_area_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["area_animation_area_test"] = module
    spec.loader.exec_module(module)
    return module


def command_restore(args: argparse.Namespace) -> int:
    areas_dir = game_areas_dir()
    lock = load_lock()
    scratch = ROOT / "animations" / "tmp" / "lock-restore"
    scratch.mkdir(parents=True, exist_ok=True)
    installer = load_area_test()
    backup_areas = Path(args.from_backup) if args.from_backup else None
    installed = {item.name for item in areas_dir.iterdir() if item.is_dir()}
    pool = sorted(item.name for item in backup_areas.iterdir() if item.is_dir()) if backup_areas \
        else sorted(lock["areas"])
    zones = args.zones or ([zone for zone in pool if zone not in installed]
                           if args.all_missing else [])
    if not zones:
        source = "la sauvegarde" if backup_areas else "le verrou"
        print(f"Indiquer --zones AR.. ou --all-missing (zones de {source} absentes du jeu).")
        return 2
    unknown = [zone for zone in zones if zone not in pool]
    if unknown:
        where = "la sauvegarde" if backup_areas else "le verrou"
        print(f"Absentes de {where}, ignorées : {' '.join(unknown)}")
        zones = [zone for zone in zones if zone in pool]
    index = StoredIndex(set(zones)) if backup_areas and zones else None
    done: list[str] = []
    for zone in zones:
        if backup_areas:
            wanted = zone_signatures(backup_areas / zone)
            build, missing, notes = resolve_zone(zone, wanted, index, prefer_accepted=not args.exact)
            if build is None:
                print(f"{zone}: ressources introuvables dans les packs stockés : {missing} — ignorée")
                continue
        else:
            entry = lock["areas"].get(zone)
            build = (entry or {}).get("build")
            notes = []
            if not build:
                print(f"{zone}: aucune recette dans le verrou — ignorée")
                continue
        try:
            leaf = build_leaf(zone, build, scratch)
        except subprocess.CalledProcessError:
            print(f"{zone}: fusion impossible (variantes liées à des positions + version acceptée "
                  "différente ?) — ignorée, à traiter à la main")
            continue
        result = installer.install_area_pack(
            leaf, game_root=Path(str(areas_dir.parents[1])),
            backup_root=installer.DEFAULT_BACKUP_ROOT, verify_only=args.verify_only,
            allow_drop=args.allow_drop)
        detail = f" ({'; '.join(notes)})" if notes else ""
        print(f"{zone}: {result.status}, {result.incoming_files} fichier(s){detail}")
        if result.status in {"installed", "already-installed"}:
            record_zone(zone, areas_dir, leaf=leaf)
            done.append(zone)
        elif result.status == "verified-only":
            done.append(zone)
        if (scratch / zone.lower()).exists():
            shutil.rmtree(scratch / zone.lower())
    label = "vérifiées (aucune écriture)" if args.verify_only else "restaurées"
    print(f"Zones {label} : {len(done)}/{len(zones)}")
    return 0


def command_record_splitroot(args: argparse.Namespace) -> int:
    """Après une installation complète : chaque zone du split-root devient sa propre recette."""
    root = Path(args.split_root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    areas_dir = game_areas_dir()
    for area in manifest.get("areas") or []:
        zone = str(area["area_id"])
        if (areas_dir / zone).is_dir():
            print(f"{zone}: {record_zone(zone, areas_dir, leaf=root / str(area.get('directory') or zone))}")
    return 0


def command_forget(args: argparse.Namespace) -> int:
    lock = load_lock()
    for zone in args.zones:
        lock["areas"].pop(zone, None)
    save_lock(lock)
    return 0


def command_prior_work(_args: argparse.Namespace) -> int:
    registry = list(csv.DictReader(
        (ROOT / "animations/index/animation_upscale_registry.csv").open(encoding="utf-8")))
    untreated = [row["resref"] for row in registry if row["status"] == "non-traité"]
    animations = ROOT / "animations"
    traces: dict[str, list[str]] = defaultdict(list)
    for resref in untreated:
        runs = animations / "ressources" / resref / "runs"
        if runs.is_dir() and any(runs.iterdir()):
            traces[resref].append("ressources/runs")
    for base in ("batches", "runs", "packs-par-zone"):
        for folder in (animations / base).glob("*"):
            if not folder.is_dir():
                continue
            low = folder.name.lower()
            for resref in untreated:
                if len(resref) >= 5 and resref.lower() in low:
                    traces[resref].append(f"{base}/{folder.name}")
    retention = (animations / "index" / "post-p3-pack-retention-20260902.json").read_text(encoding="utf-8")
    for resref in untreated:
        if re.search(r"\b" + re.escape(resref) + r"\b", retention):
            traces[resref].append("retention-json")
    print(f"non-traité : {len(untreated)} | avec traces : {len(traces)}")
    for resref, items in sorted(traces.items()):
        print(f"  {resref}: {items[:3]}{' …' if len(items) > 3 else ''}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status")
    status.add_argument("-v", "--verbose", action="store_true")
    status.add_argument("--deep", action="store_true",
                        help="réhacher toutes les frames installées et rejouer chaque recette du verrou")
    boot = commands.add_parser("bootstrap")
    boot.add_argument("--zones", nargs="*")
    restore = commands.add_parser("restore")
    restore.add_argument("--zones", nargs="*")
    restore.add_argument("--from-backup")
    restore.add_argument("--all-missing", action="store_true")
    restore.add_argument("--verify-only", action="store_true")
    restore.add_argument("--allow-drop", action="store_true")
    restore.add_argument("--exact", action="store_true",
                         help="reprendre le contenu exact de la sauvegarde (sans substituer les versions acceptées)")
    forget = commands.add_parser("forget")
    forget.add_argument("zones", nargs="+")
    record = commands.add_parser("record-splitroot")
    record.add_argument("split_root")
    commands.add_parser("prior-work")
    args = parser.parse_args(argv)
    handler = {"status": command_status, "bootstrap": command_bootstrap, "restore": command_restore,
               "forget": command_forget, "prior-work": command_prior_work,
               "record-splitroot": command_record_splitroot}[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
