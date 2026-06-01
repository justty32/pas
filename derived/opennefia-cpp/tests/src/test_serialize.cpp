#include <doctest/doctest.h>
#include <string>
#include <sstream>
#include <filesystem>
#include <core/serialize/save_load.h>
#include <core/serialize/save_store.h>
#include <core/components/meta_data_component.h>
#include <core/components/spatial_component.h>

namespace fs = std::filesystem;
namespace ser = opennefia::serialize;

// ---- 工具：快速建 registry 情境 -----------------------------------------
static entt::entity make_entity(entt::registry& reg,
                                const std::string& proto_id,
                                int x, int y,
                                entt::entity parent = entt::null)
{
    auto e = reg.create();
    reg.emplace<opennefia::MetaDataComponent>(e,
        opennefia::MetaDataComponent{proto_id, true});
    reg.emplace<opennefia::SpatialComponent>(e,
        opennefia::SpatialComponent{x, y, parent});
    return e;
}

// ==============================================================
// 基礎 stream round-trip
// ==============================================================
TEST_CASE("序列化 — stream round-trip：MetaDataComponent") {
    entt::registry reg;
    make_entity(reg, "hero", 0, 0);
    make_entity(reg, "slime", 5, 3);

    std::ostringstream oss;
    ser::save(reg, oss);

    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    int count = 0;
    bool found_hero = false, found_slime = false;
    reg.view<opennefia::MetaDataComponent>().each(
        [&](entt::entity, const opennefia::MetaDataComponent& m) {
            ++count;
            if (m.proto_id == "hero")  found_hero  = true;
            if (m.proto_id == "slime") found_slime = true;
        }
    );
    CHECK(count == 2);
    CHECK(found_hero);
    CHECK(found_slime);
}

TEST_CASE("序列化 — stream round-trip：SpatialComponent 座標") {
    entt::registry reg;
    make_entity(reg, "a", 7, 13);

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    reg.view<opennefia::MetaDataComponent, opennefia::SpatialComponent>().each(
        [](entt::entity, const opennefia::MetaDataComponent& m,
                         const opennefia::SpatialComponent& s) {
            if (m.proto_id == "a") {
                CHECK(s.x == 7);
                CHECK(s.y == 13);
            }
        }
    );
}

// ==============================================================
// parent entity 引用 round-trip（entt::entity 強型別 enum）
// ==============================================================
TEST_CASE("序列化 — SpatialComponent.parent entt::entity round-trip") {
    entt::registry reg;
    auto parent_e = make_entity(reg, "parent", 10, 20);
    auto child_e  = make_entity(reg, "child",  11, 21, parent_e);

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    entt::entity restored_parent = entt::null;
    entt::entity restored_child  = entt::null;

    reg.view<opennefia::MetaDataComponent, opennefia::SpatialComponent>().each(
        [&](entt::entity e, const opennefia::MetaDataComponent& m,
                            const opennefia::SpatialComponent& s) {
            if (m.proto_id == "parent") {
                restored_parent = e;
                // entt::entity == entt::null_t 在 doctest CHECK 中有歧義（EnTT 模板 operator==
                // 與 doctest Expression_lhs 模板 operator== 衝突）；先求值成 bool 再 CHECK。
                bool parent_is_null = (s.parent == entt::null);
                CHECK(parent_is_null);
            }
            if (m.proto_id == "child") {
                restored_child = e;
                CHECK(s.x == 11);
                CHECK(s.y == 21);
            }
        }
    );

    // 同上：entt::entity != entt::null_t 歧義，先求值成 bool
    bool parent_found = (restored_parent != entt::null);
    bool child_found  = (restored_child  != entt::null);
    REQUIRE(parent_found);
    REQUIRE(child_found);

    // entt::entity == entt::entity（同型別）同樣有歧義，先求值成 bool
    const auto& child_sp = reg.get<opennefia::SpatialComponent>(restored_child);
    bool parent_ref_ok = (child_sp.parent == restored_parent);
    CHECK(parent_ref_ok);
}

