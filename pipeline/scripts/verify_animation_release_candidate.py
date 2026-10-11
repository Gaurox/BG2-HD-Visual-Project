"""Verify one animation release candidate, its pack, provenance and QA proofs."""

from __future__ import annotations

import argparse
import contextlib
import functools
import json
import os
from pathlib import Path
from typing import Sequence

import animation_release


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vérifier un candidat de release animation")
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--animation-candidates-path", type=Path, required=True)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--area", action="append", help="zone ; option répétable pour un lot ciblé")
    scope.add_argument("--all", action="store_true", help="vérifier tous les candidats sous un même verrou")
    parser.add_argument("--animation-qa-approval-override-path", type=Path)
    parser.add_argument(
        "--allow-pending",
        action="store_true",
        help="valider les preuves d'un candidat en attente sans le promouvoir",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if (args.all or len(args.area or []) > 1) and args.animation_qa_approval_override_path:
        parser.error("un lot ne permet pas de remplacer une approbation QA individuelle")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        animation_release.configure_workspace_root(args.workspace_root)
        areas = [animation_release.normalize_area(value) for value in (args.area or [])]
        batch = args.all or len(areas) > 1
        with animation_release.workflow_lock(), contextlib.ExitStack() as cache:
            package_sync_marker = getattr(animation_release, "PACKAGE_SYNC_MARKER", None)
            animation_release.require(
                not animation_release.AUTHORITY_JOURNAL.exists()
                and not animation_release.PUBLICATION_JOURNAL.exists()
                and not (package_sync_marker and package_sync_marker.exists()),
                "transaction animation interrompue active; relancer sa commande d'origine avant la vérification",
            )
            if batch:
                # The authority lease keeps these physical inputs unchanged throughout
                # this read-only batch. Each candidate still follows the full verifier.
                workflow = animation_release.workflow_module()
                for module, names in [(animation_release, ("validate_pack", "validate_workflow_resref", "sha256_file")), (workflow, ("sha256", "_validate_runtime_pack"))]:
                    for name in names:
                        original = getattr(module, name)
                        cache.callback(setattr, module, name, original)
                        setattr(module, name, functools.lru_cache(None)(original))
            if args.all:
                document = animation_release.load_json(args.animation_candidates_path)
                areas = sorted(animation_release.normalize_area(item["area"]) for item in document["candidates"])
            animation_release.require(bool(areas), "aucun candidat à vérifier")
            results = []
            for checked_area in areas:
                results.append(animation_release.verify_release_candidate(
                    area=checked_area,
                    candidates_path=args.animation_candidates_path,
                    approval_override_path=args.animation_qa_approval_override_path,
                    allow_pending=args.allow_pending,
                ))
                if batch and not args.json:
                    print(f"OK preuves release animation : {checked_area}", flush=True)
            result = {"candidates": results, "count": len(results)} if batch else results[0]
        if args.json:
            print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
        elif not batch:
            print(f"OK preuves release animation : {areas[0]}")
        return 0
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
