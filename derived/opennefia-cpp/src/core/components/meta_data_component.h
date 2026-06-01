#pragma once
#include <string>

namespace opennefia {

// 每個遊戲物件的基礎 component。
// proto_id：Phase 2 強型別 PrototypeId<T> 的佔位，目前用裸字串。
struct MetaDataComponent {
    std::string proto_id;    // 原型 id（Phase 2 改為 PrototypeId<T>）
    bool is_alive{true};

    template<class Archive>
    void serialize(Archive& ar) { ar(proto_id, is_alive); }
};

} // namespace opennefia
