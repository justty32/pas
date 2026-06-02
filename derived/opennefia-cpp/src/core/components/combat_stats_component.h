#pragma once
#include <cstdint>

namespace opennefia {

enum class NpcVariant : uint8_t {
    putit   = 0,  // 弱・慢（紫）
    warrior = 1,  // 強・中（橙）
    bat     = 2,  // 弱・極快（青）
};

struct CombatStatsComponent {
    int        attack{ 2 };        // 攻擊傷害
    int        move_chance{ 50 };  // 行動機率 0-100
    NpcVariant variant{ NpcVariant::putit };

    template<class Archive>
    void serialize(Archive& ar) { ar(attack, move_chance, variant); }
};

} // namespace opennefia
