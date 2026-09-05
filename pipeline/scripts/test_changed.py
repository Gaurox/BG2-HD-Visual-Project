"""Plan test impact by default; execute only after explicit ``--run`` consent."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path
import re
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
RELEASE_AREA_ANIMATION = RELEASE_ROOT / "tools" / "Test-BG2HDAreaAnimationCandidate.ps1"
ANIMATION_CANDIDATES_PATH = (
    "releases/BG2-HD-Upscale/manifests/animation-release-candidates.json"
)
ANIMATION_QA_PREFIX = (
    "releases/BG2-HD-Upscale/manifests/animation-qa-approvals/"
)


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
    "workspace-command": TestGroup(
        "workspace-command",
        "python",
        ("pipeline.tests.test_workspace_command",),
    ),
    "workspace-paths": TestGroup(
        "workspace-paths",
        "python",
        ("pipeline.tests.test_workspace_paths",),
    ),
    "test-selection": TestGroup(
        "test-selection",
        "python",
        ("pipeline.tests.test_test_changed",),
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
            "pipeline.tests.test_animation_paths",
            "pipeline.tests.test_animation_release",
            "pipeline.tests.test_release_animation_delta",
            "pipeline.tests.test_animation_workflow",
            "pipeline.tests.test_animation_upscale_pipeline",
            "pipeline.tests.test_animation_interpolation_pipeline",
            "pipeline.tests.test_animation_upscale_30fps_v2",
            "pipeline.tests.test_animation_runtime_pack",
            "pipeline.tests.test_animation_pack_area_split",
            "pipeline.tests.test_combine_area_pack_splits",
        ),
    ),
    # The commands are generated per area from SelectionPlan.animation_areas.
    "animation-release": TestGroup("animation-release", "release"),
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
    "video-upscale": TestGroup(
        "video-upscale",
        "python",
        ("pipeline.tests.test_video_upscale_pipeline",),
    ),
    "video-interpolation": TestGroup(
        "video-interpolation",
        "python",
        ("pipeline.tests.test_video_interpolation_pipeline",),
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
    modules: tuple[str, ...] = ()


@dataclass(frozen=True)
class SelectionPlan:
    full: bool
    groups: tuple[str, ...]
    changed_paths: tuple[ChangedPath, ...]
    reasons: tuple[str, ...]
    extra_modules: tuple[str, ...] = ()
    selection_mode: str = "changed"
    animation_areas: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateAreaChanges:
    changed: tuple[str, ...]
    removed: tuple[str, ...]
    shared_changed: bool = False


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
    "animation_authority_lock.py",
    "animation_paths.py",
    "animation_release.py",
    "animation_workflow.py",
    "bam_export.py",
    "build_alpha_feather.py",
    "build_animation_runtime_pack.py",
    "build_blended_rgb_neutral_pack.py",
    "build_manual_alpha_mask_30fps_v2.py",
    "build_per_frame_spline_alpha_30fps_v2.py",
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
    "verify_animation_release_candidate.py",
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
VIDEO_UPSCALE_SCRIPTS = {
    "run_video_upscale.py",
}
VIDEO_INTERPOLATION_SCRIPTS = {
    "run_video_interpolation.py",
}
AREA_ID_PATTERN = re.compile(r"^(?:AR|OH)[0-9]{4}$")


def _matches(path: str, *patterns: str) -> bool:
    return any(fnmatchcase(path, pattern) for pattern in patterns)


def _is_documentation(path: str) -> bool:
    lowered = path.casefold()
    return lowered.endswith((".md", ".rst")) or path in {"AGENTS.md", "README.md"}


def _test_module(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    if _matches(normalized, "pipeline/tests/test_*.py"):
        return normalized[:-3].replace("/", ".")
    return None


def _qa_area(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    if not normalized.startswith(ANIMATION_QA_PREFIX):
        return None
    relative = normalized[len(ANIMATION_QA_PREFIX) :]
    parts = relative.split("/")
    if (
        len(parts) == 2
        and parts[1].endswith(".json")
        and AREA_ID_PATTERN.fullmatch(parts[0])
    ):
        return parts[0]
    return None


def _candidate_document(payload: object) -> tuple[dict[str, object], dict[str, object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("candidates"), list):
        raise ValueError("registre de candidats animation invalide")
    candidates: dict[str, object] = {}
    for candidate in payload["candidates"]:
        if not isinstance(candidate, dict):
            raise ValueError("entrée de candidat animation invalide")
        area = candidate.get("area")
        if not isinstance(area, str) or not AREA_ID_PATTERN.fullmatch(area):
            raise ValueError("zone de candidat animation invalide")
        if area in candidates:
            raise ValueError(f"zone de candidat animation dupliquée: {area}")
        candidates[area] = candidate
    shared = {
        key: value
        for key, value in payload.items()
        if key not in {"candidates", "generated_by"}
    }
    return candidates, shared


def candidate_area_changes(before: object, after: object) -> CandidateAreaChanges:
    before_candidates, before_shared = _candidate_document(before)
    after_candidates, after_shared = _candidate_document(after)
    changed = tuple(
        sorted(
            area
            for area, candidate in after_candidates.items()
            if before_candidates.get(area) != candidate
        )
    )
    removed = tuple(sorted(set(before_candidates) - set(after_candidates)))
    return CandidateAreaChanges(changed, removed, before_shared != after_shared)


def resolve_candidate_area_changes(base_revision: str | None = None) -> CandidateAreaChanges | None:
    """Compare the canonical register with Git; ``None`` requests the safe global gate."""

    try:
        current = json.loads((ROOT / ANIMATION_CANDIDATES_PATH).read_text(encoding="utf-8"))
        previous = json.loads(
            _run_git(("show", f"{base_revision or 'HEAD'}:{ANIMATION_CANDIDATES_PATH}"))
        )
        return candidate_area_changes(previous, current)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError):
        return None


def classify_path(path: str) -> Classification:
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    name = path.rsplit("/", 1)[-1]

    if _is_documentation(path):
        return Classification(("documentation",))
    module = _test_module(path)
    if module:
        return Classification(
            (),
            f"infrastructure de tests: {path}",
            (module,),
        )
    if path == "pipeline/scripts/test_changed.py" or _matches(path, ".github/workflows/**"):
        return Classification(
            ("test-selection",),
            f"sélecteur ou CI: {path}",
        )
    if path == "pipeline/scripts/workspace.py":
        return Classification(
            ("workspace-command",),
            f"orchestration workspace: {path}",
        )
    if path == "pipeline/scripts/progress_ui.py":
        return Classification(
            (),
            modules=("pipeline.tests.test_progress_ui",),
        )
    if path in {
        "pipeline/scripts/workspace_paths.py",
        "pipeline/scripts/WorkspacePaths.ps1",
    } or path.startswith("config/"):
        return Classification(
            ("workspace-paths",),
            f"configuration locale ou chemins: {path}",
        )
    if path in {
        "pipeline/scripts/asset_tracking_contract.py",
        "pipeline/scripts/build_global_asset_registry.py",
        "docs/asset-tracking-record.schema.json",
    }:
        return Classification(
            ("registry",),
            f"contrat ou générateur transversal du registre: {path}",
        )
    if path in {
        "pipeline/scripts/audit_workspace_integrity.py",
        "docs/workspace-run.schema.json",
    }:
        return Classification(
            ("integrity",),
            f"contrat ou audit transversal d'intégrité: {path}",
        )
    if path == "pipeline/scripts/build_graphics_inventory.py":
        return Classification(
            ("graphics-inventory",),
            f"générateur transversal d'inventaires graphiques: {path}",
        )
    if path in {".gitignore", "requirements.txt", "pipeline/scripts/bg2lib.py"} or _matches(
        path,
        "pyproject.toml",
        "pytest.ini",
        "tox.ini",
    ):
        return Classification((), f"changement transversal sans cible unique: {path}")
    if path == ANIMATION_CANDIDATES_PATH or _qa_area(path):
        return Classification(("animations", "animation-release", "registry", "integrity"))
    if path == "pipeline/scripts/animation_release.py":
        return Classification(("animations", "animation-release", "registry", "integrity"))
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
    if _matches(
        path,
        "animations/index/qa-decisions/**/*.json",
        "animations/index/selections/*.json",
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
    if (
        path.startswith("pipeline/scripts/") and name in VIDEO_UPSCALE_SCRIPTS
    ) or _matches(
        path,
        "pipeline/comfyui/workflows/SeedVR-Video-*.api.json",
    ):
        return Classification(("video-upscale",))
    if (
        path.startswith("pipeline/scripts/") and name in VIDEO_INTERPOLATION_SCRIPTS
    ) or _matches(
        path,
        "pipeline/topaz/recipes/Video-Interpolation-*.json",
    ):
        return Classification(("video-interpolation",))
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
        selection_mode="full",
    )


def select_paths(
    changed_paths: Iterable[ChangedPath],
    *,
    strict_targeted: bool = False,
    candidate_changes: CandidateAreaChanges | None = None,
) -> SelectionPlan:
    changed = tuple(changed_paths)
    reasons: list[str] = []
    selected = set() if strict_targeted else {"smoke"}
    extra_modules: list[str] = []
    animation_areas: set[str] = set()
    candidate_manifest_changed = False
    force_full = False
    for item in changed:
        status = item.status.upper()
        if status.startswith(("R", "C", "D")) and not strict_targeted:
            reasons.append(f"{status} impose la suite complète: {item.previous_path or item.path} -> {item.path}")
            force_full = True
            continue
        paths = [item.path]
        if strict_targeted and item.previous_path and item.previous_path not in paths:
            paths.append(item.previous_path)
        for path in paths:
            normalized_path = path.replace("\\", "/")
            area = _qa_area(normalized_path)
            if area:
                animation_areas.add(area)
            if normalized_path == ANIMATION_CANDIDATES_PATH:
                candidate_manifest_changed = True
            classification = classify_path(path)
            selected.update(classification.groups)
            for module in classification.modules:
                if module not in extra_modules:
                    extra_modules.append(module)
            if classification.force_full_reason:
                if strict_targeted:
                    reasons.append(
                        "ciblage strict sans escalade: " + classification.force_full_reason
                    )
                else:
                    reasons.append(classification.force_full_reason)
                    force_full = True
    if candidate_manifest_changed:
        if candidate_changes is None:
            selected.add("release")
            reasons.append(
                "diff du registre de candidats animation indéterminable: gate release globale"
            )
        else:
            animation_areas.update(candidate_changes.changed)
            if candidate_changes.removed or candidate_changes.shared_changed:
                selected.add("release")
                detail = "suppression de zone" if candidate_changes.removed else "métadonnées partagées"
                reasons.append(f"registre de candidats animation ({detail}): gate release globale")
    if force_full and not strict_targeted:
        return full_plan("fallback de sécurité", changed, reasons)
    ordered = tuple(name for name in GROUP_ORDER if name in selected)
    if not reasons:
        reasons.append(
            "sélection ciblée stricte par fichiers modifiés"
            if strict_targeted
            else "sélection par fichiers modifiés"
        )
    if strict_targeted and not ordered and not extra_modules:
        reasons.append("aucun test ciblé connu; ne rien exécuter automatiquement")
    return SelectionPlan(
        False,
        ordered,
        changed,
        tuple(reasons),
        tuple(extra_modules),
        "targeted" if strict_targeted else "changed",
        tuple(sorted(animation_areas)),
    )


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
    for module in plan.extra_modules:
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
                    (
                        sys.executable,
                        "pipeline/scripts/workspace.py",
                        "check",
                        "--scope",
                        "all",
                        "--after-full-tests",
                        "--run",
                    ),
                )
            )
        else:
            modules = python_modules_for(plan)
            if modules:
                commands.append(
                    Command(
                        "tests Python ciblés",
                        "python",
                        (sys.executable, "-m", "unittest", *modules),
                    )
                )

    if include_release:
        if plan.full or "release" in plan.groups:
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
        else:
            for area in plan.animation_areas:
                commands.append(
                    Command(
                        f"gate release animation {area}",
                        "release",
                        (
                            _powershell(),
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(RELEASE_AREA_ANIMATION),
                            "-Area",
                            area,
                            "-WorkspaceRoot",
                            str(ROOT),
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
        "mode": plan.selection_mode,
        "full": plan.full,
        "reasons": list(plan.reasons),
        "groups": list(plan.groups),
        "animation_areas": list(plan.animation_areas),
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
    print(f"mode: {plan.selection_mode}")
    for reason in plan.reasons:
        print(f"reason: {reason}")
    print("groups: " + (", ".join(plan.groups) if plan.groups else "none"))
    if plan.animation_areas:
        print("animation areas: " + ", ".join(plan.animation_areas))
    if plan.changed_paths:
        print("paths:")
        for item in plan.changed_paths:
            previous = f" {item.previous_path} ->" if item.previous_path else ""
            print(f"  {item.status}{previous} {item.path}")
    print("commands:")
    for command in commands_for(plan, only):
        print(f"  [{command.scope}] {command.label}: {_format_command(command.argv)}")


def execute_plan(
    plan: SelectionPlan,
    only: str = "all",
    *,
    keep_going: bool = False,
    runner: object = subprocess.run,
) -> int:
    failures: list[tuple[str, int, str]] = []
    for command in commands_for(plan, only):
        print(f"== {command.label} ==", flush=True)
        try:
            completed = runner(command.argv, cwd=ROOT, check=False)  # type: ignore[operator]
            code = int(completed.returncode)
            detail = f"code {code}"
        except OSError as error:
            code = 1
            detail = str(error) or type(error).__name__
        if code:
            failures.append((command.label, code, detail))
            print(
                f"FAILED [{command.scope}] {command.label}: {detail}",
                file=sys.stderr,
                flush=True,
            )
            if not keep_going:
                return code
    if failures:
        print("Failures:", file=sys.stderr)
        for label, _code, detail in failures:
            print(f"  - {label}: {detail}", file=sys.stderr)
        return failures[0][1]
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--changed",
        action="store_true",
        help="plan sûr selon Git; peut recommander full (défaut)",
    )
    mode.add_argument(
        "--targeted",
        action="store_true",
        help="plan strictement ciblé selon Git; ne devient jamais full",
    )
    mode.add_argument("--full", action="store_true", help="plan exhaustif explicite")
    parser.add_argument(
        "--run",
        action="store_true",
        help="exécute le plan; sans ce drapeau la commande affiche seulement le plan",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="continue les étapes indépendantes et récapitule tous les échecs",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="alias de compatibilité; la planification seule est maintenant le défaut",
    )
    parser.add_argument("--json", action="store_true", help="sortie JSON du plan")
    parser.add_argument("--base", help="révision Git de base pour CI ou comparaison explicite")
    parser.add_argument(
        "--only",
        choices=("all", "python", "release", "engine"),
        default="all",
        help="limite l'exécution à un scope; utilisé notamment par la CI",
    )
    args = parser.parse_args(argv)
    if args.json and args.run:
        parser.error("--json et --run sont incompatibles")
    if args.list and args.run:
        parser.error("--list et --run sont incompatibles")
    if args.keep_going and not args.run:
        parser.error("--keep-going exige --run")
    if args.run and not (args.changed or args.targeted or args.full):
        parser.error("--run exige un choix explicite: --changed, --targeted ou --full")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.full:
        plan = full_plan("demande explicite --full")
    else:
        try:
            changed_paths = collect_changed_paths(args.base)
            candidate_touched = any(
                item.path.replace("\\", "/") == ANIMATION_CANDIDATES_PATH
                or (item.previous_path or "").replace("\\", "/")
                == ANIMATION_CANDIDATES_PATH
                for item in changed_paths
            )
            plan = select_paths(
                changed_paths,
                strict_targeted=args.targeted,
                candidate_changes=(
                    resolve_candidate_area_changes(args.base) if candidate_touched else None
                ),
            )
        except (OSError, subprocess.CalledProcessError) as error:
            if args.targeted:
                plan = SelectionPlan(
                    False,
                    (),
                    (),
                    (
                        f"lecture Git impossible: {error}",
                        "aucun test ciblé connu; ne rien exécuter automatiquement",
                    ),
                    selection_mode="targeted",
                )
            else:
                plan = full_plan(f"lecture Git impossible: {error}")
    if not args.run:
        print_plan(plan, as_json=args.json, only=args.only)
        return 0
    if plan.full and not args.full:
        print_plan(plan, only=args.only)
        print(
            "REFUSED: le plan Git recommande full; utiliser --full --run après accord explicite.",
            file=sys.stderr,
        )
        return 2
    if not commands_for(plan, args.only):
        print_plan(plan, only=args.only)
        print("Aucun test ciblé exécutable pour ce scope.")
        return 0
    return execute_plan(plan, args.only, keep_going=args.keep_going)


if __name__ == "__main__":
    raise SystemExit(main())
