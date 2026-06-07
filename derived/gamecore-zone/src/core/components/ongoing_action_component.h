#pragma once
#include "core/turn/action.h"

namespace zone {

// 進行中的多回合動作。
//   progress        ：已進行的回合數（B/C 的 channel 進度）
//   remaining_ticks ：剩餘 ticks（C 用；B 不用）
struct OngoingActionComponent {
    Action action{};
    int    progress{0};
    int    remaining_ticks{0};

    template<class Archive>
    void serialize(Archive& ar) { ar(action, progress, remaining_ticks); }
};

} // namespace zone
