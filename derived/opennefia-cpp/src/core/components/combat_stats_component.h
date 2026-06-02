#pragma once
#include <cstdint>

namespace opennefia {

enum class NpcVariant : uint8_t {
    putit   = 0,  // 弱・慢（紫）
    warrior = 1,  // 強・中（橙）
    bat     = 2,  // 弱・極快（青）
};

struct CombatStatsComponent {
    int        attack{ 2 };
    int        move_chance{ 50 };
    NpcVariant variant{ NpcVariant::putit };
    int        base_hp{ 0 };       // 第 1 層基礎 HP（YAML 原型填入；0 = 不由原型控制）
    int        hp_per_floor{ 0 };  // 每層 HP 增量

    template<class Archive>
    void serialize(Archive& ar) { ar(attack, move_chance, variant, base_hp, hp_per_floor); }
};

} // namespace opennefia
