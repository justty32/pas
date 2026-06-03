#include <doctest/doctest.h>
#include <string>
#include <core/version.h>

TEST_CASE("version smoke test") {
    CHECK(!zone::version().empty());
    CHECK(zone::version() == "0.0.1-alpha");
}
