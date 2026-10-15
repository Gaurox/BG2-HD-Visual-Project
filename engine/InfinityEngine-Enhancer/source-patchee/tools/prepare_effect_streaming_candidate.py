"""Prepare DLL + INI for review; never install, probe processes, or start the game."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DLL = "InfinityEngine-Enhancer.dll"
INI = "InfinityEngine-Enhancer.ini"
DEFAULTS = {
    "EnableEffectAnimationStreaming": "true",
    "EnableEffectStreamingTrace": "false",
    "EffectCpuCacheMiB": "768", "EffectInFlightMiB": "32", "EffectHeadCacheMiB": "256",
    "EffectGpuCacheMiB": "288", "EffectMetadataMiB": "16", "EffectPackGiB": "512",
    "EffectMaxResources": "8192", "EffectPrefetchMs": "500",
}


def candidate_ini(text: str, backend: str = "streaming") -> str:
    values = dict(DEFAULTS)
    values["EnableEffectAnimationStreaming"] = "true" if backend == "streaming" else "false"
    result: list[str] = []
    seen: set[str] = set()
    shaders = False
    had_section = False
    keys = {key.lower(): key for key in values}
    newline = "\r\n" if "\r\n" in text else "\n"

    def append_missing() -> None:
        for key, value in values.items():
            if key.lower() not in seen:
                result.append(f"{key} = {value}{newline}")
                seen.add(key.lower())

    for line in text.splitlines(keepends=True):
        match = re.match(r"\s*\[([^]]+)]", line)
        if match:
            if shaders:
                if result and not result[-1].endswith(("\r", "\n")):
                    result[-1] += newline
                append_missing()
            shaders = match.group(1).lower() == "shaders"
            had_section |= shaders
        setting = re.match(r"\s*([^=;#]+?)\s*=", line) if shaders else None
        if setting and setting.group(1).strip().lower() in keys:
            key = keys[setting.group(1).strip().lower()]
            seen.add(key.lower())
            # Keep existing user budgets. Only backend selection is explicit.
            if key == "EnableEffectAnimationStreaming":
                line = f"{key} = {values[key]}{newline}"
        result.append(line)
    if shaders:
        if result and not result[-1].endswith(("\r", "\n")):
            result[-1] += newline
        append_missing()
    elif not had_section:
        result.append(f"{newline}[Shaders]{newline}")
        append_missing()
    return "".join(result)


def prepare(dll: Path, baseline_ini: Path, output: Path, backend: str = "streaming") -> dict:
    if backend not in {"streaming", "eager"}:
        raise ValueError("unknown backend")
    if output.exists() and any(output.iterdir()):
        raise ValueError("candidate directory is not empty; choose a new version")
    # Read before creating output: the installation is a read-only baseline.
    raw_ini = baseline_ini.read_bytes()
    text = raw_ini.decode("utf-8-sig")
    if dll.name.lower() != DLL.lower() or not dll.is_file():
        raise ValueError("compiled renderer DLL missing")
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(dll, output / DLL)
    encoded = candidate_ini(text, backend).encode("utf-8")
    if raw_ini.startswith(b"\xef\xbb\xbf"):
        encoded = b"\xef\xbb\xbf" + encoded
    (output / INI).write_bytes(encoded)
    report = {
        "kind": "effect-streaming-review-candidate", "backend": backend,
        "installed": False, "game_executed": False, "assets_changed": False,
        "files": {name: {"bytes": (output / name).stat().st_size,
                         "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest().upper()}
                  for name in (DLL, INI)},
        "reference": "docs/EFFETS_STREAMING_MEMOIRE_2026-10-15.md",
        "implementation": "engine/InfinityEngine-Enhancer/source-patchee/docs/effect-streaming.md",
    }
    (output / "candidate.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        "# Candidat effets streaming — non installé\n\n"
        "- DLL + INI uniquement ; les packs RGBA/BAM/VVC et shaders personnages sont conservés.\n"
        "- Budgets et autres réglages existants conservés ; backend sélectionné explicitement.\n"
        "- Retour eager : `EnableEffectAnimationStreaming = false`, au démarrage suivant.\n"
        "- Une bibliothèque >8 Gio ou >512 ressources exige aussi un ancien pack compatible pour eager.\n"
        "- Installation/restauration ultérieures : `tools/install_renderer_candidate.py`, uniquement sur demande.\n"
        "- Jeu et InfinityLoader fermés par l'utilisateur avant installation. Aucun lancement par l'agent.\n"
        "- QA ingame et cadence réelle : à effectuer par l'utilisateur ; aucune acceptation nouvelle déduite.\n",
        encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", type=Path, required=True)
    parser.add_argument("--baseline-ini", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("streaming", "eager"), default="streaming")
    args = parser.parse_args()
    baseline = args.baseline_ini
    if baseline is None:
        sys.path.insert(0, str(ROOT / "pipeline/scripts"))
        from workspace_paths import get_path
        baseline = get_path("bg2ee_game_root", required=True) / INI
    print(json.dumps(prepare(args.dll, baseline, args.output, args.backend), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
