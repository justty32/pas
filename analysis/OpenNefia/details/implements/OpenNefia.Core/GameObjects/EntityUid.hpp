#pragma once

#include <cstdint>
#include <compare>
#include <functional>
#include <string>

namespace OpenNefia::Core::GameObjects {

/**
 * @brief Unique identifier for an entity.
 * Ported from EntityUid.cs.
 */
struct EntityUid {
    int32_t _uid;

    static const EntityUid Invalid;
    static const EntityUid FirstUid;

    constexpr EntityUid() : _uid(0) {}
    constexpr explicit EntityUid(int32_t uid) : _uid(uid) {}

    bool IsValid() const { return _uid > 0; }

    bool operator==(const EntityUid& other) const { return _uid == other._uid; }
    bool operator!=(const EntityUid& other) const { return _uid != other._uid; }
    auto operator<=>(const EntityUid& other) const { return _uid <=> other._uid; }

    explicit operator int32_t() const { return _uid; }
    
    std::string ToString() const { return std::to_string(_uid); }
};

inline const EntityUid EntityUid::Invalid = EntityUid(0);
inline const EntityUid EntityUid::FirstUid = EntityUid(1);

} // namespace OpenNefia::Core::GameObjects

namespace std {
    template<>
    struct hash<OpenNefia::Core::GameObjects::EntityUid> {
        size_t operator()(const OpenNefia::Core::GameObjects::EntityUid& uid) const {
            return hash<int32_t>()(uid._uid);
        }
    };
}
