#include <doctest/doctest.h>
#include <string>
#include <sstream>
#include <filesystem>
#include <core/serialize/save_load.h>
#include <core/serialize/save_store.h>
#include <core/components/spatial_component.h>
#include <core/components/hero_component.h>
#include <core/components/actor_component.h>

namespace fs = std::filesystem;
namespace ser = zone::serialize;

// ---- 工具：快速建有 Spatial 的實體 -----------------------------------------
static entt::entity make_spatial_entity(entt::registry& reg, int x, int y,
                                        entt::entity parent = entt::null)
{
    auto e = reg.create();
    reg.emplace<zone::SpatialComponent>(e, zone::SpatialComponent{x, y, parent});
    return e;
}

// ==============================================================
// 基礎 stream round-trip：SpatialComponent 座標
// ==============================================================
TEST_CASE("序列化 — stream round-trip：SpatialComponent") {
    entt::registry reg;
    auto e1 = make_spatial_entity(reg, 3, 7);
    auto e2 = make_spatial_entity(reg, 9, 2);
    (void)e1; (void)e2;

    std::ostringstream oss;
    ser::save(reg, oss);

    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    int count = 0;
    reg.view<zone::SpatialComponent>().each(
        [&](entt::entity, const zone::SpatialComponent&) { ++count; }
    );
    CHECK(count == 2);
}

TEST_CASE("序列化 — stream round-trip：SpatialComponent 座標值") {
    entt::registry reg;
    make_spatial_entity(reg, 7, 13);

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    int found_x = -1, found_y = -1;
    reg.view<zone::SpatialComponent>().each(
        [&](entt::entity, const zone::SpatialComponent& s) {
            found_x = s.x;
            found_y = s.y;
        }
    );
    CHECK(found_x == 7);
    CHECK(found_y == 13);
}

// ==============================================================
// parent entity 引用 round-trip（entt::entity 強型別 enum）
// ==============================================================
TEST_CASE("序列化 — SpatialComponent.parent entt::entity round-trip") {
    entt::registry reg;
    auto parent_e = make_spatial_entity(reg, 10, 20);
    auto child_e  = reg.create();
    reg.emplace<zone::SpatialComponent>(child_e,
        zone::SpatialComponent{11, 21, parent_e});
    reg.emplace<zone::HeroComponent>(parent_e);  // 用 HeroComponent 標記 parent

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    // 找出 parent（有 HeroComponent）和 child（有 Spatial 且 parent != null）
    entt::entity restored_parent = entt::null;
    for (auto e : reg.view<zone::HeroComponent, zone::SpatialComponent>()) {
        restored_parent = e; break;
    }

    entt::entity restored_child = entt::null;
    reg.view<zone::SpatialComponent>().each(
        [&](entt::entity e, const zone::SpatialComponent& s) {
            bool has_parent = (s.parent != entt::null);
            if (has_parent) restored_child = e;
        }
    );

    bool parent_found = (restored_parent != entt::null);
    bool child_found  = (restored_child  != entt::null);
    REQUIRE(parent_found);
    REQUIRE(child_found);

    const auto& child_sp = reg.get<zone::SpatialComponent>(restored_child);
    CHECK(child_sp.x == 11);
    CHECK(child_sp.y == 21);
    bool parent_ref_ok = (child_sp.parent == restored_parent);
    CHECK(parent_ref_ok);
}

// ==============================================================
// 空 registry round-trip（不應崩潰）
// ==============================================================
TEST_CASE("序列化 — 空 registry round-trip") {
    entt::registry reg;
    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    int count = 0;
    reg.view<zone::SpatialComponent>().each(
        [&](entt::entity, const zone::SpatialComponent&) { ++count; }
    );
    CHECK(count == 0);
}

// ==============================================================
// 只有 HeroComponent，無 SpatialComponent
// ==============================================================
TEST_CASE("序列化 — 只有 HeroComponent，無 SpatialComponent") {
    entt::registry reg;
    auto e = reg.create();
    reg.emplace<zone::HeroComponent>(e);
    // 刻意不加 SpatialComponent

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    bool found = false;
    for (auto e2 : reg.view<zone::HeroComponent>()) {
        found = true;
        CHECK_FALSE(reg.all_of<zone::SpatialComponent>(e2));
    }
    CHECK(found);
}

// ==============================================================
// 檔案 API（直接存路徑）
// ==============================================================
TEST_CASE("序列化 — 直接路徑 save/load file") {
    auto tmp = fs::temp_directory_path() / "zone_test_savefile.bin";

    entt::registry reg;
    auto e = make_spatial_entity(reg, 3, 7);
    reg.emplace<zone::HeroComponent>(e);

    ser::save(reg, tmp);
    reg = entt::registry{};
    ser::load(reg, tmp);

    bool found = false;
    for (auto e2 : reg.view<zone::HeroComponent, zone::SpatialComponent>()) {
        found = true;
        const auto& s = reg.get<zone::SpatialComponent>(e2);
        CHECK(s.x == 3);
        CHECK(s.y == 7);
    }
    CHECK(found);

    fs::remove(tmp);
}

// ==============================================================
// FolderSaveStore round-trip
// ==============================================================
TEST_CASE("序列化 — FolderSaveStore save/load slot") {
    auto tmp_dir = fs::temp_directory_path() / "zone_test_store";
    fs::create_directories(tmp_dir);

    ser::FolderSaveStore store{tmp_dir};

    entt::registry reg;
    make_spatial_entity(reg, 5, 5);
    make_spatial_entity(reg, 8, 2);

    ser::save(reg, store, "map_01");
    reg = entt::registry{};
    ser::load(reg, store, "map_01");

    int count = 0;
    reg.view<zone::SpatialComponent>().each(
        [&](entt::entity, const zone::SpatialComponent&) { ++count; }
    );
    CHECK(count == 2);

    // store.has() 驗證
    CHECK(store.has("map_01"));
    CHECK_FALSE(store.has("map_02"));

    fs::remove_all(tmp_dir);
}

TEST_CASE("序列化 — FolderSaveStore：不存在的 slot 不崩潰") {
    auto tmp_dir = fs::temp_directory_path() / "zone_test_store2";
    ser::FolderSaveStore store{tmp_dir};

    entt::registry reg;
    ser::load(reg, store, "nonexistent");  // 應靜默忽略

    int count = 0;
    reg.view<zone::SpatialComponent>().each(
        [&](entt::entity, const zone::SpatialComponent&) { ++count; }
    );
    CHECK(count == 0);
}
