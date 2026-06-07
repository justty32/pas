#include <doctest/doctest.h>
#include <entt/entt.hpp>
#include <vector>
#include <unordered_map>

#include "core/turn/turn_scheduler.h"
#include "core/turn/turn_world.h"
#include "core/turn/action.h"
#include "core/turn/action_effects.h"
#include "core/components/actor_component.h"
#include "core/components/player_controlled_component.h"
#include "core/components/energy_component.h"

using zone::Action;
using zone::ActionKind;
using zone::SchedulerMode;
using zone::TurnWorld;

namespace {

// 記錄 channel / resolve 呼叫，供斷言。
struct Recorder : zone::ActionEffects {
    std::unordered_map<entt::entity, int>                   resolves;
    std::unordered_map<entt::entity, std::vector<int>>      channels;
    std::unordered_map<entt::entity, std::vector<ActionKind>> kinds;

    void on_channel(TurnWorld&, entt::entity e, const Action&, int turn) override {
        channels[e].push_back(turn);
    }
    void on_resolve(TurnWorld&, entt::entity e, const Action& a) override {
        resolves[e]++;
        kinds[e].push_back(a.kind);
    }
};

void register_all(zone::EffectRegistry& fx, Recorder& r) {
    fx.register_kind(ActionKind::Attack, &r);
    fx.register_kind(ActionKind::Cast,   &r);
    fx.register_kind(ActionKind::Move,   &r);
    fx.register_kind(ActionKind::Wait,   &r);
}

entt::entity add_actor(entt::registry& reg, bool player, int speed = 100) {
    auto e = reg.create();
    reg.emplace<zone::ActorComponent>(e);
    if (player) reg.emplace<zone::PlayerControlledComponent>(e);
    auto& en = reg.emplace<zone::EnergyComponent>(e);
    en.value = 0;
    en.speed_mod = speed;
    return e;
}

Action attack1() { return Action{ ActionKind::Attack, 0, 1 }; }
Action cast3()   { return Action{ ActionKind::Cast,   0, 3 }; }

// 避免 doctest 表達式模板與 entt operator==(Entity,null_t) 的多載歧義。
bool is_null(entt::entity e) { return e == entt::null; }

} // namespace

// =============================================================================
// 速度差（A、B）：快角(200) 出手約為慢角(100) 的兩倍
// =============================================================================
TEST_CASE("scheduler — 速度差：快角出手約兩倍") {
    for (auto mode : { SchedulerMode::EnergyInstant, SchedulerMode::EnergyChannel }) {
        entt::registry reg;
        Recorder rec;
        zone::EffectRegistry fx; register_all(fx, rec);
        auto slow = add_actor(reg, false, 100);
        auto fast = add_actor(reg, false, 200);
        zone::NpcDecider npc = [](entt::registry&, entt::entity) { return attack1(); };
        TurnWorld w{ reg, fx, npc };

        auto sch = zone::make_scheduler(mode);
        for (int i = 0; i < 20; ++i) sch->advance(w);

        CHECK(rec.resolves[slow] >= 1);
        CHECK(rec.resolves[fast] == 2 * rec.resolves[slow]);
    }
}

// =============================================================================
// channel 完成（B、C）：weight=3 第 3 回合才 resolve，channel turn 0→2
// =============================================================================
TEST_CASE("scheduler — channel：weight3 三回合、turn 0..2 後 resolve") {
    for (auto mode : { SchedulerMode::EnergyChannel, SchedulerMode::TickRemaining }) {
        entt::registry reg;
        Recorder rec;
        zone::EffectRegistry fx; register_all(fx, rec);
        auto e = add_actor(reg, false, 100);
        zone::NpcDecider npc = [](entt::registry&, entt::entity) { return cast3(); };
        TurnWorld w{ reg, fx, npc };

        auto sch = zone::make_scheduler(mode);
        for (int i = 0; i < 10 && rec.resolves[e] == 0; ++i) sch->advance(w);

        CHECK(rec.resolves[e] == 1);
        CHECK(rec.channels[e] == std::vector<int>{ 0, 1, 2 });
    }
}

// =============================================================================
// 打斷（B、C）：channel 中 submit 新動作 → 舊動作不 resolve、新動作 resolve
// =============================================================================
TEST_CASE("scheduler — 打斷：channel 中換動作，舊的不結算") {
    for (auto mode : { SchedulerMode::EnergyChannel, SchedulerMode::TickRemaining }) {
        entt::registry reg;
        Recorder rec;
        zone::EffectRegistry fx; register_all(fx, rec);
        auto e = add_actor(reg, true, 100);  // 玩家：用 submit 控制
        zone::NpcDecider npc = [](entt::registry&, entt::entity) { return Action::idle(); };
        TurnWorld w{ reg, fx, npc };

        auto sch = zone::make_scheduler(mode);
        sch->submit(e, cast3());
        sch->advance(w);   // 起手 + channel0
        sch->advance(w);   // channel1
        sch->submit(e, attack1());  // 打斷
        sch->advance(w);   // 應 resolve Attack；Cast 不結算

        CHECK(rec.kinds[e].size() == 1);
        CHECK(rec.kinds[e][0] == ActionKind::Attack);
    }
}

// =============================================================================
// 玩家阻塞（A、B、C）：idle 無指令停住，submit 後續推
// =============================================================================
TEST_CASE("scheduler — 玩家阻塞：停住等指令") {
    for (auto mode : { SchedulerMode::EnergyInstant, SchedulerMode::EnergyChannel,
                       SchedulerMode::TickRemaining }) {
        entt::registry reg;
        Recorder rec;
        zone::EffectRegistry fx; register_all(fx, rec);
        auto p = add_actor(reg, true, 100);
        zone::NpcDecider npc = [](entt::registry&, entt::entity) { return Action::idle(); };
        TurnWorld w{ reg, fx, npc };

        auto sch = zone::make_scheduler(mode);
        for (int i = 0; i < 5; ++i) sch->advance(w);
        CHECK(sch->waiting_actor() == p);
        CHECK(rec.resolves[p] == 0);

        sch->submit(p, attack1());
        for (int i = 0; i < 3 && rec.resolves[p] == 0; ++i) sch->advance(w);
        CHECK(rec.resolves[p] >= 1);
        CHECK(is_null(sch->waiting_actor()));
    }
}

// =============================================================================
// 多角色（A、B、C）：兩玩家依序各自阻塞
// =============================================================================
TEST_CASE("scheduler — 多角色：兩玩家依序阻塞") {
    for (auto mode : { SchedulerMode::EnergyInstant, SchedulerMode::EnergyChannel,
                       SchedulerMode::TickRemaining }) {
        entt::registry reg;
        Recorder rec;
        zone::EffectRegistry fx; register_all(fx, rec);
        auto p1 = add_actor(reg, true, 100);
        auto p2 = add_actor(reg, true, 100);
        zone::NpcDecider npc = [](entt::registry&, entt::entity) { return Action::idle(); };
        TurnWorld w{ reg, fx, npc };

        auto sch = zone::make_scheduler(mode);

        sch->advance(w);
        CHECK(sch->waiting_actor() == p1);     // 先卡低 id

        sch->submit(p1, attack1());
        sch->advance(w);
        CHECK(sch->waiting_actor() == p2);     // 再卡第二個

        sch->submit(p2, attack1());
        for (int i = 0; i < 3 &&
             (rec.resolves[p1] == 0 || rec.resolves[p2] == 0); ++i) sch->advance(w);

        CHECK(rec.resolves[p1] >= 1);
        CHECK(rec.resolves[p2] >= 1);
        CHECK(is_null(sch->waiting_actor()));
    }
}
