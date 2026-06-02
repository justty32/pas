#pragma once

namespace opennefia {

// 英雄標記（tag component）。
//
// 用「正向標記」唯一辨識玩家英雄，取代「排除法」（如 exclude<NpcAi> 找首個
// 有座標實體）——後者極脆弱：物品同樣有 Spatial 卻無 NpcAi，且 EnTT 單池
// view 由 storage 尾端往前迭代，會誤選較晚建立的物品當英雄（見 PROJECT.md §9
// 2026-06-02 戰鬥 bug）。系統要找英雄一律走 view<HeroComponent, ...>。
//
// 空 tag：std::is_empty_v 為 true，EnTT snapshot 走空型別最佳化（只存 entity，
// 不存 payload），serialize() 不會被呼叫；保留之以符合「每個 component 皆可序列化」
// 的慣例並避免未來加欄位時忘記。
struct HeroComponent {
    template<class Archive>
    void serialize(Archive&) {}
};

} // namespace opennefia
