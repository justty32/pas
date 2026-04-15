#pragma once

#include <string>

namespace OpenNefia::Core::Locale {

struct LocaleKey {
    std::string Key;

    LocaleKey() = default;
    LocaleKey(const char* key) : Key(key) {}
    LocaleKey(std::string key) : Key(std::move(key)) {}

    operator std::string() const { return Key; }
};

} // namespace OpenNefia::Core::Locale
