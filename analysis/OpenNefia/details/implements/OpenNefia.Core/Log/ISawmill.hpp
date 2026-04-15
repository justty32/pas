#pragma once

#include "LogLevel.hpp"
#include <string>
#include <string_view>
#include <exception>

namespace OpenNefia::Core::Log {

/**
 * @brief Interface for a sawmill.
 * Ported from ISawmill.cs.
 */
class ISawmill {
public:
    virtual ~ISawmill() = default;

    virtual std::string_view GetName() const = 0;
    virtual LogLevel GetLevel() const = 0;
    virtual void SetLevel(LogLevel level) = 0;

    virtual void Log(LogLevel level, std::string_view message) = 0;
    // Note: C++ variadic templates can handle the params args part.
    virtual void Log(LogLevel level, const std::exception* ex, std::string_view message) = 0;
};

} // namespace OpenNefia::Core::Log
