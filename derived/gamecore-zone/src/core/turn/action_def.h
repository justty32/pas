#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <cereal/cereal.hpp>

namespace zone {

// 資料驅動的動作定義（可組合原語；由 JSON 載入）。
// 行為邏輯仍是 C++ 原語（resolve_move / resolve_nova / heal），JSON 只挑原語與參數。
struct ActionDef {
    std::string name;
    int weight      = 1;   // channel 回合數（填入 Action.weight）
    int do_move     = 0;   // 1 = 依 param 方向移動（含撞擊/拾取）
    int nova_damage = 0;   // >0：對範圍內 actor 傷害
    int radius      = 1;   // nova 半徑（chebyshev；1=8鄰格、2=24格…）
    int dot_turns   = 0;   // >0：對命中者施加 DoT（回合數）
    int dot_power   = 0;   // DoT 每回合量
    int dot_kind    = 0;   // 0=燃燒 1=中毒 2=回復（對命中者）
    int self_heal   = 0;   // >0：對自己立即回血
    int self_regen_turns = 0;  // >0：對自己施加回復 buff（回合數）
    int self_regen_power = 0;  // 回復每回合量

    template<class Archive>
    void serialize(Archive& ar) {
        ar(CEREAL_NVP(name), CEREAL_NVP(weight), CEREAL_NVP(do_move),
           CEREAL_NVP(nova_damage), CEREAL_NVP(radius),
           CEREAL_NVP(dot_turns), CEREAL_NVP(dot_power), CEREAL_NVP(dot_kind),
           CEREAL_NVP(self_heal),
           CEREAL_NVP(self_regen_turns), CEREAL_NVP(self_regen_power));
    }
};

// 動作庫：名稱→索引 + 索引存取。從 JSON 載入（cereal JSONInputArchive）。
class ActionLibrary {
public:
    bool load_json(const std::string& path);  // 失敗回 false（不丟例外）
    void load_defaults();                      // 無檔時的硬編後備

    int  size() const { return static_cast<int>(defs_.size()); }
    const ActionDef& at(int i) const { return defs_.at(static_cast<std::size_t>(i)); }
    int  find(const std::string& name) const;  // 無則 -1

private:
    void reindex();
    std::vector<ActionDef>               defs_;
    std::unordered_map<std::string, int> index_;
};

} // namespace zone
