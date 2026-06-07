#include "core/turn/energy_instant_scheduler.h"
#include "core/turn/action_effects.h"
#include "core/components/energy_component.h"

namespace zone {

void EnergyInstantScheduler::advance(TurnWorld& w) {
    auto& reg = w.reg;
    const int threshold = w.cfg.energy_to_act;
    const int safety = threshold * 64;  // tick 上限，防無正速度死迴圈

    for (int guard = 0; guard < safety; ++guard) {
        auto all = actors_sorted(reg);

        std::vector<entt::entity> ready;
        for (auto e : all) {
            auto* en = reg.try_get<EnergyComponent>(e);
            if (en && en->value >= threshold) ready.push_back(e);
        }

        if (ready.empty()) {
            // 沒人就緒 → 全體加一 tick 能量
            for (auto e : all) {
                if (auto* en = reg.try_get<EnergyComponent>(e))
                    en->value += w.cfg.energy_per_tick * en->speed_mod / 100;
            }
            ++w.clock;
            continue;
        }

        // 處理本批就緒者（id 序）
        for (auto e : ready) {
            if (!reg.valid(e)) continue;  // 可能在本批稍早被殺
            Action a;
            if (is_player(reg, e)) {
                if (!take_pending(e, a)) { waiting_ = e; return; }  // 阻塞，保留能量
            } else {
                a = w.npc_decide ? w.npc_decide(reg, e) : Action::idle();
            }
            if (w.on_actor_turn) w.on_actor_turn(w, e);            // 回合開始：DoT 等
            if (!reg.valid(e)) continue;                          // 可能被 DoT 殺死
            if (auto* fx = w.effects.get(a.kind)) fx->on_resolve(w, e, a);  // 立即結算
            if (!reg.valid(e)) continue;
            reg.get<EnergyComponent>(e).value -= threshold * (a.weight > 0 ? a.weight : 1);
        }
        waiting_ = entt::null;
        return;
    }
    waiting_ = entt::null;
}

} // namespace zone
