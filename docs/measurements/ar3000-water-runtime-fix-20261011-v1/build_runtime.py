"""Preserve the installed renderer source; restore its current compiled water contract."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
WORK = ROOT / "maps/water-batches/runs" / HERE.name
PARENT = ROOT / "sprite/.work/monster-composite-fix-x2-20261011-v1/runtime-src"
CANONICAL = ROOT / "engine/InfinityEngine-Enhancer/source-patchee"
SRC = WORK / "runtime-src"
BUILD = WORK / "runtime-build"
EXPECTED = "28651777499111BE1D94CFD878947BCD67C0AD5062E2673F8991E153D6A46DCD"
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from workspace_paths import get_path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


game = get_path("bg2ee_game_root", required=True)
assert sha(game / "InfinityEngine-Enhancer.dll") == EXPECTED
resuming = "--resume" in sys.argv
if resuming:
    assert SRC.is_dir() and not (HERE / "runtime.json").exists()
else:
    assert not WORK.exists(), "choose a new run"
    shutil.copytree(PARENT, SRC)

# Keep the installed source's workspace adaptation and every C++ source unchanged.
name = "CMakeLists.txt"
before = (PARENT / name).read_text(encoding="utf-8")
canonical = (CANONICAL / name).read_text(encoding="utf-8")
start = before.index("    set(IEE_WATER_ROUTE2_REGISTRY\n")
end = before.index("    set(IEE_WATER_ROUTE2_PARENT_REGISTRY\n", start)
new_start = canonical.index("    set(IEE_WATER_ROUTE2_REGISTRY\n")
new_end = canonical.index("    set(IEE_WATER_ROUTE2_PARENT_REGISTRY\n", new_start)
(SRC / name).write_text(before[:start] + canonical[new_start:new_end] + before[end:],
                        encoding="utf-8", newline="\n")
shutil.copy2(CANONICAL / "tools/generate_water_route2_registry.py",
             SRC / "tools/generate_water_route2_registry.py")
changed = {"CMakeLists.txt", "tools/generate_water_route2_registry.py"}
patch = []
unchanged = 0
for path in PARENT.rglob("*"):
    if not path.is_file():
        continue
    relative = path.relative_to(PARENT).as_posix()
    if relative not in changed:
        assert sha(path) == sha(SRC / relative), relative
        unchanged += 1
    else:
        patch.extend(difflib.unified_diff(path.read_text(encoding="utf-8").splitlines(True),
                     (SRC / relative).read_text(encoding="utf-8").splitlines(True),
                     fromfile="installed/" + relative, tofile="candidate/" + relative))
(HERE / "runtime-delta.patch").write_text("".join(patch), encoding="utf-8", newline="\n")

cmake = "C:/Program Files/CMake/bin/cmake.exe"
deps = CANONICAL / "build-vs2019-30fps-multicycle/_deps"
commands = [
    [cmake, "-S", str(SRC), "-B", str(BUILD), "-G", "Visual Studio 16 2019", "-A", "x64",
     "-DBUILD_TESTING=ON", "-DIEE_BUILD_WINDOWS_DLL=ON", "-DFETCHCONTENT_UPDATES_DISCONNECTED=ON",
     f"-DPython3_EXECUTABLE={sys.executable}",
     *[f"-DFETCHCONTENT_SOURCE_DIR_{name.upper()}={deps/(name+'-src')}"
       for name in ("minhook", "spdlog", "zlib")]],
    [cmake, "--build", str(BUILD), "--config", "Release", "--target",
     "InfinityEngine-Enhancer", "iee_tests", "--parallel", "6", "--", "/nodeReuse:false"],
    [str(BUILD / "Release/iee_tests.exe")],
]
with (HERE / "runtime-build.log").open("a" if resuming else "w", encoding="utf-8") as log:
    for stage, command in zip(("configure", "build", "native-tests"), commands):
        print(stage, flush=True)
        subprocess.run(command, cwd=SRC, stdout=log, stderr=subprocess.STDOUT, check=True)

sys.path.insert(0, str(SRC / "tools"))
import generate_water_route2_registry as generator
registry = generator.default_input()
header = BUILD / "generated/iee/water_route2_registry.generated.h"
assert header.read_text(encoding="utf-8") == generator.generate(registry)
child, resolved = generator.load_registry(registry)
assert len(resolved["entries"]) == 188
ar3000 = [entry for entry in resolved["entries"] if entry["wed"]["resref"] == "AR3000"]
assert len(ar3000) == 8
for entry in ar3000:
    assert sha(game / "override" / (entry["wed"]["resref"] + ".WED")) == entry["wed"]["sha256"]
    for evidence in generator.file_records(entry):
        extension = ".TIS" if evidence["kind"] in ("BaseTis", "OverlayTis") else ".PVRZ"
        path = game / "override" / (evidence["resref"] + extension)
        assert path.stat().st_size == evidence["bytes"] and sha(path) == evidence["sha256"], path
    assert entry["local_art_opacity"]["target_draw_alpha"] == 160
candidate = WORK / "candidate"
candidate.mkdir()
shutil.copy2(BUILD / "Release/InfinityEngine-Enhancer.dll", candidate / "InfinityEngine-Enhancer.dll")
shutil.copy2(game / "InfinityEngine-Enhancer.ini", candidate / "InfinityEngine-Enhancer.ini")
report = dict(schema="bg2-water-runtime-recovery-candidate-v1", run=HERE.name,
    baseline_dll_sha256=EXPECTED, baseline_source=PARENT.relative_to(ROOT).as_posix(),
    dll=(candidate / "InfinityEngine-Enhancer.dll").relative_to(ROOT).as_posix(),
    dll_sha256=sha(candidate / "InfinityEngine-Enhancer.dll"),
    ini_sha256=sha(candidate / "InfinityEngine-Enhancer.ini"),
    registry=registry.relative_to(ROOT).as_posix(), registry_version=child["version"],
    registry_sha256_lf=hashlib.sha256(registry.read_text(encoding="utf-8").encode()).hexdigest().upper(),
    registry_entries=len(resolved["entries"]), ar3000_entries=len(ar3000),
    unchanged_source_files=unchanged, changed_source_files=sorted(changed),
    native_tests_passed=True, ar3000_file_evidence_matches=True,
    installation=False, ingame_QA=False, release=False)
(HERE / "runtime.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report), flush=True)
