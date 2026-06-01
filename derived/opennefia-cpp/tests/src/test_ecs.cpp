#include <doctest/doctest.h>
#include <core/ecs/entity_manager.h>
#include <core/ecs/event_bus.h>
#include <core/ecs/system_ctx.h>
#include <core/components/meta_data_component.h>
#include <core/components/spatial_component.h>

// ---- 測試用 component ----------------------------------------
// （HealthComponent 僅作測試，不放入 src/core/components/）
struct HealthComponent {
    int hp{100};
};

// ---- 測試用事件 ----------------------------------------------
struct DamageEvent {
    int amount{};
};

struct BroadcastSpawnEvent {
    int count{};
};

// ==============================================================
// EntityManager 基本生命週期
// ==============================================================
TEST_CASE("EntityManager — create / destroy / valid") {
    opennefia::EntityManager em;
    auto e = em.create();

    CHECK(em.valid(e));
    em.destroy(e);
    CHECK_FALSE(em.valid(e));
}

// ==============================================================
// Component emplace / get / has / try_get / remove
// ==============================================================
TEST_CASE("EntityManager — component 操作") {
    opennefia::EntityManager em;
    auto e = em.create();

    SUBCASE("emplace + get") {
        auto& pos = em.emplace<opennefia::SpatialComponent>(e, 3, 7);
        CHECK(pos.x == 3);
        CHECK(pos.y == 7);
        CHECK(em.get<opennefia::SpatialComponent>(e).x == 3);
    }

    SUBCASE("has + remove") {
        em.emplace<opennefia::MetaDataComponent>(e);
        CHECK(em.has<opennefia::MetaDataComponent>(e));
        em.remove<opennefia::MetaDataComponent>(e);
        CHECK_FALSE(em.has<opennefia::MetaDataComponent>(e));
    }

    SUBCASE("try_get：存在回傳指標，不存在回傳 nullptr") {
        CHECK(em.try_get<opennefia::SpatialComponent>(e) == nullptr);
        em.emplace<opennefia::SpatialComponent>(e);
        CHECK(em.try_get<opennefia::SpatialComponent>(e) != nullptr);
    }
}

// ==============================================================
// 定向 EventBus：subscribe + raise_local
// ==============================================================
TEST_CASE("EventBus — 定向事件 raise_local") {
    opennefia::EventBus bus;
    opennefia::EntityManager em;
    auto target = em.create();

    int received = 0;
    bus.subscribe<DamageEvent>(
        [&](entt::registry&, entt::entity, DamageEvent& ev) {
            received += ev.amount;
        }
    );

    SUBCASE("有訂閱者時呼叫 handler") {
        DamageEvent ev{42};
        bus.raise_local(em.registry(), target, ev);
        CHECK(received == 42);
    }

    SUBCASE("多次 raise_local 累加") {
        DamageEvent ev1{10}, ev2{20};
        bus.raise_local(em.registry(), target, ev1);
        bus.raise_local(em.registry(), target, ev2);
        CHECK(received == 30);
    }

    SUBCASE("handler 可修改事件物件") {
        bus.subscribe<DamageEvent>(
            [](entt::registry&, entt::entity, DamageEvent& ev) {
                ev.amount *= 2; // 第二個 handler 翻倍（攔截語意示範）
            }
        );
        DamageEvent ev{5};
        bus.raise_local(em.registry(), target, ev);
        // handler1：received += 5；handler2：ev.amount = 10（handler1 已讀完）
        CHECK(received == 5);
        CHECK(ev.amount == 10);
    }
}

TEST_CASE("EventBus — 無訂閱者時 raise_local 不崩潰") {
    opennefia::EventBus bus;
    entt::registry reg;
    auto e = reg.create();
    DamageEvent ev{99};
    bus.raise_local(reg, e, ev); // 不應崩潰
    CHECK(ev.amount == 99);      // 事件未被修改
}

// ==============================================================
// 廣播 dispatcher
// ==============================================================
TEST_CASE("EventBus — 廣播 dispatcher trigger") {
    struct Listener {
        int total{0};
        void on_spawn(const BroadcastSpawnEvent& ev) { total += ev.count; }
    };

    opennefia::EventBus bus;
    Listener listener;
    bus.dispatcher().sink<BroadcastSpawnEvent>()
        .connect<&Listener::on_spawn>(listener);

    bus.dispatcher().trigger(BroadcastSpawnEvent{5});
    bus.dispatcher().trigger(BroadcastSpawnEvent{3});
    CHECK(listener.total == 8);
}

// ==============================================================
// 系統註冊 + tick：示範 Phase 1 判準場景
// （一個系統訂閱定向事件、另一個系統發送事件、handler 修改 component）
// ==============================================================
TEST_CASE("EntityManager — add_system + tick（事件匯流排整合）") {
    opennefia::EntityManager em;
    opennefia::EventBus bus;
    opennefia::SystemCtx ctx{bus};

    // 建實體並加上 HP component
    auto hero = em.create();
    em.emplace<HealthComponent>(hero, 100);

    // 系統 A（訂閱）：收到 DamageEvent → 扣血
    // 訂閱在系統初始化階段明確寫出，不靠反射
    bus.subscribe<DamageEvent>(
        [](entt::registry& reg, entt::entity target, DamageEvent& ev) {
            if (auto* hp = reg.try_get<HealthComponent>(target)) {
                hp->hp -= ev.amount;
            }
        }
    );

    // 系統 B（發送）：每 tick 對 hero 發送 10 點傷害事件
    em.add_system([hero](entt::registry& reg, opennefia::SystemCtx& ctx) {
        DamageEvent ev{10};
        ctx.bus.raise_local(reg, hero, ev);
    });

    em.tick(ctx);
    CHECK(em.get<HealthComponent>(hero).hp == 90);

    em.tick(ctx);
    CHECK(em.get<HealthComponent>(hero).hp == 80);
}

TEST_CASE("EntityManager — 系統執行序 = 註冊序") {
    opennefia::EntityManager em;
    opennefia::EventBus bus;
    opennefia::SystemCtx ctx{bus};

    std::vector<int> order;
    em.add_system([&order](entt::registry&, opennefia::SystemCtx&) { order.push_back(1); });
    em.add_system([&order](entt::registry&, opennefia::SystemCtx&) { order.push_back(2); });
    em.add_system([&order](entt::registry&, opennefia::SystemCtx&) { order.push_back(3); });

    em.tick(ctx);
    CHECK(order == std::vector<int>{1, 2, 3});
}
