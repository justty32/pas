cmake_minimum_required(VERSION 3.17)
project(turnmap_cpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# MSVC：強制以 UTF-8 解析原始檔（原始碼含繁體中文字串）。
if(MSVC)
    add_compile_options(/utf-8)
endif()

add_executable(turnmap
    src/main.cpp
    src/tilemap.cpp
    src/pathfinding.cpp
    src/game.cpp
)
target_include_directories(turnmap PRIVATE include)

if(MSVC)
    target_compile_options(turnmap PRIVATE /W4)
else()
    target_compile_options(turnmap PRIVATE -Wall -Wextra -Wpedantic)
endif()
