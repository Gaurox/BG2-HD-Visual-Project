cmake_minimum_required(VERSION 3.20)
project(effect_tile_sharing LANGUAGES CXX)
add_executable(effect_tile_sharing tile_sharing.cpp)
target_compile_features(effect_tile_sharing PRIVATE cxx_std_20)
