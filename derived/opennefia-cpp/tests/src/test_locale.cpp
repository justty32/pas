#include <doctest/doctest.h>
#include <core/locale/locale_registry.h>
#include <filesystem>
#include <fstream>

// ==============================================================
// LocaleRegistry — 在地化字串查找與占位符替換
// ==============================================================

// 建立測試用語言檔（寫入 /tmp）
static std::string write_test_yaml() {
    const std::string path = "/tmp/opennefia_locale_test.yaml";
    std::ofstream f(path);
    f << "npc.putit: \"普提特\"\n"
      << "npc.warrior: \"戰士\"\n"
      << "item.health_potion: \"治癒藥草\"\n"
      << "msg.npc_died: \"{name} 倒下了！\"\n"
      << "msg.floor: \"第 {floor} 層\"\n";
    return path;
}

TEST_CASE("LocaleRegistry — 基本查找") {
    opennefia::LocaleRegistry locale;
    std::string path = write_test_yaml();
    locale.load(path);

    CHECK(locale.get("npc.putit")         == "普提特");
    CHECK(locale.get("npc.warrior")       == "戰士");
    CHECK(locale.get("item.health_potion") == "治癒藥草");

    std::filesystem::remove(path);
}

TEST_CASE("LocaleRegistry — 找不到 key 時回傳 key 本身（fallback）") {
    opennefia::LocaleRegistry locale;
    CHECK(locale.get("no.such.key") == "no.such.key");
    CHECK_FALSE(locale.has("no.such.key"));
}

TEST_CASE("LocaleRegistry — {var} 占位符替換") {
    opennefia::LocaleRegistry locale;
    std::string path = write_test_yaml();
    locale.load(path);

    auto result = locale.get("msg.npc_died", {{"name", "普提特"}});
    CHECK(result == "普提特 倒下了！");

    auto floor = locale.get("msg.floor", {{"floor", "3"}});
    CHECK(floor == "第 3 層");

    std::filesystem::remove(path);
}

TEST_CASE("LocaleRegistry — 找不到的占位符保留原樣") {
    opennefia::LocaleRegistry locale;
    std::string path = write_test_yaml();
    locale.load(path);

    // "name" 有，"missing" 無 → {missing} 保留
    auto result = locale.get("msg.npc_died", {{"missing_var", "x"}});
    CHECK(result == "{name} 倒下了！");  // {name} 沒被替換，保留原樣

    std::filesystem::remove(path);
}

TEST_CASE("LocaleRegistry — load 不存在的檔 = no-op") {
    opennefia::LocaleRegistry locale;
    locale.load("/tmp/opennefia_nonexistent_locale.yaml");  // 不應丟例外
    CHECK_FALSE(locale.has("npc.putit"));
}

TEST_CASE("LocaleRegistry — 多次 load 後者覆蓋前者") {
    const std::string path1 = "/tmp/opennefia_locale_a.yaml";
    const std::string path2 = "/tmp/opennefia_locale_b.yaml";
    { std::ofstream f(path1); f << "key: \"first\"\n"; }
    { std::ofstream f(path2); f << "key: \"second\"\n"; }

    opennefia::LocaleRegistry locale;
    locale.load(path1);
    CHECK(locale.get("key") == "first");
    locale.load(path2);
    CHECK(locale.get("key") == "second");  // path2 覆蓋 path1

    std::filesystem::remove(path1);
    std::filesystem::remove(path2);
}
