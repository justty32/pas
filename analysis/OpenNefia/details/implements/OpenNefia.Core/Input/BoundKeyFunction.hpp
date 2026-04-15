#pragma once

#include <string>
#include <compare>

namespace OpenNefia::Core::Input {

struct BoundKeyFunction {
    std::string FunctionName;

    BoundKeyFunction() = default;
    BoundKeyFunction(const char* name) : FunctionName(name) {}
    BoundKeyFunction(std::string name) : FunctionName(std::move(name)) {}

    bool operator==(const BoundKeyFunction& other) const {
        return FunctionName == other.FunctionName;
    }

    auto operator<=>(const BoundKeyFunction& other) const {
        return FunctionName <=> other.FunctionName;
    }
};

} // namespace OpenNefia::Core::Input

namespace std {
    template<>
    struct hash<OpenNefia::Core::Input::BoundKeyFunction> {
        size_t operator()(const OpenNefia::Core::Input::BoundKeyFunction& k) const {
            return hash<string>()(k.FunctionName);
        }
    };
}
