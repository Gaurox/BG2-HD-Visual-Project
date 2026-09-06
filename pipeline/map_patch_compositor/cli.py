"""CLI plan-only par défaut du compositeur de patch de carte."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

from . import area
from .core import CompositeError, compose, inspect_inputs, load_config


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recalage et compositing raster déterministes d'un patch dans une map.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("inspect", "lit/valide les entrées et affiche leurs preuves sans écrire"),
        ("plan", "valide entrées, configuration et destination sans écrire"),
        ("compose", "crée un nouveau run uniquement avec --run"),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--map", required=True, type=Path, help="image map source, lecture seule")
        command.add_argument("--patch", required=True, type=Path, help="image patch source, lecture seule")
        command.add_argument("--config", type=Path, help="surcharge JSON de defaults.json")
        if name in {"plan", "compose"}:
            command.add_argument("--output-run", type=Path, required=True, help="nouveau dossier de run, obligatoirement absent")
        if name == "compose":
            command.add_argument("--run", action="store_true", help="autorise l'écriture du nouveau run")
    area_plan = commands.add_parser("area-plan", help="résout la map x4 primaire d'une zone sans écrire")
    area_apply = commands.add_parser("area-apply", help="crée un nouveau raster dérivé pour une zone avec --run")
    for command in (area_plan, area_apply):
        command.add_argument("--area", required=True, help="zone BG2, par exemple AR3003")
        command.add_argument("--patch", required=True, type=Path, help="patch joint au chat, lecture seule")
        command.add_argument("--config", type=Path, help="surcharge JSON de defaults.json")
        command.add_argument("--base", choices=("base", "current"), default="current", help="base areas.csv ou sélection de patch courante")
        command.add_argument("--run-id", help="identifiant du nouveau run; proposé automatiquement sinon")
    area_apply.add_argument("--run", action="store_true", help="autorise la création du run dérivé")
    area_select = commands.add_parser("area-select", help="désigne un run validé comme raster courant avec --run")
    area_select.add_argument("--area", required=True, help="zone BG2, par exemple AR3003")
    area_select.add_argument("--run-id", required=True, help="run de patch terminé à désigner")
    area_select.add_argument("--run", action="store_true", help="autorise la mise à jour de la sélection courante")
    return parser


def _json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "area-plan":
            print(_json(area.area_plan(args.area, args.patch, args.config, base=args.base, run_id=args.run_id)), end="")
            return 0
        if args.command == "area-apply":
            if not args.run:
                raise CompositeError("area-apply reste plan-only sans --run ; utiliser area-plan")
            print(_json(area.apply_area_patch(args.area, args.patch, args.config, base=args.base, run_id=args.run_id)), end="")
            return 0
        if args.command == "area-select":
            if not args.run:
                raise CompositeError("area-select reste plan-only sans --run")
            print(_json(area.select_area_patch(args.area, args.run_id)), end="")
            return 0
        report = inspect_inputs(args.map, args.patch, args.config)
        if args.command == "inspect":
            print(_json(report), end="")
            return 0
        config = load_config(args.config)
        if args.command == "plan":
            output = args.output_run.resolve()
            report["output_run"] = output.as_posix()
            report["output_run_available"] = not output.exists() and not output.with_name(output.name + ".partial").exists()
            report["resolved_config_sha256"] = hashlib.sha256(
                json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            print(_json(report), end="")
            return 0
        if not args.run:
            raise CompositeError("compose reste plan-only sans --run")
        manifest = compose(args.map, args.patch, args.output_run, args.config)
        print(_json(manifest), end="")
        return 0
    except CompositeError as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return 2
