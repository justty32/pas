#pragma once
#include "core/turn/turn_scheduler.h"

namespace zone {

// B. 能量排程 + 可打斷 channel（spec §5.B）。最完整。
class EnergyChannelScheduler : public SchedulerBase {
public:
    void advance(TurnWorld&) override;

private:
    // 推進單一就緒 actor 一回合。回 false = 阻塞（玩家 idle 無指令）。
    bool step_actor(TurnWorld&, entt::entity);
};

} // namespace zone
