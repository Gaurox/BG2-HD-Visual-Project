"""Assemble a strict install candidate from a Release bundle and an x4 effect pack.

The output is intentionally limited to the files owned by
``install_renderer_candidate.py``: DLL, active INI and one ``iee-assets/effects``
payload.  It never mutates a game directory.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from install_renderer_candidate import TransactionError, collect_candidate_files


DLL_NAME = "InfinityEngine-Enhancer.dll"
SAMPLE_INI_NAME = "InfinityEngine-Enhancer.sample.ini"
ACTIVE_INI_NAME = "InfinityEngine-Enhancer.ini"
EFFECTS_RELATIVE = Path("iee-assets") / "effects"


def enable_effect_animation(ini: Path) -> str:
    try:
        content = ini.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise TransactionError(f"INI sample illisible : {ini}") from exc
    updated, replacements = re.subn(
        r"(?mi)^(\s*EnableEffectAnimationX4\s*=\s*)false\s*$",
        r"\g<1>true",
        content,
    )
    if replacements != 1:
        raise TransactionError(
            "EnableEffectAnimationX4=false doit apparaître exactement une fois dans l'INI sample"
        )
    return updated


def require_empty_output(output: Path) -> Path:
    if output.is_symlink():
        raise TransactionError(f"sortie liée interdite : {output}")
    if output.exists():
        if not output.is_dir():
            raise TransactionError(f"sortie non répertoire : {output}")
        if any(output.iterdir()):
            raise TransactionError(f"sortie déjà occupée : {output}")
    else:
        output.mkdir(parents=True)
    return output.resolve(strict=True)


def assemble(
    release_bundle: Path, output: Path, effects_pack: Path | None = None
) -> tuple[str, ...]:
    if release_bundle.is_symlink():
        raise TransactionError(f"bundle Release lié interdit : {release_bundle}")
    bundle = release_bundle.resolve(strict=True)
    if not bundle.is_dir() or bundle.is_symlink():
        raise TransactionError(f"bundle Release invalide : {bundle}")
    dll = bundle / DLL_NAME
    sample_ini = bundle / SAMPLE_INI_NAME
    effects = (effects_pack if effects_pack is not None else bundle / EFFECTS_RELATIVE).resolve()
    if not dll.is_file() or dll.is_symlink():
        raise TransactionError(f"DLL Release absente : {dll}")
    if not effects.is_dir() or effects.is_symlink():
        raise TransactionError(f"pack d'effets Release absent : {effects}")
    target = require_empty_output(output)
    try:
        shutil.copy2(dll, target / DLL_NAME)
        (target / ACTIVE_INI_NAME).write_text(
            enable_effect_animation(sample_ini), encoding="utf-8"
        )
        shutil.copytree(effects, target / EFFECTS_RELATIVE)
        # README is documentation for the bundle, never a game payload.
        readme = target / EFFECTS_RELATIVE / "README.md"
        if readme.exists():
            readme.unlink()
        files, _ = collect_candidate_files(target)
        return tuple(file.name for file in files)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--effects-pack",
        type=Path,
        help="pack x4 ou 30 FPS externe au bundle Release ; le bundle est la source par défaut",
    )
    args = parser.parse_args(argv)
    try:
        files = assemble(args.release_bundle, args.output, args.effects_pack)
    except (OSError, TransactionError) as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 1
    print(f"candidat d'effets prêt : {args.output.resolve()}")
    print(f"fichiers gérés : {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
