#include "core/turn/tick_remaining_scheduler.h"
#include "core/turn/action_effects.h"
#include "core/components/ongoing_action_component.h"

namespace zone {

void TickRemainingScheduler::advance(TurnWorld& w) {
    auto& reg = w.reg;

    // phase 1：決定各 actor 本回合的進行中動作（打斷 / 起手 / 阻塞）
    for (auto e : actors_sorted(reg)) {
        if (!reg.valid(e)) continue;
        Action cmd;
        bool has_cmd = take_pending(e, cmd);
        auto* og = reg.try_get<OngoingActionComponent>(e);
        bool busy = og && og->remaining_ticks > 0;
        if (has_cmd) {
            start_action(w, e, cmd);                              // 打斷或起手（覆寫進行中）
        } else if (!busy) {
            if (is_player(reg, e)) { waiting_ = e; return; }      // 阻塞
            start_action(w, e, w.npc_decide ? w.npc_decide(reg, e) : Action::idle());
        }
    }
    waiting_ = entt::null;

    // phase 2：推進整一回合（每個忙碌 actor channel 一回合，到期 resolve）
    const int tpt = w.cfg.ticks_per_turn;
    w.clock += tpt;
    for (auto e : actors_sorted(reg)) {
        if (!reg.valid(e)) continue;  // 可能被本回合稍早的結算殺死
        auto* og = reg.try_get<OngoingActionComponent>(e);
        if (!og || og->remaining_ticks <= 0) continue;
        if (w.on_actor_turn) w.on_actor_turn(w, e);   // 回合開始：DoT 等
        if (!reg.valid(e)) continue;                  // 可能被 DoT 殺死
        og = reg.try_get<OngoingActionComponent>(e);
        if (!og || og->remaining_ticks <= 0) continue;
        if (auto* fx = w.effects.get(og->action.kind)) fx->on_channel(w, e, og->action, og->progress);
        og->progress++;
        og->remaining_ticks -= tpt;
        if (og->remaining_ticks <= 0) {
            if (auto* fx = w.effects.get(og->action.kind)) fx->on_resolve(w, e, og->action);
            reg.remove<OngoingActionComponent>(e);
        }
    }
}

void TickRemainingScheduler::start_action(TurnWorld& w, entt::entity e, const Action& a) {
    auto& reg = w.reg;
    const int turns = a.weight > 0 ? a.weight : 1;
    auto* og = reg.try_get<OngoingActionComponent>(e);
    if (!og) { reg.emplace<OngoingActionComponent>(e); og = reg.try_get<OngoingActionComponent>(e); }
    og->action = a;
    og->progress = 0;
    og->remaining_ticks = turns * w.cfg.ticks_per_turn;
}

} // namespace zone
