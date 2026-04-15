#pragma once

#include "LocaleKey.hpp"

namespace OpenNefia::Core::Locale {

class ILocalizable {
public:
    virtual ~ILocalizable() = default;

    virtual void Localize(const LocaleKey& key) = 0;
};

} // namespace OpenNefia::Core::Locale
