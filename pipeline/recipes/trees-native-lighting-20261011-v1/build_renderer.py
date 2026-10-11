"""Build only the tree lighting delta on top of the exact installed AR3000 renderer."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = ROOT / "animations/batches/trees-native-lighting-20261011-v1"
BASE = ROOT / "maps/water-batches/runs/ar3000-water-runtime-fix-20261011-v1/runtime-src"
CANON = ROOT / "engine/InfinityEngine-Enhancer/source-patchee"
SRC = WORK / ".work/runtime-src"
BUILD = WORK / ".work/runtime-build"
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from workspace_paths import get_path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    game = get_path("bg2ee_game_root", required=True)
    baseline_sha = "3992155db599fcb106a8cbd71d65c46027dbff329c5066cd0d34483f9c8c8f88"
    assert sha(game/"InfinityEngine-Enhancer.dll") == baseline_sha
    assert not (HERE/"runtime.json").exists()
    changed = ["CMakeLists.txt", "src/iee/hooks.cpp", "src/iee/area_animation_x4_registry.cpp",
               "src/iee/area_animation_x4_registry.h"]
    added = ["src/iee/core/area_animation_lighting.h", "tests/area_animation_lighting_tests.cpp"]
    if "--resume" not in sys.argv:
        assert not SRC.exists()
        shutil.copytree(BASE, SRC)
        paths = [(CANON/name).relative_to(ROOT).as_posix() for name in changed]
        delta = subprocess.check_output(["git", "diff", "--", *paths], cwd=ROOT)
        patch = HERE/"runtime-delta.patch"
        patch.write_bytes(delta)
        subprocess.run(["git", "apply", "--check", "-p4", "--directory="+SRC.relative_to(ROOT).as_posix(),
                        str(patch)], cwd=ROOT, check=True)
        subprocess.run(["git", "apply", "-p4", "--directory="+SRC.relative_to(ROOT).as_posix(),
                        str(patch)], cwd=ROOT, check=True)
        for name in added:
            shutil.copy2(CANON/name, SRC/name)
    unchanged = 0
    for path in BASE.rglob("*"):
        if path.is_file() and path.relative_to(BASE).as_posix() not in changed:
            assert path.read_bytes() == (SRC/path.relative_to(BASE)).read_bytes()
            unchanged += 1
    cmake = "C:/Program Files/CMake/bin/cmake.exe"
    deps = CANON/"build-vs2019-30fps-multicycle/_deps"
    commands = [
        [cmake,"-S",str(SRC),"-B",str(BUILD),"-G","Visual Studio 16 2019","-A","x64",
         "-DBUILD_TESTING=ON","-DIEE_BUILD_WINDOWS_DLL=ON",f"-DPython3_EXECUTABLE={sys.executable}",
         *[f"-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+'-src')}" for n in ("spdlog","zlib","minhook")]],
        [cmake,"--build",str(BUILD),"--config","Release","--target",
         "InfinityEngine-Enhancer","iee_area_animation_lighting_tests","--parallel","6","--","/nodeReuse:false"],
        [str(BUILD/"Release/iee_area_animation_lighting_tests.exe")],
    ]
    with (HERE/"build.log").open("a" if "--resume" in sys.argv else "w", encoding="utf-8") as log:
        for label, command in zip(("configure","build","native lighting tests"),commands):
            print(label,flush=True)
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    old_header = BASE.parent/"runtime-build/generated/iee/water_route2_registry.generated.h"
    new_header = BUILD/"generated/iee/water_route2_registry.generated.h"
    assert old_header.read_bytes() == new_header.read_bytes(), "Preserve the exact AR3000 water contract"
    candidate = WORK/"candidate"
    candidate.mkdir()
    shutil.copy2(BUILD/"Release/InfinityEngine-Enhancer.dll",candidate/"InfinityEngine-Enhancer.dll")
    shutil.copy2(game/"InfinityEngine-Enhancer.ini",candidate/"InfinityEngine-Enhancer.ini")
    report = dict(schema="bg2-trees-native-lighting-renderer-v1",baseline_dll_sha256=baseline_sha,
        baseline_source=BASE.relative_to(ROOT).as_posix(),dll=(candidate/"InfinityEngine-Enhancer.dll").relative_to(ROOT).as_posix(),
        dll_sha256=sha(candidate/"InfinityEngine-Enhancer.dll"),ini_sha256=sha(candidate/"InfinityEngine-Enhancer.ini"),
        changed_source_files=changed+added,other_source_files_identical=unchanged,
        water_generated_header_identical=True,native_lighting_tests_passed=True,
        scope="Only unlit 1400T001-005; owner-scoped native palette transfer; alpha unchanged",
        qa_status="pending-user-ingame-test",release=False)
    (HERE/"runtime.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("Renderer candidate ready",flush=True)


if __name__ == "__main__":
    main()
