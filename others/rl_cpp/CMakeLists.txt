cmake_minimum_required(VERSION 3.17)
project(rl_cpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 學習用專案：示範程式跑大量蒙地卡羅實驗，預設用 Release 才不會慢。
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# MSVC：強制 UTF-8 解析原始檔（必須在 add_library/add_executable 之前）
if(MSVC)
    add_compile_options(/utf-8)
endif()

# ── 核心函式庫（純 C++ 標準庫，零第三方相依）─────────────────────
# 每完成一個 milestone 就把對應的 .cpp 加進來。
set(RL_SOURCES
    src/bandit.cpp
    src/bandit_agents.cpp
)

add_library(rl STATIC ${RL_SOURCES})
target_include_directories(rl PUBLIC include)

if(MSVC)
    target_compile_options(rl PRIVATE /W4)
else()
    target_compile_options(rl PRIVATE -Wall -Wextra -Wpedantic)
endif()

# ── 單元測試 ─────────────────────────────────────────────────────
enable_testing()
add_executable(rl_tests tests/main.cpp)
target_link_libraries(rl_tests PRIVATE rl)
add_test(NAME rl_tests COMMAND rl_tests)

# ── 示範程式（每個 milestone 一支，重現經典實驗結果）─────────────
add_executable(bandit_demo demos/bandit_demo.cpp)
target_link_libraries(bandit_demo PRIVATE rl)
