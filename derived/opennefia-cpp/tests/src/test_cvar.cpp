#include <doctest/doctest.h>
#include <core/cvar/cvar_registry.h>
#include <filesystem>
#include <fstream>

// ==============================================================
// CvarRegistry — 型付き設定変数レジストリ
// ==============================================================

TEST_CASE("CvarRegistry — 基本 get/set（四種型別）") {
    opennefia::CvarRegistry cvars;
    cvars.reg<int>        ("game.map_width", 60,       "地圖寬度");
    cvars.reg<float>      ("game.speed",     1.5f,     "速度係數");
    cvars.reg<bool>       ("game.debug",     false,    "除錯模式");
    cvars.reg<std::string>("game.name",      "opennefia");

    CHECK(cvars.get<int>        ("game.map_width") == 60);
    CHECK(cvars.get<float>      ("game.speed")     == doctest::Approx(1.5f));
    CHECK(cvars.get<bool>       ("game.debug")     == false);
    CHECK(cvars.get<std::string>("game.name")      == "opennefia");

    cvars.set<int>        ("game.map_width", 80);
    cvars.set<float>      ("game.speed",     2.0f);
    cvars.set<bool>       ("game.debug",     true);
    cvars.set<std::string>("game.name",      "hello");

    CHECK(cvars.get<int>        ("game.map_width") == 80);
    CHECK(cvars.get<float>      ("game.speed")     == doctest::Approx(2.0f));
    CHECK(cvars.get<bool>       ("game.debug")     == true);
    CHECK(cvars.get<std::string>("game.name")      == "hello");
}

TEST_CASE("CvarRegistry — reset 單一 / reset_all") {
    opennefia::CvarRegistry cvars;
    cvars.reg<int>("a", 5);
    cvars.reg<int>("b", 10);

    cvars.set<int>("a", 99);
    cvars.set<int>("b", 88);
    CHECK(cvars.get<int>("a") == 99);

    cvars.reset("a");
    CHECK(cvars.get<int>("a") == 5);   // a 回預設
    CHECK(cvars.get<int>("b") == 88);  // b 不受影響

    cvars.reset_all();
    CHECK(cvars.get<int>("b") == 10);  // b 也回預設
}

TEST_CASE("CvarRegistry — 未知 key 丟 out_of_range") {
    opennefia::CvarRegistry cvars;
    CHECK_THROWS_AS(cvars.get<int>("no.such"),    std::out_of_range);
    CHECK_THROWS_AS(cvars.set<int>("no.such", 1), std::out_of_range);
    CHECK_FALSE(cvars.has("no.such"));
}

TEST_CASE("CvarRegistry — YAML 存讀 round-trip") {
    const std::string path = "/tmp/opennefia_cvar_test.yaml";

    // 存
    {
        opennefia::CvarRegistry cvars;
        cvars.reg<int>        ("game.map_width", 60);
        cvars.reg<float>      ("game.speed",     1.0f);
        cvars.reg<bool>       ("game.debug",     false);
        cvars.reg<std::string>("game.name",      "default");
        cvars.set<int>        ("game.map_width", 80);
        cvars.set<float>      ("game.speed",     3.14f);
        cvars.set<bool>       ("game.debug",     true);
        cvars.set<std::string>("game.name",      "saved");
        cvars.save(path);
    }
    // 讀
    {
        opennefia::CvarRegistry cvars;
        cvars.reg<int>        ("game.map_width", 60);
        cvars.reg<float>      ("game.speed",     1.0f);
        cvars.reg<bool>       ("game.debug",     false);
        cvars.reg<std::string>("game.name",      "default");
        cvars.load(path);
        CHECK(cvars.get<int>        ("game.map_width") == 80);
        CHECK(cvars.get<float>      ("game.speed")     == doctest::Approx(3.14f));
        CHECK(cvars.get<bool>       ("game.debug")     == true);
        CHECK(cvars.get<std::string>("game.name")      == "saved");
    }
    std::filesystem::remove(path);
}

TEST_CASE("CvarRegistry — load 不存在的檔 = no-op（保留 defaults）") {
    opennefia::CvarRegistry cvars;
    cvars.reg<int>("x", 42);
    cvars.load("/tmp/opennefia_nonexistent_cvar.yaml");  // 不應丟例外
    CHECK(cvars.get<int>("x") == 42);
}

TEST_CASE("CvarRegistry — load 時未知 key 靜默略過") {
    const std::string path = "/tmp/opennefia_cvar_test3.yaml";
    {
        std::ofstream f(path);
        f << "known.key: 99\nunknown.key: 123\n";
    }
    opennefia::CvarRegistry cvars;
    cvars.reg<int>("known.key", 0);
    cvars.load(path);
    CHECK(cvars.get<int>("known.key") == 99);
    CHECK_FALSE(cvars.has("unknown.key"));
    std::filesystem::remove(path);
}
