#pragma once
#include <entt/entt.hpp>

namespace opennefia {

// 遊戲物件的座標與場景圖父子關係。
// parent：與 medps CrossZoneRef 同理，entt::entity 強型別 enum 需要
//         非對稱的 save/load 才能正確序列化——Phase 3 補齊。
struct SpatialComponent {
    int x{}, y{};
    entt::entity parent{entt::null};  // 父實體（用於場景圖；null = 頂層）

    // 非對稱 save/load split：entt::entity 是強型別 enum，需手動轉換成底層整數。
    // 仿 medps cross_zone_ref.h 的做法（C:/code/mine/medps/src/gcore/components/cross_zone_ref.h）。
    template<class Archive>
    void save(Archive& ar) const {
        ar(x, y);
        using raw_t = std::underlying_type_t<entt::entity>;
        ar(static_cast<raw_t>(parent));
    }

    template<class Archive>
    void load(Archive& ar) {
        ar(x, y);
        using raw_t = std::underlying_type_t<entt::entity>;
        raw_t raw{};
        ar(raw);
        parent = static_cast<entt::entity>(raw);
    }
};

} // namespace opennefia
