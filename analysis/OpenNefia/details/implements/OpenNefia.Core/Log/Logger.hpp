#pragma once

#include "ILogManager.hpp"
#include "../IoC/IoCManager.hpp"
#include <string_view>

namespace OpenNefia::Core::Log {

/**
 * @brief Static logging API front end.
 * Ported from Logger.cs.
 */
class Logger {
public:
    Logger() = delete;

    static ISawmill& GetSawmill(std::string_view name) {
        return IoC::IoCManager::Resolve<ILogManager>()->GetSawmill(name);
    }

    static void Log(LogLevel level, std::string_view message) {
        IoC::IoCManager::Resolve<ILogManager>()->GetRootSawmill().Log(level, message);
    }

    static void Info(std::string_view message) { Log(LogLevel::Info, message); }
    static void Debug(std::string_view message) { Log(LogLevel::Debug, message); }
    static void Warning(std::string_view message) { Log(LogLevel::Warning, message); }
    static void Error(std::string_view message) { Log(LogLevel::Error, message); }
    static void Fatal(std::string_view message) { Log(LogLevel::Fatal, message); }

    static void LogS(std::string_view sawmill, LogLevel level, std::string_view message) {
        GetSawmill(sawmill).Log(level, message);
    }

    static void InfoS(std::string_view sawmill, std::string_view message) { LogS(sawmill, LogLevel::Info, message); }
    static void DebugS(std::string_view sawmill, std::string_view message) { LogS(sawmill, LogLevel::Debug, message); }
    static void WarningS(std::string_view sawmill, std::string_view message) { LogS(sawmill, LogLevel::Warning, message); }
    static void ErrorS(std::string_view sawmill, std::string_view message) { LogS(sawmill, LogLevel::Error, message); }
    static void FatalS(std::string_view sawmill, std::string_view message) { LogS(sawmill, LogLevel::Fatal, message); }
};

} // namespace OpenNefia::Core::Log
