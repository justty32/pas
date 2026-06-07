#pragma once
#include "core/turn/turn_scheduler.h"

namespace zone {

// C. 無能量、每回合整步推進（spec §5.C，刻意用整步取代 min-jump，求決定性）。
class TickRemainingScheduler : public SchedulerBase {
public:
    void advance(TurnWorld&) override;

private:
    void start_action(TurnWorld&, entt::entity, const Action&);
};

} // namespace zone
