#include "core/turn/energy_channel_scheduler.h"
#include "core/turn/action_effects.h"
#include "core/components/energy_component.h"
#include "core/components/ongoing_action_component.h"

namespace zone {

void EnergyChannelScheduler::advance(TurnWorld& w) {
    auto& reg = w.reg;
    const int threshold = w.cfg.energy_to_act;
    const int safety = threshold * 64;

    for (int guard = 0; guard < safety; ++guard) {
        auto all = actors_sorted(reg);

        std::vector<entt::entity> ready;
        for (auto e : all) {
            auto* en = reg.try_get<EnergyComponent>(e);
            if (en && en->value >= threshold) ready.push_back(e);
        }

        if (ready.empty()) {
            for (auto e : all)
                if (auto* en = reg.try_get<EnergyComponent>(e))
                    en->value += w.cfg.energy_per_tick * en->speed_mod / 100;
            ++w.clock;
            continue;
        }

        for (auto e : ready) {
            if (!reg.valid(e)) continue;    // 可能在本批稍早被殺
            if (!step_actor(w, e)) return;  // 阻塞
        }
        waiting_ = entt::null;
        return;
    }
    waiting_ = entt::null;
}

bool EnergyChannelScheduler::step_actor(TurnWorld& w, entt::entity e) {
    auto& reg = w.reg;
    const int cost = w.cfg.energy_to_act;

    Action cmd;
    bool has_cmd = take_pending(e, cmd);
    auto* og = reg.try_get<OngoingActionComponent>(e);

    // 阻塞：玩家 idle 且無新指令 → 不取得回合（DoT 也不 tick）
    if (!has_cmd && !og && is_player(reg, e)) { waiting_ = e; return false; }

    // 此 actor 確定要進行一回合
    if (w.on_actor_turn) w.on_actor_turn(w, e);
    if (!reg.valid(e)) return true;                       // 被 DoT 殺死
    og = reg.try_get<OngoingActionComponent>(e);          // 重新取得（保險）
    auto& en = reg.get<EnergyComponent>(e);

    if (has_cmd) {
        // 新指令 = 打斷 / 起手
        if (cmd.weight <= 1) {
            if (auto* fx = w.effects.get(cmd.kind)) fx->on_resolve(w, e, cmd);
            if (reg.valid(e) && reg.all_of<OngoingActionComponent>(e))
                reg.remove<OngoingActionComponent>(e);
            if (reg.valid(e)) reg.get<EnergyComponent>(e).value -= cost;
            return true;
        }
        if (!og) { reg.emplace<OngoingActionComponent>(e); og = reg.try_get<OngoingActionComponent>(e); }
        og->action = cmd;
        og->progress = 0;
    } else if (!og) {
        // idle、需新動作（玩家已在上面阻塞，故此處必為 NPC）
        Action a = w.npc_decide ? w.npc_decide(reg, e) : Action::idle();
        if (a.weight <= 1) {
            if (auto* fx = w.effects.get(a.kind)) fx->on_resolve(w, e, a);
            if (reg.valid(e)) reg.get<EnergyComponent>(e).value -= cost;
            return true;
        }
        reg.emplace<OngoingActionComponent>(e);
        og = reg.try_get<OngoingActionComponent>(e);
        og->action = a;
        og->progress = 0;
    }

    // channel 一回合（og 此時必非空）
    if (auto* fx = w.effects.get(og->action.kind)) fx->on_channel(w, e, og->action, og->progress);
    og->progress++;
    en.value -= cost;
    if (og->progress >= og->action.weight) {
        if (auto* fx = w.effects.get(og->action.kind)) fx->on_resolve(w, e, og->action);
        if (reg.valid(e) && reg.all_of<OngoingActionComponent>(e))
            reg.remove<OngoingActionComponent>(e);
    }
    return true;
}

} // namespace zone
