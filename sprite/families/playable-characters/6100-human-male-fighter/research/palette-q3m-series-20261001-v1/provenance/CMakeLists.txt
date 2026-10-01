cmake_minimum_required(VERSION 3.20)
project(q3m_6100_host_control LANGUAGES CXX)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
add_executable(q3m_6100_palette_tests
  "G:/AI/BG2_Upscale/sprite/families/playable-characters/6100-human-male-fighter/research/palette-q3m-series-20261001-v1/provenance/palette_fraction_tests_6100.cpp"
  "G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp"
  "G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/opengl_types.cpp")
target_compile_features(q3m_6100_palette_tests PRIVATE cxx_std_20)
target_compile_definitions(q3m_6100_palette_tests PRIVATE NOMINMAX SPDLOG_COMPILED_LIB)
target_compile_options(q3m_6100_palette_tests PRIVATE /utf-8)
target_include_directories(q3m_6100_palette_tests PRIVATE
  "G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src" "G:/AI/BG2_Upscale/build/palette-q3m-p3-20261001-v5-x4/cmake/generated"
  "G:/AI/BG2_Upscale/build/palette-q3m-p2-20260930-v1/dependencies/spdlog/include"
  "G:/AI/BG2_Upscale/build/palette-q3m-p3-20261001-v5-x4/cmake/_deps/zlib-build" "G:/AI/BG2_Upscale/build/palette-q3m-p2-20260930-v1/dependencies/zlib")
target_link_libraries(q3m_6100_palette_tests PRIVATE
  "G:/AI/BG2_Upscale/build/palette-q3m-p3-20261001-v5-x4/cmake/Release/iee_common.lib"
  "G:/AI/BG2_Upscale/build/palette-q3m-p3-20261001-v5-x4/cmake/_deps/spdlog-build/Release/spdlog.lib"
  "G:/AI/BG2_Upscale/build/palette-q3m-p3-20261001-v5-x4/cmake/_deps/zlib-build/Release/zs.lib"
  opengl32 Cabinet bcrypt version psapi)
