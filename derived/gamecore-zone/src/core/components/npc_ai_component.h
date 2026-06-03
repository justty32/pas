#pragma once

namespace zone {

// NPC AI 狀態元件。
// alerted:     NPC 曾看見英雄，正在追蹤中。
// alert_turns: 失去視線後還能繼續追蹤的剩餘回合數。
struct NpcAiComponent {
    bool alerted{ false };
    int  alert_turns{ 0 };

    template<class Archive>
    void serialize(Archive& ar) { ar(alerted, alert_turns); }
};

} // namespace zone
