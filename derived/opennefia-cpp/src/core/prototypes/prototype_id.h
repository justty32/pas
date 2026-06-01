#pragma once
#include <string>
#include <string_view>

namespace opennefia {

// PrototypeId<T>：強型別的原型 id 字串包裝。
// 型別參數 T 是 tag type，用來讓編譯器區分不同種類的原型 id，
// 避免 EntityPrototype id 被誤用為 ItemPrototype id。
//
// 仿 OpenNefia C# 的 EntProtoId / ItemProtoId 強型別 id，但不靠反射——
// 只是一個帶型別 tag 的字串，序列化時就是字串。
template<typename T>
class PrototypeId {
public:
    PrototypeId() = default;
    explicit PrototypeId(std::string id) : id_(std::move(id)) {}
    explicit PrototypeId(const char* id) : id_(id) {}

    const std::string& str()   const { return id_; }
    std::string_view   view()  const { return id_; }
    bool               empty() const { return id_.empty(); }

    explicit operator bool() const { return !id_.empty(); }

    bool operator==(const PrototypeId& o) const { return id_ == o.id_; }
    bool operator!=(const PrototypeId& o) const { return id_ != o.id_; }
    bool operator< (const PrototypeId& o) const { return id_ <  o.id_; }

    template<class Archive>
    void serialize(Archive& ar) { ar(id_); }

private:
    std::string id_;
};

// ---- 常用 tag type ----
// Phase 2 只用 EntityPrototype，後續可擴充 ItemPrototype、TilePrototype 等。
struct EntityPrototypeTag {};
using EntityProtoId = PrototypeId<EntityPrototypeTag>;

} // namespace opennefia
