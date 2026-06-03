#pragma once

namespace zone {

// 遊戲全域狀態元件，掛在 map_entity_ 上，隨 AllComponents 一併序列化。
// 讓 save/load 時不需要額外的 sidecar 檔案就能還原回合數與樓層。
struct WorldStateComponent {
    int turn_count{ 0 };
    int current_floor{ 1 };

    template<class Archive>
    void serialize(Archive& ar) { ar(turn_count, current_floor); }
};

} // namespace zone
