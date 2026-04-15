#pragma once

#include <cstdint>

namespace OpenNefia::Core::Log {

/**
 * @brief Log levels for the logging system.
 * Ported from LogLevel.cs.
 */
enum class LogLevel : uint8_t {
    Verbose = 0,
    Debug = 1,
    Info = 2,
    Warning = 3,
    Error = 4,
    Fatal = 5
};

} // namespace OpenNefia::Core::Log
