cmake_minimum_required(VERSION 3.20)
project(BG2HDPayload LANGUAGES C CXX)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

set(ZLIB_LOCAL_SOURCE "" CACHE PATH "Local zlib source checkout")
set(ZLIB_BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(ZLIB_BUILD_SHARED OFF CACHE BOOL "" FORCE)
if(ZLIB_LOCAL_SOURCE)
    add_subdirectory("${ZLIB_LOCAL_SOURCE}" "${CMAKE_BINARY_DIR}/zlib")
else()
    include(FetchContent)
    FetchContent_Declare(zlib GIT_REPOSITORY https://github.com/madler/zlib.git
        GIT_TAG da607da739fa6047df13e66a2af6b8bec7c2a498)
    FetchContent_MakeAvailable(zlib)
endif()

add_executable(Expand-BG2HDPayload Expand-BG2HDPayload.cpp)
target_compile_features(Expand-BG2HDPayload PRIVATE cxx_std_20)
target_link_libraries(Expand-BG2HDPayload PRIVATE ZLIB::ZLIBSTATIC bcrypt)
