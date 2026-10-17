"""Record this renderer fix's build/test output without launching the game."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "engine/InfinityEngine-Enhancer/installations/effects-gl-flush-state-20261017-v1"
name, expected, *command = sys.argv[1:]
OUTPUT.mkdir(parents=True, exist_ok=True)
result_path = OUTPUT / f"{name}.json"
if result_path.exists():
    raise SystemExit(f"Existing evidence: {result_path}; choose a new check name")
result = subprocess.run(command, cwd=ROOT, capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW)
log = OUTPUT / f"{name}.log"
log.write_bytes(result.stdout + b"\n--- stderr ---\n" + result.stderr)
sources = [
    "engine/InfinityEngine-Enhancer/source-patchee/src/iee/effect_animation_x4_registry.cpp",
    "engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/scoped_effect_gl_state.h",
    "engine/InfinityEngine-Enhancer/source-patchee/tests/effect_texture_cache_tests.cpp",
]
record = {
    "utc": datetime.now(timezone.utc).isoformat(), "command": command,
    "returncode": result.returncode, "expected_returncode": int(expected),
    "expected_result": result.returncode == int(expected),
    "log": log.relative_to(ROOT).as_posix(),
    "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest().upper() for p in sources},
    "game_executed": False,
}
result_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"check": name, "returncode": result.returncode,
                  "expected_result": record["expected_result"], "log": record["log"]}))
print((result.stdout + result.stderr).decode("utf-8", errors="replace")[-6000:])
raise SystemExit(0 if record["expected_result"] else 1)
