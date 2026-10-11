"""Night-only T005 delta, derived from the exact installed tree-lighting source."""
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = ROOT / "animations/batches/1400t005-night-color-20261011-v1"
BASE = ROOT / "animations/batches/trees-native-lighting-20261011-v1/.work/runtime-src"
CANON = ROOT / "engine/InfinityEngine-Enhancer/source-patchee"
SRC = WORK / ".work/runtime-src"
BUILD = WORK / ".work/runtime-build"
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from workspace_paths import get_path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    game = get_path("bg2ee_game_root", required=True)
    baseline_sha = "27b600b3398a121a1369272c11656ef40cb28164e6cddd70ea206d33ab6472ac"
    assert sha(game / "InfinityEngine-Enhancer.dll") == baseline_sha
    assert not (HERE / "runtime.json").exists()
    changed = ["src/iee/hooks.cpp", "src/iee/core/area_animation_lighting.h",
               "tests/area_animation_lighting_tests.cpp"]
    if "--resume" not in sys.argv:
        assert not SRC.exists()
        shutil.copytree(BASE, SRC)
        delta = []
        for name in changed:
            before = (BASE / name).read_text(encoding="utf-8").splitlines(keepends=True)
            after = (CANON / name).read_text(encoding="utf-8").splitlines(keepends=True)
            delta.extend(difflib.unified_diff(before, after, fromfile="a/"+name, tofile="b/"+name))
            shutil.copy2(CANON / name, SRC / name)
        (HERE / "runtime-delta.patch").write_text("".join(delta), encoding="utf-8")
    unchanged = 0
    for path in BASE.rglob("*"):
        if path.is_file() and path.relative_to(BASE).as_posix() not in changed:
            assert path.read_bytes() == (SRC / path.relative_to(BASE)).read_bytes()
            unchanged += 1
    cmake = "C:/Program Files/CMake/bin/cmake.exe"
    deps = CANON / "build-vs2019-30fps-multicycle/_deps"
    commands = [
        [cmake, "-S", str(SRC), "-B", str(BUILD), "-G", "Visual Studio 16 2019", "-A", "x64",
         "-DBUILD_TESTING=ON", "-DIEE_BUILD_WINDOWS_DLL=ON", f"-DPython3_EXECUTABLE={sys.executable}",
         *[f"-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+'-src')}" for n in ("spdlog", "zlib", "minhook")]],
        [cmake, "--build", str(BUILD), "--config", "Release", "--target",
         "InfinityEngine-Enhancer", "iee_area_animation_lighting_tests", "--parallel", "6", "--", "/nodeReuse:false"],
        [str(BUILD / "Release/iee_area_animation_lighting_tests.exe")],
    ]
    with (HERE / "build.log").open("a" if "--resume" in sys.argv else "w", encoding="utf-8") as log:
        for label, command in zip(("configure", "build", "night-only tests"), commands):
            print(label, flush=True)
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    old_header = BASE.parent / "runtime-build/generated/iee/water_route2_registry.generated.h"
    new_header = BUILD / "generated/iee/water_route2_registry.generated.h"
    assert old_header.read_bytes() == new_header.read_bytes()
    candidate = WORK / "candidate"
    candidate.mkdir()
    shutil.copy2(BUILD / "Release/InfinityEngine-Enhancer.dll", candidate / "InfinityEngine-Enhancer.dll")
    shutil.copy2(game / "InfinityEngine-Enhancer.ini", candidate / "InfinityEngine-Enhancer.ini")
    report = dict(schema="bg2-t005-night-color-renderer-v1", baseline_dll_sha256=baseline_sha,
        baseline_source=BASE.relative_to(ROOT).as_posix(), dll=(candidate/"InfinityEngine-Enhancer.dll").relative_to(ROOT).as_posix(),
        dll_sha256=sha(candidate/"InfinityEngine-Enhancer.dll"), ini_sha256=sha(candidate/"InfinityEngine-Enhancer.ini"),
        changed_source_files=changed, source_sha256={n:sha(SRC/n) for n in changed},
        other_source_files_identical=unchanged, water_generated_header_identical=True,
        targeted_tests_passed=True, resref="1400T005", rgb_gains=[0.60,0.55,0.85],
        night_gate={"AR1400":"AR1400N", "AR1404":"AR1404"},
        scope="Attenuate final native RGB only for T005 in live night WED; day, other trees, alpha unchanged",
        qa_status="pending-user-ingame-test", release=False)
    (HERE/"runtime.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("Night-only renderer candidate ready",flush=True)


if __name__ == "__main__":
    main()
