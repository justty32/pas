#pragma once

#include <string>

namespace OpenNefia::Core::Configuration {

enum class CVarFlags : int {
    None = 0,
    Archive = 1 << 0,
    Internal = 1 << 1,
    Server = 1 << 2,
    Client = 1 << 3,
    Cheat = 1 << 4,
};

inline CVarFlags operator|(CVarFlags a, CVarFlags b) {
    return static_cast<CVarFlags>(static_cast<int>(a) | static_cast<int>(b));
}

template <typename T>
class CVarDef {
public:
    const std::string Name;
    const T DefaultValue;
    const CVarFlags Flags;

    CVarDef(std::string name, T defaultValue, CVarFlags flags = CVarFlags::None)
        : Name(std::move(name)), DefaultValue(defaultValue), Flags(flags) {}

    static CVarDef<T> Create(std::string name, T defaultValue, CVarFlags flags = CVarFlags::None) {
        return CVarDef<T>(name, defaultValue, flags);
    }
};

} // namespace OpenNefia::Core::Configuration
