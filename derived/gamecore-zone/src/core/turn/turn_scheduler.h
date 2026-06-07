#pragma once
#include <memory>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <entt/entt.hpp>
#include "core/turn/action.h"
#include "core/turn/turn_world.h"
#include "core/components/actor_component.h"
#include "core/components/player_controlled_component.h"

namespace zone {

// 三排程器共用介面（spec §3.4）。
class TurnScheduler {
public:
    virtual void advance(TurnWorld&) = 0;
    virtual entt::entity waiting_actor() const = 0;
    virtual void submit(entt::entity, const Action&) = 0;
    virtual ~TurnScheduler() = default;
};

enum class SchedulerMode { EnergyInstant, EnergyChannel, TickRemaining };

std::unique_ptr<TurnScheduler> make_scheduler(SchedulerMode);

// 共用基底：pending 收件匣 + waiting_actor + 常用 helper。
class SchedulerBase : public TurnScheduler {
public:
    entt::entity waiting_actor() const override { return waiting_; }
    void submit(entt::entity e, const Action& a) override { pending_[e] = a; }

protected:
    static bool is_player(entt::registry& reg, entt::entity e) {
        return reg.all_of<PlayerControlledComponent>(e);
    }

    // 取出並消費 pending；無則回 false。
    bool take_pending(entt::entity e, Action& out) {
        auto it = pending_.find(e);
        if (it == pending_.end()) return false;
        out = it->second;
        pending_.erase(it);
        return true;
    }

    // 依 entity id 排序的所有 actor（決定性迭代）。
    static std::vector<entt::entity> actors_sorted(entt::registry& reg) {
        std::vector<entt::entity> v;
        for (auto e : reg.view<ActorComponent>()) v.push_back(e);
        std::sort(v.begin(), v.end(), [](entt::entity a, entt::entity b) {
            return entt::to_integral(a) < entt::to_integral(b);
        });
        return v;
    }

    entt::entity waiting_ = entt::null;
    std::unordered_map<entt::entity, Action> pending_;
};

} // namespace zone
