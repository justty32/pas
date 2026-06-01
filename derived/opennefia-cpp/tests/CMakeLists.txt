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

# doctest 預設以前向宣告取代 <iosfwd>；MSVC 2022 + string_view 會因 ostream 不完整而報錯。
# 加此 define 讓 doctest 改用 #include <sstream>（完整標頭）。
target_compile_definitions(opennefia_test PRIVATE DOCTEST_CONFIG_USE_STD_HEADERS)

add_test(NAME opennefia_test COMMAND opennefia_test)
