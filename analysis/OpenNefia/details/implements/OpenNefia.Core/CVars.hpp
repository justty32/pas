#pragma once

#include "Configuration/CVarDef.hpp"
#include <string>

namespace OpenNefia::Core {

using namespace Configuration;

/**
 * @brief Global configuration variables.
 * Ported from CVars.cs.
 */
class CVars {
public:
    CVars() = delete;

    /*
     * Message
     */
    inline static const auto MessageFade = CVarDef<int>::Create("message.fade", 50, CVarFlags::Archive);

    /*
     * Log
     */
    inline static const auto LogEnabled = CVarDef<bool>::Create("log.enabled", true, CVarFlags::Archive);
    inline static const auto LogPath = CVarDef<std::string>::Create("log.path", "logs", CVarFlags::Archive);
    inline static const auto LogFormat = CVarDef<std::string>::Create("log.format", "log_%(date)s-T%(time)s.txt", CVarFlags::Archive);
    // Note: LogLevel would need LogLevel enum to be ported first.
    // inline static const auto LogLevel = CVarDef<LogLevel>::Create("log.level", LogLevel::Info, CVarFlags::Archive);

    /*
     * Display
     */
    inline static const auto DisplayVSync = CVarDef<bool>::Create("display.vsync", true, CVarFlags::Archive);
    inline static const auto DisplayDisplayNumber = CVarDef<int>::Create("display.displaynumber", 0, CVarFlags::Archive);
    inline static const auto DisplayWidth = CVarDef<int>::Create("display.width", 800, CVarFlags::Archive);
    inline static const auto DisplayHeight = CVarDef<int>::Create("display.height", 600, CVarFlags::Archive);
    inline static const auto DisplayUIScale = CVarDef<float>::Create("display.uiScale", 1.0f, CVarFlags::Archive);
    inline static const auto DisplayHighDPI = CVarDef<bool>::Create("display.hidpi", false, CVarFlags::Archive);
    inline static const auto DisplayTitle = CVarDef<std::string>::Create("display.title", "OpenNefia");

    /*
     * Anime
     */
    inline static const auto AnimeWait = CVarDef<float>::Create("anime.wait", 20.0f);

    /*
     * Audio
     */
    inline static const auto AudioMusic = CVarDef<bool>::Create("audio.music", true, CVarFlags::Archive);
    inline static const auto AudioMidiDevice = CVarDef<int>::Create("audio.mididevice", 0, CVarFlags::Archive);
    inline static const auto AudioSound = CVarDef<bool>::Create("audio.sound", true, CVarFlags::Archive);
    inline static const auto AudioPositionalAudio = CVarDef<bool>::Create("audio.positionalaudio", true, CVarFlags::Archive);

    /*
     * Language
     */
    inline static const auto LanguageLanguage = CVarDef<std::string>::Create("language.language", "en_US", CVarFlags::Archive);

    /*
     * Debug
     */
    inline static const auto DebugTargetFps = CVarDef<int>::Create("debug.target_fps", 60, CVarFlags::Archive);
};

} // namespace OpenNefia::Core
