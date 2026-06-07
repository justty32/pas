#pragma once

namespace zone {

// 行動值（ToME4 風）。value 每 tick 累積，達 ENERGY_TO_ACT 才能出手。
// speed_mod 為百分比：100 = 標準速度，200 = 兩倍速（每 tick 加倍能量）。
struct EnergyComponent {
    int value{0};
    int speed_mod{100};

    template<class Archive>
    void serialize(Archive& ar) { ar(value, speed_mod); }
};

} // namespace zone
