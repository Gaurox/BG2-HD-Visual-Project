"""Build a run-local 0x6100 host control; engine source/DLL stay unchanged."""
import hashlib
import json
from pathlib import Path
import subprocess

RUN = Path(__file__).resolve().parent
ROOT = next(p for p in RUN.parents if (p / "pipeline/scripts/palette_playable.py").is_file())
ENGINE = ROOT / "engine/InfinityEngine-Enhancer/source-patchee"
PRIOR = ROOT / "build/palette-q3m-p3-20261001-v5-x4/cmake"
BUILD = ROOT / "build/q3m-6100-20261001-v1/native"


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    source = ENGINE / "tests/palette_fraction_tests.cpp"
    old = source.read_text(encoding="utf-8")
    start = old.index("void inspect_pack(")
    end = old.index("}  // namespace", start)
    control = old[start:end]
    replacements = {"0x6110": "0x6100", "CHFF4G12": "CHMF4G12", "WQNMCG1": "WQLMCG1", "WQNJ8G1": "WQLJ8G1", "WQNC2G1": "WQLC2G1"}
    for before, after in replacements.items():
        assert before in control, before
        control = control.replace(before, after)
    modified = old[:start] + control + old[end:]
    provenance = RUN / "provenance"
    provenance.mkdir(exist_ok=True)
    target = provenance / "palette_fraction_tests_6100.cpp"
    with target.open("w", encoding="utf-8", newline="\n") as f:
        f.write(modified)
    dependency = ROOT / "build/palette-q3m-p2-20260930-v1/dependencies"
    script = f'''cmake_minimum_required(VERSION 3.20)
project(q3m_6100_host_control LANGUAGES CXX)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
add_executable(q3m_6100_palette_tests
  "{target.as_posix()}"
  "{(ENGINE / 'src/iee/creature_sprite_x2.cpp').as_posix()}"
  "{(ENGINE / 'src/iee/game/opengl_types.cpp').as_posix()}")
target_compile_features(q3m_6100_palette_tests PRIVATE cxx_std_20)
target_compile_definitions(q3m_6100_palette_tests PRIVATE NOMINMAX SPDLOG_COMPILED_LIB)
target_compile_options(q3m_6100_palette_tests PRIVATE /utf-8)
target_include_directories(q3m_6100_palette_tests PRIVATE
  "{(ENGINE / 'src').as_posix()}" "{(PRIOR / 'generated').as_posix()}"
  "{(dependency / 'spdlog/include').as_posix()}"
  "{(PRIOR / '_deps/zlib-build').as_posix()}" "{(dependency / 'zlib').as_posix()}")
target_link_libraries(q3m_6100_palette_tests PRIVATE
  "{(PRIOR / 'Release/iee_common.lib').as_posix()}"
  "{(PRIOR / '_deps/spdlog-build/Release/spdlog.lib').as_posix()}"
  "{(PRIOR / '_deps/zlib-build/Release/zs.lib').as_posix()}"
  opengl32 Cabinet bcrypt version psapi)
'''
    (provenance / "CMakeLists.txt").write_text(script, encoding="utf-8")
    with (RUN / "captures/native-build.log").open("ab") as log:
        for command in (["cmake", "-S", str(provenance), "-B", str(BUILD), "-G", "Visual Studio 16 2019", "-A", "x64"],
                        ["cmake", "--build", str(BUILD), "--config", "Release", "--target", "q3m_6100_palette_tests", "--parallel", "2"]):
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    proof = dict(schema="bg2-q3m-run-local-native-control-v1", source=source.relative_to(ROOT).as_posix(),
                 source_sha256=sha(source), adapted_source=target.relative_to(RUN).as_posix(),
                 adapted_source_sha256=sha(target), replacements_in_inspect_pack_only=replacements,
                 executable=(BUILD / "Release/q3m_6100_palette_tests.exe").relative_to(ROOT).as_posix(),
                 executable_sha256=sha(BUILD / "Release/q3m_6100_palette_tests.exe"),
                 engine_source_sha256=sha(ENGINE / "src/iee/creature_sprite_x2.cpp"),
                 common_library_sha256=sha(PRIOR / "Release/iee_common.lib"), dll_modified=False)
    (RUN / "native-control.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(proof), flush=True)


if __name__ == "__main__":
    main()
