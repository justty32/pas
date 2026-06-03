cmake_minimum_required(VERSION 3.14)

set(SRC "${CMAKE_CURRENT_SOURCE_DIR}/src")
file(GLOB_RECURSE test_src "${SRC}/*.cpp")

add_executable(zone_test ${test_src})
target_compile_features(zone_test PRIVATE cxx_std_20)
target_link_libraries(zone_test PRIVATE
    zone_core
    doctest::doctest
)

if(MSVC)
    target_compile_options(zone_test PRIVATE /utf-8)
endif()

# doctest 預設以前向宣告取代 <iosfwd>；MSVC 2022 + string_view 會因 ostream 不完整而報錯。
# 加此 define 讓 doctest 改用 #include <sstream>（完整標頭）。
target_compile_definitions(zone_test PRIVATE DOCTEST_CONFIG_USE_STD_HEADERS)

# 測試用：資料檔路徑（源碼目錄的 data/）傳入編譯期常數，讓測試直接讀源碼中的 YAML 夾具
target_compile_definitions(zone_test PRIVATE
    ZONE_TEST_DATA_DIR="${CMAKE_SOURCE_DIR}/data"
)

add_test(NAME zone_test COMMAND zone_test)
