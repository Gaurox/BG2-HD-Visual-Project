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


# Python tests are selected as exact modules. Groups only represent non-Python gates.
GROUP_ORDER = ("animation-release", "release", "engine")


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


AREA_ID_PATTERN = re.compile(r"^(?:AR|OH)[0-9]{4}$")

SCRIPT_TEST_ALIASES = {
    "workspace.py": ("test_workspace_command",),
    "audit_workspace_integrity.py": ("test_workspace_integrity",),
    "build_global_asset_registry.py": ("test_global_asset_registry",),
    "build_graphics_inventory.py": ("test_graphics_inventory",),
    "sync_icon_processing.py": ("test_icon_processing",),
    "build_sprite_inventory.py": ("test_sprite_inventory",),
    "verify_historical_git_evidence.py": ("test_historical_git_evidence",),
    "animation_release.py": ("test_animation_release", "test_release_animation_delta"),
    "build_spline_top_reconstructed_alpha.py": ("test_spline_top_reconstructed_alpha",),
    "combine_area_pack_splits.py": ("test_combine_area_pack_splits",),
    "merge_area_pack_resources.py": ("test_combine_area_pack_splits",),
    "split_animation_pack_by_area.py": ("test_animation_pack_area_split",),
    "inject_build.py": ("test_map_build_transaction",),
    "run_animation_upscale.py": ("test_animation_upscale_pipeline",),
    "run_animation_interpolation.py": ("test_animation_interpolation_pipeline",),
    "run_animation_upscale_30fps_v2.py": ("test_animation_upscale_30fps_v2",),
    "run_creature_sprite_x2.py": ("test_creature_sprite_x2_pipeline",),
    "run_video_upscale.py": ("test_video_upscale_pipeline",),
    "run_video_interpolation.py": ("test_video_interpolation_pipeline",),
    "extract_area_animations.py": ("test_animation_inventory",),
    "list_animations.py": ("test_animation_inventory",),
    "Install-CreatureSprite-XN-Catalog-Test.ps1": ("test_creature_sprite_xn_catalog_install",),
    "Restore-CreatureSprite-XN-Catalog-Test.ps1": ("test_creature_sprite_xn_catalog_install",),
    "Install-AreaAnimation-AreaTest.ps1": ("test_area_animation_area_test_transaction",),
    "Restore-AreaAnimation-AreaTest.ps1": ("test_area_animation_area_test_transaction",),
}
PATH_TEST_ALIASES = {
    "pipeline/area-animation-area-test/area_animation_area_test.py": (
        "test_area_animation_area_test_transaction",
    ),
    "engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py": (
        "test_renderer_candidate_transaction",
    ),
}


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


def _direct_test_modules(path: str) -> tuple[str, ...]:
    normalized = path.replace("\\", "/")
    aliases = PATH_TEST_ALIASES.get(normalized)
    if normalized.startswith("pipeline/map_patch_compositor/"):
        return ("pipeline.tests.test_map_patch_compositor",)
    if aliases is None and normalized.startswith("pipeline/scripts/"):
        aliases = SCRIPT_TEST_ALIASES.get(normalized.rsplit("/", 1)[-1])
    if aliases:
        return tuple(f"pipeline.tests.{name}" for name in aliases)
    if not normalized.startswith("pipeline/scripts/") or not normalized.endswith(".py"):
        return ()
    stem = Path(normalized).stem
    test_path = ROOT / "pipeline" / "tests" / f"test_{stem}.py"
    if test_path.is_file():
        return (f"pipeline.tests.test_{stem}",)
    return ()


def _is_asset_data(path: str) -> bool:
    return path == "areas.csv" or _matches(
        path,
        "maps/**",
        "animations/**",
        "sprite/**",
        "graphics/**",
        "interface/**",
        "video/**",
        "icons/**",
        "cursors/**",
        "effects/**",
        "projectiles/**",
        "portraits/**",
        "portraits-recrutables/**",
        "asset-tracking/**",
    )


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
    if _is_documentation(path):
        return Classification(())
    module = _test_module(path)
    if module:
        return Classification((), modules=(module,))
    if path == "pipeline/scripts/test_changed.py" or _matches(path, ".github/workflows/**"):
        if path == "pipeline/scripts/test_changed.py":
            return Classification((), modules=("pipeline.tests.test_test_changed",))
        return Classification((), f"workflow CI transversal: {path}")
    if path in {
        "pipeline/scripts/WorkspacePaths.ps1",
    } or path.startswith("config/"):
        return Classification((), modules=("pipeline.tests.test_workspace_paths",))
    if path in {".gitignore", "requirements.txt", "pipeline/scripts/bg2lib.py"} or _matches(
        path,
        "pyproject.toml",
        "pytest.ini",
        "tox.ini",
    ):
        return Classification((), f"changement transversal sans cible unique: {path}")
    if path == ANIMATION_CANDIDATES_PATH or _qa_area(path):
        return Classification(("animation-release",))
    if path.startswith("releases/BG2-HD-Upscale/"):
        return Classification(("release",), f"release, Core ou packaging: {path}")

    direct_modules = _direct_test_modules(path)
    if direct_modules:
        return Classification((), modules=direct_modules)
    if path.startswith("engine/InfinityEngine-Enhancer/source-patchee/"):
        return Classification(("engine",), f"runtime moteur: {path}")

    if _is_asset_data(path):
        return Classification(())

    return Classification((), f"chemin inconnu: {path}")


def full_plan(
    reason: str,
    changed_paths: Iterable[ChangedPath] = (),
    additional_reasons: Iterable[str] = (),
) -> SelectionPlan:
    return SelectionPlan(
        full=True,
        groups=("release", "engine"),
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
    selected: set[str] = set()
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


def explicit_changed_paths(paths: Iterable[str]) -> tuple[ChangedPath, ...]:
    """Build an isolated selection without reading unrelated Git changes."""

    changed: list[ChangedPath] = []
    seen: set[str] = set()
    for raw_path in paths:
        normalized = raw_path.strip().replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        candidate = Path(normalized)
        if (
            not normalized
            or candidate.is_absolute()
            or ".." in candidate.parts
            or normalized.startswith("/")
        ):
            raise ValueError(f"--path exige un chemin relatif au dépôt: {raw_path!r}")
        if normalized not in seen:
            changed.append(ChangedPath("M", normalized))
            seen.add(normalized)
    return tuple(changed)


def python_modules_for(plan: SelectionPlan) -> tuple[str, ...]:
    return tuple(dict.fromkeys(plan.extra_modules))


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
        "--path",
        action="append",
        default=[],
        metavar="CHEMIN",
        help="cible ce seul chemin; répétable et réservé à --targeted",
    )
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
    if args.path and not args.targeted:
        parser.error("--path exige --targeted")
    if args.path and args.base:
        parser.error("--path et --base sont incompatibles")
    try:
        explicit_changed_paths(args.path)
    except ValueError as error:
        parser.error(str(error))
    if args.run and not (args.changed or args.targeted or args.full):
        parser.error("--run exige un choix explicite: --changed, --targeted ou --full")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.full:
        plan = full_plan("demande explicite --full")
    else:
        try:
            changed_paths = (
                explicit_changed_paths(args.path)
                if args.path
                else collect_changed_paths(args.base)
            )
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
