"""Verify one animation release candidate, its pack, provenance and QA proofs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

import animation_release


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vérifier un candidat de release animation")
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--animation-candidates-path", type=Path, required=True)
    parser.add_argument("--area", required=True)
    parser.add_argument("--animation-qa-approval-override-path", type=Path)
    parser.add_argument(
        "--allow-pending",
        action="store_true",
        help="valider les preuves d'un candidat en attente sans le promouvoir",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        animation_release.configure_workspace_root(args.workspace_root)
        area = animation_release.normalize_area(args.area)
        with animation_release.workflow_lock():
            animation_release.require(
                not animation_release.AUTHORITY_JOURNAL.exists()
                and not animation_release.PUBLICATION_JOURNAL.exists()
                and not animation_release.PACKAGE_SYNC_MARKER.exists(),
                "transaction animation interrompue active; relancer sa commande d'origine avant la vérification",
            )
            result = animation_release.verify_release_candidate(
                area=area,
                candidates_path=args.animation_candidates_path,
                approval_override_path=args.animation_qa_approval_override_path,
                allow_pending=args.allow_pending,
            )
        if args.json:
            print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
        else:
            print(f"OK preuves release animation : {area}")
        return 0
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
