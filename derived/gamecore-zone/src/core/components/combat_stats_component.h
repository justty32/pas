#pragma once
#include <cstdint>

namespace zone {

struct CombatStatsComponent {
    int attack{ 2 };
    int move_chance{ 50 };

    template<class Archive>
    void serialize(Archive& ar) { ar(attack, move_chance); }
};

} // namespace zone
