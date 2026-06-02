cmake_minimum_required(VERSION 3.14)
project(opennefia_cpp)

# CMake 4.0+ 不再接受 cmake_minimum_required(VERSION < 3.5)。
# 許多 FetchContent 依賴（doctest v2.4.11 等）仍用舊宣告；透過此變數相容。
if(NOT DEFINED CMAKE_POLICY_VERSION_MINIMUM)
    set(CMAKE_POLICY_VERSION_MINIMUM "3.5" CACHE STRING
        "Allow FetchContent deps that still declare cmake_minimum_required < 3.5 (CMake 4.0+ compat)")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# UTF-8 source files (Traditional Chinese comments); tell MSVC explicitly.
if(MSVC)
    add_compile_options(/utf-8)
endif()

if("${CMAKE_BUILD_TYPE}" STREQUAL "")
    set(CMAKE_BUILD_TYPE Debug)
endif()

set(BUILD_PATH ${PROJECT_BINARY_DIR}/bin)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY             "${BUILD_PATH}")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY             "${BUILD_PATH}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY             "${BUILD_PATH}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG       "${BUILD_PATH}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE     "${BUILD_PATH}")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_DEBUG       "${BUILD_PATH}")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE     "${BUILD_PATH}")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_DEBUG       "${BUILD_PATH}")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_RELEASE     "${BUILD_PATH}")

# ---- vendored dependencies (FetchContent) ----
include(FetchContent)

# 與 medps 對齊：EnTT v3.16.0、cereal v1.3.2
FetchContent_Declare(entt
    GIT_REPOSITORY https://github.com/skypjack/entt.git
    GIT_TAG        v3.16.0
    GIT_SHALLOW    TRUE
)
FetchContent_Declare(cereal
    GIT_REPOSITORY https://github.com/USCiLab/cereal.git
    GIT_TAG        v1.3.2
    GIT_SHALLOW    TRUE
)
# yaml-cpp 0.8.0：cmake_minimum_required(VERSION 2.8.12) → 靠頂部的
# CMAKE_POLICY_VERSION_MINIMUM=3.5 降級相容（同 doctest 的解法）。
FetchContent_Declare(yaml-cpp
    GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
    GIT_TAG        0.8.0
    GIT_SHALLOW    TRUE
)
FetchContent_Declare(spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG        v1.14.1
    GIT_SHALLOW    TRUE
)
FetchContent_Declare(doctest
    GIT_REPOSITORY https://github.com/doctest/doctest.git
    GIT_TAG        v2.4.11
    GIT_SHALLOW    TRUE
)

# cereal: 只要 header 介面，關掉所有附加建置
set(SKIP_PERFORMANCE_COMPARISON ON  CACHE BOOL "" FORCE)
set(BUILD_SANDBOX               OFF CACHE BOOL "" FORCE)
set(BUILD_DOC                   OFF CACHE BOOL "" FORCE)
set(WITH_WERROR                 OFF CACHE BOOL "" FORCE)
# yaml-cpp: 不建測試與工具
set(YAML_CPP_BUILD_TESTS        OFF CACHE BOOL "" FORCE)
set(YAML_CPP_BUILD_TOOLS        OFF CACHE BOOL "" FORCE)
# spdlog: 不建範例與測試
set(SPDLOG_BUILD_EXAMPLE        OFF CACHE BOOL "" FORCE)
set(SPDLOG_BUILD_TESTS          OFF CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(entt cereal yaml-cpp spdlog doctest)

# yaml-cpp 0.8.0 的 emitterutils.cpp 用了 uint16_t 卻沒 #include <cstdint>。
# 在 GCC 13+ / 新版 libstdc++（本機 GCC 16）下標頭不再間接帶入而編譯失敗；
# MSVC 與舊 GCC 因標頭傳遞鏈不同未觸發。對該目標強制前置 include 修正。
if(TARGET yaml-cpp AND (CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES "Clang"))
    target_compile_options(yaml-cpp PRIVATE -include cstdint)
endif()

# ---- opennefia_core（godot-free STATIC）----
set(SRC "${CMAKE_CURRENT_SOURCE_DIR}/src")
file(GLOB_RECURSE core_src
    "${SRC}/*.cpp" "${SRC}/*.hpp" "${SRC}/*.h"
)
# 核心編譯單元不得包含前端；/gbind/ 是未來前端綁定，本階段排除
list(FILTER core_src EXCLUDE REGEX "/gbind/")
source_group(TREE "${SRC}" FILES ${core_src})

add_library(opennefia_core STATIC ${core_src})
target_compile_features(opennefia_core PUBLIC cxx_std_20)
target_include_directories(opennefia_core PUBLIC "${SRC}")
target_link_libraries(opennefia_core PUBLIC
    EnTT::EnTT
    cereal::cereal
    yaml-cpp::yaml-cpp
    spdlog::spdlog
)

# ---- 測試 ----
include(CTest)
enable_testing()
add_subdirectory(tests)

# ---- 選用：Godot 4 GDExtension 前端綁定（暫緩，預設 OFF）----
option(OPENNEFIA_BUILD_GDEXTENSION
    "Build the Godot 4 GDExtension facade (src/gbind)" OFF)
if(OPENNEFIA_BUILD_GDEXTENSION)
    # 預設指向本 repo 的 projects/godot-cpp（derived/opennefia-cpp/ 往上兩層）；
    # 可用 -DGODOT_CPP_DIR=... 覆寫到其他 checkout。
    set(GODOT_CPP_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../projects/godot-cpp"
        CACHE PATH "Path to the godot-cpp checkout")
    add_subdirectory("${GODOT_CPP_DIR}" "${CMAKE_BINARY_DIR}/godot-cpp-build")

    file(GLOB_RECURSE gbind_src "${SRC}/gbind/*.cpp" "${SRC}/gbind/*.h")
    add_library(opennefia_gd SHARED ${gbind_src})
    set_target_properties(opennefia_gd PROPERTIES CXX_STANDARD 20)
    target_include_directories(opennefia_gd PRIVATE "${SRC}")
    target_link_libraries(opennefia_gd PRIVATE opennefia_core godot-cpp)
    # 資料目錄（原型 YAML 等）傳入編譯期常數
    target_compile_definitions(opennefia_gd PRIVATE
        OPENNEFIA_DATA_DIR="${CMAKE_SOURCE_DIR}/data"
    )
endif()
