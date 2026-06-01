cmake_minimum_required(VERSION 3.14)

set(SRC "${CMAKE_CURRENT_SOURCE_DIR}/src")
file(GLOB_RECURSE test_src "${SRC}/*.cpp")

add_executable(opennefia_test ${test_src})
target_compile_features(opennefia_test PRIVATE cxx_std_20)
target_link_libraries(opennefia_test PRIVATE
    opennefia_core
    doctest::doctest
)

if(MSVC)
    target_compile_options(opennefia_test PRIVATE /utf-8)
endif()

add_test(NAME opennefia_test COMMAND opennefia_test)
