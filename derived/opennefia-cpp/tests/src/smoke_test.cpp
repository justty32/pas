#include <doctest/doctest.h>
#include <string>
#include <core/version.h>

TEST_CASE("version smoke test") {
    CHECK(!opennefia::version().empty());
    CHECK(opennefia::version() == "0.0.1-alpha");
}
