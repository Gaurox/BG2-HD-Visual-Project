"""Run only tests whose filename directly matches a changed Python script."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def normalize(path: str) -> str:
    value = path.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    candidate = Path(value)
    if not value or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"chemin hors dépôt: {path}")
    return value


def changed_paths(base: str | None = None) -> list[str]:
    def git_names(revision: str) -> list[str]:
        return subprocess.run(
            ["git", "-c", "core.quotepath=false", "diff", "--name-only", revision, "--"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.splitlines()

    tracked = git_names(f"{base}...HEAD") if base else []
    working = git_names("HEAD")
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.splitlines()
    return list(dict.fromkeys(filter(None, tracked + working + untracked)))


def modules_for(paths: list[str]) -> list[str]:
    modules = []
    for raw in paths:
        path = normalize(raw)
        if path.startswith("pipeline/tests/test_") and path.endswith(".py"):
            module = path[:-3].replace("/", ".")
        elif path.startswith("pipeline/scripts/") and path.endswith(".py"):
            test = ROOT / "pipeline" / "tests" / f"test_{Path(path).stem}.py"
            if not test.is_file():
                continue
            module = f"pipeline.tests.test_{Path(path).stem}"
        else:
            continue
        if module not in modules:
            modules.append(module)
    return modules


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--changed", action="store_true")
    mode.add_argument("--targeted", action="store_true")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--base")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.targeted and not args.path:
        parser.error("--targeted exige --path")
    if args.changed and args.path:
        parser.error("--path est réservé à --targeted")
    if args.targeted and args.base:
        parser.error("--base est réservé à --changed")
    if args.run and args.json:
        parser.error("--run et --json sont incompatibles")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    paths = args.path if args.targeted else changed_paths(args.base)
    modules = modules_for(paths)
    payload = {"paths": paths, "tests": modules}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("tests: " + (", ".join(modules) if modules else "none"))
    if args.run and modules:
        return subprocess.run(
            [sys.executable, "-m", "unittest", *modules], cwd=ROOT, check=False
        ).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
