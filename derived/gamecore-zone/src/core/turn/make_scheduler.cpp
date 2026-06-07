#include "core/turn/turn_scheduler.h"
#include "core/turn/energy_instant_scheduler.h"
#include "core/turn/energy_channel_scheduler.h"
#include "core/turn/tick_remaining_scheduler.h"

namespace zone {

std::unique_ptr<TurnScheduler> make_scheduler(SchedulerMode m) {
    switch (m) {
        case SchedulerMode::EnergyInstant: return std::make_unique<EnergyInstantScheduler>();
        case SchedulerMode::EnergyChannel: return std::make_unique<EnergyChannelScheduler>();
        case SchedulerMode::TickRemaining: return std::make_unique<TickRemainingScheduler>();
    }
    return nullptr;
}

} // namespace zone
