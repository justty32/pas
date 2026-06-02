#pragma once

namespace opennefia {

// NPC 簡易 AI 狀態元件。
// 目前只做「wander」——每 tick 以 50% 機率隨機移動一格可走方向。
// 未來可加 patrol_target、aggro_range 等欄位。
struct NpcAiComponent {
    template<class Archive>
    void serialize(Archive& ar) { /* 目前無需持久欄位 */ }
};

} // namespace opennefia
