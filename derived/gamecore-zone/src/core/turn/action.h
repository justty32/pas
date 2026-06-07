#pragma once
#include <cstdint>

namespace zone {

// 動作種類。enum 起步、之後可換成資料表索引（見 spec §3.1）。
enum class ActionKind : uint8_t {
    Idle,    // 待命：無進行中行動、等待下一個決策
    Move,    // 移動
    Attack,  // 近戰攻擊
    Cast,    // 詠唱（多回合 channel 的代表）
    Wait,    // 原地等待（消耗一回合）
    Skill,   // 資料驅動技能：行為由 ActionDef（JSON）決定，param 帶方向、def 帶定義索引
};

inline constexpr int kActionKindCount = 6;

// 「指令」值型別。三排程器共用；weight 由各排程器各自解讀：
//   A：能量成本倍率（useEnergy = ENERGY_TO_ACT × weight）
//   B：channel 回合數（>1 才進 channel）
//   C：remaining_ticks = weight × TICKS_PER_TURN
struct Action {
    ActionKind kind  = ActionKind::Idle;
    int        param = 0;   // 方向打包 / 目標 entity / 法術 id
    int        weight = 1;  // 多重 / 多長
    int        def    = -1; // Skill：ActionLibrary 內的定義索引（-1 = 無）

    static Action idle() { return Action{ ActionKind::Idle, 0, 0, -1 }; }

    template<class Archive>
    void serialize(Archive& ar) { ar(kind, param, weight, def); }
};

} // namespace zone
