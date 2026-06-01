#pragma once
#include <entt/entt.hpp>

namespace opennefia {

// 遊戲物件的座標與場景圖父子關係。
// parent：與 medps CrossZoneRef 同理，entt::entity 強型別 enum 需要
//         非對稱的 save/load 才能正確序列化——Phase 3 補齊。
struct SpatialComponent {
    int x{}, y{};
    entt::entity parent{entt::null};  // 父實體（用於場景圖；null = 頂層）

    template<class Archive>
    void serialize(Archive& ar) {
        ar(x, y);
        // parent 的序列化在 Phase 3 用 save/load split 處理（entt::entity → raw int）
    }
};

} // namespace opennefia
