#include <doctest/doctest.h>
#include <core/ecs/entity_manager.h>
#include <core/ecs/system_ctx.h>
#include <core/components/actor_component.h>
#include <core/components/spatial_component.h>

// ---- 測試用 component ----------------------------------------
// （HealthComponent 僅作測試，不放入 src/core/components/）
struct HealthComponent {
    int hp{100};
};

// ==============================================================
// EntityManager 基本生命週期
// ==============================================================
TEST_CASE("EntityManager — create / destroy / valid") {
    zone::EntityManager em;
    auto e = em.create();

    CHECK(em.valid(e));
    em.destroy(e);
    CHECK_FALSE(em.valid(e));
}

// ==============================================================
// Component emplace / get / has / try_get / remove
// ==============================================================
TEST_CASE("EntityManager — component 操作") {
    zone::EntityManager em;
    auto e = em.create();

    SUBCASE("emplace + get") {
        auto& pos = em.emplace<zone::SpatialComponent>(e, 3, 7);
        CHECK(pos.x == 3);
        CHECK(pos.y == 7);
        CHECK(em.get<zone::SpatialComponent>(e).x == 3);
    }

    SUBCASE("has + remove") {
        em.emplace<zone::ActorComponent>(e);
        CHECK(em.has<zone::ActorComponent>(e));
        em.remove<zone::ActorComponent>(e);
        CHECK_FALSE(em.has<zone::ActorComponent>(e));
    }

    SUBCASE("try_get：存在回傳指標，不存在回傳 nullptr") {
        CHECK(em.try_get<zone::SpatialComponent>(e) == nullptr);
        em.emplace<zone::SpatialComponent>(e);
        CHECK(em.try_get<zone::SpatialComponent>(e) != nullptr);
    }
}

// ==============================================================
// 系統註冊 + tick：add_system / 執行序
// ==============================================================
TEST_CASE("EntityManager — add_system + tick（damage 扣血）") {
    zone::EntityManager em;
    zone::SystemCtx ctx;

    // 建實體並加上 HP component
    auto hero = em.create();
    em.emplace<HealthComponent>(hero, 100);

    // 系統 A：每 tick 扣血 10
    em.add_system([hero](entt::registry& reg, zone::SystemCtx&) {
        if (auto* hp = reg.try_get<HealthComponent>(hero)) {
            hp->hp -= 10;
        }
    });

    em.tick(ctx);
    CHECK(em.get<HealthComponent>(hero).hp == 90);

    em.tick(ctx);
    CHECK(em.get<HealthComponent>(hero).hp == 80);
}

TEST_CASE("EntityManager — 系統執行序 = 註冊序") {
    zone::EntityManager em;
    zone::SystemCtx ctx;

    std::vector<int> order;
    em.add_system([&order](entt::registry&, zone::SystemCtx&) { order.push_back(1); });
    em.add_system([&order](entt::registry&, zone::SystemCtx&) { order.push_back(2); });
    em.add_system([&order](entt::registry&, zone::SystemCtx&) { order.push_back(3); });

    em.tick(ctx);
    CHECK(order == std::vector<int>{1, 2, 3});
}

TEST_CASE("ActorComponent — 可作為 actor poll 標記") {
    zone::EntityManager em;
    auto hero = em.create();
    auto item = em.create();

    em.registry().emplace<zone::ActorComponent>(hero);
    // item 不掛 ActorComponent

    int count = 0;
    for (auto e : em.registry().view<zone::ActorComponent>()) {
        (void)e;
        ++count;
    }
    CHECK(count == 1);
    CHECK(em.registry().all_of<zone::ActorComponent>(hero));
    CHECK_FALSE(em.registry().all_of<zone::ActorComponent>(item));
}
