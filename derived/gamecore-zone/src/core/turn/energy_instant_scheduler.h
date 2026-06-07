#pragma once
#include "core/turn/turn_scheduler.h"

namespace zone {

// A. 純 ToME4：動作瞬間結算 + 能量成本決定下次行動（spec §5.A）。
class EnergyInstantScheduler : public SchedulerBase {
public:
    void advance(TurnWorld&) override;
};

} // namespace zone