// ==============================================================
// is_alive flag round-trip
// ==============================================================
TEST_CASE("序列化 — MetaDataComponent.is_alive round-trip") {
    entt::registry reg;
    auto alive = reg.create();
    reg.emplace<opennefia::MetaDataComponent>(alive,
        opennefia::MetaDataComponent{"alive_one", true});
    auto dead = reg.create();
    reg.emplace<opennefia::MetaDataComponent>(dead,
        opennefia::MetaDataComponent{"dead_one", false});

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    reg.view<opennefia::MetaDataComponent>().each(
        [](entt::entity, const opennefia::MetaDataComponent& m) {
            if (m.proto_id == "alive_one") CHECK(m.is_alive == true);
            if (m.proto_id == "dead_one")  CHECK(m.is_alive == false);
        }
    );
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
    reg.view<opennefia::MetaDataComponent>().each(
        [&](entt::entity, const opennefia::MetaDataComponent&) { ++count; }
    );
    CHECK(count == 0);
}

// ==============================================================
// 只有部分 component 的 entity（无 SpatialComponent）
// ==============================================================
TEST_CASE("序列化 — 只有 MetaDataComponent，無 SpatialComponent") {
    entt::registry reg;
    auto e = reg.create();
    reg.emplace<opennefia::MetaDataComponent>(e,
        opennefia::MetaDataComponent{"meta_only", true});
    // 刻意不加 SpatialComponent

    std::ostringstream oss;
    ser::save(reg, oss);
    reg = entt::registry{};
    std::istringstream iss{oss.str()};
    ser::load(reg, iss);

    bool found = false;
    reg.view<opennefia::MetaDataComponent>().each(
        [&](entt::entity e2, const opennefia::MetaDataComponent& m) {
            if (m.proto_id == "meta_only") {
                found = true;
                CHECK_FALSE(reg.all_of<opennefia::SpatialComponent>(e2));
            }
        }
    );
    CHECK(found);
}

// ==============================================================
// 檔案 API（直接存路徑）
// ==============================================================
TEST_CASE("序列化 — 直接路徑 save/load file") {
    auto tmp = fs::temp_directory_path() / "opennefia_test_savefile.bin";

    entt::registry reg;
    make_entity(reg, "map_hero", 3, 7);

    ser::save(reg, tmp);
    reg = entt::registry{};
    ser::load(reg, tmp);

    bool found = false;
    reg.view<opennefia::MetaDataComponent, opennefia::SpatialComponent>().each(
        [&](entt::entity, const opennefia::MetaDataComponent& m,
                          const opennefia::SpatialComponent& s) {
            if (m.proto_id == "map_hero") {
                found = true;
                CHECK(s.x == 3);
                CHECK(s.y == 7);
            }
        }
    );
    CHECK(found);

    fs::remove(tmp);
}

// ==============================================================
// FolderSaveStore round-trip
// ==============================================================
TEST_CASE("序列化 — FolderSaveStore save/load slot") {
    auto tmp_dir = fs::temp_directory_path() / "opennefia_test_store";
    fs::create_directories(tmp_dir);

    ser::FolderSaveStore store{tmp_dir};

    entt::registry reg;
    make_entity(reg, "warrior", 5, 5);
    make_entity(reg, "wizard",  8, 2);

    ser::save(reg, store, "map_01");
    reg = entt::registry{};
    ser::load(reg, store, "map_01");

    int count = 0;
    bool w1 = false, w2 = false;
    reg.view<opennefia::MetaDataComponent>().each(
        [&](entt::entity, const opennefia::MetaDataComponent& m) {
            ++count;
            if (m.proto_id == "warrior") w1 = true;
            if (m.proto_id == "wizard")  w2 = true;
        }
    );
    CHECK(count == 2);
    CHECK(w1);
    CHECK(w2);

    // store.has() 驗證
    CHECK(store.has("map_01"));
    CHECK_FALSE(store.has("map_02"));

    fs::remove_all(tmp_dir);
}

TEST_CASE("序列化 — FolderSaveStore：不存在的 slot 不崩潰") {
    auto tmp_dir = fs::temp_directory_path() / "opennefia_test_store2";
    ser::FolderSaveStore store{tmp_dir};

    entt::registry reg;
    ser::load(reg, store, "nonexistent");  // 應靜默忽略

    int count = 0;
    reg.view<opennefia::MetaDataComponent>().each(
        [&](entt::entity, const opennefia::MetaDataComponent&) { ++count; }
    );
    CHECK(count == 0);
}
