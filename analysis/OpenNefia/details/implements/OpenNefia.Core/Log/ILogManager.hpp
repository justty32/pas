#pragma once

#include "ISawmill.hpp"
#include <memory>

namespace OpenNefia::Core::Log {

/**
 * @brief Interface for the LogManager.
 * Ported from ILogManager.cs.
 */
class ILogManager {
public:
    virtual ~ILogManager() = default;

    virtual ISawmill& GetRootSawmill() = 0;
    virtual ISawmill& GetSawmill(std::string_view name) = 0;
};

} // namespace OpenNefia::Core::Log
