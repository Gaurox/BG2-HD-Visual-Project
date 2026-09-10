#!/usr/bin/env python3
"""Build deterministic standalone shader-suite overrides from tracked parts."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "assets" / "shader-suite"
TEMPLATES = PARTS / "templates"
OUTPUT = ROOT / "assets" / "override"
COMMON_TOKEN = "@@IEE_CREATURE_HD_COMMON@@"
TARGETS = ("fpDraw.glsl", "fpSprite.glsl", "fpSELECT.glsl")


class BuildError(RuntimeError):
    pass


def render_shader(name: str) -> str:
    template = (TEMPLATES / name).read_text(encoding="utf-8")
    common = (PARTS / "creature-hd-common.glsl").read_text(encoding="utf-8").rstrip()
    if template.count(COMMON_TOKEN) != 1:
        raise BuildError(f"{name}: expected exactly one common-part token")
    rendered = template.replace(COMMON_TOKEN, common)
    if COMMON_TOKEN in rendered or "#version" in rendered:
        raise BuildError(f"{name}: invalid rendered source")
    return rendered.rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if tracked outputs differ")
    parser.add_argument("--run", action="store_true", help="write tracked outputs")
    args = parser.parse_args(argv)
    if args.check and args.run:
        parser.error("choose --check or --run")

    changed: list[str] = []
    rendered: dict[str, str] = {}
    for name in TARGETS:
        rendered[name] = render_shader(name)
        output = OUTPUT / name
        current = output.read_text(encoding="utf-8") if output.exists() else None
        if current != rendered[name]:
            changed.append(name)

    print(f"targets={len(TARGETS)}")
    print(f"changed={','.join(changed) if changed else '<none>'}")
    print(f"action={'write' if args.run else 'check' if args.check else 'plan-only'}")
    if args.check and changed:
        raise BuildError(f"stale shader outputs: {', '.join(changed)}")
    if args.run:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for name in changed:
            (OUTPUT / name).write_text(rendered[name], encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
