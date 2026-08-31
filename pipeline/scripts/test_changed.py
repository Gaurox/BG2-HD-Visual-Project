"""Select and run the smallest safe validation suite for changed repository paths."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
ENGINE_ROOT = ROOT / "engine" / "InfinityEngine-Enhancer" / "source-patchee"
ENGINE_BUILD = ROOT / "build" / "iee"
RELEASE_ROOT = ROOT / "releases" / "BG2-HD-Upscale"
RELEASE_PHASE2 = RELEASE_ROOT / "tools" / "Test-BG2HD-Phase2.ps1"


@dataclass(frozen=True)
class TestGroup:
    name: str
    scope: str
    modules: tuple[str, ...] = ()


GROUPS = {
    "smoke": TestGroup(
        "smoke",
        "python",
        (
            "pipeline.tests.test_workspace_command",
            "pipeline.tests.test_workspace_paths",
        ),
    ),
    "documentation": TestGroup(
        "documentation",
        "python",
        ("pipeline.tests.test_repository_docs",),
    ),
    "maps": TestGroup(
        "maps",
        "python",
        (
            "pipeline.tests.test_map_build_transaction",
            "pipeline.tests.test_wed_cover_animation_patch",
            "pipeline.tests.test_wed_mask_polygon_patch",
        ),
    ),
    "map-diagnostics": TestGroup(
        "map-diagnostics",
        "python",
        (
            "pipeline.tests.test_benchmark_pvrz_decode",
            "pipeline.tests.test_repack_pvrz_compression",
            "pipeline.tests.test_repage_pvrz_blocks",
        ),
    ),
    "animations": TestGroup(
        "animations",
        "python",
        (
            "pipeline.tests.test_animation_inventory",
            "pipeline.tests.test_animation_upscale_pipeline",
            "pipeline.tests.test_animation_interpolation_pipeline",
            "pipeline.tests.test_animation_upscale_30fps_v2",
            "pipeline.tests.test_animation_runtime_pack",
            "pipeline.tests.test_animation_pack_area_split",
            "pipeline.tests.test_combine_area_pack_splits",
        ),
    ),
    "sprite-inventory": TestGroup(
        "sprite-inventory",
        "python",
        (
            "pipeline.tests.test_sprite_inventory",
            "pipeline.tests.test_generate_character_complete_x2_jobs",
            "pipeline.tests.test_generate_sprite_family_append",
        ),
    ),
    "sprite-formats": TestGroup(
        "sprite-formats",
        "python",
        (
            "pipeline.tests.test_creature_sprite_x2_pipeline",
            "pipeline.tests.test_creature_sprite_xn_catalog",
        ),
    ),
    "sprite-installation": TestGroup(
        "sprite-installation",
        "python",
        ("pipeline.tests.test_creature_sprite_xn_catalog_install",),
    ),
    "graphics-inventory": TestGroup(
        "graphics-inventory",
        "python",
        ("pipeline.tests.test_graphics_inventory",),
    ),
    "registry": TestGroup(
        "registry",
        "python",
        (
            "pipeline.tests.test_asset_tracking_contract",
            "pipeline.tests.test_global_asset_registry",
        ),
    ),
    "integrity": TestGroup(
        "integrity",
        "python",
        (
            "pipeline.tests.test_historical_git_evidence",
            "pipeline.tests.test_workspace_integrity",
        ),
    ),
    "renderer-transaction": TestGroup(
        "renderer-transaction",
        "python",
        ("pipeline.tests.test_renderer_candidate_transaction",),
    ),
    "release": TestGroup("release", "release"),
    "engine": TestGroup("engine", "engine"),
}

GROUP_ORDER = tuple(GROUPS)


@dataclass(frozen=True)
class ChangedPath:
    status: str
    path: str
    previous_path: str | None = None


@dataclass(frozen=True)
class Classification:
    groups: tuple[str, ...]
    force_full_reason: str | None = None


@dataclass(frozen=True)
class SelectionPlan:
    full: bool
    groups: tuple[str, ...]
    changed_paths: tuple[ChangedPath, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Command:
    label: str
    scope: str
    argv: tuple[str, ...]


MAP_SCRIPTS = {
    "area_decode.py",
    "audit_area_preflight.py",
    "audit_water_area.py",
    "batch_extract.py",
    "batch_extract_secondary.py",
    "build_area_lightmap_pack.py",
    "build_spline_alpha_mask.py",
    "build_spline_map_alpha.py",
    "build_upscaled_area.py",
    "build_upscaled_legacy_tis.py",
    "build_water_contour_feather.py",
    "build_wed_cover_animation_patch.py",
    "build_wed_mask_polygon_patch.py",
    "extract_legacy_tis_frames.py",
    "inject_build.py",
    "refresh_area_catalog.py",
    "render_liquid_overlay_mask.py",
    "render_secondary.py",
    "render_tile_classes.py",
    "run_seedvr_comfyui.py",
    "validate_x1_masters.py",
    "verify_upscaled.py",
}
MAP_DIAGNOSTIC_SCRIPTS = {
    "benchmark_pvrz_decode.py",
    "repack_pvrz_compression.py",
    "repage_pvrz_blocks.py",
}
ANIMATION_SCRIPTS = {
    "bam_export.py",
    "build_alpha_feather.py",
    "build_animation_runtime_pack.py",
    "build_blended_rgb_neutral_pack.py",
    "build_manual_alpha_mask_30fps_v2.py",
    "combine_area_pack_splits.py",
    "export_bam_frames.py",
    "extract_area_animations.py",
    "list_animations.py",
    "merge_area_pack_resources.py",
    "merge_v2_base_pack.py",
    "run_animation_interpolation.py",
    "run_animation_upscale.py",
    "run_animation_upscale_30fps_v2.py",
    "split_animation_pack_by_area.py",
    "sync_animation_upscale_registry.py",
    "upscale_animation_frames.py",
}
SPRITE_INVENTORY_SCRIPTS = {
    "build_sprite_inventory.py",
    "generate_character_complete_x2_jobs.py",
    "generate_sprite_family_append.py",
}
SPRITE_FORMAT_SCRIPTS = {
    "run_creature_sprite_x2.py",
    "xbr2x_batch.js",
    "Install-CreatureSprite-X2-Test.ps1",
    "Restore-CreatureSprite-X2-Test.ps1",
    "Install-CreatureSprite-XN-Test.ps1",
    "Restore-CreatureSprite-XN-Test.ps1",
}
SPRITE_INSTALL_SCRIPTS = {
    "Install-CreatureSprite-XN-Catalog-Test.ps1",
    "Restore-CreatureSprite-XN-Catalog-Test.ps1",
}
GRAPHICS_SCRIPTS = {
    "extract_character_portraits.py",
    "extract_encountered_portraits.py",
    "extract_joinable_portraits.py",
    "organize_ppe_portraits.py",
    "survey_creature_portraits.py",
}
TRANSVERSAL_PATHS = {
    ".gitignore",
    "requirements.txt",
    "pipeline/scripts/asset_tracking_contract.py",
    "pipeline/scripts/audit_workspace_integrity.py",
    "pipeline/scripts/bg2lib.py",
    "pipeline/scripts/build_global_asset_registry.py",
    "pipeline/scripts/build_graphics_inventory.py",
    "pipeline/scripts/test_changed.py",
    "pipeline/scripts/workspace.py",
    "pipeline/scripts/workspace_paths.py",
    "pipeline/scripts/WorkspacePaths.ps1",
    "docs/asset-tracking-record.schema.json",
    "docs/workspace-run.schema.json",
}


def _matches(path: str, *patterns: str) -> bool:
    return any(fnmatchcase(path, pattern) for pattern in patterns)


def _is_documentation(path: str) -> bool:
    lowered = path.casefold()
    return lowered.endswith((".md", ".rst")) or path in {"AGENTS.md", "README.md"}


def classify_path(path: str) -> Classification:
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    name = path.rsplit("/", 1)[-1]

    if _is_documentation(path):
        return Classification(("documentation",))
    if path in TRANSVERSAL_PATHS or _matches(
        path,
        ".github/workflows/**",
        "config/**",
        "pipeline/tests/**",
        "pyproject.toml",
        "pytest.ini",
        "tox.ini",
    ):
        return Classification((), f"changement transversal ou infrastructure de tests: {path}")
    if path.startswith("releases/BG2-HD-Upscale/"):
        return Classification(("release",), f"release, Core ou packaging: {path}")
    if path == "engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py":
        return Classification(("renderer-transaction",))
    if path.startswith("engine/InfinityEngine-Enhancer/source-patchee/"):
        return Classification(("engine",), f"runtime moteur: {path}")

    if path == "areas.csv":
        return Classification(("maps", "registry", "integrity"))
    if path.startswith("maps/"):
        return Classification(("maps",))
    if path.startswith("pipeline/scripts/") and name in MAP_DIAGNOSTIC_SCRIPTS:
        return Classification(("map-diagnostics",))
    if path.startswith("pipeline/scripts/") and name in MAP_SCRIPTS:
        return Classification(("maps",))

    if _matches(
        path,
        "animations/index/path-migrations.json",
        "animations/index/qa-evidence-migrations.json",
        "animations/**/qa-approval.json",
    ):
        return Classification(("animations", "registry", "integrity"))
    if path.startswith("animations/index/"):
        return Classification(("animations", "registry"))
    if path.startswith("animations/"):
        return Classification(("animations",))
    if path.startswith("pipeline/scripts/") and name in ANIMATION_SCRIPTS:
        return Classification(("animations",))
    if path.startswith("pipeline/scripts/") and _matches(
        name,
        "Install-AreaAnimation*.ps1",
        "Install-AreaAnimations*.ps1",
        "Restore-AreaAnimation*.ps1",
        "Restore-AreaAnimations*.ps1",
        "Set-AreaAnimations-*.ps1",
    ):
        return Classification(("animations",))

    if path.startswith("pipeline/scripts/") and name in SPRITE_INSTALL_SCRIPTS:
        return Classification(("sprite-installation",))
    if path.startswith("pipeline/scripts/") and name in SPRITE_INVENTORY_SCRIPTS:
        return Classification(("sprite-inventory",))
    if path.startswith("pipeline/scripts/") and name in SPRITE_FORMAT_SCRIPTS:
        return Classification(("sprite-formats",))
    if _matches(path, "sprite/**/current-generation.json", "sprite/**/active-test.json"):
        return Classification(("registry", "integrity"))
    if path.startswith("sprite/index/"):
        return Classification(("sprite-inventory", "registry"))
    if path.startswith("sprite/"):
        return Classification(("sprite-formats",))

    if path.startswith("pipeline/scripts/") and name in GRAPHICS_SCRIPTS:
        return Classification(("graphics-inventory", "registry"))
    if _matches(
        path,
        "graphics/**",
        "interface/**",
        "video/index/**",
        "icons/**",
        "cursors/**",
        "effects/**",
        "projectiles/**",
        "portraits/*.csv",
        "portraits/**/*.csv",
        "portraits-recrutables/*.csv",
        "portraits-recrutables/**/*.csv",
    ):
        return Classification(("graphics-inventory", "registry"))

    if _matches(path, "asset-tracking/workspace-integrity.json", "asset-tracking/runs.*"):
        return Classification(("integrity",))
    if path.startswith("asset-tracking/"):
        return Classification(("registry",))
    if _matches(
        path,
        "docs/workspace-cleanup-manifest*.json",
        "docs/workspace-archive-manifest*.json",
    ):
        return Classification(("integrity",))

    return Classification((), f"chemin inconnu: {path}")


def full_plan(
    reason: str,
    changed_paths: Iterable[ChangedPath] = (),
    additional_reasons: Iterable[str] = (),
) -> SelectionPlan:
    return SelectionPlan(
        full=True,
        groups=GROUP_ORDER,
        changed_paths=tuple(changed_paths),
        reasons=(reason, *tuple(additional_reasons)),
    )


def select_paths(changed_paths: Iterable[ChangedPath]) -> SelectionPlan:
    changed = tuple(changed_paths)
    reasons: list[str] = []
    selected = {"smoke"}
    for item in changed:
        status = item.status.upper()
        if status.startswith(("R", "C", "D")):
            reasons.append(f"{status} impose la suite complète: {item.previous_path or item.path} -> {item.path}")
            continue
        classification = classify_path(item.path)
        selected.update(classification.groups)
        if classification.force_full_reason:
            reasons.append(classification.force_full_reason)
    if reasons:
        return full_plan("fallback de sécurité", changed, reasons)
    ordered = tuple(name for name in GROUP_ORDER if name in selected)
    return SelectionPlan(False, ordered, changed, ("sélection par fichiers modifiés",))


def parse_name_status(payload: str) -> tuple[ChangedPath, ...]:
    changed: list[ChangedPath] = []
    for raw_line in payload.splitlines():
        if not raw_line.strip():
            continue
        fields = raw_line.split("\t")
        status = fields[0]
        if (status.startswith("R") or status.startswith("C")) and len(fields) >= 3:
            changed.append(ChangedPath(status, fields[2], fields[1]))
        elif len(fields) >= 2:
            changed.append(ChangedPath(status, fields[1]))
        else:
            changed.append(ChangedPath("?", raw_line))
    return tuple(changed)


def _run_git(arguments: Sequence[str]) -> str:
    completed = subprocess.run(
        ("git", "-c", "core.quotepath=false", *arguments),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout


def collect_changed_paths(base: str | None = None) -> tuple[ChangedPath, ...]:
    changed: list[ChangedPath] = []
    if base:
        changed.extend(parse_name_status(_run_git(("diff", "--name-status", "--find-renames", f"{base}...HEAD", "--"))))
        changed.extend(parse_name_status(_run_git(("diff", "--name-status", "--find-renames", "HEAD", "--"))))
    else:
        changed.extend(parse_name_status(_run_git(("diff", "--name-status", "--find-renames", "HEAD", "--"))))
    for path in _run_git(("ls-files", "--others", "--exclude-standard")).splitlines():
        if path:
            changed.append(ChangedPath("??", path))
    unique: dict[tuple[str, str, str | None], ChangedPath] = {}
    for item in changed:
        unique[(item.status, item.path, item.previous_path)] = item
    return tuple(unique.values())


def python_modules_for(plan: SelectionPlan) -> tuple[str, ...]:
    modules: list[str] = []
    for name in plan.groups:
        for module in GROUPS[name].modules:
            if module not in modules:
                modules.append(module)
    return tuple(modules)


def _powershell() -> str:
    return shutil.which("pwsh") or ("powershell.exe" if os.name == "nt" else "pwsh")


def commands_for(plan: SelectionPlan, only: str = "all") -> tuple[Command, ...]:
    commands: list[Command] = []
    include_python = only in {"all", "python"}
    include_release = only in {"all", "release"}
    include_engine = only in {"all", "engine"}

    if include_python:
        if plan.full:
            commands.append(
                Command(
                    "suite Python complète",
                    "python",
                    (
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "pipeline/tests",
                        "-p",
                        "test_*.py",
                    ),
                )
            )
            commands.append(
                Command(
                    "sorties workspace après tests complets",
                    "python",
                    (sys.executable, "pipeline/scripts/workspace.py", "check", "--after-full-tests"),
                )
            )
        else:
            commands.append(
                Command(
                    "tests Python ciblés",
                    "python",
                    (sys.executable, "-m", "unittest", *python_modules_for(plan)),
                )
            )

    if include_release and (plan.full or "release" in plan.groups):
        commands.append(
            Command(
                "gate release Phase 2",
                "release",
                (
                    _powershell(),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(RELEASE_PHASE2),
                    "-ReleaseRoot",
                    str(RELEASE_ROOT),
                ),
            )
        )

    if include_engine and (plan.full or "engine" in plan.groups):
        ctest_arguments = ["ctest", "--test-dir", str(ENGINE_BUILD)]
        if os.name == "nt":
            ctest_arguments.extend(("-C", "Debug"))
        ctest_arguments.append("--output-on-failure")
        commands.extend(
            (
                Command(
                    "configuration moteur",
                    "engine",
                    (
                        "cmake",
                        "-S",
                        str(ENGINE_ROOT),
                        "-B",
                        str(ENGINE_BUILD),
                        "-DBUILD_TESTING=ON",
                    ),
                ),
                Command(
                    "build moteur et tests",
                    "engine",
                    ("cmake", "--build", str(ENGINE_BUILD), "--parallel", "2"),
                ),
                Command(
                    "tests moteur",
                    "engine",
                    tuple(ctest_arguments),
                ),
            )
        )
    return tuple(commands)


def plan_payload(plan: SelectionPlan, only: str = "all") -> dict[str, object]:
    commands = commands_for(plan, only)
    return {
        "mode": "full" if plan.full else "changed",
        "full": plan.full,
        "reasons": list(plan.reasons),
        "groups": list(plan.groups),
        "changed_paths": [
            {"status": item.status, "path": item.path, "previous_path": item.previous_path}
            for item in plan.changed_paths
        ],
        "python_modules": list(python_modules_for(plan)) if not plan.full else ["pipeline/tests/test_*.py"],
        "run_python": any(command.scope == "python" for command in commands),
        "run_release": any(command.scope == "release" for command in commands),
        "run_engine": any(command.scope == "engine" for command in commands),
        "commands": [
            {"label": command.label, "scope": command.scope, "argv": list(command.argv)}
            for command in commands
        ],
    }


def _format_command(argv: Sequence[str]) -> str:
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def print_plan(plan: SelectionPlan, *, as_json: bool = False, only: str = "all") -> None:
    if as_json:
        print(json.dumps(plan_payload(plan, only), ensure_ascii=False, indent=2))
        return
    print(f"mode: {'full' if plan.full else 'changed'}")
    for reason in plan.reasons:
        print(f"reason: {reason}")
    print("groups: " + ", ".join(plan.groups))
    if plan.changed_paths:
        print("paths:")
        for item in plan.changed_paths:
            previous = f" {item.previous_path} ->" if item.previous_path else ""
            print(f"  {item.status}{previous} {item.path}")
    print("commands:")
    for command in commands_for(plan, only):
        print(f"  [{command.scope}] {command.label}: {_format_command(command.argv)}")


def execute_plan(plan: SelectionPlan, only: str = "all") -> int:
    for command in commands_for(plan, only):
        print(f"== {command.label} ==", flush=True)
        completed = subprocess.run(command.argv, cwd=ROOT, check=False)
        if completed.returncode:
            return completed.returncode
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--changed", action="store_true", help="sélectionne selon Git (défaut)")
    mode.add_argument("--full", action="store_true", help="exécute la validation exhaustive")
    parser.add_argument("--list", action="store_true", help="affiche le plan sans l'exécuter")
    parser.add_argument("--json", action="store_true", help="sortie JSON; implique --list")
    parser.add_argument("--base", help="révision Git de base pour CI ou comparaison explicite")
    parser.add_argument(
        "--only",
        choices=("all", "python", "release", "engine"),
        default="all",
        help="limite l'exécution à un scope; utilisé notamment par la CI",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.full:
        plan = full_plan("demande explicite --full")
    else:
        try:
            plan = select_paths(collect_changed_paths(args.base))
        except (OSError, subprocess.CalledProcessError) as error:
            plan = full_plan(f"lecture Git impossible: {error}")
    if args.list or args.json:
        print_plan(plan, as_json=args.json, only=args.only)
        return 0
    return execute_plan(plan, args.only)


if __name__ == "__main__":
    raise SystemExit(main())
